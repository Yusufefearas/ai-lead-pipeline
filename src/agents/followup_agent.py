"""Follow-up agent: a short second-touch Turkish LinkedIn message.

Enables a simple multi-step outreach sequence (first DM -> follow-up).
"""
from __future__ import annotations

from ..models import CleanLead, EnrichmentResult, FollowUpMessage
from ..prompts import linkedin_followup_prompt
from .base_agent import BaseAgent


class FollowUpAgent(BaseAgent):
    def run(
        self, lead: CleanLead, enrichment: EnrichmentResult, first_dm: str
    ) -> FollowUpMessage:
        data = self.run_json(linkedin_followup_prompt(lead, enrichment, first_dm))
        return FollowUpMessage(**data)
