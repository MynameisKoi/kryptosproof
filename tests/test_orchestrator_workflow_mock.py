"""
Mocked end-to-end tests for the orchestrator handoff: red team tool → JSON → blue team tool.

No real LLM or Docker — sub-agents and execution pipeline are patched to return valid schema instances.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pydantic_ai import RunContext

from config import settings
from schemas import (
    AttackPayload,
    AttackScriptResult,
    ExecutionResult,
    FixScriptResult,
    FilePatch,
    SandboxInfo,
    TestResult as BlueTeamTestResult,
    VulnerabilityCheckResult,
)
from ai.agents.orchestrator import (
    OrchestratorDeps,
    run_blue_team,
    run_red_team,
)
from ai.agents.red_team.attack_script import attack_script_agent
from ai.agents.blue_team.fix_script import fix_script_agent
from ai.agents.blue_team.testing import testing_agent

TARGET = "http://test.local:8080"


def _valid_attack_script() -> str:
    """Meets tools.attack_validation.validate_attack_script_result (min length, httpx, etc.)."""
    return f"""
import httpx

TARGET = "{TARGET}"

def main() -> None:
    client = httpx.Client(timeout=15.0)
    response = client.get(TARGET.rstrip("/") + "/probe", follow_redirects=True)
    print("[OK]", response.status_code)
    if "error" in response.text.lower():
        print("[VULN] reflected")

if __name__ == "__main__":
    main()
"""


def _attack_result() -> AttackScriptResult:
    return AttackScriptResult(
        vulnerability_type="SQL Injection",
        severity="high",
        target_url=TARGET,
        description="Parameterized test attack for orchestrator workflow mock.",
        target_endpoints=["/probe", "/login"],
        payloads=[
            AttackPayload(
                name="probe",
                payload="1' OR '1'='1",
                endpoint="/login",
                method="POST",
                params={},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                body="user=1",
            )
        ],
        script=_valid_attack_script(),
        expected_indicators=["SQL", "syntax"],
    )


def _execution_result(attack: AttackScriptResult) -> ExecutionResult:
    return ExecutionResult(
        attack_type=attack.vulnerability_type,
        target_url=TARGET,
        sandbox=SandboxInfo(
            container_id="mock-sandbox-1",
            image=settings.sandbox_image,
            network=settings.sandbox_network,
        ),
        exit_code=0,
        stdout="[VULN] reflected\n",
        stderr="",
        crash_detected=False,
        vulnerabilities_confirmed=["SQL Injection"],
        error_logs="",
        logs="mock execution log line",
        status="exploited",
        raw_responses=[{"status_code": 500, "snippet": "syntax"}],
    )


def _fix_result() -> FixScriptResult:
    return FixScriptResult(
        vulnerability_type="SQL Injection",
        severity="high",
        root_cause="Unparameterized query",
        fix_description="Use bound parameters",
        patches=[
            FilePatch(
                file_path="app/db.py",
                original_snippet="execute(f",
                patched_snippet="execute(",
                explanation="Bind parameters",
            )
        ],
        fix_script="# mock fix",
        dependencies_required=[],
        references=["OWASP A03:2021"],
    )


def _test_result() -> BlueTeamTestResult:
    return BlueTeamTestResult(
        overall_patched=True,
        checks=[
            VulnerabilityCheckResult(
                vulnerability_type="SQL Injection",
                patched=True,
                evidence="No [VULN] in stdout",
            )
        ],
        status="fully_patched",
        residual_vulnerabilities=[],
        recommendation="Deploy",
        retest_stdout="ok",
        retest_stderr="",
    )


def _orch_ctx() -> RunContext[OrchestratorDeps]:
    ctx = MagicMock(spec=RunContext)
    ctx.deps = OrchestratorDeps(target_url=TARGET)
    return ctx


@pytest.mark.asyncio
async def test_run_red_team_returns_json_with_attack_and_tool_log() -> None:
    attack = _attack_result()
    execution = _execution_result(attack)

    with (
        patch.object(attack_script_agent, "run", new_callable=AsyncMock) as m_attack,
        patch(
            "ai.agents.orchestrator.run_attack_execution",
            new_callable=AsyncMock,
        ) as m_exec,
    ):
        m_attack.return_value = MagicMock(output=attack)
        m_exec.return_value = execution

        raw = await run_red_team(_orch_ctx(), "sql_injection")

    m_attack.assert_awaited_once()
    m_exec.assert_awaited_once_with(attack, TARGET)

    data = json.loads(raw)
    assert "tool_log" in data
    assert data["target_url"] == TARGET
    assert data["vulnerabilities_confirmed"] == ["SQL Injection"]
    assert "_attack_script" in data
    assert data["_attack_script"]["vulnerability_type"] == "SQL Injection"


@pytest.mark.asyncio
async def test_run_blue_team_round_trip_after_run_red_team() -> None:
    attack = _attack_result()
    execution = _execution_result(attack)
    fix = _fix_result()
    test = _test_result()

    with (
        patch.object(attack_script_agent, "run", new_callable=AsyncMock) as m_attack,
        patch(
            "ai.agents.orchestrator.run_attack_execution",
            new_callable=AsyncMock,
        ) as m_exec,
        patch.object(fix_script_agent, "run", new_callable=AsyncMock) as m_fix,
        patch.object(testing_agent, "run", new_callable=AsyncMock) as m_test,
    ):
        m_attack.return_value = MagicMock(output=attack)
        m_exec.return_value = execution
        m_fix.return_value = MagicMock(output=fix)
        m_test.return_value = MagicMock(output=test)

        red_json = await run_red_team(_orch_ctx(), "sql_injection")
        blue_json = await run_blue_team(_orch_ctx(), red_json)

    m_fix.assert_awaited_once()
    m_test.assert_awaited_once()

    blue = json.loads(blue_json)
    assert "tool_log" in blue
    assert blue["fix"]["vulnerability_type"] == "SQL Injection"
    assert blue["test"]["overall_patched"] is True
    assert blue["test"]["status"] == "fully_patched"


@pytest.mark.asyncio
async def test_run_blue_team_without_attack_script_skips_testing_agent() -> None:
    execution = _execution_result(_attack_result())
    fix = _fix_result()
    payload = execution.model_dump()
    payload["_attack_script"] = {}
    red_json = json.dumps(payload)

    with (
        patch.object(fix_script_agent, "run", new_callable=AsyncMock) as m_fix,
        patch.object(testing_agent, "run", new_callable=AsyncMock) as m_test,
    ):
        m_fix.return_value = MagicMock(output=fix)
        blue_json = await run_blue_team(_orch_ctx(), red_json)

    m_fix.assert_awaited_once()
    m_test.assert_not_called()

    blue = json.loads(blue_json)
    assert blue["test"]["status"] == "failed"
    assert blue["test"]["overall_patched"] is False
