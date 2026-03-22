"""
Blue Team — Testing Agent
Re-runs the original attack scripts after patching to verify vulnerabilities are resolved.
"""
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import Agent, RunContext

from schemas import AttackScriptResult, FixScriptResult, TestResult
from config import settings
from tools.sandbox import create_sandbox, run_script_string, destroy_sandbox

_PROMPT = (Path(__file__).parent.parent.parent / "prompt" / "blue_team" / "testing.md").read_text()


@dataclass
class TestingDeps:
    attack_script: AttackScriptResult
    fix_result: FixScriptResult
    target_url: str


testing_agent = Agent(
    model="anthropic:claude-opus-4-6",
    deps_type=TestingDeps,
    result_type=TestResult,
    system_prompt=_PROMPT,
)


@testing_agent.tool
async def create_verification_sandbox(ctx: RunContext[TestingDeps]) -> str:
    """Create a fresh sandbox container for post-patch verification."""
    container_id = await create_sandbox(
        image=settings.sandbox_image,
        network=settings.sandbox_network,
    )
    return container_id


@testing_agent.tool
async def rerun_attack(ctx: RunContext[TestingDeps], container_id: str) -> dict:
    """Re-run the original attack script against the (now patched) target."""
    result = await run_script_string(
        container_id=container_id,
        script=ctx.deps.attack_script.script,
        timeout=settings.sandbox_timeout,
    )
    return {
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "crash_detected": result.crash_detected,
        "vuln_markers_found": "[VULN]" in result.stdout,
    }


@testing_agent.tool
async def teardown_verification_sandbox(ctx: RunContext[TestingDeps], container_id: str) -> str:
    """Destroy the verification sandbox container."""
    await destroy_sandbox(container_id)
    return f"Verification container {container_id} destroyed."


@testing_agent.tool
async def get_fix_summary(ctx: RunContext[TestingDeps]) -> dict:
    """Return the fix script details for reference during verification."""
    fr = ctx.deps.fix_result
    return {
        "vulnerability_type": fr.vulnerability_type,
        "fix_description": fr.fix_description,
        "patches_count": len(fr.patches),
        "patch_files": [p.file_path for p in fr.patches],
    }
