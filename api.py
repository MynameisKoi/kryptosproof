"""
KryptosProof FastAPI server
Exposes the red-team / blue-team audit pipeline as a REST API.
"""
# Load .env before any agent/model imports so API keys are available
from dotenv import load_dotenv
load_dotenv()

import uuid
from datetime import datetime, timezone
from typing import Any

import logfire
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings

if settings.logfire_token:
    logfire.configure(
        token=settings.logfire_token,
        environment=settings.logfire_environment or "local",
        service_name="kryptosproof",
    )
    logfire.instrument_pydantic_ai()

app = FastAPI(title="KryptosProof API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "kryptosproof-api"}

# In-memory audit store
_audits: dict[str, dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_audit(audit_id: str, target_url: str) -> dict[str, Any]:
    phases = [
        {"id": "attack-script",      "name": "Attack Script Generation", "team": "red_team",  "status": "pending", "startedAt": None, "completedAt": None, "durationMs": None, "output": None, "summary": None},
        {"id": "exploit-execution",  "name": "Exploit Execution",        "team": "red_team",  "status": "pending", "startedAt": None, "completedAt": None, "durationMs": None, "output": None, "summary": None},
        {"id": "fix-generation",     "name": "Fix Generation",           "team": "blue_team", "status": "pending", "startedAt": None, "completedAt": None, "durationMs": None, "output": None, "summary": None},
        {"id": "patch-verification", "name": "Patch Verification",       "team": "blue_team", "status": "pending", "startedAt": None, "completedAt": None, "durationMs": None, "output": None, "summary": None},
    ]
    return {
        "id": audit_id,
        "targetUrl": target_url,
        "status": "pending",
        "overallStatus": None,
        "createdAt": _now(),
        "completedAt": None,
        "phases": phases,
        "vulnerabilities": [],
        "totalVulnerabilities": 0,
        "patchedCount": 0,
        "reportMarkdown": None,
        "fixResults": [],
    }


def _set_phase(
    audit: dict,
    phase_id: str,
    status: str,
    output: str | None = None,
    summary: str | None = None,
) -> None:
    for p in audit["phases"]:
        if p["id"] == phase_id:
            p["status"] = status
            if status == "running" and not p["startedAt"]:
                p["startedAt"] = _now()
            if status in ("completed", "failed"):
                p["completedAt"] = _now()
                if p["startedAt"]:
                    start = datetime.fromisoformat(p["startedAt"])
                    end = datetime.fromisoformat(p["completedAt"])
                    p["durationMs"] = int((end - start).total_seconds() * 1000)
            if output is not None:
                p["output"] = output
            if summary is not None:
                p["summary"] = summary
            break


def _append_phase_output(audit: dict, phase_id: str, text: str) -> None:
    for p in audit["phases"]:
        if p["id"] == phase_id:
            p["output"] = (p["output"] or "") + text + "\n"
            break


def _map_report_to_audit(audit: dict, report: Any) -> None:
    """Populate audit summary fields from the final SecurityAuditReport.
    Vulnerabilities are frozen after phase 2 — we never overwrite them here."""
    audit["totalVulnerabilities"] = report.total_vulnerabilities
    audit["patchedCount"] = report.patched_count
    audit["overallStatus"] = report.overall_status
    audit["reportMarkdown"] = report.report_markdown


async def _run_audit_task(audit_id: str) -> None:
    from ai.agents.orchestrator import OrchestratorDeps, orchestrator_agent
    from schemas import SecurityAuditReport
    from tools.mock_pipeline import run_mock_audit

    audit = _audits[audit_id]
    audit["status"] = "running"
    target_url = audit["targetUrl"]

    # Show the first phase immediately so the frontend sees activity right away
    _set_phase(audit, "attack-script", "running",
               summary="Orchestrator is planning the attack…",
               output=f"[{_now()}] Orchestrator started — awaiting first tool call…\n")

    # ── Callbacks passed via OrchestratorDeps ─────────────────────────
    # pydantic-ai forwards ctx.deps to every tool call, so these are
    # guaranteed to fire even when tool patching would be skipped.

    def on_red_team_start(vulnerability_focus: str) -> None:
        _set_phase(audit, "attack-script", "running",
                   summary=f"Generating {vulnerability_focus} attack script…")
        _append_phase_output(audit, "attack-script",
                             f"\n{'─'*50}\n[{_now()}] ▶ {vulnerability_focus.upper()}\n"
                             f"[{_now()}] Generating attack script…")

    def on_red_team_end(vulnerability_focus: str, data: dict) -> None:
        stdout = data.get("stdout", "")
        stderr = data.get("stderr", "")
        vulns = data.get("vulnerabilities_confirmed", [])
        status = data.get("status", "")
        exit_code = data.get("exit_code", "?")

        log = (
            f"exit={exit_code}  status={status}\n"
            f"\n--- stdout ---\n{stdout or '(empty)'}\n"
            f"\n--- stderr ---\n{stderr or '(empty)'}\n"
            f"\n--- confirmed ---\n" +
            ("\n".join(f"  [VULN] {v}" for v in vulns) or "  (none)")
        )

        result_label = f"{'VULNERABLE' if vulns else 'PASSED'} — {len(vulns)} finding(s)"
        _append_phase_output(audit, "attack-script",
                             f"[{_now()}] ✓ Script generated → executing in sandbox…")

        # Exploit-execution: stay running, accumulate per-type output
        _set_phase(audit, "exploit-execution", "running",
                   summary=f"Executing {vulnerability_focus}…")
        _append_phase_output(audit, "exploit-execution",
                             f"\n{'─'*50}\n[{_now()}] ▶ {vulnerability_focus.upper()}\n"
                             f"{log}\n"
                             f"[{_now()}] → {result_label}")

        # Add findings as they come in
        for v in vulns:
            audit["vulnerabilities"].append({
                "id": str(uuid.uuid4()),
                "type": vulnerability_focus,
                "severity": data.get("_attack_script", {}).get("severity", "medium"),
                "confirmed": True,
                "patched": False,
                "description": v,
                "endpoint": None,
                "cve": None,
                "logs": log,
            })
        if not vulns:
            audit["vulnerabilities"].append({
                "id": str(uuid.uuid4()),
                "type": vulnerability_focus,
                "severity": "low",
                "confirmed": False,
                "patched": False,
                "description": f"No vulnerability confirmed (status: {status})",
                "endpoint": None,
                "cve": None,
                "logs": log,
            })

    def on_blue_team_start() -> None:
        _set_phase(audit, "fix-generation", "running",
                   summary="Generating fix scripts…",
                   output=f"[{_now()}] Blue team analyzing vulnerabilities…\n")

    def on_blue_team_end(result: dict) -> None:
        if result.get("skipped"):
            return

        fix = result.get("fix", {})
        test = result.get("test", {})

        fix_log = (
            f"[{_now()}] Fix script ready for {fix.get('vulnerability_type', '?')}\n"
            f"{'='*60}\n"
            f"vulnerability: {fix.get('vulnerability_type', '?')}\n"
            f"root_cause:    {fix.get('root_cause', '')}\n"
            f"fix:           {fix.get('fix_description', '')}\n"
            f"\n--- fix script ---\n{fix.get('fix_script', '(none)')}"
        )
        _set_phase(audit, "fix-generation", "completed",
                   summary=f"Fix generated for {fix.get('vulnerability_type', '?')}",
                   output=fix_log)

        overall_patched = test.get("overall_patched", False)
        retest_log = (
            f"[{_now()}] Patch verification complete\n"
            f"{'='*60}\n"
            f"result:         {'✓ PATCHED' if overall_patched else '✗ UNPATCHED'}\n"
            f"recommendation: {test.get('recommendation', '')}\n"
            f"\n--- retest stdout ---\n{test.get('retest_stdout', '(empty)')}\n"
            f"\n--- retest stderr ---\n{test.get('retest_stderr', '(empty)')}"
        )
        _set_phase(audit, "patch-verification", "running",
                   summary="Verifying patch…",
                   output=f"[{_now()}] Re-running attack to verify fix…\n")
        _set_phase(audit, "patch-verification", "completed",
                   summary="✓ Patched" if overall_patched else "✗ Unpatched",
                   output=retest_log)

        audit["fixResults"].append({
            "vulnerabilityType": fix.get("vulnerability_type", ""),
            "overallPatched": overall_patched,
            "rootCause": fix.get("root_cause", ""),
            "fixDescription": fix.get("fix_description", ""),
            "fixScript": fix.get("fix_script", ""),
            "patches": fix.get("patches", []),
            "recommendation": test.get("recommendation", ""),
            "references": fix.get("references", []),
        })

    try:
        if settings.mock_mode:
            report: SecurityAuditReport = await run_mock_audit(
                target_url=target_url,
                on_red_team_start=on_red_team_start,
                on_red_team_end=on_red_team_end,
                on_blue_team_start=on_blue_team_start,
                on_blue_team_end=on_blue_team_end,
            )
        else:
            result = await orchestrator_agent.run(
                f"Run a complete security audit against: {target_url}. "
                "Test for SQL Injection, XSS, Command Injection, Path Traversal, and CSRF. "
                "After red team, apply blue team fixes and verify each vulnerability is patched.",
                deps=OrchestratorDeps(
                    target_url=target_url,
                    on_red_team_start=on_red_team_start,
                    on_red_team_end=on_red_team_end,
                    on_blue_team_start=on_blue_team_start,
                    on_blue_team_end=on_blue_team_end,
                ),
            )
            report: SecurityAuditReport = result.output

        # Populate summary fields from the final report (vulnerabilities stay frozen)
        _map_report_to_audit(audit, report)
        audit["status"] = "completed"
        audit["completedAt"] = _now()

        # Mark any still-pending phases as completed
        for p in audit["phases"]:
            if p["status"] in ("pending", "running"):
                _set_phase(audit, p["id"], "completed")

    except Exception as e:
        audit["status"] = "failed"
        audit["completedAt"] = _now()
        for p in audit["phases"]:
            if p["status"] in ("pending", "running"):
                _set_phase(audit, p["id"], "failed", output=str(e))


# ── Request / Response models ──────────────────────────────────────────────────

class StartAuditRequest(BaseModel):
    targetUrl: str
    vulnerabilityTypes: list[str] | None = None
    severityThreshold: str | None = None


class SandboxRunRequest(BaseModel):
    script: str
    timeout: int = 30


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.post("/api/audits", status_code=201)
async def start_audit(req: StartAuditRequest, background_tasks: BackgroundTasks):
    audit_id = str(uuid.uuid4())[:8]
    audit = _make_audit(audit_id, req.targetUrl)
    _audits[audit_id] = audit
    background_tasks.add_task(_run_audit_task, audit_id)
    return audit


@app.get("/api/audits")
async def list_audits():
    return sorted(_audits.values(), key=lambda a: a["createdAt"], reverse=True)


@app.get("/api/audits/{audit_id}")
async def get_audit(audit_id: str):
    audit = _audits.get(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    return audit


@app.post("/api/sandbox/run")
async def sandbox_run(req: SandboxRunRequest):
    """Run an arbitrary Python script in the sandbox and return stdout/stderr."""
    from tools.sandbox import create_sandbox, run_script_string, destroy_sandbox
    cid = await create_sandbox(image=settings.sandbox_image, network=settings.sandbox_network)
    try:
        result = await run_script_string(cid, req.script, timeout=req.timeout)
    finally:
        await destroy_sandbox(cid)
    return {
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "crash_detected": result.crash_detected,
    }
