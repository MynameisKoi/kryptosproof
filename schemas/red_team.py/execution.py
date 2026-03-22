from pydantic import BaseModel, Field
from typing import Literal


class SandboxInfo(BaseModel):
    container_id: str = ""
    image: str = ""
    network: str = ""


class ExecutionResult(BaseModel):
    attack_type: str = ""
    target_url: str = ""
    sandbox: SandboxInfo = Field(default_factory=SandboxInfo)
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    crash_detected: bool = False
    vulnerabilities_confirmed: list[str] = Field(
        default_factory=list,
        description="List of vulnerability types confirmed by the execution"
    )
    error_logs: str = Field(
        default="",
        description="Parsed error logs relevant to blue team patching"
    )
    logs: str = Field(
        default="",
        description="Combined human-readable run log (status, stdout/stderr excerpts) for agents and tracing",
    )
    status: Literal["exploited", "failed", "partial", "error"] = "failed"
    raw_responses: list[dict] = Field(
        default_factory=list,
        description="HTTP responses captured during execution"
    )
