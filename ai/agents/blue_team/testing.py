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
    model=settings.model,
    deps_type=TestingDeps,
    output_type=TestResult,
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
def analyze_fix_coverage(ctx: RunContext[TestingDeps]) -> dict:
    """
    Statically analyze the fix_script to verify it contains the correct defensive patterns
    for the confirmed vulnerability type. Use this as the primary verification signal
    since the live target (DVWA) cannot be patched mid-audit.
    """
    fr = ctx.deps.fix_result
    script = (fr.fix_script or "").lower()
    patches_text = " ".join(
        f"{p.patched_snippet}" for p in fr.patches
    ).lower()
    combined = script + " " + patches_text
    vuln = fr.vulnerability_type.lower()

    _PATTERNS: dict[str, list[str]] = {
        "sql injection":         ["parameterized", "prepared statement", "cursor.execute", "execute(", "?", "%s", "sqlalchemy", "orm", "bindparam"],
        "xss":                   ["html.escape", "markupsafe", "escape(", "content-security-policy", "csp", "htmlspecialchars", "bleach", "sanitize"],
        "command injection":     ["shlex.quote", "shell=false", "shell = false", "allowlist", "whitelist", "subprocess.run([", "popen(["],
        "path traversal":        ["os.path.realpath", "os.path.abspath", "normpath", "resolve()", "startswith", "basedir"],
        "csrf":                  ["csrf_token", "x-csrf-token", "samesite", "origin header", "referer header", "double submit"],
        "broken authentication": ["bcrypt", "argon2", "pbkdf2", "secrets.token", "account lockout", "rate_limit", "ratelimit", "max_attempts"],
        "ssrf":                  ["allowlist", "whitelist", "private", "loopback", "127.0.0.1", "urlparse", "socket.gethostbyname"],
    }

    matched: list[str] = []
    for key, patterns in _PATTERNS.items():
        if key in vuln or any(word in vuln for word in key.split()):
            matched = [p for p in patterns if p in combined]
            break

    score = min(100, len(matched) * 25)
    return {
        "vulnerability_type": fr.vulnerability_type,
        "matched_defensive_patterns": matched,
        "coverage_score": score,
        "assessment": "strong" if score >= 75 else "moderate" if score >= 25 else "weak — fix likely incomplete",
        "patches_count": len(fr.patches),
        "fix_script_lines": len(fr.fix_script.splitlines()) if fr.fix_script else 0,
        "has_references": len(fr.references) > 0,
    }


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
