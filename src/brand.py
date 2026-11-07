"""Brand profile loaded from a YAML file (see config/brand.yaml).

Keeps company-specific copy out of the prompts so the same pipeline can
run for any product. The file path comes from the BRAND_CONFIG env var.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

import yaml
from pydantic import BaseModel, Field

from .config import get_settings


class Brand(BaseModel):
    name: str
    tagline: str
    facts: List[str] = Field(default_factory=list)
    proof_points: List[str] = Field(default_factory=list)
    proof_short: str = ""
    buyer_benefits: List[str] = Field(default_factory=list)
    signature: str

    def brief(self) -> str:
        """Multi-line brief injected into prompts to ground the AI."""
        def bullets(items: List[str]) -> str:
            return "\n".join(f"- {item}" for item in items)

        parts = [f"{self.name}: {self.tagline}"]
        if self.facts:
            parts.append("What it is:\n" + bullets(self.facts))
        if self.proof_points:
            parts.append(
                "Proof points (the company's own figures; use naturally, never as hype):\n"
                + bullets(self.proof_points)
            )
        if self.buyer_benefits:
            parts.append("Why HR cares:\n" + bullets(self.buyer_benefits))
        return "\n".join(parts)


@lru_cache(maxsize=None)
def load_brand(path: str) -> Brand:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return Brand(**data)


def get_brand() -> Brand:
    return load_brand(get_settings().brand_config)
