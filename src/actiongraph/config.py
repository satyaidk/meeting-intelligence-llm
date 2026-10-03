"""Application configuration.

Every setting comes from an environment variable prefixed with ``ACTIONGRAPH_``
(or from a local ``.env`` file). Nothing secret is hard-coded.

Why pydantic-settings instead of ``os.getenv``? Settings are *typed and
validated*: ``ACTIONGRAPH_REVIEW_THRESHOLD=abc`` fails loudly at start-up
instead of causing a confusing bug deep inside the pipeline.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ACTIONGRAPH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---------------------------------------------------------------
    llm_provider: Literal["anthropic", "offline"] = "anthropic"
    anthropic_model: str = "claude-opus-5-5"
    anthropic_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    anthropic_max_tokens: int = Field(16000, gt=0)
    anthropic_enable_fallback: bool = True
    # The SDK reads ANTHROPIC_API_KEY from the real environment by itself, but a
    # value written only in `.env` would not reach it - so we load it here too.
    # SecretStr keeps the key out of logs and reprs.
    anthropic_api_key: SecretStr | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")

    # --- Storage -----------------------------------------------------------
    database_url: str = "sqlite:///data/actiongraph.db"

    # --- Human-in-the-loop -------------------------------------------------
    review_threshold: float = Field(0.7, ge=0.0, le=1.0)

    # --- Speech-to-text ----------------------------------------------------
    whisper_model: str = "base"
    whisper_device: str = "cpu"

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings (read once, then cached)."""
    return Settings()
