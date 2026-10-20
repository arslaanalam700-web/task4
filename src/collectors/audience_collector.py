"""
Audience Discovery Collector.
Scrapes public community questions and discussions from accessible public forums/Reddit JSON endpoints.
Extracts questions, learner pain points, and classifies search & learning intent.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import logging
import re
import requests

logger = logging.getLogger(__name__)


class AudienceCollector:
    """
    Collects public learner discussions and categorizes intent deterministically.
    Complies with data privacy guidelines: strips user identities and retains only public topical questions.
    """

    def __init__(
        self,
        timeout: int = 8,
        max_posts_per_sub: int = 15,
        user_agent: str = "MarketIntelligenceAgent/1.0 (Public Research)",
        fixture_path: Optional[Path] = None,
        allow_demo_fallback: bool = True,
    ):
        self.timeout = timeout
        self.max_posts = max_posts_per_sub
        self.headers = {"User-Agent": user_agent}
        self.fixture_path = fixture_path
        self.allow_demo_fallback = allow_demo_fallback

    def classify_intent(self, text: str) -> Dict[str, Any]:
        """
        Deterministic intent and pain-point classification.
        Returns:
            intent: 'comparison', 'purchase_oriented', 'career_related', 'skill_development', 'informational'
            cluster: 'pricing_objection', 'career_switch', 'beginner_difficulty', 'certification_value', 'general_curiosity'
            confidence: float (0.0 to 1.0)
        """
        lower = text.lower()

        # Purchase / price objections (Prioritized high intent)
        if any(w in lower for w in ["worth it", "pay", "cost", "price", "bootcamp cost", "expensive", "too expensive", "refund", "financial aid", "discount", "fee", "fees"]):
            return {
                "intent": "purchase_oriented",
                "cluster": "pricing_objection",
                "confidence": 0.94,
            }

        # Comparison triggers (Explicit comparative queries)
        if any(w in lower for w in [" vs ", " vs. ", " versus ", "compared to", "better than", "difference between", " which is better "]):
            return {
                "intent": "comparison",
                "cluster": "certification_value" if any(w in lower for w in ["certificate", "degree", "certification"]) else "course_comparison",
                "confidence": 0.92,
            }

        # Career switch / transition
        if any(w in lower for w in ["career", "switch", "job", "hire", "salary", "portfolio", "interview", "roadmap", "transition", "non-tech", "age"]):
            return {
                "intent": "career_related",
                "cluster": "career_switch",
                "confidence": 0.90,
            }

        # Skill development / beginner difficulty
        if any(w in lower for w in ["stuck", "error", "project", "practice", "tutorial hell", "syntax", "paralyzed", "hard time", "beginner", "how to build"]):
            return {
                "intent": "skill_development",
                "cluster": "beginner_difficulty",
                "confidence": 0.91,
            }

        # Informational default
        return {
            "intent": "informational",
            "cluster": "general_curiosity",
            "confidence": 0.82,
        }

    def collect_subreddit_insights(self, subreddit: str, category_slug: str) -> Dict[str, Any]:
        """
        Attempts to read the public JSON endpoint of a subreddit (no OAuth or private data).
        Falls back to verified fixtures if Reddit returns HTTP 429/403.
        """
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={self.max_posts}"
        result = {
            "subreddit": subreddit,
            "category_slug": category_slug,
            "insights": [],
            "status": "success",
            "is_demo": False,
            "error": None,
        }

        insights_found = []
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                children = data.get("data", {}).get("children", [])
                now_str = datetime.utcnow().isoformat()

                for post in children:
                    pdata = post.get("data", {})
                    if pdata.get("stickied", False):
                        continue

                    title = pdata.get("title", "").strip()
                    selftext = pdata.get("selftext", "").strip()
                    permalink = pdata.get("permalink", "")
                    post_url = f"https://www.reddit.com{permalink}" if permalink else f"https://www.reddit.com/r/{subreddit}"

                    combined_text = f"{title} {selftext}"
                    classification = self.classify_intent(combined_text)

                    insights_found.append(
                        {
                            "category_slug": category_slug,
                            "source_type": "reddit",
                            "title_or_question": title[:200],
                            "body_snippet": selftext[:400] if selftext else title[:200],
                            "intent_classification": classification["intent"],
                            "pain_point_cluster": classification["cluster"],
                            "confidence_score": classification["confidence"],
                            "source_url": post_url,
                            "collected_at": now_str,
                        }
                    )
            else:
                logger.warning(f"Reddit r/{subreddit} returned HTTP {resp.status_code}")
                result["error"] = f"HTTP {resp.status_code}"
        except Exception as e:
            logger.info(f"Could not connect to live Reddit r/{subreddit} ({e}). Evaluating fixture fallback.")
            result["error"] = str(e)

        if insights_found:
            result["insights"] = insights_found
            result["is_demo"] = False
            return result

        # Fallback to fixtures
        if self.allow_demo_fallback:
            fixture_insights = self._load_fixture_data(category_slug)
            if fixture_insights:
                result["insights"] = fixture_insights
                result["is_demo"] = True
                result["status"] = "fallback_fixture"
                return result

        result["status"] = "no_data"
        return result

    def _load_fixture_data(self, category_slug: str) -> List[Dict[str, Any]]:
        if not self.fixture_path:
            return []
        fixture_file = self.fixture_path / "audience_sample.json"
        if not fixture_file.exists():
            return []

        try:
            with open(fixture_file, "r", encoding="utf-8") as f:
                all_insights = json.load(f)
            now_str = datetime.utcnow().isoformat()
            filtered = [i for i in all_insights if i.get("category_slug") == category_slug]
            for item in filtered:
                item["collected_at"] = now_str
            return filtered
        except Exception as e:
            logger.error(f"Failed to read audience fixture: {e}")
            return []
