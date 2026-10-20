"""
Tests for Data Collectors and Resilient Fallbacks.
Verifies graceful handling of network drops and fallback to offline fixtures.
"""

from pathlib import Path
from src.collectors.audience_collector import AudienceCollector
from src.collectors.competitor_collector import CompetitorCollector
from src.collectors.google_trends import GoogleTrendsCollector

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "data" / "fixtures"


def test_google_trends_fixture_fallback():
    collector = GoogleTrendsCollector(
        timeout=1,
        retries=1,
        fixture_path=FIXTURE_DIR,
        allow_demo_fallback=True,
    )
    # Even if live Google Trends fails or times out, fixture data must be returned
    res = collector.collect_interest_over_time(["python course"], "python-programming", geo="IN")
    assert res["status"] in ["success", "fallback_fixture"]
    assert len(res["records"]) > 0
    assert res["records"][0]["category_slug"] == "python-programming"


def test_competitor_fixture_fallback():
    collector = CompetitorCollector(
        timeout=1,
        fixture_path=FIXTURE_DIR,
        allow_demo_fallback=True,
    )
    res = collector.collect_competitor_data(
        competitor_profile={"id": "coursera", "name": "Coursera", "public_catalog_url": "https://invalid-url.fake"},
        target_categories=[{"slug": "python-programming", "name": "Python", "keywords": ["python"]}],
    )
    assert res["status"] in ["success", "fallback_fixture"]
    assert len(res["offerings"]) > 0


def test_audience_intent_classifier():
    collector = AudienceCollector()

    comp_res = collector.classify_intent("Coursera vs Udemy: which is better for python?")
    assert comp_res["intent"] == "comparison"

    pur_res = collector.classify_intent("Is the $2000 Bootcamp worth it or too expensive?")
    assert pur_res["intent"] == "purchase_oriented"
    assert pur_res["cluster"] == "pricing_objection"

    car_res = collector.classify_intent("How to switch careers from marketing to data analytics?")
    assert car_res["intent"] == "career_related"
    assert car_res["cluster"] == "career_switch"
