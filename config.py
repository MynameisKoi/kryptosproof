from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM (optional env overrides; agents may still use a fixed provider string)
    open_ai_api: str = Field(default="", description="Optional API key for Google AI if used")
    model: str = Field(default="anthropic:claude-opus-4-6")

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
