"""
Deterministic Opportunity Scoring Engine.
Calculates a 0-100 opportunity score using 6 transparent, weighted dimensions.
Distinguishes measured evidence, derived indicators, and confidence levels.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import numpy as np
from src.config import ScoringWeights


class OpportunityScoringEngine:
    """
    Ranks market opportunities deterministically.
    Never assumes missing competitor data implies low competition (neutral 50.0 + evidence penalty).
    """

    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.weights = weights or ScoringWeights()

    def calculate_score(
        self,
        category_slug: str,
        keyword_or_topic: str,
        geography: str = "IN",
        relative_interest: Optional[float] = None,
        momentum_delta: Optional[float] = None,
        is_exact_category_match: bool = True,
        competitor_count: Optional[int] = None,
        has_verified_competitor_pricing: bool = False,
        intent_type: Optional[str] = None,
        sources_count: int = 1,
        is_demo_data: bool = False,
        freshness_days: int = 1,
    ) -> Dict[str, Any]:
        """
        Calculates individual component scores (0-100) and weighted total.
        Returns a complete audit trail of the calculation.
        """
        # 1. Demand Evidence Score (0-100)
        # Directly based on measured Google Trends relative-interest index (0-100)
        if relative_interest is not None:
            demand_score = float(np.clip(relative_interest, 0.0, 100.0))
            demand_notes = f"Measured relative-interest index: {demand_score:.1f}/100"
        else:
            demand_score = 25.0  # Conservative baseline when unobserved
            demand_notes = "Unobserved search demand; defaulted to conservative baseline (25.0)"

        # 2. Industry Relevance Score (0-100)
        # Direct curriculum alignment with target category
        if is_exact_category_match:
            relevance_score = 95.0
            relevance_notes = "Direct primary category alignment"
        else:
            relevance_score = 70.0
            relevance_notes = "Adjacent or peripheral topic alignment"

        # 3. Growth Momentum Score (0-100)
        # Scaled from momentum delta: 0 delta -> 50.0 baseline; +10 delta -> 100.0; -10 delta -> 0.0
        if momentum_delta is not None:
            raw_momentum = 50.0 + (momentum_delta * 5.0)
            momentum_score = float(np.clip(raw_momentum, 0.0, 100.0))
            momentum_notes = f"Derived momentum velocity: {momentum_delta:+.2f} pts/wk"
        else:
            momentum_score = 50.0  # Neutral baseline
            momentum_notes = "No historical velocity delta; neutral baseline (50.0)"

        # 4. Competitive Opportunity Score (0-100)
        # Measures white-space opportunity.
        # CRITICAL RULE: Missing competition data is NEVER treated as low competition.
        if competitor_count is None or competitor_count == 0:
            competition_score = 50.0
            competition_notes = "Competitor coverage unverified; neutral assumption applied (50.0)"
        else:
            # If many competitors offer verified cheap courses, white-space opportunity is lower
            # If competitors charge high unverified fees or have gaps, opportunity is higher
            if has_verified_competitor_pricing and competitor_count > 3:
                competition_score = 55.0  # Saturated, established price points
                competition_notes = f"Saturated market with {competitor_count} verified competitors"
            elif competitor_count <= 2:
                competition_score = 80.0  # Favorable competitive gap
                competition_notes = f"Few active competitors ({competitor_count}) detected"
            else:
                competition_score = 65.0
                competition_notes = f"Moderate competition ({competitor_count} observed competitors)"

        # 5. Audience Intent Score (0-100)
        # High purchase/career intent yields higher commercial organic value
        intent_map = {
            "purchase_oriented": (95.0, "High commercial purchase intent"),
            "comparison": (90.0, "Active comparative evaluation intent"),
            "career_related": (85.0, "High upskilling/career-switch intent"),
            "skill_development": (75.0, "Practical implementation need"),
            "informational": (65.0, "Top-of-funnel informational intent"),
        }
        intent_score, intent_notes = intent_map.get(intent_type, (60.0, "Unclassified / exploratory intent"))

        # 6. Evidence Quality & Freshness Score (0-100)
        # Penalizes weak, unverified, or stale evidence
        base_quality = 40.0
        if sources_count >= 2:
            base_quality += 30.0
        elif sources_count == 1:
            base_quality += 15.0

        if not is_demo_data:
            base_quality += 20.0  # Real verified live observation bonus
        else:
            base_quality += 10.0  # Offline fixture baseline

        if freshness_days <= 7:
            base_quality += 10.0
        elif freshness_days <= 30:
            base_quality += 5.0

        evidence_score = float(np.clip(base_quality, 0.0, 100.0))
        evidence_notes = f"Sources: {sources_count}, Demo: {is_demo_data}, Freshness: {freshness_days}d"

        # Calculate Total Weighted Opportunity Score
        total_score = (
            (self.weights.demand_evidence * demand_score)
            + (self.weights.industry_relevance * relevance_score)
            + (self.weights.growth_momentum * momentum_score)
            + (self.weights.competitive_opportunity * competition_score)
            + (self.weights.audience_intent * intent_score)
            + (self.weights.evidence_quality * evidence_score)
        )
        total_score = round(float(np.clip(total_score, 0.0, 100.0)), 2)

        # Confidence Level Determination
        if evidence_score >= 80.0 and sources_count >= 2:
            confidence_level = "High"
        elif evidence_score >= 60.0:
            confidence_level = "Medium"
        else:
            confidence_level = "Low"

        # Calculation audit breakdown
        breakdown = {
            "demand": {"score": round(demand_score, 1), "weight": self.weights.demand_evidence, "contribution": round(demand_score * self.weights.demand_evidence, 2), "notes": demand_notes},
            "relevance": {"score": round(relevance_score, 1), "weight": self.weights.industry_relevance, "contribution": round(relevance_score * self.weights.industry_relevance, 2), "notes": relevance_notes},
            "momentum": {"score": round(momentum_score, 1), "weight": self.weights.growth_momentum, "contribution": round(momentum_score * self.weights.growth_momentum, 2), "notes": momentum_notes},
            "competition": {"score": round(competition_score, 1), "weight": self.weights.competitive_opportunity, "contribution": round(competition_score * self.weights.competitive_opportunity, 2), "notes": competition_notes},
            "intent": {"score": round(intent_score, 1), "weight": self.weights.audience_intent, "contribution": round(intent_score * self.weights.audience_intent, 2), "notes": intent_notes},
            "evidence": {"score": round(evidence_score, 1), "weight": self.weights.evidence_quality, "contribution": round(evidence_score * self.weights.evidence_quality, 2), "notes": evidence_notes},
        }

        return {
            "category_slug": category_slug,
            "keyword_or_topic": keyword_or_topic,
            "geography": geography,
            "demand_score": round(demand_score, 1),
            "relevance_score": round(relevance_score, 1),
            "momentum_score": round(momentum_score, 1),
            "competition_score": round(competition_score, 1),
            "intent_score": round(intent_score, 1),
            "evidence_score": round(evidence_score, 1),
            "total_opportunity_score": total_score,
            "confidence_level": confidence_level,
            "scored_at": datetime.utcnow().isoformat(),
            "calculation_breakdown": breakdown,
        }
