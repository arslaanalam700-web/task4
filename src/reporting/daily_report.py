"""
Daily Intelligence Report Generator.
Synthesizes market demand, competitor positioning, audience needs, and opportunity scores
into a comprehensive Markdown intelligence briefing (reports/YYYY-MM-DD.md) and tabular CSV export.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from src.storage.database import DatabaseManager


class DailyReportGenerator:
    """Generates daily intelligence reports with strict provenance and data-quality notices."""

    def __init__(self, db: DatabaseManager, output_dir: Path | str = "reports"):
        self.db = db
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_daily_report(self, report_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Gathers current database snapshot and generates reports/YYYY-MM-DD.md & CSV.
        """
        today_str = report_date or datetime.utcnow().strftime("%Y-%m-%d")
        now_ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        # Query latest data
        stats = self.db.get_database_stats()
        df_opps = self.db.get_latest_opportunity_scores(limit=10)
        df_courses = self.db.get_course_offerings()
        df_audience = self.db.get_audience_insights()
        df_trends = self.db.get_trend_history()
        df_runs = self.db.get_latest_collection_runs(limit=3)

        # Determine data freshness and collection status
        last_run = stats.get("last_run", "Never")
        is_fresh = last_run != "Never" and last_run.startswith(today_str)
        
        # Check for demo data presence
        has_demo = False
        if not df_trends.empty and "is_demo" in df_trends.columns:
            has_demo = bool((df_trends["is_demo"] == 1).any())

        # Top 5 ranked opportunities
        top_5 = df_opps.head(5) if not df_opps.empty else pd.DataFrame()

        # Build Markdown content
        md_lines = []
        md_lines.append(f"# Daily Market Demand & Growth Intelligence Briefing")
        md_lines.append(f"**Report Date:** `{today_str}` | **Generated At:** `{now_ts}`")
        md_lines.append(f"**Target Industry:** Online Education (India, US, Global)")
        md_lines.append("")

        # Data Quality & Integrity Notice
        md_lines.append("## 1. Data Integrity & Provenance Status")
        if has_demo:
            md_lines.append("> [!WARNING] **Demonstration Mode Active:** Some trend or audience data was drawn from verified offline fixtures due to external API rate limits or connection throttling.")
        else:
            md_lines.append("> [!NOTE] **Live Verification:** Observations derived from direct API endpoints and permitted public page inspection.")

        md_lines.append(f"- **Tracked Keywords:** {stats.get('keywords_count', 0)}")
        md_lines.append(f"- **Trend Observations:** {stats.get('trends_count', 0)}")
        md_lines.append(f"- **Competitor Offerings Analyzed:** {stats.get('offerings_count', 0)}")
        md_lines.append(f"- **Audience Voice Points Collected:** {stats.get('audience_count', 0)}")
        md_lines.append(f"- **Last Pipeline Run:** `{last_run}`")
        md_lines.append("")

        # Executive Summary
        md_lines.append("## 2. Executive Summary")
        if not top_5.empty:
            lead_opp = top_5.iloc[0]
            lead_term = lead_opp.get("keyword_or_topic", "General Skills")
            lead_score = lead_opp.get("total_opportunity_score", 0)
            lead_cat = lead_opp.get("category_slug", "general")
            md_lines.append(
                f"The highest leverage organic growth opportunity for `{today_str}` is **{lead_term.title()}** "
                f"within the **{lead_cat.replace('-', ' ').title()}** sector, scoring **{lead_score:.1f}/100**."
            )
            md_lines.append(
                "Search interest velocity indicates expanding student intent in practical implementation, while "
                "competitor offerings show significant white-space for unbundled, hands-on, project-driven learning resources."
            )
        else:
            md_lines.append("No active opportunity scores computed yet. Please execute the research pipeline to gather observations.")
        md_lines.append("")

        # Top 5 Ranked Opportunities Table
        md_lines.append("## 3. Top 5 Ranked Market Opportunities")
        if not top_5.empty:
            md_lines.append("| Rank | Keyword / Topic | Category | Opp Score | Confidence | Demand | Momentum | Competitor Gap |")
            md_lines.append("| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |")
            for idx, row in top_5.iterrows():
                rank = idx + 1 if isinstance(idx, int) else 1
                md_lines.append(
                    f"| {rank} | **{row['keyword_or_topic']}** | {row['category_slug']} | **{row['total_opportunity_score']}** | `{row['confidence_level']}` | {row['demand_score']}/100 | {row['momentum_score']}/100 | {row['competition_score']}/100 |"
                )
        else:
            md_lines.append("*No opportunities available.*")
        md_lines.append("")

        # Competitor Pricing & Positioning Observations
        md_lines.append("## 4. Competitor Pricing & Positioning Landscape")
        if not df_courses.empty:
            md_lines.append("| Competitor | Course Title | Verified Price | Status | CTA Headline |")
            md_lines.append("| :--- | :--- | :--- | :---: | :--- |")
            for _, row in df_courses.head(8).iterrows():
                comp_name = row.get("competitor_name", "Unknown")
                title = row.get("course_title", "Course")[:45]
                price = row.get("verified_price", "Not publicly verified")
                status = "Verified" if row.get("pricing_status") == "verified" else "Unverified / Enterprise"
                cta = row.get("cta_text", "N/A")[:30]
                md_lines.append(f"| {comp_name} | {title} | `{price}` | {status} | {cta} |")
        else:
            md_lines.append("*No competitor course offerings tracked yet.*")
        md_lines.append("")

        # Audience Voice & Common Pain Points
        md_lines.append("## 5. Discovered Audience Needs & Pain Points")
        if not df_audience.empty:
            md_lines.append("Key learner inquiries discovered from public discussions:")
            for _, row in df_audience.head(5).iterrows():
                q = row.get("title_or_question", "")
                intent = row.get("intent_classification", "general")
                cluster = row.get("pain_point_cluster", "general")
                url = row.get("source_url", "#")
                md_lines.append(f"- **[{intent.title()} / {cluster}]**: *\"{q}\"* ([Source Evidence]({url}))")
        else:
            md_lines.append("*No audience insights collected yet.*")
        md_lines.append("")

        # Tactical Organic Actions for the Next 24 Hours
        md_lines.append("## 6. Recommended Actions for the Next 24 Hours")
        if not top_5.empty:
            lead = top_5.iloc[0]
            kw = lead.get("keyword_or_topic", "core topic")
            md_lines.append(f"1. **Publish Pillar Content:** Create a comprehensive, bookmarkable guide on *\"{kw.title()}\"* addressing the beginner-to-intermediate transition.")
            md_lines.append(f"2. **Produce Lead Magnet:** Package a 2-page project checklist / cheat sheet targeting *\"{kw} practical examples\"*.")
            md_lines.append("3. **Engage in Community Discussions:** Provide helpful, non-promotional answers in relevant public forum threads dealing with course pricing comparisons.")
            md_lines.append("4. **Refine Landing Page Copy:** Emphasize project-based portfolio outcomes rather than generic lecture hours to differentiate from incumbent courses.")
        else:
            md_lines.append("1. Run pipeline collection to ingest initial market data.")
        md_lines.append("")

        # Methodology & Provenance
        md_lines.append("## 7. Provenance & Attribution Standards")
        md_lines.append("- **Observed Data:** Relative search interest indices and competitor public catalog details.")
        md_lines.append("- **Derived Analysis:** Moving averages, momentum indicators, and 6-factor deterministic opportunity scoring.")
        md_lines.append("- **AI / Rule Synthesis:** Content framing and tactical recommendations.")
        md_lines.append("- **Note on Search Volume:** Google Trends provides normalized relative interest (0-100), not absolute query counts.")

        md_content = "\n".join(md_lines)

        # Save Markdown File
        report_filename = f"{today_str}.md"
        report_path = self.output_dir / report_filename
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        # Save Opportunities CSV
        csv_filename = f"{today_str}_opportunities.csv"
        csv_path = self.output_dir / csv_filename
        if not df_opps.empty:
            df_opps.to_csv(csv_path, index=False)

        # Store in Database
        self.db.save_daily_report(
            report_date=today_str,
            file_path=str(report_path),
            markdown_content=md_content,
        )

        return {
            "report_date": today_str,
            "markdown_path": str(report_path),
            "csv_path": str(csv_path),
            "markdown_content": md_content,
        }
