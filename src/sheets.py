"""Google Sheets upload (optional).

Skips gracefully when credentials are absent so the CSV output always
works without extra setup.
"""
from __future__ import annotations

import pandas as pd

from .config import Settings, get_settings
from .logger import get_logger

log = get_logger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def upload_to_google_sheets(df: pd.DataFrame, settings: Settings | None = None) -> None:
    """Upload the enriched dataframe to a single sheet, replacing its content."""
    settings = settings or get_settings()
    if not settings.google_sheet_id or not settings.google_service_account_json:
        log.warning("Google Sheets env missing; skipping upload (CSV still saved).")
        return

    # Hottest leads first for a CRM-style view.
    if "lead_score" in df.columns:
        df = df.sort_values("lead_score", ascending=False)

    try:
        import gspread
        from google.oauth2.service_account import Credentials
        from gspread.utils import rowcol_to_a1

        creds = Credentials.from_service_account_file(
            settings.google_service_account_json, scopes=_SCOPES
        )
        client = gspread.authorize(creds)
        worksheet = client.open_by_key(settings.google_sheet_id).sheet1
        worksheet.clear()
        worksheet.update(
            [df.columns.tolist()] + df.astype(str).values.tolist(),
            value_input_option="RAW",
        )
        log.info("Uploaded %d rows to Google Sheets.", len(df))

        # CRM polish: frozen + bold header, filter. Non-fatal if it fails.
        try:
            header_range = f"A1:{rowcol_to_a1(1, len(df.columns))}"
            worksheet.freeze(rows=1)
            worksheet.format(
                header_range,
                {
                    "textFormat": {"bold": True},
                    "backgroundColor": {"red": 0.85, "green": 0.91, "blue": 0.97},
                },
            )
            worksheet.set_basic_filter()
        except Exception as fmt_exc:
            log.warning("Sheet formatting skipped: %s", fmt_exc)
    except Exception as exc:
        log.error("Google Sheets upload failed: %s", exc)
