"""Application configuration loaded from environment variables.

Single source of truth for credentials and tunables. No secrets are
hardcoded; everything comes from the environment (see .env.example).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_model: str
    openai_temperature: float
    apify_api_token: str | None
    apify_actor_id: str
    google_sheet_id: str | None
    google_service_account_json: str | None
    max_leads: int
    brand_config: str


class MissingConfigError(RuntimeError):
    """Raised when required configuration values are absent."""


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def get_settings() -> Settings:
    """Build a typed Settings object from the current environment."""
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        openai_temperature=_get_float("OPENAI_TEMPERATURE", 0.4),
        apify_api_token=os.getenv("APIFY_API_TOKEN"),
        apify_actor_id=os.getenv(
            "APIFY_ACTOR_ID", "apimaestro/linkedin-profile-search-scraper"
        ),
        google_sheet_id=os.getenv("GOOGLE_SHEET_ID"),
        google_service_account_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"),
        max_leads=_get_int("MAX_LEADS", 100),
        brand_config=os.getenv("BRAND_CONFIG") or "config/brand.yaml",
    )


def require(settings: Settings, *fields: str) -> None:
    """Raise a clear error if any of the given settings fields are empty."""
    missing = [f for f in fields if not getattr(settings, f, None)]
    if missing:
        raise MissingConfigError(
            "Missing required environment variables: "
            + ", ".join(f.upper() for f in missing)
        )
