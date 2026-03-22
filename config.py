from pydantic_settings import BaseSettings
from typing import Literal
from dotenv import load_dotenv
import os
load_dotenv()

class Settings(BaseSettings):
    # LLM
    open_ai_api: str = os.getenv("GOOGLE_AI_API")
    model: str = os.getenv("AI_MODEL")

    # Target
    target_url: str = ""

    # Docker sandbox
    sandbox_image: str = "python:3.11-slim"
    sandbox_network: str = "kryptosproof_sandbox"
    sandbox_timeout: int = 30  # seconds

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    # LogFire 
    logfire_token: str = os.getenv("LOGFIRE_TOKEN")
    logfire_environment: str = os.getenv("LOGFIRE_ENVIRONMENT")
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
