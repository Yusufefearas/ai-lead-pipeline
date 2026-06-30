"""Cold email agent: personalized Turkish email copy.

Generated as an outreach artifact (subject + body). Sending is out of
scope; email addresses are not collected (see README).
"""
from __future__ import annotations

from ..models import CleanLead, ColdEmail, EnrichmentResult
from ..prompts import cold_email_prompt
from .base_agent import BaseAgent


class EmailAgent(BaseAgent):
    def run(self, lead: CleanLead, enrichment: EnrichmentResult) -> ColdEmail:
        data = self.run_json(cold_email_prompt(lead, enrichment))
        return ColdEmail(**data)
