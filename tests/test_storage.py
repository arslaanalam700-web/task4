"""
Tests for SQLite Database Storage and Operations.
Verifies table creation, upserts, deduplication constraints, and query retrievals.
"""

from src.storage.database import DatabaseManager


def test_schema_initialization(temp_db: DatabaseManager):
    stats = temp_db.get_database_stats()
    assert stats["keywords_count"] == 0
    assert stats["trends_count"] == 0
    assert stats["competitors_count"] == 0


def test_keyword_upsert_and_deduplication(temp_db: DatabaseManager):
    id1 = temp_db.upsert_keyword("python course", "python-programming", "Online education")
    id2 = temp_db.upsert_keyword("python course", "python-programming", "Online education")
    assert id1 == id2

    keywords = temp_db.get_keywords("python-programming")
    assert len(keywords) == 1
    assert keywords[0]["term"] == "python course"


def test_trend_observations_upsert(temp_db: DatabaseManager):
    kw_id = temp_db.upsert_keyword("python course", "python-programming")
    record = {
        "keyword_id": kw_id,
        "geography": "IN",
        "date_observed": "2026-08-01",
        "relative_interest": 80.0,
        "momentum": 2.0,
        "direction": "rising",
        "source_url": "https://trends.google.com",
        "collected_at": "2026-08-01T00:00:00",
        "is_demo": 0,
    }
    inserted = temp_db.insert_trend_observations([record])
    assert inserted == 1

    # Insert updated observation for same date (conflict update)
    record["relative_interest"] = 85.0
    temp_db.insert_trend_observations([record])

    df = temp_db.get_trend_history(keyword_id=kw_id, geography="IN")
    assert len(df) == 1
    assert df["relative_interest"].iloc[0] == 85.0


def test_competitor_and_course_offerings(temp_db: DatabaseManager):
    temp_db.upsert_competitor("coursera", "Coursera", "https://www.coursera.org", "Degree seekers")
    offering = {
        "competitor_id": "coursera",
        "category_slug": "python-programming",
        "course_title": "Python for Everybody",
        "verified_price": "$49/month",
        "currency": "USD",
        "pricing_status": "verified",
        "promo_text": "Financial aid available",
        "cta_text": "Enroll Now",
        "landing_url": "https://www.coursera.org/specializations/python",
        "collected_at": "2026-08-01T00:00:00",
    }
    inserted = temp_db.insert_course_offerings([offering])
    assert inserted == 1

    df_courses = temp_db.get_course_offerings(category_slug="python-programming")
    assert len(df_courses) == 1
    assert df_courses["verified_price"].iloc[0] == "$49/month"
    assert df_courses["competitor_name"].iloc[0] == "Coursera"
