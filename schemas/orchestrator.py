from pydantic import BaseModel, Field
from typing import Literal


class VulnerabilityReport(BaseModel):
    type: str
    severity: Literal["critical", "high", "medium", "low"]
    confirmed: bool
    patched: bool
    description: str


class SecurityAuditReport(BaseModel):
    target_url: str
    vulnerabilities_found: list[VulnerabilityReport]
    total_vulnerabilities: int
    patched_count: int
    overall_status: Literal["secure", "vulnerable", "partially_patched"]
    attack_summary: str
    fix_summary: str
    recommendations: list[str]
    report_markdown: str = Field(
        description="Full human-readable markdown report of the audit"
    )
