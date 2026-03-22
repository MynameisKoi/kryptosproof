from pydantic import BaseModel, Field
from typing import Literal


class FilePatch(BaseModel):
    file_path: str
    original_snippet: str
    patched_snippet: str
    explanation: str


class FixScriptResult(BaseModel):
    vulnerability_type: str
    severity: Literal["critical", "high", "medium", "low"]
    root_cause: str = Field(description="Why the vulnerability exists")
    fix_description: str = Field(description="Human-readable explanation of the fix")
    patches: list[FilePatch]
    fix_script: str = Field(
        description="Full Python/bash script that applies the fixes to the target environment"
    )
    dependencies_required: list[str] = Field(
        default_factory=list,
        description="Any new packages/libraries required by the fix"
    )
    references: list[str] = Field(
        default_factory=list,
        description="CVE IDs, OWASP links, or other references"
    )
