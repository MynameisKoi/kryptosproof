"""
Mock pipeline — bypasses LLM calls and Docker sandbox for fast end-to-end testing.
Enable with: MOCK_MODE=true

Simulates a realistic audit with 3 confirmed + 2 clean vulnerability types,
one fix that succeeds and one that fails verification.
"""
import asyncio
from typing import Callable

from schemas import SecurityAuditReport, VulnerabilityReport

# ── Simulated red team results ─────────────────────────────────────────────────

_RED_TEAM = [
    {
        "vulnerability_focus": "SQL Injection",
        "confirmed": True,
        "vulnerabilities_confirmed": [
            "SQL Injection confirmed via UNION-based attack on /login.php"
        ],
        "stdout": (
            "[OK] Connecting to target…\n"
            "[OK] Fetching login form…\n"
            "[OK] Testing parameter: username\n"
            "[VULN] SQL Injection confirmed via UNION-based attack on /login.php: "
            "' UNION SELECT 1,user(),3-- - returned database user\n"
            "[OK] Script complete"
        ),
        "stderr": "",
        "exit_code": 0,
        "status": "exploited",
        "severity": "high",
    },
    {
        "vulnerability_focus": "XSS",
        "confirmed": True,
        "vulnerabilities_confirmed": [
            "Reflected XSS confirmed in 'search' parameter on /vulnerabilities/xss_r/"
        ],
        "stdout": (
            "[OK] Connecting to target…\n"
            "[OK] Testing reflected XSS payloads…\n"
            "[VULN] Reflected XSS confirmed in 'search' parameter: "
            "<script>alert(1)</script> returned unescaped in response\n"
            "[OK] Script complete"
        ),
        "stderr": "",
        "exit_code": 0,
        "status": "exploited",
        "severity": "high",
    },
    {
        "vulnerability_focus": "Command Injection",
        "confirmed": False,
        "vulnerabilities_confirmed": [],
        "stdout": (
            "[OK] Connecting to target…\n"
            "[OK] Testing command injection payloads on /vulnerabilities/exec/…\n"
            "[OK] Payload '; whoami' — response did not contain command output\n"
            "[OK] Payload '| id' — response did not contain command output\n"
            "[OK] No command injection detected"
        ),
        "stderr": "",
        "exit_code": 0,
        "status": "failed",
        "severity": "low",
    },
    {
        "vulnerability_focus": "Path Traversal",
        "confirmed": False,
        "vulnerabilities_confirmed": [],
        "stdout": (
            "[OK] Connecting to target…\n"
            "[OK] Testing path traversal payloads…\n"
            "[OK] Payload '../../etc/passwd' — file contents not returned\n"
            "[OK] No path traversal detected"
        ),
        "stderr": "",
        "exit_code": 0,
        "status": "failed",
        "severity": "low",
    },
    {
        "vulnerability_focus": "CSRF",
        "confirmed": True,
        "vulnerabilities_confirmed": [
            "CSRF confirmed — state-changing form accepted request without valid token"
        ],
        "stdout": (
            "[OK] Connecting to target…\n"
            "[OK] Checking forms for CSRF tokens…\n"
            "[OK] Submitting forged cross-origin request…\n"
            "[VULN] CSRF confirmed — state-changing form accepted request without valid token\n"
            "[OK] Script complete"
        ),
        "stderr": "",
        "exit_code": 0,
        "status": "exploited",
        "severity": "medium",
    },
]

# ── Simulated blue team results ────────────────────────────────────────────────

_BLUE_TEAM: dict[str, dict] = {
    "SQL Injection": {
        "fix": {
            "vulnerability_type": "SQL Injection",
            "root_cause": "Raw string concatenation used to build SQL queries",
            "fix_description": "Replace string concatenation with parameterized queries / prepared statements",
            "fix_script": (
                "import sqlite3\n\n"
                "# BEFORE (vulnerable):\n"
                "# query = f\"SELECT * FROM users WHERE username = '{username}'\"\n\n"
                "# AFTER (safe):\n"
                "conn = sqlite3.connect('dvwa.db')\n"
                "cursor = conn.cursor()\n"
                "cursor.execute('SELECT * FROM users WHERE username = ?', (username,))\n"
                "rows = cursor.fetchall()\n"
            ),
            "patches": [
                {
                    "file_path": "vulnerabilities/sqli/source/low.php",
                    "original_snippet": "$query = \"SELECT first_name, last_name FROM users WHERE user_id = '$id';\";",
                    "patched_snippet": "$query = \"SELECT first_name, last_name FROM users WHERE user_id = ?;\";\n$stmt = $pdo->prepare($query);\n$stmt->execute([$id]);",
                    "explanation": "Use PDO prepared statement to prevent SQL injection",
                }
            ],
            "references": [
                "https://owasp.org/www-community/attacks/SQL_Injection",
                "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
            ],
        },
        "test": {
            "overall_patched": True,
            "checks": [],
            "status": "patched",
            "residual_vulnerabilities": [],
            "recommendation": "Deploy parameterized queries across all database interaction points and enable a WAF rule for SQLi patterns.",
            "retest_stdout": "[OK] SQL Injection test — no vulnerability detected after fix",
            "retest_stderr": "",
        },
    },
    "XSS": {
        "fix": {
            "vulnerability_type": "XSS",
            "root_cause": "User-supplied input rendered directly into HTML without escaping",
            "fix_description": "Escape all user output with html.escape() and add Content-Security-Policy header",
            "fix_script": (
                "import html\n\n"
                "# BEFORE (vulnerable):\n"
                "# return f'<p>Hello {name}</p>'\n\n"
                "# AFTER (safe):\n"
                "safe_name = html.escape(name)\n"
                "return f'<p>Hello {safe_name}</p>'\n"
            ),
            "patches": [
                {
                    "file_path": "vulnerabilities/xss_r/source/low.php",
                    "original_snippet": "echo '<pre>Hello ' . $_GET[ 'name' ] . '</pre>';",
                    "patched_snippet": "echo '<pre>Hello ' . htmlspecialchars($_GET['name'], ENT_QUOTES, 'UTF-8') . '</pre>';",
                    "explanation": "Escape user input with htmlspecialchars before rendering",
                }
            ],
            "references": [
                "https://owasp.org/www-community/attacks/xss/",
                "https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html",
            ],
        },
        "test": {
            "overall_patched": True,
            "checks": [],
            "status": "patched",
            "residual_vulnerabilities": [],
            "recommendation": "Add Content-Security-Policy: default-src 'self' header to all responses.",
            "retest_stdout": "[OK] XSS test — output is properly escaped after fix",
            "retest_stderr": "",
        },
    },
    "CSRF": {
        "fix": {
            "vulnerability_type": "CSRF",
            "root_cause": "State-changing forms do not validate a per-session CSRF token",
            "fix_description": "Generate a cryptographically random token per session and validate it on every POST",
            "fix_script": (
                "import secrets\n\n"
                "# Generate token at session start:\n"
                "session['csrf_token'] = secrets.token_hex(32)\n\n"
                "# Validate on POST:\n"
                "if request.form.get('csrf_token') != session.get('csrf_token'):\n"
                "    abort(403, 'Invalid CSRF token')\n"
            ),
            "patches": [],
            "references": [
                "https://owasp.org/www-community/attacks/csrf",
                "https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html",
            ],
        },
        "test": {
            "overall_patched": False,
            "checks": [],
            "status": "unpatched",
            "residual_vulnerabilities": [
                "Server does not validate the CSRF token value on POST requests"
            ],
            "recommendation": "Ensure the server rejects POST requests where the submitted csrf_token does not match the session value.",
            "retest_stdout": "[VULN] CSRF still exploitable — token present in form but not validated server-side",
            "retest_stderr": "",
        },
    },
}

# ── Runner ─────────────────────────────────────────────────────────────────────

_STEP_DELAY = 4.0  # seconds between steps


async def run_mock_audit(
    target_url: str,
    on_red_team_start: Callable[[str], None],
    on_red_team_end: Callable[[str, dict], None],
    on_blue_team_start: Callable[[], None],
    on_blue_team_end: Callable[[dict], None],
) -> SecurityAuditReport:
    """
    Runs a complete mock audit, firing all the same callbacks as the real pipeline.
    Returns a SecurityAuditReport matching what the orchestrator would produce.
    """

    # ── Phase 1: Red team ──────────────────────────────────────────────────────
    for vuln in _RED_TEAM:
        on_red_team_start(vuln["vulnerability_focus"])
        await asyncio.sleep(_STEP_DELAY)

        execution_dict = {
            "attack_type": vuln["vulnerability_focus"],
            "target_url": target_url,
            "exit_code": vuln["exit_code"],
            "stdout": vuln["stdout"],
            "stderr": vuln["stderr"],
            "crash_detected": False,
            "vulnerabilities_confirmed": vuln["vulnerabilities_confirmed"],
            "status": vuln["status"],
            "error_logs": "",
            "logs": "",
            "_attack_script": {"severity": vuln["severity"]},
        }
        on_red_team_end(vuln["vulnerability_focus"], execution_dict)
        await asyncio.sleep(_STEP_DELAY)

    # ── Phase 2: Blue team (confirmed only) ───────────────────────────────────
    for vuln in _RED_TEAM:
        if not vuln["confirmed"]:
            continue

        focus = vuln["vulnerability_focus"]
        fix_data = _BLUE_TEAM.get(focus)
        if not fix_data:
            continue

        on_blue_team_start()
        await asyncio.sleep(_STEP_DELAY)

        on_blue_team_end(fix_data)
        await asyncio.sleep(_STEP_DELAY)

    # ── Phase 3: Report ───────────────────────────────────────────────────────
    confirmed = [v for v in _RED_TEAM if v["confirmed"]]
    patched_count = sum(
        1
        for v in confirmed
        if _BLUE_TEAM.get(v["vulnerability_focus"], {})
        .get("test", {})
        .get("overall_patched", False)
    )

    vuln_reports = [
        VulnerabilityReport(
            type=v["vulnerability_focus"],
            severity=v["severity"],
            confirmed=v["confirmed"],
            patched=(
                _BLUE_TEAM.get(v["vulnerability_focus"], {})
                .get("test", {})
                .get("overall_patched", False)
            ),
            description=(
                v["vulnerabilities_confirmed"][0]
                if v["vulnerabilities_confirmed"]
                else f"No {v['vulnerability_focus']} vulnerability confirmed"
            ),
        )
        for v in _RED_TEAM
    ]

    overall = (
        "secure" if patched_count == len(confirmed) and len(confirmed) > 0
        else "partially_patched" if patched_count > 0
        else "vulnerable"
    )

    report_md = f"""# KryptosProof Mock Audit Report

**Target:** {target_url}
**Mode:** Mock (fast pipeline test)

## Summary
- Vulnerabilities found: {len(confirmed)}
- Successfully patched: {patched_count}
- Overall status: **{overall.replace("_", " ").title()}**

## Confirmed Vulnerabilities
{chr(10).join(f"- **{v['vulnerability_focus']}** ({v['severity']}) — {v['vulnerabilities_confirmed'][0] if v['vulnerabilities_confirmed'] else 'N/A'}" for v in confirmed)}

## Clean (No Vulnerability Confirmed)
{chr(10).join(f"- {v['vulnerability_focus']}" for v in _RED_TEAM if not v['confirmed'])}

## Patch Results
{chr(10).join(f"- **{v['vulnerability_focus']}**: {'✓ Patched' if _BLUE_TEAM.get(v['vulnerability_focus'], {}).get('test', {}).get('overall_patched') else '✗ Unpatched'}" for v in confirmed)}

---
*Generated by KryptosProof mock pipeline*
"""

    return SecurityAuditReport(
        target_url=target_url,
        vulnerabilities_found=vuln_reports,
        total_vulnerabilities=len(confirmed),
        patched_count=patched_count,
        overall_status=overall,
        attack_summary=f"Tested {len(_RED_TEAM)} vulnerability types — {len(confirmed)} confirmed.",
        fix_summary=f"{patched_count}/{len(confirmed)} confirmed vulnerabilities successfully patched.",
        recommendations=[
            "Use parameterized queries for all database interactions",
            "Escape all user-supplied output before rendering in HTML",
            "Validate CSRF tokens server-side on every state-changing request",
        ],
        report_markdown=report_md,
    )
