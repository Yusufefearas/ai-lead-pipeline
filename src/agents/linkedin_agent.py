"""LinkedIn DM agent: personalized Turkish DM (primary outreach channel)."""
from __future__ import annotations

from ..models import CleanLead, EnrichmentResult, LinkedInMessage
from ..prompts import linkedin_dm_prompt
from .base_agent import BaseAgent


class LinkedInAgent(BaseAgent):
    def run(self, lead: CleanLead, enrichment: EnrichmentResult) -> LinkedInMessage:
        data = self.run_json(linkedin_dm_prompt(lead, enrichment))
        return LinkedInMessage(**data)
