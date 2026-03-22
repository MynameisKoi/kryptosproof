"""
Integration tests for blue_team agents: each test performs a real LLM request.

- Model: `BLUE_TEAM_TEST_MODEL` if set, else `settings.model` from MODEL / AI_MODEL in `.env`.
- Mocks Docker sandbox helpers only for `testing_agent` so the model still runs and may call tools,
  without requiring a local Docker daemon.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.exceptions import ModelHTTPError

from config import settings
from ai.agents.blue_team.fix_script import fix_script_agent, FixScriptDeps
from ai.agents.blue_team.handoff_report import handoff_report_agent, HandoffReportDeps
from ai.agents.blue_team.testing import testing_agent, TestingDeps
from schemas import (
    AttackScriptResult,
    AttackPayload,
    BlueTeamHandoffReport,
    ExecutionResult,
    FixScriptResult,
    FilePatch,
    SandboxInfo,
    TestResult as BlueTeamTestResult,
)


def _live_model() -> str:
    override = os.getenv("BLUE_TEAM_TEST_MODEL", "").strip()
    if override:
        return override
    return settings.model


async def _guard_rate_limit(awaitable):
    """Skip the test when the provider returns 429 (quota / rate limit)."""
    try:
        return await awaitable
    except ModelHTTPError as e:
        if e.status_code == 429:
            pytest.skip(f"LLM API rate limited or quota exhausted: {e}")
        raise


@pytest.fixture
def live_model_name() -> str:
    return _live_model()


@pytest.fixture
def sample_execution_result() -> ExecutionResult:
    return ExecutionResult(
        attack_type="sql_injection",
        target_url="http://example.test",
        sandbox=SandboxInfo(
            container_id="test-container",
            image="python:3.11-slim",
            network="kryptosproof_sandbox",
        ),
        exit_code=0,
        stdout="[VULN] SQL error in response body",
        stderr="",
        crash_detected=False,
        vulnerabilities_confirmed=["SQL Injection"],
        error_logs="",
        status="exploited",
        raw_responses=[{"status_code": 500, "body_snippet": "syntax error"}],
    )


@pytest.fixture
def sample_attack_and_fix(
    sample_execution_result: ExecutionResult,
) -> tuple[AttackScriptResult, FixScriptResult]:
    attack = AttackScriptResult(
        vulnerability_type="SQL Injection",
        severity="high",
        target_url=sample_execution_result.target_url,
        description="Test payload against login",
        target_endpoints=["/login"],
        payloads=[
            AttackPayload(
                name="basic",
                payload="' OR '1'='1",
                endpoint="/login",
                method="POST",
                params={},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                body="user=admin&password=test",
            )
        ],
        script='print("attack script placeholder")',
        expected_indicators=["SQL", "syntax"],
    )
    fix = FixScriptResult(
        vulnerability_type="SQL Injection",
        severity="high",
        root_cause="Unparameterized query",
        fix_description="Use parameterized queries",
        patches=[
            FilePatch(
                file_path="db.py",
                original_snippet="cursor.execute(f",
                patched_snippet="cursor.execute(",
                explanation="Bind parameters safely",
            )
        ],
        fix_script="# apply patches",
        dependencies_required=[],
        references=["OWASP A03:2021"],
    )
    return attack, fix


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fix_script_agent_calls_llm(
    live_model_name: str,
    sample_execution_result: ExecutionResult,
) -> None:
    result = await _guard_rate_limit(
        fix_script_agent.run(
            "Propose a minimal fix plan for the confirmed vulnerability. "
            "Use get_execution_details once if helpful, then return a complete FixScriptResult.",
            deps=FixScriptDeps(execution_result=sample_execution_result),
            model=live_model_name,
        )
    )
    assert isinstance(result.output, FixScriptResult)
    assert result.usage().total_tokens > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_handoff_report_agent_calls_llm(live_model_name: str) -> None:
    result = await _guard_rate_limit(
        handoff_report_agent.run(
            "Blue team hit the iteration limit after 2 attempts. "
            "Produce a handoff report for developers with concrete next steps.",
            deps=HandoffReportDeps(),
            model=live_model_name,
        )
    )
    assert isinstance(result.output, BlueTeamHandoffReport)
    assert result.output.summary_of_attempts
    assert result.usage().total_tokens > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_testing_agent_calls_llm(
    live_model_name: str,
    sample_attack_and_fix: tuple[AttackScriptResult, FixScriptResult],
) -> None:
    attack, fix = sample_attack_and_fix
    mock_run = MagicMock()
    mock_run.exit_code = 0
    mock_run.stdout = "ok"
    mock_run.stderr = ""
    mock_run.crash_detected = False

    with (
        patch(
            "ai.agents.blue_team.testing.create_sandbox",
            new_callable=AsyncMock,
            return_value="fake-verify-container",
        ),
        patch(
            "ai.agents.blue_team.testing.run_script_string",
            new_callable=AsyncMock,
            return_value=mock_run,
        ),
        patch("ai.agents.blue_team.testing.destroy_sandbox", new_callable=AsyncMock),
    ):
        result = await _guard_rate_limit(
            testing_agent.run(
                "Verify whether the vulnerability is addressed after the fix. "
                "Use sandbox tools as needed, then return a complete TestResult.",
                deps=TestingDeps(
                    attack_script=attack,
                    fix_result=fix,
                    target_url="http://example.test",
                ),
                model=live_model_name,
            )
        )

    assert isinstance(result.output, BlueTeamTestResult)
    assert result.usage().total_tokens > 0
