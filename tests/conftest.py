"""Load `.env` so integration tests can see API keys during collection."""

import os

from dotenv import load_dotenv

load_dotenv()

# Importing `Agent(...)` validates the configured provider; allow collection without real keys.
if not any(
    os.getenv(k)
    for k in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_AI_API",
    )
):
    os.environ.setdefault("OPENAI_API_KEY", "test-mock-import-only")
