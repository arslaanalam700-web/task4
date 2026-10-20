"""
Content Intelligence Module.
Transforms empirical demand trends, competitor pricing gaps, and audience pain points
into actionable, high-ROI organic marketing content concepts.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from src.intelligence.ai_provider import AIProvider


class ContentIdeaGenerator:
    """Generates structured, evidence-backed content plans using LLM or deterministic rules."""

    def __init__(self, ai_provider: Optional[AIProvider] = None):
        self.ai = ai_provider or AIProvider()

    def generate_ideas_for_opportunity(
        self,
        opportunity: Dict[str, Any],
        competitors_summary: Optional[List[Dict[str, Any]]] = None,
        audience_insight: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generates 2 to 3 multi-format organic content assets for a scored opportunity.
        Retains strict traceability to verified source evidence.
        """
        keyword = opportunity.get("keyword_or_topic", "Course")
        cat_slug = opportunity.get("category_slug", "general")
        opp_id = opportunity.get("id")
        opp_score = opportunity.get("total_opportunity_score", 70.0)

        # Collect supporting evidence links
        evidence_urls = []
        if audience_insight and audience_insight.get("source_url"):
            evidence_urls.append(audience_insight["source_url"])
        if competitors_summary:
            for c in competitors_summary[:2]:
                if c.get("landing_url"):
                    evidence_urls.append(c["landing_url"])

        # Construct deterministic templates based on intent & topic
        ideas = []

        # 1. Comparison & Buying Guide (High intent)
        ideas.append(
            {
                "opportunity_score_id": opp_id,
                "title": f"The Realistic 2026 Guide to {keyword.title()}: Cost, Roadmap, and Honest Comparison",
                "target_keyword": keyword,
                "category_slug": cat_slug,
                "intended_audience": "Career switchers and professionals evaluating paid vs free learning paths",
                "search_intent": "Comparison / Purchase Decision",
                "content_format": "Course Comparison & Buyer's Guide",
                "production_effort": "Medium",
                "suggested_cta": "Download our Free Syllabus & ROI Comparison Worksheet",
                "rationale": f"High commercial intent with verified demand index of {opportunity.get('demand_score', 'N/A')}. Addresses learner anxiety regarding certification value vs price.",
                "supporting_evidence_urls": evidence_urls,
                "generated_at": datetime.utcnow().isoformat(),
                "is_ai_generated": False,
            }
        )

        # 2. Hands-on Tutorial / Problem Solver (Overcomes Tutorial Hell)
        ideas.append(
            {
                "opportunity_score_id": opp_id,
                "title": f"Stop Tutorial Hell: How to Build Your First Real-World Project with {keyword.title()}",
                "target_keyword": f"{keyword} project tutorial",
                "category_slug": cat_slug,
                "intended_audience": "Intermediate beginners stuck on syntax without portfolio projects",
                "search_intent": "Skill Development",
                "content_format": "Step-by-Step Hands-on Tutorial + GitHub Repo",
                "production_effort": "High",
                "suggested_cta": "Clone the starter template on GitHub and join our community discord",
                "rationale": "Audience discovery data highlights widespread paralysis when transitioning from video lectures to blank IDEs.",
                "supporting_evidence_urls": evidence_urls,
                "generated_at": datetime.utcnow().isoformat(),
                "is_ai_generated": False,
            }
        )

        # 3. High-Value Lead Magnet / Cheat Sheet
        ideas.append(
            {
                "opportunity_score_id": opp_id,
                "title": f"The No-Fluff {keyword.title()} Interview & Architecture Cheat Sheet (PDF)",
                "target_keyword": f"{keyword} cheat sheet pdf",
                "category_slug": cat_slug,
                "intended_audience": "Active job seekers preparing for technical interviews",
                "search_intent": "Career Preparation",
                "content_format": "Free Downloadable Lead Magnet / Summary Sheet",
                "production_effort": "Low",
                "suggested_cta": "Get the Free 2-Page PDF Delivered to Your Inbox",
                "rationale": "Captures top-of-funnel email leads by condensing essential formulas, architecture diagrams, and syntax nuances.",
                "supporting_evidence_urls": evidence_urls,
                "generated_at": datetime.utcnow().isoformat(),
                "is_ai_generated": False,
            }
        )

        # If local LLM is available, refine the titles and hooks
        if self.ai.is_available:
            prompt = (
                f"Given target keyword '{keyword}' in category '{cat_slug}', suggest a viral, high-trust YouTube video title "
                f"and hook that dispels myths about learning this skill. Keep it concise."
            )
            ai_res = self.ai.generate_completion(prompt)
            if ai_res:
                ideas.append(
                    {
                        "opportunity_score_id": opp_id,
                        "title": ai_res.split("\n")[0][:120],
                        "target_keyword": keyword,
                        "category_slug": cat_slug,
                        "intended_audience": "Visual learners exploring tech skills",
                        "search_intent": "Informational",
                        "content_format": "YouTube Video Breakdown",
                        "production_effort": "High",
                        "suggested_cta": "Subscribe for weekly practical tutorials",
                        "rationale": "Generated via local AI model from verified keyword demand.",
                        "supporting_evidence_urls": evidence_urls,
                        "generated_at": datetime.utcnow().isoformat(),
                        "is_ai_generated": True,
                    }
                )

        return ideas
