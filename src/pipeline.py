"""End-to-end pipeline orchestration.

Scrape -> clean -> enrich (1 call) -> LinkedIn DM (1 call) ->
cold email (1 call) -> CSV -> optional Google Sheets. A single failing
lead never stops the run.
"""
from __future__ import annotations

import os
from typing import Iterable

import pandas as pd

from .agents.cleaning_agent import clean_leads, qualify_leads
from .agents.email_agent import EmailAgent
from .agents.enrichment_agent import EnrichmentAgent
from .agents.followup_agent import FollowUpAgent
from .agents.linkedin_agent import LinkedInAgent
from .agents.reply_classifier_agent import ReplyClassifierAgent
from .apify_scraper import RAW_CSV, SearchSpec, run_apify_scraper
from .config import get_settings
from .logger import get_logger
from .models import FINAL_COLUMNS, CleanLead, EnrichedLead, EnrichmentResult

log = get_logger(__name__)

OUTPUT_CSV = "output/enriched_leads.csv"
SAMPLE_CSV = "data/sample/sample_leads.csv"
REPLIES_CSV = "data/sample/sample_replies.csv"
CLASSIFIED_CSV = "output/classified_replies.csv"


def _process_lead(
    lead: CleanLead,
    enrich_agent: EnrichmentAgent,
    linkedin_agent: LinkedInAgent,
    email_agent: EmailAgent,
    followup_agent: FollowUpAgent,
) -> EnrichedLead:
    enrichment = enrich_agent.run(lead)
    linkedin = linkedin_agent.run(lead, enrichment)
    email = email_agent.run(lead, enrichment)
    followup = followup_agent.run(lead, enrichment, linkedin.linkedin_dm)
    return EnrichedLead(
        **lead.model_dump(),
        **enrichment.model_dump(),
        linkedin_dm=linkedin.linkedin_dm,
        linkedin_followup=followup.linkedin_followup,
        email_subject=email.email_subject,
        email_body=email.email_body,
    )


def run_pipeline(
    searches: Iterable[SearchSpec],
    max_leads: int = 100,
    sample: bool = False,
    from_cache: bool = False,
) -> None:
    settings = get_settings()

    if sample:
        log.info("Sample mode: loading bundled leads from %s", SAMPLE_CSV)
        raw_df = pd.read_csv(SAMPLE_CSV).fillna("")
    elif from_cache:
        log.info("Using cached raw leads from %s (no Apify call)", RAW_CSV)
        raw_df = pd.read_csv(RAW_CSV).fillna("")
    else:
        log.info("Starting pipeline (max_leads=%d)", max_leads)
        raw_df = run_apify_scraper(searches, max_leads=max_leads, settings=settings)

    if raw_df.empty:
        log.error("No leads collected. Aborting.")
        return

    clean_df = clean_leads(raw_df)
    clean_df = qualify_leads(clean_df)
    if clean_df.empty:
        log.error("No qualified leads after filtering. Aborting.")
        return
    log.info("Qualified dataset: %d leads", len(clean_df))

    enrich_agent = EnrichmentAgent(settings)
    linkedin_agent = LinkedInAgent(settings)
    email_agent = EmailAgent(settings)
    followup_agent = FollowUpAgent(settings)

    enriched_rows: list[dict] = []
    total = len(clean_df)
    for i, record in enumerate(clean_df.to_dict(orient="records"), start=1):
        lead = CleanLead(**record)
        log.info("Enriching lead %d/%d: %s", i, total, lead.full_name)
        try:
            enriched = _process_lead(
                lead, enrich_agent, linkedin_agent, email_agent, followup_agent
            )
            enriched_rows.append(enriched.to_row())
        except Exception as exc:  # never crash on a single lead
            log.error("Failed lead %s: %s", lead.full_name, exc)

    out_df = pd.DataFrame(enriched_rows, columns=FINAL_COLUMNS)
    out_df = out_df.sort_values("lead_score", ascending=False).reset_index(drop=True)
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    out_df.to_csv(OUTPUT_CSV, index=False)
    log.info("Saved %d enriched leads -> %s", len(out_df), OUTPUT_CSV)

    from .sheets import upload_to_google_sheets

    upload_to_google_sheets(out_df, settings=settings)
    log.info("Pipeline completed.")


def backfill_followups(csv_path: str = OUTPUT_CSV) -> None:
    """Add a linkedin_followup column to an existing enriched CSV.

    Reuses the already-computed enrichment + first DM, so it costs only
    one extra AI call per lead (no re-scraping, no re-enrichment).
    """
    settings = get_settings()
    df = pd.read_csv(csv_path).fillna("")
    followup_agent = FollowUpAgent(settings)

    followups: list[str] = []
    total = len(df)
    for i, record in enumerate(df.to_dict(orient="records"), start=1):
        lead = CleanLead(**{k: record.get(k, "") for k in CleanLead.model_fields})
        enrichment = EnrichmentResult(
            **{k: record.get(k, "") for k in EnrichmentResult.model_fields if record.get(k, "") != ""}
        )
        log.info("Follow-up %d/%d: %s", i, total, lead.full_name)
        try:
            msg = followup_agent.run(lead, enrichment, str(record.get("linkedin_dm", "")))
            followups.append(msg.linkedin_followup)
        except Exception as exc:
            log.error("Follow-up failed for %s: %s", lead.full_name, exc)
            followups.append("")

    df["linkedin_followup"] = followups
    df = df.reindex(columns=FINAL_COLUMNS)
    df.to_csv(csv_path, index=False)
    log.info("Backfilled follow-ups -> %s", csv_path)


def regenerate_outreach(csv_path: str = OUTPUT_CSV) -> None:
    """Regenerate DM + email + follow-up for an existing enriched CSV.

    Reuses the stored enrichment, so it re-runs only the 3 outreach calls
    per lead (no re-scraping, no re-enrichment) — handy for iterating on
    messaging/brand voice.
    """
    settings = get_settings()
    df = pd.read_csv(csv_path).fillna("")
    linkedin_agent = LinkedInAgent(settings)
    email_agent = EmailAgent(settings)
    followup_agent = FollowUpAgent(settings)

    total = len(df)
    for i, record in enumerate(df.to_dict(orient="records"), start=1):
        lead = CleanLead(**{k: record.get(k, "") for k in CleanLead.model_fields})
        enrichment = EnrichmentResult(
            **{k: record.get(k, "") for k in EnrichmentResult.model_fields if record.get(k, "") != ""}
        )
        log.info("Regenerating outreach %d/%d: %s", i, total, lead.full_name)
        try:
            linkedin = linkedin_agent.run(lead, enrichment)
            email = email_agent.run(lead, enrichment)
            followup = followup_agent.run(lead, enrichment, linkedin.linkedin_dm)
            df.at[i - 1, "linkedin_dm"] = linkedin.linkedin_dm
            df.at[i - 1, "linkedin_followup"] = followup.linkedin_followup
            df.at[i - 1, "email_subject"] = email.email_subject
            df.at[i - 1, "email_body"] = email.email_body
        except Exception as exc:
            log.error("Outreach regen failed for %s: %s", lead.full_name, exc)

    df = df.reindex(columns=FINAL_COLUMNS)
    df.to_csv(csv_path, index=False)
    log.info("Regenerated outreach -> %s", csv_path)


def classify_replies(
    input_csv: str = REPLIES_CSV, output_csv: str = CLASSIFIED_CSV
) -> None:
    """Classify inbound replies and suggest a CRM status + next step for each.

    Input CSV needs at least a `reply` column (optionally full_name, company).
    """
    settings = get_settings()
    df = pd.read_csv(input_csv).fillna("")
    agent = ReplyClassifierAgent(settings)

    rows: list[dict] = []
    total = len(df)
    for i, record in enumerate(df.to_dict(orient="records"), start=1):
        reply = str(record.get("reply", ""))
        name = str(record.get("full_name", ""))
        company = str(record.get("company", ""))
        log.info("Classifying reply %d/%d: %s", i, total, name or "(unknown)")
        try:
            result = agent.run(reply, name, company)
            rows.append(
                {
                    "full_name": name,
                    "company": company,
                    "reply": reply,
                    "reply_category": result.reply_category,
                    "reply_sentiment": result.reply_sentiment,
                    "suggested_crm_status": result.suggested_crm_status,
                    "suggested_next_step": result.suggested_next_step,
                    "classification_reason": result.classification_reason,
                }
            )
        except Exception as exc:
            log.error("Reply classification failed for %s: %s", name, exc)

    out_df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    out_df.to_csv(output_csv, index=False)
    log.info("Classified %d replies -> %s", len(out_df), output_csv)
