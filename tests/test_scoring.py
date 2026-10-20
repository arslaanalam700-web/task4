"""
Tests for Deterministic Opportunity Scoring Engine.
Verifies score bounds [0, 100], missing-value handling, weight enforcement, and confidence tiers.
"""

import pytest
from src.config import ScoringWeights
from src.intelligence.opportunity_scoring import OpportunityScoringEngine


def test_scoring_weights_validation():
    # Valid weights that sum to 1.0
    weights = ScoringWeights(
        demand_evidence=0.30,
        industry_relevance=0.20,
        growth_momentum=0.15,
        competitive_opportunity=0.15,
        audience_intent=0.10,
        evidence_quality=0.10,
    )
    assert weights is not None

    # Invalid weights that do not sum to 1.0
    with pytest.raises(ValueError):
        ScoringWeights(
            demand_evidence=0.50,
            industry_relevance=0.50,
            growth_momentum=0.50,
            competitive_opportunity=0.15,
            audience_intent=0.10,
            evidence_quality=0.10,
        )


def test_deterministic_scoring_bounds():
    engine = OpportunityScoringEngine()

    # Extreme high input
    high_score = engine.calculate_score(
        category_slug="python-programming",
        keyword_or_topic="python course",
        geography="IN",
        relative_interest=100.0,
        momentum_delta=20.0,
        is_exact_category_match=True,
        competitor_count=1,
        has_verified_competitor_pricing=False,
        intent_type="purchase_oriented",
        sources_count=3,
        is_demo_data=False,
        freshness_days=1,
    )
    assert 0.0 <= high_score["total_opportunity_score"] <= 100.0
    assert high_score["confidence_level"] == "High"
    assert high_score["total_opportunity_score"] >= 80.0

    # Extreme low / missing input
    low_score = engine.calculate_score(
        category_slug="unrelated",
        keyword_or_topic="unknown topic",
        geography="IN",
        relative_interest=None,
        momentum_delta=-15.0,
        is_exact_category_match=False,
        competitor_count=None,
        has_verified_competitor_pricing=False,
        intent_type=None,
        sources_count=0,
        is_demo_data=True,
        freshness_days=60,
    )
    assert 0.0 <= low_score["total_opportunity_score"] <= 100.0
    assert low_score["confidence_level"] == "Low"
    assert low_score["total_opportunity_score"] < 50.0


def test_missing_competition_does_not_assume_low_competition():
    """
    CRITICAL REQUIREMENT: Avoid treating missing competition data as proof of low competition.
    Engine must assign neutral 50.0 competition score rather than a high 90+ score.
    """
    engine = OpportunityScoringEngine()
    result = engine.calculate_score(
        category_slug="data-analytics",
        keyword_or_topic="data analytics course",
        competitor_count=None,  # Missing!
    )
    assert result["competition_score"] == 50.0
    assert "neutral assumption" in result["calculation_breakdown"]["competition"]["notes"]


def test_scoring_determinism():
    """Exact same inputs must produce exact same outputs."""
    engine = OpportunityScoringEngine()
    run1 = engine.calculate_score(
        category_slug="python-programming",
        keyword_or_topic="python course",
        relative_interest=85.0,
        momentum_delta=3.5,
    )
    run2 = engine.calculate_score(
        category_slug="python-programming",
        keyword_or_topic="python course",
        relative_interest=85.0,
        momentum_delta=3.5,
    )
    assert run1["total_opportunity_score"] == run2["total_opportunity_score"]
    assert run1["demand_score"] == run2["demand_score"]
    assert run1["momentum_score"] == run2["momentum_score"]
