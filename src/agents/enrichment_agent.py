"""Combined enrichment agent: company intel + pain + score + strategy.

One OpenAI call per lead (instead of four) for lower cost and latency.
"""
from __future__ import annotations

from ..logger import get_logger
from ..models import CleanLead, EnrichmentResult
from ..prompts import enrichment_prompt
from .base_agent import BaseAgent

log = get_logger(__name__)


class EnrichmentAgent(BaseAgent):
    def run(self, lead: CleanLead) -> EnrichmentResult:
        data = self.run_json(enrichment_prompt(lead))
        # Pydantic ignores extra keys and clamps/normalizes via validators.
        return EnrichmentResult(**data)
