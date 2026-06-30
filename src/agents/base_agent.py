"""Reusable OpenAI client wrapper shared by every AI agent.

Centralizes the client, JSON-only parsing, and retry logic so no agent
duplicates OpenAI plumbing.
"""
from __future__ import annotations

import json
from typing import Any

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import Settings, get_settings, require
from ..logger import get_logger

log = get_logger(__name__)

_SYSTEM = (
    "You are a precise assistant. Always respond with a single valid JSON "
    "object and nothing else."
)


class BaseAgent:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        require(self.settings, "openai_api_key")
        self.client = OpenAI(api_key=self.settings.openai_api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        reraise=True,
    )
    def _complete(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.settings.openai_model,
            temperature=self.settings.openai_temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or "{}"

    def run_json(self, prompt: str) -> dict[str, Any]:
        """Call the model and parse a JSON object, tolerating stray text."""
        raw = self._complete(prompt)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            start, end = raw.find("{"), raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                data = json.loads(raw[start : end + 1])
            else:
                log.error("Could not parse JSON from model output: %s", raw[:200])
                raise
        # Some models emit literal "\n" sequences; turn them into real breaks.
        return {
            k: (v.replace("\\n", "\n").strip() if isinstance(v, str) else v)
            for k, v in data.items()
        }
