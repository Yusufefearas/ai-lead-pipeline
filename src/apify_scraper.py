"""Apify-based LinkedIn profile search scraper.

Targets apimaestro/linkedin-profile-search-scraper, which searches by
structured params (job title, location, name) and needs no cookies.
Email discovery is intentionally left OFF: LinkedIn DM is the primary
channel and guessed emails add low-quality, undeliverable data.

The actor returns a nested object per profile (basic_info + experience[]),
so normalization flattens it to our canonical lead schema.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

import pandas as pd
from apify_client import ApifyClient

from .config import Settings, get_settings, require
from .logger import get_logger

log = get_logger(__name__)

RAW_CSV = "data/raw/raw_leads.csv"
BASE_COLS = [
    "full_name",
    "company",
    "title",
    "linkedin_url",
    "email",
    "location",
    "english_proficiency",
]


@dataclass
class SearchSpec:
    """One LinkedIn search. At least one field must be set."""

    current_job_title: str = ""
    location: str = ""
    firstname: str = ""
    lastname: str = ""


def build_actor_input(spec: SearchSpec, max_profiles: int = 100) -> dict:
    """Map a SearchSpec to the actor's input payload.

    max_profiles caps how many profiles the actor pulls per run, so a
    small --max-leads does not silently bill for 100 profiles.
    """
    payload = {
        "current_job_title": spec.current_job_title,
        "location": spec.location,
        "firstname": spec.firstname,
        "lastname": spec.lastname,
        "max_profiles": max(1, max_profiles),
        "include_email": False,  # email discovery off by design
    }
    # Drop empty strings, but keep False / ints.
    return {k: v for k, v in payload.items() if v not in ("", None)}


def _current_role(experience: object) -> tuple[str, str]:
    """Return (title, company) for the current or most-recent experience."""
    if not isinstance(experience, list) or not experience:
        return "", ""
    for exp in experience:
        if isinstance(exp, dict) and exp.get("is_current"):
            return str(exp.get("title", "")), str(exp.get("company", ""))
    first = experience[0] if isinstance(experience[0], dict) else {}
    return str(first.get("title", "")), str(first.get("company", ""))


def _english_proficiency(languages: object) -> str:
    """Return the self-reported English proficiency from the languages list."""
    if not isinstance(languages, list):
        return ""
    for lang in languages:
        if isinstance(lang, dict) and "english" in str(lang.get("language", "")).lower():
            return str(lang.get("proficiency", "")).strip()
    return ""


def normalize_item(item: dict) -> dict:
    """Flatten one nested actor profile into our canonical lead schema."""
    basic = item.get("basic_info") or {}
    title, company = _current_role(item.get("experience"))

    location = basic.get("location") or {}
    if isinstance(location, dict):
        location = location.get("full") or location.get("city") or ""

    full_name = basic.get("fullname") or (
        f"{basic.get('first_name', '')} {basic.get('last_name', '')}".strip()
    )

    return {
        "full_name": str(full_name).strip(),
        "company": str(company or basic.get("current_company") or "").strip(),
        "title": str(title or basic.get("headline") or "").strip(),
        "linkedin_url": str(basic.get("profile_url") or "").strip(),
        "email": str(basic.get("email") or "").strip(),
        "location": str(location).strip(),
        "english_proficiency": _english_proficiency(item.get("languages")),
    }


def run_apify_scraper(
    searches: Iterable[SearchSpec],
    max_leads: int = 100,
    settings: Settings | None = None,
) -> pd.DataFrame:
    """Run the actor per search until max_leads is reached, save raw_leads.csv."""
    settings = settings or get_settings()
    require(settings, "apify_api_token", "apify_actor_id")
    client = ApifyClient(settings.apify_api_token)

    rows: list[dict] = []
    for spec in searches:
        remaining = max_leads - len(rows)
        if remaining <= 0:
            break
        actor_input = build_actor_input(spec, max_profiles=min(remaining, 100))
        log.info("Running Apify actor for: %s", actor_input)
        try:
            run = client.actor(settings.apify_actor_id).call(run_input=actor_input)
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                row = normalize_item(item)
                if not row["full_name"]:
                    continue
                if not row["linkedin_url"]:
                    log.warning("Lead without LinkedIn URL: %s", row["full_name"])
                rows.append(row)
                if len(rows) >= max_leads:
                    break
        except Exception as exc:  # keep going across searches
            log.error("Apify search failed for %s: %s", actor_input, exc)

    df = pd.DataFrame(rows, columns=BASE_COLS)
    os.makedirs(os.path.dirname(RAW_CSV), exist_ok=True)
    df.to_csv(RAW_CSV, index=False)
    log.info("Saved %d raw leads -> %s", len(df), RAW_CSV)
    return df
