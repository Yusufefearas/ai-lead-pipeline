"""CLI entry point.

    python -m src.main sample
    python -m src.main run --job-title "HR Manager" --location "Istanbul, Turkey" --max-leads 100
"""
from __future__ import annotations

import typer

from .apify_scraper import SearchSpec
from .config import get_settings
from .pipeline import (
    OUTPUT_CSV,
    backfill_followups,
    classify_replies,
    regenerate_outreach,
    run_pipeline,
)

app = typer.Typer(
    add_completion=False,
    help="AI lead pipeline: find B2B leads, score them and write personalised outreach.",
)

DEFAULT_JOB_TITLES = [
    "HR Manager",
    "Human Resources Manager",
    "Talent Acquisition Specialist",
    "Recruiter",
    "People and Culture Manager",
    "Learning and Development Specialist",
]
DEFAULT_LOCATIONS = ["Istanbul, Turkey", "Ankara, Turkey", "Izmir, Turkey"]


def _build_searches(job_titles: list[str], locations: list[str]) -> list[SearchSpec]:
    return [
        SearchSpec(current_job_title=title, location=loc)
        for loc in locations
        for title in job_titles
    ]


@app.command()
def run(
    job_title: list[str] = typer.Option(
        None, "--job-title", help="HR job title to search (repeatable)."
    ),
    location: list[str] = typer.Option(
        None, "--location", help="Location to search (repeatable)."
    ),
    max_leads: int = typer.Option(
        None, "--max-leads", help="Max leads to collect (default from MAX_LEADS)."
    ),
    from_cache: bool = typer.Option(
        False, "--from-cache", help="Reprocess the cached raw_leads.csv instead of calling Apify."
    ),
) -> None:
    """Run the full pipeline against live Apify search (or cached raw leads)."""
    settings = get_settings()
    titles = job_title or DEFAULT_JOB_TITLES
    locations = location or DEFAULT_LOCATIONS
    searches = _build_searches(titles, locations)
    run_pipeline(
        searches,
        max_leads=max_leads or settings.max_leads,
        sample=False,
        from_cache=from_cache,
    )


@app.command()
def sample() -> None:
    """Run the full AI pipeline on a small bundled sample (no Apify needed; OpenAI key required)."""
    run_pipeline([], max_leads=5, sample=True)


@app.command()
def followup() -> None:
    """Add a multi-step follow-up message to an existing enriched CSV (1 AI call/lead, no re-scrape)."""
    backfill_followups(OUTPUT_CSV)


@app.command()
def outreach() -> None:
    """Regenerate DM + email + follow-up on the existing enriched CSV (e.g. after editing config/brand.yaml)."""
    regenerate_outreach(OUTPUT_CSV)


@app.command()
def classify() -> None:
    """Auto-classify inbound replies (data/sample/sample_replies.csv) into category + CRM status."""
    classify_replies()


@app.command()
def upload() -> None:
    """Upload the existing enriched CSV to Google Sheets (needs GOOGLE_* env vars)."""
    import pandas as pd

    from .sheets import upload_to_google_sheets

    df = pd.read_csv(OUTPUT_CSV).fillna("")
    upload_to_google_sheets(df)


if __name__ == "__main__":
    app()
