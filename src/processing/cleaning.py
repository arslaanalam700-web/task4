"""
Data Cleaning and Normalization Module.
Sanitizes raw records, removes duplicates, validates URL structures, and enforces types.
"""

from typing import Any, Dict, List, Optional
import re
import pandas as pd


def sanitize_text(text: Optional[Any]) -> str:
    """Removes non-printable characters and trims whitespace."""
    if text is None:
        return ""
    s = str(text).strip()
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", s)


def clean_trend_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Ensures proper types and formats for Google Trends observations."""
    if df.empty:
        return df

    cleaned = df.copy()
    if "relative_interest" in cleaned.columns:
        cleaned["relative_interest"] = pd.to_numeric(cleaned["relative_interest"], errors="coerce").fillna(0.0)
        # Ensure within bounds 0 to 100
        cleaned["relative_interest"] = cleaned["relative_interest"].clip(0.0, 100.0)

    if "date_observed" in cleaned.columns:
        cleaned["date_observed"] = pd.to_datetime(cleaned["date_observed"], errors="coerce").dt.strftime("%Y-%m-%d")

    # Drop any null dates or terms
    cleaned = cleaned.dropna(subset=["date_observed"])
    if "term" in cleaned.columns:
        cleaned["term"] = cleaned["term"].astype(str).str.strip().str.lower()

    return cleaned


def deduplicate_observations(records: List[Dict[str, Any]], key_fields: List[str]) -> List[Dict[str, Any]]:
    """Deduplicates dictionaries based on specific key fields."""
    seen = set()
    unique_records = []
    for r in records:
        key = tuple(r.get(f) for f in key_fields)
        if key not in seen:
            seen.add(key)
            unique_records.append(r)
    return unique_records
