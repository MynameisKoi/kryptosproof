"""
Deterministic red-team execution: Docker sandbox + structured ExecutionResult.
No LLM — avoids inconsistent parsing of stdout/stderr.
"""
from __future__ import annotations

import re
from typing import Literal

from config import settings
from schemas import AttackScriptResult, ExecutionResult, SandboxInfo
from tools.sandbox import SandboxResult, create_sandbox, destroy_sandbox, run_script_string
from tools.tool_logs import merge_tool_logs


def _truncate_output(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 24] + "\n... [stdout/stderr truncated]"


def _parse_vuln_markers(stdout: str) -> list[str]:
    """Extract human-readable confirmations from lines containing [VULN]."""
    seen: set[str] = set()
    out: list[str] = []
    for line in stdout.splitlines():
        if "[VULN]" not in line.upper():
            continue
        m = re.search(r"\[VULN\]\s*:?\s*(.*)", line, flags=re.IGNORECASE)
        raw = m.group(1).strip() if m else ""
        desc = raw if raw and raw.upper() != "[VULN]" else line.strip()
        if desc and desc not in seen:
            seen.add(desc)
            out.append(desc[:500])
    return out


def _indicator_hits(attack: AttackScriptResult, stdout: str) -> list[str]:
    """If the script forgot [VULN] but printed expected indicators, still confirm."""
    hits: list[str] = []
    for ind in attack.expected_indicators:
        if ind and ind.strip() and ind in stdout:
            hits.append(f"{attack.vulnerability_type} (matched indicator)")
    return list(dict.fromkeys(hits))


def _merge_confirmed(attack: AttackScriptResult, stdout: str) -> list[str]:
    markers = _parse_vuln_markers(stdout)
    if markers:
        return markers
    return _indicator_hits(attack, stdout)


def _derive_status(
    crash_detected: bool,
    exit_code: int,
    vulnerabilities_confirmed: list[str],
) -> Literal["exploited", "failed", "partial", "error"]:
    if vulnerabilities_confirmed:
        if crash_detected:
            return "partial"
        return "exploited"
    if crash_detected or exit_code != 0:
        return "error"
    return "failed"


def _trim_error_logs(stderr: str, max_chars: int | None = None) -> str:
    cap = max_chars if max_chars is not None else min(12000, settings.max_execution_output_chars)
    s = stderr.strip()
    if len(s) <= cap:
        return s
    return s[: cap - 20] + "\n... [truncated]"


def execution_result_from_sandbox(
    attack: AttackScriptResult,
    target_url: str,
    container_id: str,
    sr: SandboxResult,
) -> ExecutionResult:
    vulns = _merge_confirmed(attack, sr.stdout)
    status = _derive_status(sr.crash_detected, sr.exit_code, vulns)
    cap = settings.max_execution_output_chars
    out = _truncate_output(sr.stdout, cap)
    err = _truncate_output(sr.stderr, cap)
    log_blob = merge_tool_logs(
        f"run_attack_execution exit_code={sr.exit_code} crash_detected={sr.crash_detected} status={status}",
        f"vulnerabilities_confirmed: {len(vulns)} — {vulns[:5]}",
        "stdout:\n" + out[: min(8000, settings.max_execution_output_chars)],
        "stderr:\n" + err[: min(8000, settings.max_execution_output_chars)],
    )
    return ExecutionResult(
        attack_type=attack.vulnerability_type,
        target_url=target_url,
        sandbox=SandboxInfo(
            container_id=container_id,
            image=settings.sandbox_image,
            network=settings.sandbox_network,
        ),
        exit_code=sr.exit_code,
        stdout=out,
        stderr=err,
        crash_detected=sr.crash_detected,
        vulnerabilities_confirmed=vulns,
        error_logs=_trim_error_logs(err),
        logs=log_blob,
        status=status,
        raw_responses=[],
    )


async def run_attack_execution(attack: AttackScriptResult, target_url: str) -> ExecutionResult:
    """
    Create sandbox → run attack.script (httpx installed in container) → destroy → ExecutionResult.
    """
    cid = await create_sandbox(image=settings.sandbox_image, network=settings.sandbox_network)
    try:
        sr = await run_script_string(
            cid,
            attack.script,
            timeout=settings.sandbox_timeout,
        )
    finally:
        await destroy_sandbox(cid)
    return execution_result_from_sandbox(attack, target_url, cid, sr)
