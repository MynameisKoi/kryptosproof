from pydantic import BaseModel, Field


class BlueTeamHandoffReport(BaseModel):
    """Returned when blue team stops without fully patching (e.g. iteration limit)."""

    summary_of_attempts: str = Field(
        description="What was tried in each iteration (fixes, apply results, verification outcomes)"
    )
    failure_analysis: str = Field(
        description="Why the vulnerability remains or verification failed; note regressions or "
        "when fixing one issue may surface another (e.g. stricter validation breaks a flow)"
    )
    developer_recommendations: list[str] = Field(
        description="Ordered, actionable next steps for the development team"
    )
