"""
Every red-team tool result should include a human-readable `logs` string
(subprocess I/O, errors, or a short summary) so agents and observability can surface run output consistently.
"""

from __future__ import annotations

from typing import Any


def merge_tool_logs(*parts: str | None, max_chars: int = 24_000) -> str:
    """Join non-empty parts; truncate from the end if over max_chars."""
    text = "\n".join(p.strip() for p in parts if p and str(p).strip())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 32] + "\n... [logs truncated]"


def logs_from_run_cmd(
    raw: dict[str, Any],
    *,
    stdout_cap: int = 12_000,
    stderr_cap: int = 12_000,
) -> str:
    """Build log text from `_run_cmd` / similar dicts with command, exit_code, stdout, stderr, error."""
    bits: list[str] = []
    cmd = raw.get("command")
    if cmd:
        bits.append("command: " + " ".join(str(c) for c in cmd))
    if raw.get("exit_code") is not None:
        bits.append(f"exit_code: {raw['exit_code']}")
    if raw.get("error"):
        bits.append(f"error: {raw['error']}")
    so = raw.get("stdout") or ""
    se = raw.get("stderr") or ""
    if so:
        bits.append("stdout:\n" + str(so)[:stdout_cap])
    if se:
        bits.append("stderr:\n" + str(se)[:stderr_cap])
    return merge_tool_logs(*bits)


def with_logs(d: dict[str, Any], *extra: str | None, max_chars: int = 24_000) -> dict[str, Any]:
    """Return a shallow copy of `d` with `logs` set, merging prior `logs` and `extra` parts."""
    prior = d.get("logs")
    merged = merge_tool_logs(prior, *extra, max_chars=max_chars)
    out = dict(d)
    out["logs"] = merged
    return out
