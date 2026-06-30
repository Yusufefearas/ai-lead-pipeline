"""English prompt templates.

All agents must return JSON only. Enrichment values are estimates;
outreach copy (LinkedIn DM + cold email) is written in Turkish.
"""
from __future__ import annotations

from .models import CleanLead, EnrichmentResult

# Brand brief — verifiable facts about Northwind English used to ground the AI.
# NOTE: confirm/adjust the proof numbers before a real campaign.
_COMPANY = (
    "Northwind English — Turkey's online English-SPEAKING training service.\n"
    "What it is:\n"
    "- 1-on-1 live speaking lessons with native English-speaking instructors (US-based team).\n"
    "- Low-friction: microphone only (no camera), short 10/20/30-minute sessions, "
    "2-5 days a week, scheduled around a busy work life.\n"
    "- AI-supported platform gives instant feedback on mistakes; a progress report after every lesson.\n"
    "- Levels A1-C2, with personalized programs for companies and teams.\n"
    "Proof points (the company's own figures — use naturally, never as hype):\n"
    "- Trusted by 100+ corporate companies and 37,000+ learners.\n"
    "- Focus is real, usable speaking ability fast — not grammar memorization.\n"
    "Why HR cares:\n"
    "- Builds employees' confidence to speak English in meetings, with global teams, and with customers.\n"
    "- Measurable progress (reports), flexible scheduling, manageable per-person cost."
)

# Shared copywriting guidance for outreach messages.
_COPYWRITING = (
    "Write like a sharp B2B growth marketer, not a generic sales bot:\n"
    "- Open with the recipient's world or desired outcome, not with us.\n"
    "- Make ONE specific, concrete value tied to their likely pain point.\n"
    "- You MAY cite a real proof point (e.g. '100+ kurum, 37.000+ öğrenci') where it fits naturally.\n"
    "- Confident and warm; persuasive but never exaggerated, salesy, or false.\n"
    "- Tight and skimmable; one single, easy CTA."
)


def enrichment_prompt(lead: CleanLead) -> str:
    """Single prompt that produces company intel + pain + score + strategy."""
    return f"""You are an experienced B2B sales analyst for {_COMPANY}

IMPORTANT framing: this person is a potential CORPORATE BUYER who would
purchase English-speaking training FOR THEIR TEAM / COMPANY — NOT an
individual learner. Their own English level is irrelevant; what matters is
their authority to buy and their team's need.

Analyze the lead below and return ESTIMATES only. You only know the fields
provided; do NOT invent verified facts (no exact headcount, revenue, clients).

Lead:
- Full name: {lead.full_name}
- Title: {lead.title or "unknown"}
- Company: {lead.company or "unknown"}
- Location: {lead.location or "unknown"}

Return a JSON object with EXACTLY these keys:
{{
  "company_sector": "best-guess industry sector",
  "company_size": "one of: SMB | Mid-Market | Enterprise",
  "international_company": true or false,
  "english_training_probability": integer 1-10 (how much THE COMPANY'S WORKFORCE likely needs English training: weigh international operations, customer-facing roles, and sector — NOT this person's own English),
  "pain_point": "one likely HR/L&D pain point this buyer faces for their team",
  "pain_point_reason": "short reason, one sentence",
  "lead_score": integer 1-100, scored as a BUYER of team training (see rubric),
  "score_reason": "short reason, one sentence",
  "outreach_angle": "best communication angle (e.g. Employee Development, International Hiring, Customer Experience, Internal Communication, Leadership, Learning Culture)",
  "key_message": "one-sentence core value message tailored to this buyer and their team"
}}

lead_score rubric (be decisive — use the FULL 1-100 range, avoid clustering):
- Budget/decision authority over L&D & training (HIGHEST: CHRO, HR Director,
  L&D / Training Manager, People & Culture lead; MEDIUM: HR Manager / HRBP;
  LOWER: HR Specialist, Recruiter, junior/coordinator roles).
- Company size: more employees = bigger team need and deal size.
- Workforce English need: international ops, customer-facing, sector fit.
- The lead's OWN English proficiency must NOT affect the score.

Rules:
- company_size MUST be exactly one of SMB, Mid-Market, Enterprise.
- company_sector / company_size / international_company are ESTIMATES, never facts.
- Return JSON only. No markdown, no commentary.
"""


def linkedin_dm_prompt(lead: CleanLead, e: EnrichmentResult) -> str:
    return f"""You write short, personalized LinkedIn DMs in TURKISH on behalf of {_COMPANY}

Recipient:
- Name: {lead.full_name}
- Title: {lead.title or "unknown"}
- Company: {lead.company or "unknown"}
- Likely pain point: {e.pain_point}
- Outreach angle: {e.outreach_angle}
- Key message: {e.key_message}

{_COPYWRITING}

Write ONE LinkedIn DM in Turkish.

Requirements:
- Turkish language, natural and human, NOT generic.
- 70-120 words.
- Friendly and professional; no exaggerated or misleading claims.
- Reference the person's role or company and the likely HR challenge.
- Make the English-speaking-training value concrete (e.g. confidence in meetings
  with global teams / customers), and cite a proof point if it fits.
- End with a low-pressure CTA (a short question or offer to share more).
- Do NOT add placeholder text like [Your Name] or [Adınız]. If you sign off,
  sign simply as "Northwind English ekibi".

Return a JSON object: {{"linkedin_dm": "..."}}
JSON only. No markdown.
"""


def linkedin_followup_prompt(lead: CleanLead, e: EnrichmentResult, first_dm: str) -> str:
    """A short Turkish follow-up DM, sent ~3-4 days after the first if no reply."""
    return f"""You write a SHORT Turkish LinkedIn follow-up message on behalf of {_COMPANY}

This is the SECOND touch, sent a few days after the first message got no reply.

Recipient:
- Name: {lead.full_name}
- Title: {lead.title or "unknown"}
- Company: {lead.company or "unknown"}
- Likely pain point: {e.pain_point}
- Outreach angle: {e.outreach_angle}

First message already sent:
\"\"\"{first_dm}\"\"\"

Write ONE follow-up message in Turkish.

Requirements:
- Turkish, warm and low-pressure; acknowledge you reached out before.
- 30-70 words (clearly shorter than the first message).
- Add ONE new angle or a lightweight, concrete value (e.g. a practical idea,
  a relevant observation, or a no-strings offer like a short free demo).
- Do NOT invent statistics or percentages. You MAY cite the real proof points
  (100+ kurum, 37.000+ öğrenci) if it fits naturally.
- Do not repeat the first message. Do not guilt-trip about no reply.
- End with a very soft CTA (e.g. "uygun olmazsa hiç sorun değil").
- Sign off as "Northwind English ekibi". No placeholders like [Adınız].

Return a JSON object: {{"linkedin_followup": "..."}}
JSON only. No markdown.
"""


def reply_classification_prompt(reply_text: str, lead_name: str = "", company: str = "") -> str:
    """Classify an inbound reply to the outbound campaign and suggest a CRM action."""
    return f"""You triage inbound replies to a B2B outreach campaign for {_COMPANY.splitlines()[0]}

Reply is from {lead_name or "a lead"} at {company or "unknown company"} (Turkish):
\"\"\"{reply_text}\"\"\"

Classify it. Return a JSON object with EXACTLY these keys:
{{
  "reply_category": "one of: INTERESTED | QUESTION | NOT_INTERESTED | OUT_OF_OFFICE | UNSUBSCRIBE | OTHER",
  "reply_sentiment": "one of: positive | neutral | negative",
  "suggested_crm_status": "one of: MEETING | INTERESTED | NURTURE | NOT_INTERESTED | DO_NOT_CONTACT | FOLLOW_UP_LATER",
  "suggested_next_step": "a short, concrete next action for the sales rep, in TURKISH",
  "classification_reason": "one short sentence, in Turkish"
}}

Rules:
- UNSUBSCRIBE / opt-out requests must map to suggested_crm_status DO_NOT_CONTACT.
- A clear meeting/demo request is INTERESTED + MEETING.
- Out-of-office / auto-replies are OUT_OF_OFFICE + FOLLOW_UP_LATER.
- Return JSON only. No markdown.
"""


def cold_email_prompt(lead: CleanLead, e: EnrichmentResult) -> str:
    return f"""You write short, personalized cold emails in TURKISH on behalf of {_COMPANY}

Recipient:
- Name: {lead.full_name}
- Title: {lead.title or "unknown"}
- Company: {lead.company or "unknown"}
- Likely pain point: {e.pain_point}
- Outreach angle: {e.outreach_angle}
- Key message: {e.key_message}

{_COPYWRITING}

Write ONE cold email in Turkish.

Requirements:
- Turkish language, natural and human, NOT mass-marketing.
- Subject: short, specific, curiosity- or benefit-driven (no clickbait).
- Body: 100-180 words, personalized to the role/company and pain point.
- Make the value concrete and cite a proof point (100+ kurum, 37.000+ öğrenci) where natural.
- End with a soft CTA.
- No spammy wording, no false claims.
- Do NOT add placeholder text like [Your Name] or [Adınız]. Sign off as
  "Northwind English ekibi".

Return a JSON object: {{"email_subject": "...", "email_body": "..."}}
JSON only. No markdown.
"""
