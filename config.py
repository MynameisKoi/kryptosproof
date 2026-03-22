import os
from typing import Literal, Self

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM — MODEL / AI_MODEL set the pydantic-ai model id; Gemini auth from any of these env names
    model: str = Field(
        default=os.getenv("AI_MODEL", ""),
    )
    gemini_api_key: str = Field(
        default="",
        description="Gemini / Google AI Studio API key (pydantic-ai reads GEMINI_API_KEY from the environment).",
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_AI_API", "GOOGLE_API_KEY"),
    )

    @model_validator(mode="after")
    def normalize_model_and_sync_gemini_env(self) -> Self:
        """Add provider prefix when a bare model name is given (gpt-* → openai:, gemini-* → google-gla:)."""
        m = self.model.strip()
        if not m:
            self.model = "anthropic:claude-opus-4-6"
        elif ":" not in m:
            low = m.lower()
            if low.startswith("gemini"):
                self.model = f"google-gla:{m}"
            elif low.startswith(("gpt-", "o1-", "o3-", "o4-")):
                self.model = f"openai:{m}"

        key = self.gemini_api_key.strip()
        if key:
            os.environ.setdefault("GEMINI_API_KEY", key)
        return self

    # Target
    target_url: str = "http://dvwa:80"

    # Docker sandbox
    sandbox_image: str = "python:3.11-slim"
    sandbox_network: str = "kryptosproof_sandbox"
    sandbox_timeout: int = 30  # seconds

    # Attack script quality (Agent 1)
    attack_script_min_chars: int = 80
    max_attack_script_bytes: int = 400_000
    attack_output_retries: int = 4  # pydantic-ai output validation / ModelRetry rounds

    # Execution logs stored on ExecutionResult
    max_execution_output_chars: int = 400_000

    # Red team external CLIs (Nuclei, FFUF, SQLMap)
    red_team_nuclei_timeout: int = 120
    red_team_ffuf_timeout: int = 90
    red_team_sqlmap_timeout: int = 180

    # PayloadsAllTheThings — local clone path (see third_party/)
    payloads_root: str = "third_party/PayloadsAllTheThings"

    # Blue team — Gitleaks (optional local repo)
    source_repo_path: str | None = None
    gitleaks_timeout: int = 120

    # Blue team — patch workspace mirror source (optional host path to copy into workspace)
    blue_team_mirror_source: str | None = None

    # OWASP ZAP JSON API (ZAP daemon must be running)
    zap_proxy_url: str = "http://127.0.0.1:8080"
    zap_api_key: str = ""
    zap_http_timeout: float = 45.0
    zap_spider_max_wait: int = 180

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Logfire (optional — empty disables token-based features in tests/CI)
    logfire_token: str = ""
    logfire_environment: str = ""


settings = Settings()
