"""
Read payload lines from a local PayloadsAllTheThings checkout (or any tree under PAYLOADS_ROOT).
Clone: git clone https://github.com/swisskyrepo/PayloadsAllTheThings.git third_party/PayloadsAllTheThings
"""
from __future__ import annotations

from pathlib import Path

from config import settings
from tools.tool_logs import merge_tool_logs, with_logs


def _root() -> Path:
    base = Path(settings.payloads_root)
    if not base.is_absolute():
        base = Path.cwd() / base
    return base.resolve()


def _safe_relative(path: str) -> Path:
    rel = Path(path.strip().replace("\\", "/").lstrip("/"))
    if ".." in rel.parts or rel.is_absolute():
        raise ValueError("invalid path")
    return rel


def search_payload_files(keyword: str, *, max_results: int = 80) -> dict:
    """Find .txt files under the payload root whose path contains keyword (case-insensitive)."""
    root = _root()
    if not root.is_dir():
        return with_logs(
            {
                "available": False,
                "root": str(root),
                "error": "PAYLOADS_ROOT does not exist — clone PayloadsAllTheThings (see project docs).",
                "matches": [],
            },
            f"PAYLOADS_ROOT missing: {root}",
        )
    kw = keyword.lower()
    matches: list[str] = []
    for p in root.rglob("*.txt"):
        try:
            rel = p.relative_to(root)
        except ValueError:
            continue
        if kw in str(rel).lower():
            matches.append(str(rel).replace("\\", "/"))
            if len(matches) >= max_results:
                break
    return with_logs(
        {
            "available": True,
            "root": str(root),
            "keyword": keyword,
            "matches": matches,
            "truncated": len(matches) >= max_results,
        },
        merge_tool_logs(
            f"pat_search keyword={keyword!r}",
            f"matches: {len(matches)} path(s)" + (" (truncated)" if len(matches) >= max_results else ""),
        ),
    )


def read_payload_lines(relative_path: str, *, max_lines: int = 60) -> dict:
    """Read up to max_lines non-empty lines from a file under PAYLOADS_ROOT."""
    root = _root()
    try:
        rel = _safe_relative(relative_path)
    except ValueError as e:
        return with_logs({"available": False, "error": str(e), "lines": []}, str(e))
    path = (root / rel).resolve()
    if not str(path).startswith(str(root)) or not path.is_file():
        return with_logs(
            {"available": False, "error": "file not found or outside payload root", "lines": []},
            "file not found or outside payload root",
        )
    lines: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return with_logs({"available": False, "error": str(e), "lines": []}, str(e))
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s[:500])
        if len(lines) >= max_lines:
            break
    return with_logs(
        {
            "available": True,
            "path": str(rel).replace("\\", "/"),
            "lines": lines,
            "truncated": len(lines) >= max_lines,
        },
        merge_tool_logs(
            f"pat_read path={rel.as_posix()!r}",
            f"lines returned: {len(lines)}" + (" (truncated)" if len(lines) >= max_lines else ""),
        ),
    )
