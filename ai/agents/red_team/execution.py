"""
Red Team — execution is deterministic (see tools.execution_pipeline + tools.sandbox).
This module re-exports the pipeline for imports and docs.
"""
from dataclasses import dataclass

from schemas import AttackScriptResult
from tools.execution_pipeline import run_attack_execution

__all__ = ["run_attack_execution", "ExecutionDeps"]


@dataclass
class ExecutionDeps:
    """Legacy shape kept for callers that built deps for the old execution agent."""

    attack_script: AttackScriptResult
    target_url: str
