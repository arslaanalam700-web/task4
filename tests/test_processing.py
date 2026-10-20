"""
Tests for Data Cleaning and Trend Analysis.
Verifies momentum velocity, moving window calculations, and direction categorization.
"""

import pandas as pd
from src.processing.cleaning import clean_trend_dataframe, deduplicate_observations
from src.processing.trend_analysis import compute_keyword_momentum


def test_clean_trend_dataframe():
    raw_data = pd.DataFrame(
        {
            "term": ["  Python Course  ", "data analytics"],
            "relative_interest": ["85.5", "120.0"],  # Over 100 should be clipped
            "date_observed": ["2026-08-01", "invalid-date"],
        }
    )
    cleaned = clean_trend_dataframe(raw_data)
    assert len(cleaned) == 1  # Invalid date dropped
    assert cleaned["term"].iloc[0] == "python course"
    assert cleaned["relative_interest"].iloc[0] == 85.5


def test_deduplicate_observations():
    records = [
        {"term": "python", "geo": "IN", "val": 10},
        {"term": "python", "geo": "IN", "val": 20},
        {"term": "python", "geo": "US", "val": 30},
    ]
    deduped = deduplicate_observations(records, ["term", "geo"])
    assert len(deduped) == 2


def test_compute_keyword_momentum_rising():
    # Sequence of increasing values
    df = pd.DataFrame(
        {
            "date_observed": ["2026-08-01", "2026-08-08", "2026-08-15", "2026-08-22"],
            "relative_interest": [50.0, 60.0, 75.0, 85.0],
        }
    )
    stats = compute_keyword_momentum(df)
    assert stats["momentum"] > 0
    assert stats["direction"] in ["rising", "breakout"]
    assert stats["latest_interest"] == 85.0


def test_compute_keyword_momentum_falling():
    # Sequence of decreasing values
    df = pd.DataFrame(
        {
            "date_observed": ["2026-08-01", "2026-08-08", "2026-08-15", "2026-08-22"],
            "relative_interest": [90.0, 80.0, 65.0, 50.0],
        }
    )
    stats = compute_keyword_momentum(df)
    assert stats["momentum"] < 0
    assert stats["direction"] == "falling"
