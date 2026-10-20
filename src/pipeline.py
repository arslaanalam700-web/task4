"""
Master Research & Intelligence Pipeline Orchestrator.
Coordinates data collection, cleaning, scoring, content generation, and report publishing.
Guarantees resilience: failure of an individual data source does not abort the entire pipeline.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
from src.collectors.audience_collector import AudienceCollector
from src.collectors.competitor_collector import CompetitorCollector
from src.collectors.google_trends import GoogleTrendsCollector
from src.config import AppConfig, load_config
from src.intelligence.content_ideas import ContentIdeaGenerator
from src.intelligence.opportunity_scoring import OpportunityScoringEngine
from src.processing.trend_analysis import analyze_category_trends
from src.reporting.daily_report import DailyReportGenerator
from src.storage.database import DatabaseManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


class MarketIntelligencePipeline:
    """End-to-end autonomous research and growth intelligence pipeline."""

    def __init__(self, config: Optional[AppConfig] = None, force_fixtures: bool = False):
        self.config = config or load_config()
        self.force_fixtures = force_fixtures
        self.db = DatabaseManager(self.config.storage.absolute_db_path)
        self.fixture_dir = self.config.storage.absolute_fixture_path

        # Initialize collectors
        allow_demo = self.config.collectors.google_trends.allow_demo_fallback or force_fixtures
        self.trends_collector = GoogleTrendsCollector(
            timeout=self.config.collectors.google_trends.timeout_seconds,
            retries=self.config.collectors.google_trends.max_retries,
            sleep_between_requests=self.config.collectors.google_trends.sleep_between_requests,
            fixture_path=self.fixture_dir,
            allow_demo_fallback=allow_demo,
        )

        self.competitor_collector = CompetitorCollector(
            timeout=self.config.collectors.competitor.request_timeout,
            user_agent=self.config.collectors.competitor.user_agent,
            fixture_path=self.fixture_dir,
            allow_demo_fallback=allow_demo,
        )

        self.audience_collector = AudienceCollector(
            timeout=self.config.collectors.audience.request_timeout,
            max_posts_per_sub=self.config.collectors.audience.max_posts_per_sub,
            fixture_path=self.fixture_dir,
            allow_demo_fallback=allow_demo,
        )

        # Intelligence & scoring
        self.scoring_engine = OpportunityScoringEngine(weights=self.config.scoring_weights)
        self.content_generator = ContentIdeaGenerator()
        self.reporter = DailyReportGenerator(self.db, output_dir=self.config.reporting.absolute_output_dir)

    def run(self, selected_category_slug: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes full collection, analysis, scoring, and reporting workflow.
        Returns execution summary.
        """
        run_id = self.db.create_collection_run()
        logger.info(f"Starting market intelligence pipeline run #{run_id}")

        errors = []
        sources_contacted = 0
        total_records_saved = 0

        categories = self.config.research.categories
        if selected_category_slug:
            categories = [c for c in categories if c.slug == selected_category_slug]

        primary_geo = self.config.research.geographies.primary.code

        try:
            # 1. Collect & Store Keywords and Google Trends
            logger.info("Phase 1: Ingesting keywords & Google Trends observations...")
            for cat in categories:
                # Register keywords in db
                for kw in cat.keywords:
                    kw_id = self.db.upsert_keyword(kw, cat.slug, self.config.research.industry)

                sources_contacted += 1
                try:
                    trends_res = self.trends_collector.collect_interest_over_time(
                        keywords=cat.keywords,
                        category_slug=cat.slug,
                        geo=primary_geo,
                    )
                    records = trends_res.get("records", [])
                    if records:
                        # Map keyword IDs
                        kw_map = {k["term"]: k["id"] for k in self.db.get_keywords(cat.slug)}
                        for r in records:
                            r["keyword_id"] = kw_map.get(r["term"].lower(), 1)
                        saved_cnt = self.db.insert_trend_observations(records)
                        total_records_saved += saved_cnt
                    else:
                        errors.append(f"No trend data collected for category {cat.slug}")
                except Exception as e:
                    logger.error(f"Error collecting trends for {cat.slug}: {e}")
                    errors.append(f"Trends error [{cat.slug}]: {str(e)}")

            # 2. Collect Competitor Intelligence
            logger.info("Phase 2: Crawling competitor public offerings and pricing...")
            for comp in self.config.competitors:
                sources_contacted += 1
                try:
                    self.db.upsert_competitor(comp.id, comp.name, comp.website, comp.target_audience)
                    cat_dicts = [{"slug": c.slug, "name": c.name, "keywords": c.keywords} for c in categories]
                    comp_res = self.competitor_collector.collect_competitor_data(
                        competitor_profile=comp.model_dump(),
                        target_categories=cat_dicts,
                    )
                    offerings = comp_res.get("offerings", [])
                    if offerings:
                        for o in offerings:
                            o["competitor_id"] = comp.id
                        saved_cnt = self.db.insert_course_offerings(offerings)
                        total_records_saved += saved_cnt
                except Exception as e:
                    logger.error(f"Error collecting competitor {comp.name}: {e}")
                    errors.append(f"Competitor error [{comp.name}]: {str(e)}")

            # 3. Collect Audience Voice and Needs
            logger.info("Phase 3: Discovering audience learning inquiries and objections...")
            for idx, cat in enumerate(categories):
                # Map subreddit to category if available
                sub = self.config.audience.subreddits[idx % len(self.config.audience.subreddits)]
                sources_contacted += 1
                try:
                    aud_res = self.audience_collector.collect_subreddit_insights(subreddit=sub, category_slug=cat.slug)
                    insights = aud_res.get("insights", [])
                    if insights:
                        saved_cnt = self.db.insert_audience_insights(insights)
                        total_records_saved += saved_cnt
                except Exception as e:
                    logger.error(f"Error collecting audience insights for {cat.slug} from r/{sub}: {e}")
                    errors.append(f"Audience error [r/{sub}]: {str(e)}")

            # 4. Process Trends & Execute Deterministic Opportunity Scoring
            logger.info("Phase 4: Running trend momentum analysis & deterministic opportunity scoring...")
            df_trends = self.db.get_trend_history(geography=primary_geo)
            trend_summaries = analyze_category_trends(df_trends)

            # Get competitor counts and verified pricing status per category
            df_offerings = self.db.get_course_offerings()
            df_audience_all = self.db.get_audience_insights()

            scored_opportunities = []
            for item in trend_summaries:
                cat_slug = item["category_slug"]
                kw = item["term"]

                # Check competitor context for category
                cat_offers = df_offerings[df_offerings["category_slug"] == cat_slug] if not df_offerings.empty else pd.DataFrame()
                comp_count = len(cat_offers["competitor_id"].unique()) if not cat_offers.empty else 0
                has_verified = (cat_offers["pricing_status"] == "verified").any() if not cat_offers.empty else False

                # Audience intent match
                cat_aud = df_audience_all[df_audience_all["category_slug"] == cat_slug] if not df_audience_all.empty else pd.DataFrame()
                dominant_intent = cat_aud["intent_classification"].iloc[0] if not cat_aud.empty else "skill_development"

                opp = self.scoring_engine.calculate_score(
                    category_slug=cat_slug,
                    keyword_or_topic=kw,
                    geography=primary_geo,
                    relative_interest=item["latest_interest"],
                    momentum_delta=item["momentum"],
                    is_exact_category_match=True,
                    competitor_count=comp_count,
                    has_verified_competitor_pricing=has_verified,
                    intent_type=dominant_intent,
                    sources_count=2 if not cat_aud.empty else 1,
                    is_demo_data=self.force_fixtures or bool(df_trends["is_demo"].max() if not df_trends.empty else False),
                )
                scored_opportunities.append(opp)

            score_ids = self.db.insert_opportunity_scores(scored_opportunities)
            total_records_saved += len(score_ids)

            # 5. Generate Evidence-Backed Content Opportunities
            logger.info("Phase 5: Generating actionable content marketing strategies...")
            df_latest_opps = self.db.get_latest_opportunity_scores(limit=10)
            all_content_ideas = []
            for _, opp_row in df_latest_opps.iterrows():
                opp_dict = dict(opp_row)
                comp_subset = df_offerings[df_offerings["category_slug"] == opp_dict.get("category_slug")].to_dict(orient="records")
                aud_subset = df_audience_all[df_audience_all["category_slug"] == opp_dict.get("category_slug")]
                aud_dict = dict(aud_subset.iloc[0]) if not aud_subset.empty else None

                ideas = self.content_generator.generate_ideas_for_opportunity(
                    opportunity=opp_dict,
                    competitors_summary=comp_subset,
                    audience_insight=aud_dict,
                )
                all_content_ideas.extend(ideas)

            content_saved = self.db.insert_content_opportunities(all_content_ideas)
            total_records_saved += content_saved

            # 6. Generate Daily Intelligence Report
            logger.info("Phase 6: Publishing daily intelligence report and CSV...")
            report_summary = self.reporter.generate_daily_report()

            # Finish Collection Run Record
            status = "PARTIAL_FAIL" if errors else "SUCCESS"
            self.db.finish_collection_run(
                run_id=run_id,
                status=status,
                sources_count=sources_contacted,
                records_count=total_records_saved,
                errors=errors,
            )
            logger.info(f"Pipeline run #{run_id} completed with status: {status}. Saved {total_records_saved} records.")

            return {
                "run_id": run_id,
                "status": status,
                "sources_contacted": sources_contacted,
                "records_saved": total_records_saved,
                "errors": errors,
                "report": report_summary,
            }

        except Exception as e:
            logger.error(f"Fatal pipeline error: {e}", exc_info=True)
            self.db.finish_collection_run(
                run_id=run_id,
                status="FAILED",
                sources_count=sources_contacted,
                records_count=total_records_saved,
                errors=[str(e)],
            )
            raise
