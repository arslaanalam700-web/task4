"""
End-to-End Smoke Test for Market Demand & Growth Intelligence Pipeline.
Verifies the complete pipeline runs offline with fixtures, storing observations,
calculating deterministic scores, generating content, and saving daily reports.
"""

from pathlib import Path
from src.config import load_config
from src.pipeline import MarketIntelligencePipeline


def test_full_pipeline_offline_execution(tmp_path: Path):
    # Load config and override DB and reporting path to tmp_path
    config = load_config()
    test_db_path = tmp_path / "e2e_test.db"
    test_report_dir = tmp_path / "e2e_reports"

    config.storage.database_path = str(test_db_path)
    config.reporting.output_dir = str(test_report_dir)

    # Initialize and execute pipeline forced with fixtures
    pipeline = MarketIntelligencePipeline(config=config, force_fixtures=True)
    summary = pipeline.run()

    # Assertions
    assert summary["status"] in ["SUCCESS", "PARTIAL_FAIL"]
    assert summary["records_saved"] > 0
    assert summary["sources_contacted"] > 0

    # Verify Database Tables
    stats = pipeline.db.get_database_stats()
    assert stats["keywords_count"] > 0
    assert stats["trends_count"] > 0
    assert stats["offerings_count"] > 0
    assert stats["audience_count"] > 0
    assert stats["opportunities_count"] > 0

    # Verify Report Output Files
    report_res = summary["report"]
    assert Path(report_res["markdown_path"]).exists()
    assert Path(report_res["csv_path"]).exists()

    # Content opportunities generated
    df_content = pipeline.db.get_content_opportunities()
    assert len(df_content) > 0
