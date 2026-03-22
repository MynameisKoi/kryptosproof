"""
Gitleaks — secret scanning on a local source tree (blue team / supply-chain).
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


def _which() -> str | None:
    return shutil.which("gitleaks")


async def run_gitleaks(repo_path: str) -> dict[str, Any]:
    """Run gitleaks detect with JSON report. repo_path must be a directory."""
    exe = _which()
    path = Path(repo_path).resolve()
    if not exe:
        return {"tool": "gitleaks", "available": False, "error": "gitleaks not found in PATH", "findings": []}
    if not path.is_dir():
        return {"tool": "gitleaks", "available": True, "error": f"not a directory: {path}", "findings": []}

    fd, out = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        cmd = [
            exe,
            "detect",
            "--source",
            str(path),
            "--report-path",
            out,
            "--report-format",
            "json",
        ]
        if not (path / ".git").exists():
            cmd.append("--no-git")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy(),
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(),
                timeout=settings.gitleaks_timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            return {
                "tool": "gitleaks",
                "available": True,
                "error": f"timeout after {settings.gitleaks_timeout}s",
                "findings": [],
            }

        stderr = stderr_b.decode("utf-8", errors="replace")
        raw = Path(out).read_text(encoding="utf-8", errors="replace")
        findings: list[dict[str, Any]] = []
        if raw.strip():
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    findings = data[:500]
                elif isinstance(data, dict) and "findings" in data:
                    findings = list(data["findings"])[:500]
            except json.JSONDecodeError:
                pass

        return {
            "tool": "gitleaks",
            "available": True,
            "repo_path": str(path),
            "exit_code": proc.returncode or 0,
            "stderr_excerpt": stderr[:4000],
            "findings": findings,
            "findings_truncated": len(findings) >= 500,
        }
    finally:
        try:
            os.unlink(out)
        except OSError:
            pass
