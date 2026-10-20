"""
AI Market Demand & Growth Intelligence Agent - Streamlit Web Dashboard.
Polished, production-ready interface for market trends, competitor intelligence,
audience insights, transparent opportunity scoring, and organic growth planning.
"""

import sys
from pathlib import Path
from datetime import datetime
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Setup paths
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.config import load_config
from src.pipeline import MarketIntelligencePipeline
from src.storage.database import DatabaseManager

# Page Configuration
st.set_page_config(
    page_title="AI Market Demand & Growth Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .badge-high {
        background-color: #DEF7EC;
        color: #03543F;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-med {
        background-color: #FEF08A;
        color: #713F12;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-low {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .stAlert {
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_db_and_config():
    config = load_config()
    db = DatabaseManager(config.storage.absolute_db_path)
    return db, config


db, config = get_db_and_config()

# Sidebar Controls
st.sidebar.image("https://img.icons8.com/fluency/96/combo-chart.png", width=64)
st.sidebar.title("Market Intelligence")
st.sidebar.markdown("**Growth Agent v1.0**")

# Category & Geography Filters
categories = [c.name for c in config.research.categories]
category_map = {c.name: c.slug for c in config.research.categories}
selected_cat_name = st.sidebar.selectbox("Course Category", ["All Categories"] + categories)
selected_cat_slug = category_map.get(selected_cat_name) if selected_cat_name != "All Categories" else None

geographies = [config.research.geographies.primary] + config.research.geographies.optional
geo_names = [g.name for g in geographies]
geo_map = {g.name: g.code for g in geographies}
selected_geo_name = st.sidebar.selectbox("Target Geography", geo_names)
selected_geo_code = geo_map.get(selected_geo_name, "IN")

score_threshold = st.sidebar.slider("Min Opportunity Score", min_value=0, max_value=100, value=50, step=5)

st.sidebar.divider()

# Navigation
page = st.sidebar.radio(
    "Navigation",
    [
        "🏛️ Overview",
        "📈 Demand Explorer",
        "🏢 Competitor Analysis",
        "👥 Audience Insights",
        "🎯 Opportunity Ranking",
        "💡 Content Planner",
        "📑 Reports & Data Quality",
    ],
)

st.sidebar.divider()

# Action Buttons
st.sidebar.markdown("### Pipeline Actions")
col_run, col_demo = st.sidebar.columns(2)
if col_run.button("⚡ Live Run", use_container_width=True):
    with st.spinner("Executing Research Pipeline (Live)..."):
        pipeline = MarketIntelligencePipeline(config=config, force_fixtures=False)
        res = pipeline.run(selected_category_slug=selected_cat_slug)
        st.sidebar.success(f"Run #{res['run_id']} finished!")
        st.rerun()

if col_demo.button("📦 Load Demo", use_container_width=True):
    with st.spinner("Ingesting Verified Offline Fixtures..."):
        pipeline = MarketIntelligencePipeline(config=config, force_fixtures=True)
        res = pipeline.run(selected_category_slug=selected_cat_slug)
        st.sidebar.success("Fixtures loaded successfully!")
        st.rerun()

# --- Page 1: Overview ---
if page == "🏛️ Overview":
    st.markdown('<div class="main-header">Market Demand & Growth Intelligence Overview</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub-header">Autonomous intelligence system tracking <strong>{config.research.industry}</strong> across <strong>{selected_geo_name}</strong></div>',
        unsafe_allow_html=True,
    )

    stats = db.get_database_stats()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Keywords Tracked", stats["keywords_count"], "Live Taxonomy")
    m2.metric("Trend Observations", stats["trends_count"], "Time-series points")
    m3.metric("Competitor Offerings", stats["offerings_count"], f"{stats['competitors_count']} Competitors")
    m4.metric("Audience Pain Points", stats["audience_count"], "Discussions")

    st.markdown("---")

    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("Top Opportunity Highlights")
        df_opps = db.get_latest_opportunity_scores(category_slug=selected_cat_slug, limit=5)
        if not df_opps.empty:
            df_display = df_opps[["keyword_or_topic", "category_slug", "total_opportunity_score", "confidence_level", "demand_score", "momentum_score"]].copy()
            df_display.columns = ["Keyword / Topic", "Category", "Score", "Confidence", "Demand", "Momentum"]
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("No opportunity scores found in database yet. Click '⚡ Live Run' or '📦 Load Demo' in the sidebar to populate data.")

    with c2:
        st.subheader("System Health & Freshness")
        st.markdown(
            f"""
            - **Industry:** `{config.research.industry}`
            - **Default Scoring Engine:** 6-Factor Deterministic
            - **Active Geography:** `{selected_geo_name} ({selected_geo_code})`
            - **Last Run Executed:** `{stats['last_run']}`
            - **Daily Reports Generated:** `{stats['reports_count']}`
            """
        )
        runs_df = db.get_latest_collection_runs(limit=3)
        if not runs_df.empty:
            st.markdown("**Recent Pipeline Runs:**")
            st.dataframe(runs_df[["id", "started_at", "status", "records_collected_count"]], hide_index=True)

# --- Page 2: Demand Explorer ---
elif page == "📈 Demand Explorer":
    st.markdown('<div class="main-header">Demand Explorer: Search Interest Trends</div>', unsafe_allow_html=True)
    st.info("ℹ️ **Data Methodology Notice:** Google Trends measures **normalized relative interest (0-100)** relative to the peak search period, NOT absolute search volumes. This prevents false estimations while providing accurate velocity and direction.")

    df_trends = db.get_trend_history(geography=selected_geo_code, category_slug=selected_cat_slug)

    if not df_trends.empty:
        # Filter by keyword if multiple
        available_keywords = sorted(list(df_trends["term"].unique()))
        selected_keywords = st.multiselect("Filter Keywords", available_keywords, default=available_keywords[:4])

        filtered_trends = df_trends[df_trends["term"].isin(selected_keywords)]

        if not filtered_trends.empty:
            fig = px.line(
                filtered_trends,
                x="date_observed",
                y="relative_interest",
                color="term",
                title=f"Relative Search Interest Over Time ({selected_geo_name})",
                labels={"date_observed": "Date", "relative_interest": "Relative Interest (0-100)", "term": "Keyword"},
                markers=True,
            )
            fig.update_layout(template="plotly_white", hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

            # Keyword Summary Table
            st.subheader("Trend Direction & Velocity Summary")
            summary_rows = []
            for term, grp in filtered_trends.groupby("term"):
                latest = grp.iloc[-1]
                summary_rows.append(
                    {
                        "Keyword": term,
                        "Category": latest.get("category_slug", "general"),
                        "Current Interest": latest.get("relative_interest", 0.0),
                        "Momentum Velocity": f"{latest.get('momentum', 0.0):+.2f}",
                        "Direction": latest.get("direction", "stable").upper(),
                        "Data Source": "Offline Fixture" if latest.get("is_demo") == 1 else "Live Google Trends",
                        "Source Link": latest.get("source_url", ""),
                    }
                )
            summary_df = pd.DataFrame(summary_rows)
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
        else:
            st.warning("Please select at least one keyword to view trends.")
    else:
        st.warning("No trend observations found for this selection. Ingest data using the sidebar.")

# --- Page 3: Competitor Analysis ---
elif page == "🏢 Competitor Analysis":
    st.markdown('<div class="main-header">Competitor Landscape & Offerings</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Public course offerings, verified price points, and market positioning</div>', unsafe_allow_html=True)

    df_courses = db.get_course_offerings(category_slug=selected_cat_slug)

    if not df_courses.empty:
        # Metrics
        total_courses = len(df_courses)
        verified_prices = len(df_courses[df_courses["pricing_status"] == "verified"])
        free_courses = len(df_courses[df_courses["pricing_status"] == "free"])
        unverified_prices = len(df_courses[df_courses["pricing_status"] == "not_publicly_verified"])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tracked Offerings", total_courses)
        c2.metric("Publicly Verified Prices", verified_prices)
        c3.metric("Free / Freemium Courses", free_courses)
        c4.metric("Unverified / Enterprise", unverified_prices)

        st.markdown("---")

        st.subheader("Competitor Course Comparison Table")
        display_df = df_courses[["competitor_name", "course_title", "category_slug", "verified_price", "pricing_status", "cta_text", "landing_url"]].copy()
        display_df.columns = ["Competitor", "Course Title", "Category", "Public Price", "Pricing Status", "Call To Action", "URL"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.subheader("Pricing Transparency Breakdown")
        status_counts = df_courses["pricing_status"].value_counts().reset_index()
        status_counts.columns = ["Pricing Status", "Count"]
        fig_pie = px.pie(
            status_counts,
            names="Pricing Status",
            values="Count",
            color="Pricing Status",
            color_discrete_map={
                "verified": "#10B981",
                "free": "#3B82F6",
                "not_publicly_verified": "#F59E0B",
            },
            title="Distribution of Competitor Pricing Visibility",
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    else:
        st.info("No competitor course records found. Run the pipeline to collect competitor data.")

# --- Page 4: Audience Insights ---
elif page == "👥 Audience Insights":
    st.markdown('<div class="main-header">Audience Needs & Voice of the Learner</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Discovered learner inquiries, objections, and buying considerations from public communities</div>', unsafe_allow_html=True)

    df_aud = db.get_audience_insights(category_slug=selected_cat_slug)

    if not df_aud.empty:
        c1, c2 = st.columns([1, 1])
        with c1:
            intent_counts = df_aud["intent_classification"].value_counts().reset_index()
            intent_counts.columns = ["Intent Classification", "Count"]
            fig_intent = px.bar(
                intent_counts,
                x="Intent Classification",
                y="Count",
                color="Intent Classification",
                title="Learner Search Intent Distribution",
            )
            fig_intent.update_layout(template="plotly_white", showlegend=False)
            st.plotly_chart(fig_intent, use_container_width=True)

        with c2:
            pain_counts = df_aud["pain_point_cluster"].value_counts().reset_index()
            pain_counts.columns = ["Pain Point Cluster", "Count"]
            fig_pain = px.pie(
                pain_counts,
                names="Pain Point Cluster",
                values="Count",
                title="Common Learner Friction Points & Objections",
            )
            st.plotly_chart(fig_pain, use_container_width=True)

        st.subheader("Learner Inquiries & Evidence Feed")
        for _, row in df_aud.iterrows():
            with st.expander(f"📌 {row['title_or_question']}"):
                st.write(f"**Learner Snippet:** {row['body_snippet']}")
                st.write(f"**Intent:** `{row['intent_classification']}` | **Friction Cluster:** `{row['pain_point_cluster']}` | **Confidence:** `{row['confidence_score']:.2f}`")
                st.markdown(f"**Verifiable Source:** [View Public Discussion Link]({row['source_url']})")
    else:
        st.info("No audience insights discovered yet. Use the sidebar to initiate collection.")

# --- Page 5: Opportunity Ranking ---
elif page == "🎯 Opportunity Ranking":
    st.markdown('<div class="main-header">Deterministic Opportunity Ranking</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Transparent 6-factor opportunity score ranking keywords by commercial organic leverage</div>', unsafe_allow_html=True)

    df_opps = db.get_latest_opportunity_scores(category_slug=selected_cat_slug, limit=50)

    if not df_opps.empty:
        # Apply score threshold filter
        filtered_opps = df_opps[df_opps["total_opportunity_score"] >= score_threshold].copy()

        st.markdown(f"Showing **{len(filtered_opps)}** opportunities scoring **{score_threshold}+** / 100")

        # Opportunity Table
        cols_show = ["keyword_or_topic", "category_slug", "total_opportunity_score", "confidence_level", "demand_score", "relevance_score", "momentum_score", "competition_score", "intent_score", "evidence_score"]
        opp_display = filtered_opps[cols_show].copy()
        opp_display.columns = ["Topic / Keyword", "Category", "Score (0-100)", "Confidence", "Demand", "Relevance", "Momentum", "Competition", "Intent", "Evidence"]
        st.dataframe(opp_display, use_container_width=True, hide_index=True)

        # Detailed breakdown inspector
        st.subheader("Score Audit Inspector")
        opp_options = filtered_opps["keyword_or_topic"].tolist()
        if opp_options:
            selected_term = st.selectbox("Select Topic to Inspect Component Audit Breakdown", opp_options)
            chosen_row = filtered_opps[filtered_opps["keyword_or_topic"] == selected_term].iloc[0]

            b1, b2, b3 = st.columns(3)
            b1.metric("Total Opportunity Score", f"{chosen_row['total_opportunity_score']}/100")
            b2.metric("Confidence Level", chosen_row["confidence_level"])
            b3.metric("Geography", chosen_row.get("geography", "IN"))

            breakdown_json = chosen_row.get("calculation_breakdown_json")
            if breakdown_json:
                try:
                    breakdown = json.loads(breakdown_json) if isinstance(breakdown_json, str) else breakdown_json
                    comp_names = list(breakdown.keys())
                    comp_contribs = [breakdown[k]["contribution"] for k in comp_names]
                    comp_notes = [breakdown[k]["notes"] for k in comp_names]

                    fig_bar = px.bar(
                        x=comp_names,
                        y=comp_contribs,
                        labels={"x": "Dimension", "y": "Weighted Contribution (pts)"},
                        title=f"Dimension Contribution Breakdown for '{selected_term}'",
                        text=comp_contribs,
                    )
                    fig_bar.update_layout(template="plotly_white")
                    st.plotly_chart(fig_bar, use_container_width=True)

                    st.markdown("**Component Logic Notes:**")
                    for k in comp_names:
                        st.markdown(f"- **{k.title()} ({breakdown[k]['score']}/100, weight: {breakdown[k]['weight']*100:.0f}%):** {breakdown[k]['notes']}")
                except Exception as e:
                    st.caption(f"Audit json parsing: {e}")

    else:
        st.info("No opportunity scores found. Run the research pipeline to compute scores.")

# --- Page 6: Content Planner ---
elif page == "💡 Content Planner":
    st.markdown('<div class="main-header">Evidence-Backed Content Planner</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Actionable organic marketing concepts generated directly from researched demand gaps</div>', unsafe_allow_html=True)

    df_content = db.get_content_opportunities(category_slug=selected_cat_slug)

    if not df_content.empty:
        # Download button
        csv_data = df_content.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Full Content Plan (CSV)",
            data=csv_data,
            file_name="content_opportunities_plan.csv",
            mime="text/csv",
        )

        st.markdown("---")

        for idx, row in df_content.iterrows():
            with st.container():
                st.markdown(f"### 📝 {row['title']}")
                c1, c2, c3, c4 = st.columns(4)
                c1.write(f"**Target Keyword:** `{row['target_keyword']}`")
                c2.write(f"**Format:** `{row['content_format']}`")
                c3.write(f"**Effort:** `{row['production_effort']}`")
                c4.write(f"**Search Intent:** `{row['search_intent']}`")

                st.write(f"**Target Audience:** {row['intended_audience']}")
                st.write(f"**Call to Action (CTA):** *{row['suggested_cta']}*")
                st.write(f"**Why Test This:** {row['rationale']}")

                ev_urls = row.get("supporting_evidence_urls")
                if ev_urls:
                    try:
                        urls = json.loads(ev_urls) if isinstance(ev_urls, str) else ev_urls
                        if urls:
                            st.markdown("**Supporting Evidence:** " + " | ".join([f"[Source {i+1}]({u})" for i, u in enumerate(urls)]))
                    except Exception:
                        pass
                st.markdown("---")
    else:
        st.info("No content opportunities generated yet. Run the pipeline to produce content strategies.")

# --- Page 7: Reports & Data Quality ---
elif page == "📑 Reports & Data Quality":
    st.markdown('<div class="main-header">Daily Reports & Pipeline Audit Log</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Download executive briefing documents and inspect data source freshness</div>', unsafe_allow_html=True)

    df_reports = db.get_daily_reports()

    if not df_reports.empty:
        selected_report_date = st.selectbox("Select Report Date", df_reports["report_date"].tolist())
        report_text = db.get_report_content(selected_report_date)

        col_dl_md, col_dl_csv = st.columns(2)
        if report_text:
            col_dl_md.download_button(
                label="📄 Download Report (Markdown)",
                data=report_text.encode("utf-8"),
                file_name=f"{selected_report_date}_intelligence_report.md",
                mime="text/markdown",
            )

        csv_file_path = Path("reports") / f"{selected_report_date}_opportunities.csv"
        if csv_file_path.exists():
            with open(csv_file_path, "rb") as f:
                col_dl_csv.download_button(
                    label="📈 Download Scored Opportunities (CSV)",
                    data=f.read(),
                    file_name=f"{selected_report_date}_opportunities.csv",
                    mime="text/csv",
                )

        st.markdown("---")
        if report_text:
            st.markdown(report_text)
    else:
        st.info("No daily reports generated yet. Execute the pipeline to generate your first briefing.")

    st.subheader("Data Pipeline Execution History & Health")
    runs_history = db.get_latest_collection_runs(limit=10)
    if not runs_history.empty:
        st.dataframe(runs_history, use_container_width=True, hide_index=True)
