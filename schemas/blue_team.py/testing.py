from pydantic import BaseModel, Field
from typing import Literal


class VulnerabilityCheckResult(BaseModel):
    vulnerability_type: str
    patched: bool
    evidence: str = Field(description="HTTP response or log excerpt proving the result")
    remaining_risk: str | None = None


class TestResult(BaseModel):
    overall_patched: bool
    checks: list[VulnerabilityCheckResult]
    status: Literal["fully_patched", "partially_patched", "failed"]
    residual_vulnerabilities: list[str] = Field(
        default_factory=list,
        description="Vulnerabilities that still exist after patching"
    )
    recommendation: str
    retest_stdout: str
    retest_stderr: str
