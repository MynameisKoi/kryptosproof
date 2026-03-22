"""
Blue Team — Handoff Report Agent
Produces developer-facing summaries when patching stops short (e.g. iteration limit).
"""
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import Agent

from config import settings
from schemas import BlueTeamHandoffReport

_PROMPT = (Path(__file__).parent.parent.parent / "prompt" / "blue_team" / "handoff_report.md").read_text()


@dataclass
class HandoffReportDeps:
    """No runtime deps; context is passed in the user prompt."""

    pass


handoff_report_agent = Agent(
    model=settings.model,
    deps_type=HandoffReportDeps,
    output_type=BlueTeamHandoffReport,
    system_prompt=_PROMPT,
)
