from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    # LLM
    anthropic_api_key: str = ""
    model: str = "claude-opus-4-6"

    # Target
    target_url: str = "http://dvwa:80"

    # Docker sandbox
    sandbox_image: str = "python:3.11-slim"
    sandbox_network: str = "kryptosproof_sandbox"
    sandbox_timeout: int = 30  # seconds

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
