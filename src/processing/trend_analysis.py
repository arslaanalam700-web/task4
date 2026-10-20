"""
Trend Analysis and Momentum Calculation Module.
Calculates velocity of search interest, moving averages, direction classifications, and regional comparisons.
"""

from typing import Any, Dict, List
import numpy as np
import pandas as pd


def compute_keyword_momentum(df_keyword_series: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes momentum and direction classification for a single keyword series.
    Requires columns: 'date_observed', 'relative_interest'.
    """
    if df_keyword_series.empty or len(df_keyword_series) < 2:
        return {
            "mean_interest": 0.0,
            "latest_interest": 0.0,
            "momentum": 0.0,
            "direction": "stable",
            "peak_interest": 0.0,
        }

    # Sort ascending by date
    sorted_df = df_keyword_series.sort_values("date_observed", ascending=True)
    interests = sorted_df["relative_interest"].values

    latest_val = float(interests[-1])
    mean_val = float(np.mean(interests))
    peak_val = float(np.max(interests))

    # Divide window into two halves to measure shift
    half_idx = max(1, len(interests) // 2)
    prior_half = interests[:half_idx]
    recent_half = interests[half_idx:]

    prior_mean = float(np.mean(prior_half)) if len(prior_half) > 0 else latest_val
    recent_mean = float(np.mean(recent_half)) if len(recent_half) > 0 else latest_val

    # Momentum is the delta between recent average and prior average
    momentum = round(recent_mean - prior_mean, 2)

    # Classify direction
    if momentum > 10.0 and latest_val >= 70.0:
        direction = "breakout"
    elif momentum > 2.0:
        direction = "rising"
    elif momentum < -2.0:
        direction = "falling"
    else:
        direction = "stable"

    return {
        "mean_interest": round(mean_val, 1),
        "latest_interest": round(latest_val, 1),
        "momentum": momentum,
        "direction": direction,
        "peak_interest": round(peak_val, 1),
    }


def analyze_category_trends(df_trends: pd.DataFrame) -> List[Dict[str, Any]]:
    """Analyzes each keyword within a trend dataset and compiles summaries."""
    if df_trends.empty:
        return []

    results = []
    for term, group in df_trends.groupby("term"):
        stats = compute_keyword_momentum(group)
        category_slug = group["category_slug"].iloc[0] if "category_slug" in group.columns else "general"
        geo = group["geography"].iloc[0] if "geography" in group.columns else "IN"
        source_url = group["source_url"].iloc[0] if "source_url" in group.columns else ""

        results.append(
            {
                "term": term,
                "category_slug": category_slug,
                "geography": geo,
                "mean_interest": stats["mean_interest"],
                "latest_interest": stats["latest_interest"],
                "momentum": stats["momentum"],
                "direction": stats["direction"],
                "peak_interest": stats["peak_interest"],
                "data_points": len(group),
                "source_url": source_url,
            }
        )

    return sorted(results, key=lambda x: (x["latest_interest"], x["momentum"]), reverse=True)
