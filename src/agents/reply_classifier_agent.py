"""Auto-reply classification agent.

Triages inbound replies (INTERESTED / QUESTION / NOT_INTERESTED /
OUT_OF_OFFICE / UNSUBSCRIBE / OTHER) and suggests a CRM status + next
step, closing the outbound loop.
"""
from __future__ import annotations

from ..models import ReplyClassification
from ..prompts import reply_classification_prompt
from .base_agent import BaseAgent


class ReplyClassifierAgent(BaseAgent):
    def run(
        self, reply_text: str, lead_name: str = "", company: str = ""
    ) -> ReplyClassification:
        data = self.run_json(
            reply_classification_prompt(reply_text, lead_name, company)
        )
        return ReplyClassification(**data)
