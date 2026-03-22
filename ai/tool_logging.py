"""Log agent tool calls and attach a short line to each tool result for the model."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("kryptosproof.tools")


def tool_return(name: str, value: Any, detail: str = "") -> Any:
    """
    Emit a log line for this tool call and return `value` with a `tool_log` field
    (or wrap non-dicts so the model always sees the log).
    """
    line = f"{name}" + (f": {detail}" if detail else "")
    logger.info("tool_call %s", line)
    msg = f"[{name}] {detail}".strip() if detail else f"[{name}]"

    if isinstance(value, dict):
        return {**value, "tool_log": msg}
    if isinstance(value, list):
        return {"data": value, "tool_log": msg}
    if isinstance(value, str):
        return {"result": value, "tool_log": msg}
    return {"result": value, "tool_log": msg}


def tool_return_json(name: str, obj: dict[str, Any], detail: str = "") -> str:
    """Like tool_return but for orchestrator tools that return JSON strings."""
    line = f"{name}" + (f": {detail}" if detail else "")
    logger.info("tool_call %s", line)
    msg = f"[{name}] {detail}".strip() if detail else f"[{name}]"
    return json.dumps({**obj, "tool_log": msg})
