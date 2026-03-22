"""
Red Team — Attack Script Agent
Generates targeted web exploit scripts for a given URL.
"""
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import Agent, RunContext

from schemas import AttackScriptResult
from tools.web_recon import probe_endpoints, get_security_headers, detect_technologies, get_forms

_PROMPT = (Path(__file__).parent.parent.parent / "prompt" / "red_team" / "attack_script.md").read_text()


@dataclass
class AttackScriptDeps:
    target_url: str


attack_script_agent = Agent(
    model="anthropic:claude-opus-4-6",
    deps_type=AttackScriptDeps,
    result_type=AttackScriptResult,
    system_prompt=_PROMPT,
)


@attack_script_agent.tool
async def probe_target_endpoints(ctx: RunContext[AttackScriptDeps]) -> list[dict]:
    """Probe common endpoints on the target and return their status/headers."""
    return await probe_endpoints(ctx.deps.target_url)


@attack_script_agent.tool
async def check_security_headers(ctx: RunContext[AttackScriptDeps]) -> dict:
    """Return security-relevant HTTP response headers for the target."""
    return await get_security_headers(ctx.deps.target_url)


@attack_script_agent.tool
async def detect_target_technologies(ctx: RunContext[AttackScriptDeps]) -> dict:
    """Detect server technology and frameworks used by the target."""
    return await detect_technologies(ctx.deps.target_url)


@attack_script_agent.tool
async def extract_forms(ctx: RunContext[AttackScriptDeps], path: str = "/") -> list[dict]:
    """Extract HTML forms from a specific path on the target (useful for CSRF/injection)."""
    url = ctx.deps.target_url.rstrip("/") + path
    return await get_forms(url)
