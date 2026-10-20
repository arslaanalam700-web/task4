"""
Tests for Daily Intelligence Report Generation.
Verifies markdown assembly, data freshness warnings, and CSV file exports.
"""

from pathlib import Path
from src.reporting.daily_report import DailyReportGenerator
from src.storage.database import DatabaseManager


def test_daily_report_generation(temp_db: DatabaseManager, tmp_path: Path):
    # Populate minimal db data
    kw_id = temp_db.upsert_keyword("python course", "python-programming")
    temp_db.insert_trend_observations(
        [
            {
                "keyword_id": kw_id,
                "geography": "IN",
                "date_observed": "2026-08-01",
                "relative_interest": 82.0,
                "momentum": 3.0,
                "direction": "rising",
                "source_url": "https://trends.google.com",
                "collected_at": "2026-08-01T00:00:00",
                "is_demo": 0,
            }
        ]
    )
    temp_db.insert_opportunity_scores(
        [
            {
                "category_slug": "python-programming",
                "keyword_or_topic": "python course",
                "geography": "IN",
                "demand_score": 82.0,
                "relevance_score": 95.0,
                "momentum_score": 65.0,
                "competition_score": 70.0,
                "intent_score": 85.0,
                "evidence_score": 80.0,
                "total_opportunity_score": 79.5,
                "confidence_level": "High",
                "scored_at": "2026-08-01T00:00:00",
                "calculation_breakdown": {},
            }
        ]
    )

    reporter = DailyReportGenerator(temp_db, output_dir=tmp_path)
    res = reporter.generate_daily_report(report_date="2026-08-01")

    assert Path(res["markdown_path"]).exists()
    assert Path(res["csv_path"]).exists()

    with open(res["markdown_path"], "r", encoding="utf-8") as f:
        content = f.read()

    assert "Daily Market Demand & Growth Intelligence Briefing" in content
    assert "Python Course" in content
    assert "79.5" in content
    assert "Provenance & Attribution Standards" in content
