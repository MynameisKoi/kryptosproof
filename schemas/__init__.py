"""
Schemas package — loads Pydantic models from subdirectories that use non-standard
naming conventions (red_team.py/, blue_team.py/).
"""
import importlib.util
from pathlib import Path

_base = Path(__file__).parent


def _load(rel_path: str):
    path = _base / rel_path
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Red team schemas
_rt_attack = _load("red_team.py/attack_script.py")
_rt_exec = _load("red_team.py/execution.py")

# Blue team schemas
_bt_fix = _load("blue_team.py/fix_script.py")
_bt_test = _load("blue_team.py/testing.py")
_bt_handoff = _load("blue_team.py/handoff_report.py")

# Orchestrator schemas (regular import path)
from schemas.orchestrator import SecurityAuditReport, VulnerabilityReport  # noqa: E402

AttackPayload = _rt_attack.AttackPayload
AttackScriptResult = _rt_attack.AttackScriptResult

SandboxInfo = _rt_exec.SandboxInfo
ExecutionResult = _rt_exec.ExecutionResult

FilePatch = _bt_fix.FilePatch
FixScriptResult = _bt_fix.FixScriptResult

VulnerabilityCheckResult = _bt_test.VulnerabilityCheckResult
TestResult = _bt_test.TestResult

BlueTeamHandoffReport = _bt_handoff.BlueTeamHandoffReport

__all__ = [
    "AttackPayload",
    "AttackScriptResult",
    "SandboxInfo",
    "ExecutionResult",
    "FilePatch",
    "FixScriptResult",
    "VulnerabilityCheckResult",
    "TestResult",
    "VulnerabilityReport",
    "SecurityAuditReport",
    "BlueTeamHandoffReport",
]
