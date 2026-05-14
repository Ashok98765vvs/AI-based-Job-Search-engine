"""Central configuration loaded from environment variables."""
from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).parent


def _split(v: str) -> List[str]:
    return [s.strip() for s in v.split(",") if s.strip()]


class Settings(BaseSettings):
    """All runtime configuration. Reads from .env automatically."""

    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout: int = 120

    # DB
    database_url: str = "sqlite:///data/jobintel.db"

    # Freshness
    fresh_window_hours: int = 24

    # Scraping
    http_concurrency: int = 10
    http_rate_per_sec: int = 5
    http_timeout: int = 30
    http_retries: int = 3
    cache_ttl_seconds: int = 900

    # Boards (comma separated env vars)
    greenhouse_boards: str = "airbnb,stripe,doordash"
    lever_boards: str = "netflix,palantir,ramp"
    ashby_boards: str = "openai,vanta,posthog,linear"

    # Adzuna
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "us"
    adzuna_results_per_page: int = 50

    # Logs
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    # Derived helpers ---------------------------------------------------
    @property
    def greenhouse_list(self) -> List[str]:
        return _split(self.greenhouse_boards)

    @property
    def lever_list(self) -> List[str]:
        return _split(self.lever_boards)

    @property
    def ashby_list(self) -> List[str]:
        return _split(self.ashby_boards)

    @property
    def root(self) -> Path:
        return ROOT


settings = Settings()

# Ensure required runtime dirs exist.
for sub in ("data", "logs", "exports", "resumes"):
    (ROOT / sub).mkdir(parents=True, exist_ok=True)
