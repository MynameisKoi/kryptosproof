"""
Hard validation for AttackScriptResult before sandbox execution.
Used by the Attack Script agent output_validator (ModelRetry) and as a final guard in the orchestrator.
"""
from __future__ import annotations

import re

from config import settings
from schemas import AttackScriptResult


class AttackScriptValidationError(ValueError):
    """Raised when an attack script is not safe to run or does not meet contracts."""


def _norm_url(u: str) -> str:
    return u.strip().rstrip("/").lower()


def validate_attack_script_result(attack: AttackScriptResult, expected_target_url: str) -> None:
    """
    Ensure the model produced a runnable httpx-based script aligned with the audit target.
    Raises AttackScriptValidationError with a message suitable for ModelRetry.
    """
    if _norm_url(attack.target_url) != _norm_url(expected_target_url):
        raise AttackScriptValidationError(
            f"target_url must equal the audit target ({expected_target_url!r}); got {attack.target_url!r}."
        )

    script = attack.script.strip()
    if len(script) < settings.attack_script_min_chars:
        raise AttackScriptValidationError(
            f"script is too short (min {settings.attack_script_min_chars} chars after strip)."
        )
    if len(script) > settings.max_attack_script_bytes:
        raise AttackScriptValidationError(
            f"script exceeds max size ({settings.max_attack_script_bytes} bytes)."
        )

    if not re.search(r"(?m)^\s*(import httpx|from httpx\s+import)", script):
        raise AttackScriptValidationError(
            "script must import httpx (e.g. `import httpx` or `from httpx import ...`)."
        )

    if re.search(r"(?m)^\s*(import subprocess|from subprocess)\b", script):
        raise AttackScriptValidationError("script must not import subprocess (use httpx only in the sandbox).")
    if re.search(r"os\.system\s*\(", script):
        raise AttackScriptValidationError("script must not call os.system (use httpx only).")

    if not attack.description.strip():
        raise AttackScriptValidationError("description must be non-empty.")

    if not attack.target_endpoints:
        raise AttackScriptValidationError("target_endpoints must list at least one path or URL fragment.")

    if not re.search(r'print\s*\(.*\[VULN\]', script, re.IGNORECASE):
        raise AttackScriptValidationError(
            "script must contain at least one print('[VULN] ...') call so confirmed vulnerabilities can be detected. "
            "Add a line like: print('[VULN] <description of what was found>') when a vulnerability is confirmed."
        )

    if not attack.expected_indicators:
        raise AttackScriptValidationError(
            "expected_indicators must contain at least one string that appears in stdout when the vulnerability is confirmed."
        )
