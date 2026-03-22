"""Tests for deterministic execution parsing and status logic."""
from tools.execution_pipeline import (
    _derive_status,
    _merge_confirmed,
    _parse_vuln_markers,
)
from schemas import AttackScriptResult


def test_parse_vuln_markers_dedupes():
    out = "[VULN] SQLi\n[VULN] SQLi\n[VULN] XSS: reflected"
    got = _parse_vuln_markers(out)
    assert "SQLi" in got[0]
    assert len(got) == 2


def test_derive_status_exploited():
    assert _derive_status(False, 0, ["a"]) == "exploited"


def test_derive_status_partial():
    assert _derive_status(True, 0, ["a"]) == "partial"


def test_derive_status_failed():
    assert _derive_status(False, 0, []) == "failed"


def test_derive_status_error():
    assert _derive_status(True, 1, []) == "error"


def test_merge_prefers_vuln_markers_over_indicators():
    attack = AttackScriptResult(
        vulnerability_type="XSS",
        severity="high",
        target_url="http://t/",
        description="probe",
        target_endpoints=["/"],
        payloads=[],
        script="import httpx\n" + ("x" * 80),
        expected_indicators=["INJECTED"],
    )
    stdout = "[VULN] confirmed\nbody INJECTED"
    assert "confirmed" in _merge_confirmed(attack, stdout)[0]


def test_merge_indicator_fallback():
    attack = AttackScriptResult(
        vulnerability_type="XSS",
        severity="high",
        target_url="http://t/",
        description="probe",
        target_endpoints=["/"],
        payloads=[],
        script="import httpx\n" + ("x" * 80),
        expected_indicators=["UNIQUE_MARKER"],
    )
    stdout = "no bracket line but UNIQUE_MARKER here"
    m = _merge_confirmed(attack, stdout)
    assert m and "matched indicator" in m[0]
