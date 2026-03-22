"""
Red Team — Execution Agent
Runs attack scripts inside an isolated Docker sandbox and captures results.
"""
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import Agent, RunContext

from schemas import AttackScriptResult, ExecutionResult
from config import settings
from tools.sandbox import create_sandbox, run_script_string, destroy_sandbox

_PROMPT = (Path(__file__).parent.parent.parent / "prompt" / "red_team" / "execution.md").read_text()


@dataclass
class ExecutionDeps:
    attack_script: AttackScriptResult
    target_url: str


execution_agent = Agent(
    model="anthropic:claude-opus-4-6",
    deps_type=ExecutionDeps,
    result_type=ExecutionResult,
    system_prompt=_PROMPT,
)


@execution_agent.tool
async def create_attack_sandbox(ctx: RunContext[ExecutionDeps]) -> str:
    """Spin up an isolated Docker container on the sandbox network. Returns container ID."""
    container_id = await create_sandbox(
        image=settings.sandbox_image,
        network=settings.sandbox_network,
    )
    return container_id


@execution_agent.tool
async def run_attack_script(ctx: RunContext[ExecutionDeps], container_id: str) -> dict:
    """Execute the attack script inside the sandbox container. Returns stdout, stderr, exit_code."""
    result = await run_script_string(
        container_id=container_id,
        script=ctx.deps.attack_script.script,
        timeout=settings.sandbox_timeout,
    )
    return {
        "container_id": result.container_id,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "crash_detected": result.crash_detected,
    }


@execution_agent.tool
async def teardown_sandbox(ctx: RunContext[ExecutionDeps], container_id: str) -> str:
    """Stop and remove the sandbox container after execution."""
    await destroy_sandbox(container_id)
    return f"Container {container_id} destroyed."
