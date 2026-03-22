"""Tests for attack script validation."""
import pytest

from tools.attack_validation import AttackScriptValidationError, validate_attack_script_result
from schemas import AttackScriptResult


def _valid_script() -> str:
    return "\n".join(
        [
            "import httpx",
            'TARGET = "http://dvwa:80/"',
            "async def main():",
            "    async with httpx.AsyncClient() as c:",
            "        r = await c.get(TARGET)",
            '        print("[OK]", r.status_code)',
            "if __name__ == '__main__':",
            "    import asyncio",
            "    asyncio.run(main())",
            "",
        ]
    )


def test_validate_ok():
    a = AttackScriptResult(
        vulnerability_type="Recon",
        severity="low",
        target_url="http://dvwa:80",
        description="Smoke check against target.",
        target_endpoints=["/"],
        payloads=[],
        script=_valid_script(),
        expected_indicators=[],
    )
    validate_attack_script_result(a, "http://dvwa:80")


def test_validate_target_mismatch():
    a = AttackScriptResult(
        vulnerability_type="Recon",
        severity="low",
        target_url="http://other/",
        description="x",
        target_endpoints=["/"],
        payloads=[],
        script=_valid_script(),
        expected_indicators=[],
    )
    with pytest.raises(AttackScriptValidationError):
        validate_attack_script_result(a, "http://dvwa:80")


def test_validate_no_httpx():
    a = AttackScriptResult(
        vulnerability_type="Recon",
        severity="low",
        target_url="http://dvwa:80",
        description="x",
        target_endpoints=["/"],
        payloads=[],
        script="print(1)" + "x" * 80,
        expected_indicators=[],
    )
    with pytest.raises(AttackScriptValidationError):
        validate_attack_script_result(a, "http://dvwa:80")


def test_validate_subprocess_forbidden():
    s = _valid_script() + "\nimport subprocess\n"
    a = AttackScriptResult(
        vulnerability_type="Recon",
        severity="low",
        target_url="http://dvwa:80",
        description="x",
        target_endpoints=["/"],
        payloads=[],
        script=s,
        expected_indicators=[],
    )
    with pytest.raises(AttackScriptValidationError):
        validate_attack_script_result(a, "http://dvwa:80")
