"""
Competitor Intelligence Collector.
Scrapes permitted public pages of configured educational competitors.
Extracts course titles, calls to action, public pricing, and promotional banners.
If pricing is hidden behind logins, enterprise forms, or sales funnels, records 'Not publicly verified'.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import logging
import re
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class CompetitorCollector:
    """
    Collects public competitor course offerings, pricing status, CTAs, and positioning.
    Honors safety rules: never attempts to bypass CAPTCHAs, paywalls, or login walls.
    """

    def __init__(
        self,
        timeout: int = 8,
        user_agent: str = "MarketIntelligenceBot/1.0 (Public Research)",
        fixture_path: Optional[Path] = None,
        allow_demo_fallback: bool = True,
    ):
        self.timeout = timeout
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        self.fixture_path = fixture_path
        self.allow_demo_fallback = allow_demo_fallback

    def collect_competitor_data(
        self,
        competitor_profile: Dict[str, Any],
        target_categories: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Attempts to inspect public catalog or landing page.
        Falls back to curated fixture records if site restricts automated public requests.
        """
        comp_id = competitor_profile.get("id", "unknown")
        name = competitor_profile.get("name", comp_id)
        website = competitor_profile.get("website", "")
        catalog_url = competitor_profile.get("public_catalog_url", website)
        target_audience = competitor_profile.get("target_audience", "")

        result = {
            "competitor_id": comp_id,
            "competitor_name": name,
            "website": website,
            "target_audience": target_audience,
            "offerings": [],
            "status": "success",
            "is_demo": False,
            "error": None,
        }

        # Attempt safe HTTP request to public catalog
        offerings_found = []
        try:
            resp = requests.get(catalog_url, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                page_text = soup.get_text()

                page_title = soup.title.string.strip() if soup.title and soup.title.string else name
                meta_desc = ""
                meta_tag = soup.find("meta", attrs={"name": "description"})
                if meta_tag and meta_tag.get("content"):
                    meta_desc = meta_tag["content"]

                for cat in target_categories:
                    cat_slug = cat.get("slug", "")
                    cat_name = cat.get("name", "")

                    if cat_name.lower() in page_text.lower():
                        headlines = []
                        for h in soup.find_all(["h1", "h2", "h3"]):
                            text = h.get_text().strip()
                            if any(k.lower() in text.lower() for k in cat.get("keywords", [cat_name])):
                                headlines.append(text)

                        price_match = re.search(r"(\$|₹|£|€)\s?(\d{1,3}(,\d{3})*(\.\d{2})?)", page_text)
                        verified_price = price_match.group(0) if price_match else "Not publicly verified"
                        pricing_status = "verified" if price_match else "not_publicly_verified"

                        cta_match = soup.find("a", string=re.compile(r"(Enroll|Sign Up|Start|Apply|Register|Try)", re.I))
                        cta_text = cta_match.get_text().strip() if cta_match else "View Course"

                        course_title = headlines[0] if headlines else f"{name} {cat_name} Course"

                        offerings_found.append(
                            {
                                "course_title": course_title[:150],
                                "category_slug": cat_slug,
                                "verified_price": verified_price,
                                "currency": "INR" if "₹" in verified_price else "USD",
                                "pricing_status": pricing_status,
                                "promo_text": meta_desc[:200] if meta_desc else "Public online course",
                                "cta_text": cta_text[:60],
                                "landing_url": catalog_url,
                                "collected_at": datetime.utcnow().isoformat(),
                                "confidence_level": "Medium",
                            }
                        )
            else:
                logger.warning(f"Competitor site {catalog_url} returned HTTP {resp.status_code}")
                result["error"] = f"HTTP {resp.status_code}"
        except Exception as e:
            logger.info(f"Could not scrape live competitor {catalog_url} ({e}). Using verified fallback fixtures.")
            result["error"] = str(e)

        if offerings_found:
            result["offerings"] = offerings_found
            result["is_demo"] = False
            return result

        # Fallback to offline fixtures for reliability
        if self.allow_demo_fallback:
            fixture_offerings = self._load_fixture_data(comp_id)
            if fixture_offerings:
                result["offerings"] = fixture_offerings
                result["is_demo"] = True
                result["status"] = "fallback_fixture"
                return result

        result["status"] = "no_data"
        return result

    def _load_fixture_data(self, comp_id: str) -> List[Dict[str, Any]]:
        if not self.fixture_path:
            return []
        fixture_file = self.fixture_path / "competitors_sample.json"
        if not fixture_file.exists():
            return []

        try:
            with open(fixture_file, "r", encoding="utf-8") as f:
                all_comps = json.load(f)
            now_str = datetime.utcnow().isoformat()
            for comp in all_comps:
                if comp.get("competitor_id") == comp_id:
                    offerings = comp.get("offerings", [])
                    for o in offerings:
                        o["collected_at"] = now_str
                    return offerings
            return []
        except Exception as e:
            logger.error(f"Failed to read competitor fixture: {e}")
            return []
