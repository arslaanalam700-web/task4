"""
Pytest configuration and shared fixtures for AI Market Demand & Growth Intelligence Agent.
"""

from pathlib import Path
import pytest
from src.config import AppConfig, load_config
from src.storage.database import DatabaseManager


@pytest.fixture
def temp_db(tmp_path: Path) -> DatabaseManager:
    """Creates an isolated temporary SQLite database for tests."""
    db_file = tmp_path / "test_market_intelligence.db"
    return DatabaseManager(db_file)


@pytest.fixture
def base_config() -> AppConfig:
    """Loads baseline application configuration."""
    return load_config()


@pytest.fixture
def sample_trend_records():
    return [
        {"term": "python course", "category_slug": "python-programming", "geography": "IN", "date_observed": "2026-08-01", "relative_interest": 75.0, "momentum": 2.0, "direction": "rising", "source_url": "https://trends.google.com", "collected_at": "2026-08-01T00:00:00", "is_demo": 1},
        {"term": "python course", "category_slug": "python-programming", "geography": "IN", "date_observed": "2026-08-08", "relative_interest": 85.0, "momentum": 5.0, "direction": "rising", "source_url": "https://trends.google.com", "collected_at": "2026-08-08T00:00:00", "is_demo": 1},
    ]
