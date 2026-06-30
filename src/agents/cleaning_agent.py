"""Rule-based cleaning + qualification (no LLM).

clean_leads  -> dedupe + normalize raw leads.
qualify_leads -> drop out-of-scope leads BEFORE the costly AI enrichment
                 step (wrong location or non-HR title). Each dropped lead
                 saves 3 OpenAI calls.
"""
from __future__ import annotations

import os
import re
import unicodedata

import pandas as pd

from ..logger import get_logger

log = get_logger(__name__)

PROCESSED_CSV = "data/processed/clean_leads.csv"
_BASE_COLS = [
    "full_name",
    "company",
    "title",
    "linkedin_url",
    "email",
    "location",
    "english_proficiency",
]

# Title must look HR-related (ascii-normalized substrings).
_HR_KEYWORDS = (
    "hr",
    "human resources",
    "insan kaynak",
    "talent",
    "recruit",
    "people",
    "culture",
    "learning",
    "development",
    "l&d",
)
# Location is kept if unknown, contains a Turkey token, or a major TR city.
_TURKEY_TOKENS = (
    # Country
    "turkey",
    "turkiye",
    "türkiye",
    "republic of turkey",
    "türkiye cumhuriyeti",

    # Marmara
    "istanbul",
    "bursa",
    "kocaeli",
    "izmit",
    "sakarya",
    "adapazari",
    "adapazarı",
    "tekirdag",
    "tekirdağ",
    "edirne",
    "kirklareli",
    "kırklareli",
    "yalova",
    "balikesir",
    "balıkesir",
    "canakkale",
    "çanakkale",
    "bilecik",

    # Aegean
    "izmir",
    "manisa",
    "aydin",
    "aydın",
    "mugla",
    "muğla",
    "denizli",
    "usak",
    "uşak",
    "kutahya",
    "kütahya",
    "afyon",
    "afyonkarahisar",

    # Mediterranean
    "antalya",
    "mersin",
    "adana",
    "hatay",
    "iskenderun",
    "iskenderun",
    "kahramanmaras",
    "kahramanmaraş",
    "osmaniye",
    "burdur",
    "isparta",

    # Central Anatolia
    "ankara",
    "konya",
    "eskisehir",
    "eskişehir",
    "kayseri",
    "kirikkale",
    "kırıkkale",
    "aksaray",
    "karaman",
    "nevsehir",
    "nevşehir",
    "nigde",
    "niğde",
    "yozgat",
    "cankiri",
    "çankırı",
    "kirsehir",
    "kırşehir",
    "sivas",

    # Black Sea
    "samsun",
    "trabzon",
    "ordu",
    "giresun",
    "rize",
    "artvin",
    "sinop",
    "kastamonu",
    "zonguldak",
    "bartin",
    "bartın",
    "karabuk",
    "karabük",
    "amasya",
    "tokat",
    "corum",
    "çorum",
    "duzce",
    "düzce",
    "bolu",
    "bayburt",
    "gumushane",
    "gümüşhane",

    # Eastern Anatolia
    "erzurum",
    "erzincan",
    "kars",
    "igdir",
    "ığdır",
    "agri",
    "ağrı",
    "ardahan",
    "mus",
    "muş",
    "bingol",
    "bingöl",
    "bitlis",
    "van",
    "hakkari",
    "elazig",
    "elazığ",
    "malatya",
    "tunceli",

    # Southeastern Anatolia
    "gaziantep",
    "sanliurfa",
    "şanlıurfa",
    "urfa",
    "diyarbakir",
    "diyarbakır",
    "mardin",
    "siirt",
    "sirnak",
    "şırnak",
    "batman",
    "kilis",
    "adiyaman",
    "adıyaman",

    # Frequently seen districts in LinkedIn
    "besiktas",
    "beşiktaş",
    "sisli",
    "şişli",
    "kadikoy",
    "kadıköy",
    "umraniye",
    "ümraniye",
    "atasehir",
    "ataşehir",
    "pendik",
    "tuzla",
    "gebze",
    "cankaya",
    "çankaya",
    "bornova",
    "konak",
    "nilufer",
    "nilüfer",
    "osmangazi",
    "yildirim",
    "yıldırım",
    "karşıyaka",
    "karsiyaka",
)


def _norm(value: object) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def _ascii(value: object) -> str:
    """Lowercase + strip diacritics so Turkish text matches plain keywords."""
    text = str(value).casefold()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def clean_leads(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize text, drop empty/duplicate rows, save clean_leads.csv."""
    df = df.copy()
    for col in _BASE_COLS:
        if col not in df.columns:
            df[col] = ""
    df = df[_BASE_COLS].fillna("")
    for col in _BASE_COLS:
        df[col] = df[col].map(_norm)

    df = df[df["full_name"] != ""]

    with_url = df[df["linkedin_url"] != ""].drop_duplicates(subset=["linkedin_url"])
    without_url = df[df["linkedin_url"] == ""]
    df = pd.concat([with_url, without_url], ignore_index=True)
    df = df.drop_duplicates(subset=["full_name", "company"]).reset_index(drop=True)

    os.makedirs(os.path.dirname(PROCESSED_CSV), exist_ok=True)
    df.to_csv(PROCESSED_CSV, index=False)
    log.info("Saved %d clean leads -> %s", len(df), PROCESSED_CSV)
    return df


def _location_ok(value: str) -> bool:
    norm = _ascii(value)
    if not norm:  # unknown -> keep (don't over-filter)
        return True
    return any(token in norm for token in _TURKEY_TOKENS)


def _title_is_hr(value: str) -> bool:
    norm = _ascii(value)
    if not norm:  # unknown -> keep
        return True
    return any(keyword in norm for keyword in _HR_KEYWORDS)


def qualify_leads(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only in-scope leads: located in Turkey with an HR/L&D title.

    We deliberately do NOT filter on the lead's own English level: this is a
    B2B corporate motion where the buyer purchases training FOR THEIR TEAM, so
    a fluent HR Director is still a valid (often high-value) buyer.
    """
    df = df.copy()
    before = len(df)

    location_mask = df["location"].map(_location_ok)
    hr_mask = df["title"].map(_title_is_hr)

    dropped_location = int((~location_mask).sum())
    dropped_title = int((~hr_mask).sum())

    df = df[location_mask & hr_mask].reset_index(drop=True)

    log.info(
        "Qualification: %d -> %d leads (dropped: %d non-Turkey, %d non-HR)",
        before,
        len(df),
        dropped_location,
        dropped_title,
    )
    return df
