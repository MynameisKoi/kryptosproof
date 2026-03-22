"""
Orchestrator Agent
Top-level coordinator: drives red team → blue team → report cycle.
"""
from dataclasses import dataclass
from pathlib import Path
import json

from pydantic_ai import Agent, RunContext

from schemas import (
    AttackScriptResult,
    ExecutionResult,
    FixScriptResult,
    TestResult,
    SecurityAuditReport,
)
from ai.agents.red_team.attack_script import attack_script_agent, AttackScriptDeps
from ai.agents.red_team.execution import execution_agent, ExecutionDeps
from ai.agents.blue_team.fix_script import fix_script_agent, FixScriptDeps
from ai.agents.blue_team.testing import testing_agent, TestingDeps

_PROMPT = (Path(__file__).parent.parent / "prompt" / "orchestrator.md").read_text()


@dataclass
class OrchestratorDeps:
    target_url: str


orchestrator_agent = Agent(
    model="anthropic:claude-opus-4-6",
    deps_type=OrchestratorDeps,
    result_type=SecurityAuditReport,
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
    attack: AttackScriptResult = attack_result.data

    # Step 2: Execute in sandbox
    exec_result = await execution_agent.run(
        f"Execute this {attack.vulnerability_type} attack script against {target_url}",
        deps=ExecutionDeps(attack_script=attack, target_url=target_url),
    )
    execution: ExecutionResult = exec_result.data

    # Attach the attack script to the execution result for blue team use
    execution_dict = execution.model_dump()
    execution_dict["_attack_script"] = attack.model_dump()

    return json.dumps(execution_dict)


@orchestrator_agent.tool
async def run_blue_team(ctx: RunContext[OrchestratorDeps], execution_result_json: str) -> str:
    """
    Run a full blue team cycle: generate fix and verify it eliminates the vulnerability.
    Returns JSON-serialized TestResult.
    """
    target_url = ctx.deps.target_url
    data = json.loads(execution_result_json)

    attack_data = data.pop("_attack_script", {})
    execution = ExecutionResult(**data)
    attack = AttackScriptResult(**attack_data) if attack_data else None

    # Step 1: Generate fix
    fix_result = await fix_script_agent.run(
        f"Generate fixes for confirmed vulnerabilities: {execution.vulnerabilities_confirmed}",
        deps=FixScriptDeps(execution_result=execution),
    )
    fix: FixScriptResult = fix_result.data

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
        test: TestResult = test_result.data
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
    return json.dumps(result)


async def run_audit(target_url: str) -> SecurityAuditReport:
    """Entry point: run a full security audit against target_url."""
    result = await orchestrator_agent.run(
        f"Run a complete security audit against: {target_url}. "
        "Test for SQL Injection, XSS, Command Injection, Path Traversal, and CSRF. "
        "After red team, apply blue team fixes and verify each vulnerability is patched.",
        deps=OrchestratorDeps(target_url=target_url),
    )
    return result.data
