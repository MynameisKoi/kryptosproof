"""
Blue Team — Fix Script Agent
Analyzes red team execution results and generates patches for confirmed vulnerabilities.
"""
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import Agent, RunContext

from schemas import ExecutionResult, FixScriptResult

_PROMPT = (Path(__file__).parent.parent.parent / "prompt" / "blue_team" / "fix_script.md").read_text()


@dataclass
class FixScriptDeps:
    execution_result: ExecutionResult


fix_script_agent = Agent(
    model="anthropic:claude-opus-4-6",
    deps_type=FixScriptDeps,
    result_type=FixScriptResult,
    system_prompt=_PROMPT,
)


@fix_script_agent.tool
async def get_execution_details(ctx: RunContext[FixScriptDeps]) -> dict:
    """Retrieve full execution result details: logs, confirmed vulnerabilities, and sandbox info."""
    er = ctx.deps.execution_result
    return {
        "attack_type": er.attack_type,
        "target_url": er.target_url,
        "status": er.status,
        "vulnerabilities_confirmed": er.vulnerabilities_confirmed,
        "error_logs": er.error_logs,
        "stdout": er.stdout,
        "stderr": er.stderr,
        "crash_detected": er.crash_detected,
        "raw_responses": er.raw_responses,
    }
