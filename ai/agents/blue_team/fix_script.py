"""
Blue Team — Fix Script Agent
Analyzes red team execution results and generates patches for confirmed vulnerabilities.
"""
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import Agent, RunContext

from config import settings
from ai.tool_logging import tool_return
from schemas import ExecutionResult, FixScriptResult
from tools.gitleaks import run_gitleaks

_PROMPT = (Path(__file__).parent.parent.parent / "prompt" / "blue_team" / "fix_script.md").read_text()


@dataclass
class FixScriptDeps:
    execution_result: ExecutionResult
    source_repo_path: str | None = None


fix_script_agent = Agent(
    model=settings.model,
    deps_type=FixScriptDeps,
    output_type=FixScriptResult,
    system_prompt=_PROMPT,
)


@fix_script_agent.tool
async def get_execution_details(ctx: RunContext[FixScriptDeps]) -> dict:
    """Retrieve full execution result details: logs, confirmed vulnerabilities, and sandbox info."""
    er = ctx.deps.execution_result
    return tool_return(
        "get_execution_details",
        {
            "attack_type": er.attack_type,
            "target_url": er.target_url,
            "status": er.status,
            "vulnerabilities_confirmed": er.vulnerabilities_confirmed,
            "error_logs": er.error_logs,
            "stdout": er.stdout,
            "stderr": er.stderr,
            "crash_detected": er.crash_detected,
            "raw_responses": er.raw_responses,
        },
        detail=er.target_url,
    )


@fix_script_agent.tool
async def scan_secrets_with_gitleaks(ctx: RunContext[FixScriptDeps]) -> dict:
    """
    Run Gitleaks on SOURCE_REPO_PATH (configured via environment / orchestrator deps).
    Use to find hardcoded keys before recommending credential rotation.
    """
    path = ctx.deps.source_repo_path
    if not path:
        return tool_return(
            "scan_secrets_with_gitleaks",
            {
                "available": False,
                "error": "No source_repo_path — set SOURCE_REPO_PATH to a local clone of the app under review.",
            },
            detail="no path",
        )
    data = await run_gitleaks(path)
    return tool_return("scan_secrets_with_gitleaks", data, detail=path)
