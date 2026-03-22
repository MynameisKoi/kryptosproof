from pydantic import BaseModel, Field
from typing import Literal


class AttackPayload(BaseModel):
    name: str
    payload: str
    endpoint: str
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    params: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None


class AttackScriptResult(BaseModel):
    vulnerability_type: str = Field(
        description="e.g. SQL Injection, XSS, CSRF, Path Traversal, Command Injection, SSRF, Broken Auth"
    )
    severity: Literal["critical", "high", "medium", "low"]
    target_url: str
    description: str = Field(description="What this attack does and why it works")
    target_endpoints: list[str]
    payloads: list[AttackPayload]
    script: str = Field(description="Full Python script that runs all payloads via httpx")
    expected_indicators: list[str] = Field(
        description="Strings/patterns in the response that confirm successful exploitation"
    )
