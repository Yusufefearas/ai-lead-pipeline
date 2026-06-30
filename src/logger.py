"""Project-wide logger using Rich for readable, human-friendly output."""
from __future__ import annotations

import logging

from rich.logging import RichHandler

_CONFIGURED = False


def get_logger(name: str = "growth_ai_ops") -> logging.Logger:
    """Return a configured logger. Safe to call from any module."""
    global _CONFIGURED
    if not _CONFIGURED:
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
        )
        # Keep our own logs readable: silence third-party HTTP/client chatter.
        for noisy in ("httpx", "httpcore", "openai", "urllib3", "apify_client"):
            logging.getLogger(noisy).setLevel(logging.WARNING)
        _CONFIGURED = True
    return logging.getLogger(name)
