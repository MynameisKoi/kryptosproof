"""
Red Team — Attack Script Agent
Generates targeted web exploit scripts for a given URL.
"""
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelRetry

from config import settings
from schemas import AttackScriptResult
from tools.attack_validation import AttackScriptValidationError, validate_attack_script_result
from tools.payloads_pat import read_payload_lines, search_payload_files
from tools.red_team import run_ffuf_directory_fuzz, run_nuclei_scan, run_sqlmap_probe
from tools.web_recon import probe_endpoints, get_security_headers, detect_technologies, get_forms, authenticate_to_target
from tools.zap_api import zap_active_scan, zap_ping, zap_spider_and_alerts

_PROMPT = (Path(__file__).parent.parent.parent / "prompt" / "red_team" / "attack_script.md").read_text()


@dataclass
class AttackScriptDeps:
    target_url: str


attack_script_agent = Agent(
    model=settings.model,
    deps_type=AttackScriptDeps,
    output_type=AttackScriptResult,
    system_prompt=_PROMPT,
    retries=3,
)


@attack_script_agent.output_validator
def validate_attack_output(ctx: RunContext[AttackScriptDeps], data: AttackScriptResult) -> AttackScriptResult:
    try:
        validate_attack_script_result(data, ctx.deps.target_url)
    except AttackScriptValidationError as e:
        raise ModelRetry(str(e)) from e
    return data


@attack_script_agent.tool
async def authenticate(ctx: RunContext[AttackScriptDeps]) -> dict:
    """
    Detect whether the target requires authentication and attempt login with common credentials.
    Call this FIRST before generating the attack script.
    Returns login URL, form fields, session cookies, and a note explaining that the attack
    script must reproduce the login sequence itself (the sandbox does not share this session).
    """
    return await authenticate_to_target(ctx.deps.target_url)


@attack_script_agent.tool
async def probe_target_endpoints(ctx: RunContext[AttackScriptDeps]) -> dict:
    """Probe common endpoints on the target; result includes `endpoints` and human-readable `logs`."""
    return await probe_endpoints(ctx.deps.target_url)


@attack_script_agent.tool
async def check_security_headers(ctx: RunContext[AttackScriptDeps]) -> dict:
    """Return security-relevant HTTP response headers for the target plus `logs`."""
    return await get_security_headers(ctx.deps.target_url)


@attack_script_agent.tool
async def detect_target_technologies(ctx: RunContext[AttackScriptDeps]) -> dict:
    """Detect server technology and frameworks used by the target; includes `logs`."""
    return await detect_technologies(ctx.deps.target_url)


@attack_script_agent.tool
async def extract_forms(ctx: RunContext[AttackScriptDeps], path: str = "/") -> dict:
    """Extract HTML forms from a path; result includes `forms` and `logs`."""
    url = ctx.deps.target_url.rstrip("/") + path
    return await get_forms(url)


@attack_script_agent.tool
async def nuclei_scan(
    ctx: RunContext[AttackScriptDeps],
    tags: str | None = None,
    severity: str | None = None,
) -> dict:
    """
    Run Nuclei template scan against the target URL (JSON findings).
    Optional: comma-separated template tags (e.g. cve,tech) and severity filter.
    """
    return await run_nuclei_scan(ctx.deps.target_url, tags=tags, severity=severity)


@attack_script_agent.tool
async def ffuf_fuzz_directories(
    ctx: RunContext[AttackScriptDeps],
    wordlist_path: str | None = None,
) -> dict:
    """
    FFUF: fuzz path segments from the default wordlist (or a custom wordlist path).
    """
    return await run_ffuf_directory_fuzz(ctx.deps.target_url, wordlist_path=wordlist_path)


@attack_script_agent.tool
async def sqlmap_scan(ctx: RunContext[AttackScriptDeps], url_with_parameter: str) -> dict:
    """
    Run sqlmap against a full URL that includes at least one query parameter to test (e.g. ...?id=1).
    Pass the complete URL string; do not pass the bare site root.
    """
    return await run_sqlmap_probe(url_with_parameter)


@attack_script_agent.tool
async def pat_search_payload_files(ctx: RunContext[AttackScriptDeps], keyword: str) -> dict:
    """
    Search the local PayloadsAllTheThings tree (PAYLOADS_ROOT) for .txt paths matching keyword (e.g. sqli, xss).
    Clone the repo first if this returns unavailable.
    """
    return search_payload_files(keyword)


@attack_script_agent.tool
async def pat_read_payload_lines(
    ctx: RunContext[AttackScriptDeps],
    relative_path: str,
    max_lines: int = 40,
) -> dict:
    """Read sanitized payload lines from a file under PAYLOADS_ROOT (path from pat_search_payload_files)."""
    return read_payload_lines(relative_path, max_lines=max_lines)


@attack_script_agent.tool
async def zap_status(ctx: RunContext[AttackScriptDeps]) -> dict:
    """Check whether OWASP ZAP JSON API is reachable (ZAP_PROXY_URL)."""
    return await zap_ping()


@attack_script_agent.tool
async def zap_spider_scan(ctx: RunContext[AttackScriptDeps]) -> dict:
    """
    Run ZAP spider against the audit target, then return passive alerts.
    Requires ZAP running and able to reach the target URL (same Docker network if applicable).
    """
    return await zap_spider_and_alerts(ctx.deps.target_url)


@attack_script_agent.tool
async def zap_aggressive_active_scan(ctx: RunContext[AttackScriptDeps]) -> dict:
    """
    Start ZAP active scan against the target — destructive; only for authorized test environments.
    """
    return await zap_active_scan(ctx.deps.target_url)
