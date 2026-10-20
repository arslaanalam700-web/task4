"""
Google Trends Collector.
Retrieves normalized relative search interest indices from Google Trends via pytrends.
Includes robust rate-limit handling, retry backoff, and fallback demo mode.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import logging
import time
import pandas as pd

# Compatibility patch for urllib3 v2.x with pytrends
try:
    import urllib3.util.retry
    _orig_retry_init = urllib3.util.retry.Retry.__init__
    def _patched_retry_init(self, *args, **kwargs):
        if "method_whitelist" in kwargs:
            kwargs["allowed_methods"] = kwargs.pop("method_whitelist")
        return _orig_retry_init(self, *args, **kwargs)
    urllib3.util.retry.Retry.__init__ = _patched_retry_init
except Exception:
    pass

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False

logger = logging.getLogger(__name__)


class GoogleTrendsCollector:
    """
    Collects normalized relative-interest indices (0-100) from Google Trends.
    Important: Google Trends data represents relative popularity compared to the peak point
    in the selected region and timeframe, NOT absolute search volumes.
    """

    def __init__(
        self,
        timeout: int = 10,
        retries: int = 2,
        sleep_between_requests: float = 2.0,
        fixture_path: Optional[Path] = None,
        allow_demo_fallback: bool = True,
    ):
        self.timeout = timeout
        self.retries = retries
        self.sleep_between = sleep_between_requests
        self.fixture_path = fixture_path
        self.allow_demo_fallback = allow_demo_fallback
        self.pytrend: Optional[Any] = None

        if PYTRENDS_AVAILABLE:
            try:
                self.pytrend = TrendReq(
                    hl="en-US",
                    tz=330,  # IST offset or default
                    timeout=(timeout, timeout),
                    retries=retries,
                    backoff_factor=0.5,
                )
            except Exception as e:
                logger.warning(f"Could not initialize TrendReq: {e}")
                self.pytrend = None

    def collect_interest_over_time(
        self,
        keywords: List[str],
        category_slug: str,
        geo: str = "IN",
        timeframe: str = "today 3-m",
    ) -> Dict[str, Any]:
        """
        Attempts to query live Google Trends for a batch of keywords (up to 5 at a time).
        Falls back to labeled fixture data if pytrends is unavailable or throttled.
        """
        result = {
            "source": "google_trends",
            "category_slug": category_slug,
            "geography": geo,
            "timeframe": timeframe,
            "is_demo": False,
            "status": "success",
            "records": [],
            "error": None,
        }

        # Try live collection if client exists
        if self.pytrend is not None:
            try:
                batch = keywords[:5]
                self.pytrend.build_payload(kw_list=batch, cat=0, timeframe=timeframe, geo=geo, gprop="")
                df = self.pytrend.interest_over_time()

                if df is not None and not df.empty:
                    now_str = datetime.utcnow().isoformat()
                    records = []
                    for col in batch:
                        if col in df.columns:
                            series = df[col]
                            # Compute quick momentum on series
                            vals = series.values
                            half = max(1, len(vals) // 2)
                            prior_mean = float(vals[:half].mean()) if len(vals[:half]) > 0 else 0.0
                            recent_mean = float(vals[half:].mean()) if len(vals[half:]) > 0 else 0.0
                            momentum = round(recent_mean - prior_mean, 2)
                            direction = "rising" if momentum > 2.0 else ("falling" if momentum < -2.0 else "stable")

                            for date_idx, val in series.items():
                                date_str = date_idx.strftime("%Y-%m-%d") if hasattr(date_idx, "strftime") else str(date_idx)[:10]
                                records.append(
                                    {
                                        "term": col,
                                        "category_slug": category_slug,
                                        "geography": geo,
                                        "date_observed": date_str,
                                        "relative_interest": float(val),
                                        "momentum": momentum,
                                        "direction": direction,
                                        "source_url": f"https://trends.google.com/trends/explore?geo={geo}&q={col.replace(' ', '+')}",
                                        "collected_at": now_str,
                                        "is_demo": 0,
                                    }
                                )
                    if records:
                        result["records"] = records
                        result["is_demo"] = False
                        logger.info(f"Successfully collected {len(records)} live trend data points for {category_slug}")
                        return result
            except Exception as e:
                logger.warning(f"Live Google Trends query failed for {keywords}: {e}. Evaluating fallback.")
                result["error"] = str(e)

        # Fallback to offline fixtures if live failed or pytrends is rate limited
        if self.allow_demo_fallback:
            fixture_records = self._load_fixture_data(category_slug, geo)
            if fixture_records:
                result["records"] = fixture_records
                result["is_demo"] = True
                result["status"] = "fallback_fixture"
                logger.info(f"Using {len(fixture_records)} labeled fixture data points for {category_slug}")
                return result

        result["status"] = "failed"
        return result

    def _load_fixture_data(self, category_slug: str, geo: str) -> List[Dict[str, Any]]:
        """Loads curated offline fixture data for demo / offline reliability."""
        if not self.fixture_path:
            return []
        fixture_file = self.fixture_path / "trends_sample.json"
        if not fixture_file.exists():
            return []

        try:
            with open(fixture_file, "r", encoding="utf-8") as f:
                all_records = json.load(f)
            filtered = [r for r in all_records if r.get("category_slug") == category_slug]
            now_str = datetime.utcnow().isoformat()
            for r in filtered:
                r["collected_at"] = now_str
                r["is_demo"] = 1
                r.setdefault("momentum", 0.0)
                r.setdefault("direction", "stable")
            return filtered
        except Exception as e:
            logger.error(f"Failed to read trends fixture file: {e}")
            return []
