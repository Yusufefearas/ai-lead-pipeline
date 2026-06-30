"""Pydantic data models for the lead pipeline.

EnrichmentResult holds the combined output of the single Enrichment
Agent (company intelligence + pain point + score + strategy).
"""
from __future__ import annotations

from pydantic import BaseModel, field_validator

COMPANY_SIZE_BUCKETS = ("SMB", "Mid-Market", "Enterprise")
REPLY_CATEGORIES = (
    "INTERESTED",
    "QUESTION",
    "NOT_INTERESTED",
    "OUT_OF_OFFICE",
    "UNSUBSCRIBE",
    "OTHER",
)

# Canonical column order for the final CSV and Google Sheet.
FINAL_COLUMNS = [
    "full_name",
    "company",
    "title",
    "linkedin_url",
    "email",
    "location",
    "english_proficiency",
    "company_sector",
    "company_size",
    "international_company",
    "english_training_probability",
    "pain_point",
    "pain_point_reason",
    "lead_score",
    "score_reason",
    "outreach_angle",
    "key_message",
    "linkedin_dm",
    "linkedin_followup",
    "email_subject",
    "email_body",
    "crm_status",
]


class CleanLead(BaseModel):
    full_name: str
    company: str = ""
    title: str = ""
    linkedin_url: str = ""
    email: str = ""
    location: str = ""
    english_proficiency: str = ""


class EnrichmentResult(BaseModel):
    """Combined enrichment output. All company fields are AI estimates."""

    company_sector: str = ""
    company_size: str = "SMB"
    international_company: bool = False
    english_training_probability: int = 5
    pain_point: str = ""
    pain_point_reason: str = ""
    lead_score: int = 50
    score_reason: str = ""
    outreach_angle: str = ""
    key_message: str = ""

    @field_validator("company_size")
    @classmethod
    def _bucket(cls, v: str) -> str:
        text = (v or "").strip()
        for bucket in COMPANY_SIZE_BUCKETS:
            if bucket.lower() == text.lower():
                return bucket
        low = text.lower()
        if any(k in low for k in ("enterprise", "large", "corp")):
            return "Enterprise"
        if any(k in low for k in ("mid", "medium")):
            return "Mid-Market"
        return "SMB"

    @field_validator("english_training_probability")
    @classmethod
    def _clamp_prob(cls, v: int) -> int:
        return max(1, min(10, int(v)))

    @field_validator("lead_score")
    @classmethod
    def _clamp_score(cls, v: int) -> int:
        return max(1, min(100, int(v)))


class LinkedInMessage(BaseModel):
    linkedin_dm: str = ""


class FollowUpMessage(BaseModel):
    linkedin_followup: str = ""


class ColdEmail(BaseModel):
    email_subject: str = ""
    email_body: str = ""


class ReplyClassification(BaseModel):
    """Auto-classification of an inbound reply, with a suggested CRM action."""

    reply_category: str = "OTHER"
    reply_sentiment: str = "neutral"
    suggested_crm_status: str = ""
    suggested_next_step: str = ""
    classification_reason: str = ""

    @field_validator("reply_category")
    @classmethod
    def _category(cls, v: str) -> str:
        text = (v or "").strip().upper().replace(" ", "_")
        return text if text in REPLY_CATEGORIES else "OTHER"


class EnrichedLead(BaseModel):
    """The final, CRM-ready record written to CSV / Google Sheets."""

    full_name: str
    company: str = ""
    title: str = ""
    linkedin_url: str = ""
    email: str = ""
    location: str = ""
    english_proficiency: str = ""
    company_sector: str = ""
    company_size: str = ""
    international_company: bool = False
    english_training_probability: int = 0
    pain_point: str = ""
    pain_point_reason: str = ""
    lead_score: int = 0
    score_reason: str = ""
    outreach_angle: str = ""
    key_message: str = ""
    linkedin_dm: str = ""
    linkedin_followup: str = ""
    email_subject: str = ""
    email_body: str = ""
    crm_status: str = "NEW"

    def to_row(self) -> dict:
        """Return a dict in canonical FINAL_COLUMNS order."""
        return {col: getattr(self, col) for col in FINAL_COLUMNS}
