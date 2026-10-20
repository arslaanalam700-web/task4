"""
Configuration module for AI Market Demand & Growth Intelligence Agent.
Handles loading YAML configurations, environment overrides, and schema validation.
"""

from pathlib import Path
from typing import Dict, List, Optional
import os
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

# Load .env file if available
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class KeywordCategory(BaseModel):
    name: str
    slug: str
    keywords: List[str] = Field(default_factory=list)


class Geography(BaseModel):
    code: str
    name: str


class GeographiesConfig(BaseModel):
    primary: Geography
    optional: List[Geography] = Field(default_factory=list)


class ResearchScope(BaseModel):
    industry: str = "Online education"
    categories: List[KeywordCategory] = Field(default_factory=list)
    geographies: GeographiesConfig
    timeframes: Dict[str, object] = Field(default_factory=dict)


class CompetitorProfile(BaseModel):
    id: str
    name: str
    website: str
    target_audience: str = ""
    sample_categories: List[str] = Field(default_factory=list)
    public_catalog_url: str = ""


class ScoringWeights(BaseModel):
    demand_evidence: float = 0.30
    industry_relevance: float = 0.20
    growth_momentum: float = 0.15
    competitive_opportunity: float = 0.15
    audience_intent: float = 0.10
    evidence_quality: float = 0.10

    @model_validator(mode="after")
    def validate_weights_sum(self):
        total = (
            self.demand_evidence
            + self.industry_relevance
            + self.growth_momentum
            + self.competitive_opportunity
            + self.audience_intent
            + self.evidence_quality
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Scoring weights must sum to 1.0 (current sum: {total:.4f})")
        return self


class GoogleTrendsCollectorConfig(BaseModel):
    enabled: bool = True
    sleep_between_requests: float = 2.0
    timeout_seconds: int = 10
    max_retries: int = 2
    allow_demo_fallback: bool = True


class CompetitorCollectorConfig(BaseModel):
    enabled: bool = True
    request_timeout: int = 8
    user_agent: str = "MarketIntelligenceBot/1.0"
    max_pages_per_domain: int = 3
    verify_ssl: bool = True


class AudienceCollectorConfig(BaseModel):
    enabled: bool = True
    request_timeout: int = 8
    max_posts_per_sub: int = 15


class CollectorsConfig(BaseModel):
    google_trends: GoogleTrendsCollectorConfig = Field(default_factory=GoogleTrendsCollectorConfig)
    competitor: CompetitorCollectorConfig = Field(default_factory=CompetitorCollectorConfig)
    audience: AudienceCollectorConfig = Field(default_factory=AudienceCollectorConfig)


class StorageConfig(BaseModel):
    database_path: str = "data/market_intelligence.db"
    fixture_path: str = "data/fixtures"

    @property
    def absolute_db_path(self) -> Path:
        p = Path(self.database_path)
        return p if p.is_absolute() else BASE_DIR / p

    @property
    def absolute_fixture_path(self) -> Path:
        p = Path(self.fixture_path)
        return p if p.is_absolute() else BASE_DIR / p


class ReportingConfig(BaseModel):
    output_dir: str = "reports"
    top_n_opportunities: int = 5

    @property
    def absolute_output_dir(self) -> Path:
        p = Path(self.output_dir)
        return p if p.is_absolute() else BASE_DIR / p


class AudienceConfig(BaseModel):
    subreddits: List[str] = Field(default_factory=list)
    pain_point_triggers: List[str] = Field(default_factory=list)


class AppConfig(BaseModel):
    app: Dict[str, str] = Field(default_factory=dict)
    research: ResearchScope
    competitors: List[CompetitorProfile] = Field(default_factory=list)
    audience: AudienceConfig = Field(default_factory=AudienceConfig)
    scoring_weights: ScoringWeights = Field(default_factory=ScoringWeights)
    collectors: CollectorsConfig = Field(default_factory=CollectorsConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)


_cached_config: Optional[AppConfig] = None


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Loads configuration from YAML file and applies environment overrides."""
    global _cached_config
    if _cached_config is not None and config_path is None:
        return _cached_config

    target_path = Path(config_path) if config_path else BASE_DIR / "config" / "settings.yaml"

    if not target_path.exists():
        raise FileNotFoundError(f"Configuration file not found at: {target_path}")

    with open(target_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Environment variable overrides
    if os.getenv("DATABASE_PATH"):
        data.setdefault("storage", {})["database_path"] = os.getenv("DATABASE_PATH")
    if os.getenv("REPORTING_DIR"):
        data.setdefault("reporting", {})["output_dir"] = os.getenv("REPORTING_DIR")

    config = AppConfig(**data)
    if config_path is None:
        _cached_config = config
    return config


def reset_cached_config():
    """Resets the singleton config cache (useful for tests)."""
    global _cached_config
    _cached_config = None
