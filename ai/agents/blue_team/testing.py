"""
Blue Team — Testing Agent
Re-runs the original attack scripts after patching to verify vulnerabilities are resolved.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from pydantic_ai import Agent, RunContext

from config import settings
from ai.tool_logging import tool_return
from schemas import AttackScriptResult, FixScriptResult, TestResult
from tools.sandbox import create_sandbox, run_script_string, destroy_sandbox

_PROMPT = (Path(__file__).parent.parent.parent / "prompt" / "blue_team" / "testing.md").read_text()


@dataclass
class TestingDeps:
    """Injected deps for verification runs (not a pytest class — name matches `Test*`)."""

    __test__: ClassVar[bool] = False

    attack_script: AttackScriptResult
    fix_result: FixScriptResult
    target_url: str


testing_agent = Agent(
    model=settings.model,
    deps_type=TestingDeps,
    output_type=TestResult,
    system_prompt=_PROMPT,
)


@testing_agent.tool
async def create_verification_sandbox(ctx: RunContext[TestingDeps]) -> dict:
    """Create a fresh sandbox container for post-patch verification."""
    container_id = await create_sandbox(
        image=settings.sandbox_image,
        network=settings.sandbox_network,
    )
    return tool_return("create_verification_sandbox", {"container_id": container_id}, detail=container_id)


@testing_agent.tool
async def rerun_attack(ctx: RunContext[TestingDeps], container_id: str) -> dict:
    """Re-run the original attack script against the (now patched) target."""
    result = await run_script_string(
        container_id=container_id,
        script=ctx.deps.attack_script.script,
        timeout=settings.sandbox_timeout,
    )
    return tool_return(
        "rerun_attack",
        {
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "crash_detected": result.crash_detected,
            "vuln_markers_found": "[VULN]" in result.stdout,
        },
        detail=f"container_id={container_id}",
    )


@testing_agent.tool
async def teardown_verification_sandbox(ctx: RunContext[TestingDeps], container_id: str) -> dict:
    """Destroy the verification sandbox container."""
    await destroy_sandbox(container_id)
    msg = f"Verification container {container_id} destroyed."
    return tool_return(
        "teardown_verification_sandbox",
        {"message": msg, "container_id": container_id},
        detail=container_id,
    )


@testing_agent.tool
async def get_fix_summary(ctx: RunContext[TestingDeps]) -> dict:
    """Return the fix script details for reference during verification."""
    fr = ctx.deps.fix_result
    return tool_return(
        "get_fix_summary",
        {
            "vulnerability_type": fr.vulnerability_type,
            "fix_description": fr.fix_description,
            "patches_count": len(fr.patches),
            "patch_files": [p.file_path for p in fr.patches],
        },
        detail=fr.vulnerability_type,
    )
