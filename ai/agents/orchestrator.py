"""
Orchestrator Agent
Top-level coordinator: drives red team → blue team → report cycle.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
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
from tools.attack_validation import AttackScriptValidationError, validate_attack_script_result
from tools.execution_pipeline import run_attack_execution
from ai.agents.blue_team.fix_script import fix_script_agent, FixScriptDeps
from ai.agents.blue_team.testing import testing_agent, TestingDeps
from config import settings

_PROMPT = (Path(__file__).parent.parent / "prompt" / "orchestrator.md").read_text()


@dataclass
class OrchestratorDeps:
    target_url: str
    execution_results: list[dict] = field(default_factory=list)
    on_red_team_start: Callable[[str], None] | None = field(default=None)
    on_red_team_end: Callable[[str, dict], None] | None = field(default=None)
    on_blue_team_start: Callable[[], None] | None = field(default=None)
    on_blue_team_end: Callable[[dict], None] | None = field(default=None)


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
    if ctx.deps.on_red_team_start:
        ctx.deps.on_red_team_start(vulnerability_focus)

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

    # Store in deps so run_blue_team can read it directly (bypasses LLM JSON passing)
    execution_dict = execution.model_dump()
    execution_dict["_attack_script"] = attack.model_dump()
    ctx.deps.execution_results.append(execution_dict)

    if ctx.deps.on_red_team_end:
        ctx.deps.on_red_team_end(vulnerability_focus, execution_dict)

    return json.dumps(execution_dict)


@orchestrator_agent.tool
async def run_blue_team(ctx: RunContext[OrchestratorDeps], execution_result_json: str) -> str:
    """
    Run a full blue team cycle: generate fix and verify it eliminates the vulnerability.
    Returns JSON-serialized TestResult.
    """
    if ctx.deps.on_blue_team_start:
        ctx.deps.on_blue_team_start()

    target_url = ctx.deps.target_url

    # Read from deps directly — avoids LLM truncating/losing the JSON
    if ctx.deps.execution_results:
        data = ctx.deps.execution_results.pop(0)
    else:
        data = json.loads(execution_result_json)

    attack_data = data.pop("_attack_script", {})
    execution = ExecutionResult(**data)
    attack = AttackScriptResult(**attack_data) if attack_data else None

    # Skip blue team if nothing was confirmed
    if not execution.vulnerabilities_confirmed:
        return json.dumps({"skipped": True, "reason": "no vulnerabilities confirmed — blue team not needed"})

    # Step 1: Generate fix (retry once if verification fails)
    _MAX_FIX_ATTEMPTS = 2
    fix: FixScriptResult | None = None
    test: TestResult | None = None

    for attempt in range(_MAX_FIX_ATTEMPTS):
        retry_context = (
            ""
            if attempt == 0
            else (
                f"\n\nPrevious fix attempt failed verification. "
                f"Residual vulnerabilities: {test.residual_vulnerabilities}. "
                f"Recommendation: {test.recommendation}. "
                "Please revise the fix to address these gaps."
            )
        )
        fix_result = await fix_script_agent.run(
            f"Generate fixes for confirmed vulnerabilities: {execution.vulnerabilities_confirmed}{retry_context}",
            deps=FixScriptDeps(
                execution_result=execution,
                source_repo_path=settings.source_repo_path,
            ),
        )
        fix = fix_result.output

        if not attack:
            break

        # Step 2: Verify fix
        test_result = await testing_agent.run(
            f"Verify the {fix.vulnerability_type} fix works by re-running the original attack",
            deps=TestingDeps(
                attack_script=attack,
                fix_result=fix,
                target_url=target_url,
            ),
        )
        test = test_result.output

        if test.overall_patched:
            break  # success — no retry needed

    if not attack or test is None:
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

    if ctx.deps.on_blue_team_end:
        ctx.deps.on_blue_team_end(result)

    return json.dumps(result)


async def run_audit(target_url: str) -> SecurityAuditReport:
    """Entry point: run a full security audit against target_url."""
    result = await orchestrator_agent.run(
        f"Run a complete security audit against: {target_url}. "
        "Test for SQL Injection, XSS, Command Injection, Path Traversal, and CSRF. "
        "After red team, apply blue team fixes and verify each vulnerability is patched.",
        deps=OrchestratorDeps(target_url=target_url),
    )
    return result.output
