"""
Open-source red team CLI wrappers (Nuclei, FFUF, SQLMap).
Invokes binaries from PATH; returns structured dicts for the Attack Script agent.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from config import settings


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_wordlist() -> Path:
    return _project_root() / "wordlists" / "common.txt"


def _which(name: str) -> str | None:
    return shutil.which(name)


async def _run_cmd(
    cmd: list[str],
    *,
    timeout: int,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, **(env or {})},
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return {
            "ok": False,
            "error": f"timeout after {timeout}s",
            "command": cmd,
            "exit_code": -1,
            "stdout": "",
            "stderr": "",
        }

    stdout = stdout_b.decode("utf-8", errors="replace")
    stderr = stderr_b.decode("utf-8", errors="replace")
    code = proc.returncode if proc.returncode is not None else -1
    return {
        "ok": code == 0,
        "command": cmd,
        "exit_code": code,
        "stdout": stdout,
        "stderr": stderr,
    }


def _parse_jsonl(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


async def run_nuclei_scan(
    target_url: str,
    *,
    tags: str | None = None,
    severity: str | None = None,
) -> dict[str, Any]:
    """
    Run ProjectDiscovery Nuclei against a single URL.
    Uses JSON lines on stdout (-jsonl -silent). Templates must be present (run nuclei -update-templates).
    """
    exe = _which("nuclei")
    if not exe:
        return {
            "tool": "nuclei",
            "available": False,
            "error": "nuclei not found in PATH",
            "findings": [],
        }

    cmd = [
        exe,
        "-u",
        target_url,
        "-jsonl",
        "-silent",
        "-no-color",
    ]
    if severity:
        cmd.extend(["-severity", severity])
    else:
        cmd.extend(["-severity", "critical,high,medium,low"])
    if tags:
        cmd.extend(["-tags", tags])

    raw = await _run_cmd(cmd, timeout=settings.red_team_nuclei_timeout)
    findings = _parse_jsonl(raw["stdout"])
    return {
        "tool": "nuclei",
        "available": True,
        "target_url": target_url,
        "tags": tags,
        "severity_filter": severity or "critical,high,medium,low",
        "exit_code": raw["exit_code"],
        "stderr": raw["stderr"][:8000],
        "findings": findings[:200],
        "findings_truncated": len(findings) > 200,
    }


async def run_ffuf_directory_fuzz(
    base_url: str,
    *,
    wordlist_path: str | None = None,
) -> dict[str, Any]:
    """
    FFUF directory discovery: GET {base}/FUZZ with a wordlist.
    base_url should be scheme+host[+port], e.g. http://dvwa:80
    """
    exe = _which("ffuf")
    if not exe:
        return {
            "tool": "ffuf",
            "available": False,
            "error": "ffuf not found in PATH",
            "results": [],
        }

    wl = Path(wordlist_path) if wordlist_path else _default_wordlist()
    if not wl.is_file():
        return {
            "tool": "ffuf",
            "available": True,
            "error": f"wordlist not found: {wl}",
            "results": [],
        }

    base = base_url.rstrip("/")
    url = f"{base}/FUZZ"

    fd, out_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        cmd = [
            exe,
            "-w",
            str(wl),
            "-u",
            url,
            "-of",
            "json",
            "-o",
            out_path,
            "-t",
            "20",
            "-timeout",
            "5",
            "-ac",
        ]
        raw = await _run_cmd(cmd, timeout=settings.red_team_ffuf_timeout)
        body = Path(out_path).read_text(encoding="utf-8", errors="replace")
        try:
            parsed = json.loads(body) if body.strip() else {}
        except json.JSONDecodeError:
            parsed = {"raw": body[:4000]}
        results = parsed.get("results") if isinstance(parsed, dict) else []
        if not isinstance(results, list):
            results = []
        return {
            "tool": "ffuf",
            "available": True,
            "target_url": url,
            "wordlist": str(wl),
            "exit_code": raw["exit_code"],
            "stderr": raw["stderr"][:4000],
            "results": results[:300],
            "results_truncated": len(results) > 300,
        }
    finally:
        try:
            os.unlink(out_path)
        except OSError:
            pass


async def run_sqlmap_probe(
    target_url: str,
    *,
    extra_args: str | None = None,
) -> dict[str, Any]:
    """
    Run sqlmap against a URL that includes an injectable parameter (e.g. ...?id=1).
    Uses conservative batch defaults; scope to a single URL only.
    """
    exe = _which("sqlmap")
    if not exe:
        return {
            "tool": "sqlmap",
            "available": False,
            "error": "sqlmap not found in PATH",
            "summary": None,
        }

    cmd = [
        exe,
        "-u",
        target_url,
        "--batch",
        "--flush-session",
        "--timeout=30",
        "--retries=1",
        "--risk=1",
        "--level=1",
        "--threads=1",
    ]
    if extra_args:
        cmd.extend(extra_args.split())

    raw = await _run_cmd(cmd, timeout=settings.red_team_sqlmap_timeout)
    out = raw["stdout"] + "\n" + raw["stderr"]
    return {
        "tool": "sqlmap",
        "available": True,
        "target_url": target_url,
        "exit_code": raw["exit_code"],
        "output_excerpt": out[:12000],
        "likely_vulnerable": any(
            s in out.lower()
            for s in (
                "is vulnerable",
                "injectable",
                "parameter: ",
                "type: boolean-based",
                "type: error-based",
                "type: time-based",
                "type: union query",
            )
        ),
    }
