"""
Orchestrator Agent
Top-level coordinator: drives red team → blue team → report cycle.
"""
from dataclasses import dataclass
from pathlib import Path
import json

from pydantic_ai import Agent, RunContext

from config import settings
from ai.tool_logging import tool_return_json
from schemas import (
    AttackScriptResult,
    ExecutionResult,
    FixScriptResult,
    TestResult,
    SecurityAuditReport,
)
from ai.agents.red_team.attack_script import attack_script_agent, AttackScriptDeps
from tools.attack_validation import AttackScriptValidationError, validate_attack_script_result
from tools.execution_pipeline import run_attack_execution
from ai.agents.blue_team.fix_script import fix_script_agent, FixScriptDeps
from ai.agents.blue_team.testing import testing_agent, TestingDeps

_PROMPT = (Path(__file__).parent.parent / "prompt" / "orchestrator.md").read_text()


@dataclass
class OrchestratorDeps:
    target_url: str


orchestrator_agent = Agent(
    model=settings.model,
    deps_type=OrchestratorDeps,
    output_type=SecurityAuditReport,
    system_prompt=_PROMPT,
)


@orchestrator_agent.tool
async def run_red_team(ctx: RunContext[OrchestratorDeps], vulnerability_focus: str) -> str:
    """
    Run a full red team cycle for a specific vulnerability type.
    Returns JSON-serialized ExecutionResult with confirmed vulnerabilities and logs.
    """
    target_url = ctx.deps.target_url

    # Step 1: Generate attack script
    attack_result = await attack_script_agent.run(
        f"Generate a {vulnerability_focus} attack script for target: {target_url}",
        deps=AttackScriptDeps(target_url=target_url),
    )
    attack: AttackScriptResult = attack_result.output

    try:
        validate_attack_script_result(attack, target_url)
    except AttackScriptValidationError as e:
        raise RuntimeError(f"Attack script failed final validation: {e}") from e

    # Step 2: Execute in sandbox (deterministic — no LLM)
    execution: ExecutionResult = await run_attack_execution(attack, target_url)

    # Attach the attack script to the execution result for blue team use
    execution_dict = execution.model_dump()
    execution_dict["_attack_script"] = attack.model_dump()

    return tool_return_json(
        "run_red_team",
        execution_dict,
        detail=f"vulnerability_focus={vulnerability_focus}",
    )


@orchestrator_agent.tool
async def run_blue_team(ctx: RunContext[OrchestratorDeps], execution_result_json: str) -> str:
    """
    Run a full blue team cycle: generate fix and verify it eliminates the vulnerability.
    Returns JSON-serialized TestResult.
    """
    target_url = ctx.deps.target_url
    data = json.loads(execution_result_json)
    data.pop("tool_log", None)

    attack_data = data.pop("_attack_script", {})
    execution = ExecutionResult(**data)
    attack = AttackScriptResult(**attack_data) if attack_data else None

    # Step 1: Generate fix
    fix_result = await fix_script_agent.run(
        f"Generate fixes for confirmed vulnerabilities: {execution.vulnerabilities_confirmed}",
        deps=FixScriptDeps(
            execution_result=execution,
            source_repo_path=settings.source_repo_path,
        ),
    )
    fix: FixScriptResult = fix_result.output

    # Step 2: Verify fix (re-run attack)
    if attack:
        test_result = await testing_agent.run(
            f"Verify the {fix.vulnerability_type} fix works by re-running the original attack",
            deps=TestingDeps(
                attack_script=attack,
                fix_result=fix,
                target_url=target_url,
            ),
        )
        test: TestResult = test_result.output
    else:
        # No attack script available — create a minimal test result
        test = TestResult(
            overall_patched=False,
            checks=[],
            status="failed",
            residual_vulnerabilities=execution.vulnerabilities_confirmed,
            recommendation="Could not re-run attack — manual verification required.",
            retest_stdout="",
            retest_stderr="",
        )

    result = {
        "fix": fix.model_dump(),
        "test": test.model_dump(),
    }
    return tool_return_json("run_blue_team", result, detail=f"target={target_url}")


async def run_audit(target_url: str) -> SecurityAuditReport:
    """Entry point: run a full security audit against target_url."""
    result = await orchestrator_agent.run(
        f"Run a complete security audit against: {target_url}. "
        "Test for SQL Injection, XSS, Command Injection, Path Traversal, and CSRF. "
        "After red team, apply blue team fixes and verify each vulnerability is patched.",
        deps=OrchestratorDeps(target_url=target_url),
    )
    return result.output
