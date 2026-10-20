"""
SQLite Storage Module for AI Market Demand & Growth Intelligence Agent.
Provides schema creation, indexing, duplicate prevention, and transactional query helpers.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import sqlite3
import pandas as pd


SCHEMA_SQL = """
-- Sources tracking
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_type TEXT NOT NULL, -- 'trends', 'competitor', 'audience'
    base_url TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    last_checked_at TEXT
);

-- Tracked keywords
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT NOT NULL,
    category_slug TEXT NOT NULL,
    industry TEXT NOT NULL DEFAULT 'Online education',
    created_at TEXT NOT NULL,
    UNIQUE(term, category_slug, industry)
);

-- Time-series Google Trends observations
CREATE TABLE IF NOT EXISTS trend_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword_id INTEGER NOT NULL,
    geography TEXT NOT NULL, -- e.g. 'IN', 'US', 'WORLD'
    date_observed TEXT NOT NULL, -- YYYY-MM-DD
    relative_interest REAL NOT NULL, -- 0.0 to 100.0 (normalized index)
    momentum REAL DEFAULT 0.0, -- velocity of interest change
    direction TEXT DEFAULT 'stable', -- 'rising', 'falling', 'stable', 'breakout'
    source_url TEXT,
    collected_at TEXT NOT NULL,
    is_demo INTEGER DEFAULT 0,
    FOREIGN KEY (keyword_id) REFERENCES keywords (id),
    UNIQUE(keyword_id, geography, date_observed)
);

-- Competitor metadata
CREATE TABLE IF NOT EXISTS competitors (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    website TEXT NOT NULL,
    target_audience TEXT,
    last_scraped_at TEXT
);

-- Competitor course offerings, pricing and positioning
CREATE TABLE IF NOT EXISTS course_offerings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competitor_id TEXT NOT NULL,
    category_slug TEXT NOT NULL,
    course_title TEXT NOT NULL,
    verified_price TEXT NOT NULL, -- e.g. '$49/mo', '₹2,499', or 'Not publicly verified'
    currency TEXT DEFAULT 'USD',
    pricing_status TEXT NOT NULL, -- 'verified', 'not_publicly_verified', 'free'
    promo_text TEXT,
    cta_text TEXT,
    landing_url TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    FOREIGN KEY (competitor_id) REFERENCES competitors (id),
    UNIQUE(competitor_id, course_title, category_slug)
);

-- Audience questions, challenges and intent discoveries
CREATE TABLE IF NOT EXISTS audience_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_slug TEXT NOT NULL,
    source_type TEXT NOT NULL, -- 'reddit', 'youtube_faq', 'forum'
    title_or_question TEXT NOT NULL,
    body_snippet TEXT,
    intent_classification TEXT NOT NULL, -- 'informational', 'comparison', 'purchase_oriented', 'skill_development', 'career_related'
    pain_point_cluster TEXT, -- 'pricing_objection', 'beginner_difficulty', 'career_switch', 'certification_value'
    confidence_score REAL DEFAULT 0.8,
    source_url TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    UNIQUE(source_url, title_or_question)
);

-- Transparent opportunity scoring records
CREATE TABLE IF NOT EXISTS opportunity_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_slug TEXT NOT NULL,
    keyword_or_topic TEXT NOT NULL,
    geography TEXT DEFAULT 'IN',
    demand_score REAL NOT NULL,
    relevance_score REAL NOT NULL,
    momentum_score REAL NOT NULL,
    competition_score REAL NOT NULL,
    intent_score REAL NOT NULL,
    evidence_score REAL NOT NULL,
    total_opportunity_score REAL NOT NULL,
    confidence_level TEXT NOT NULL, -- 'High', 'Medium', 'Low'
    scored_at TEXT NOT NULL,
    calculation_breakdown_json TEXT
);

-- Evidence-backed content opportunities
CREATE TABLE IF NOT EXISTS content_opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_score_id INTEGER,
    title TEXT NOT NULL,
    target_keyword TEXT NOT NULL,
    category_slug TEXT NOT NULL,
    intended_audience TEXT NOT NULL,
    search_intent TEXT NOT NULL,
    content_format TEXT NOT NULL,
    production_effort TEXT NOT NULL, -- 'Low', 'Medium', 'High'
    suggested_cta TEXT NOT NULL,
    rationale TEXT NOT NULL,
    supporting_evidence_urls TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    is_ai_generated INTEGER DEFAULT 0,
    FOREIGN KEY (opportunity_score_id) REFERENCES opportunity_scores (id)
);

-- Pipeline execution audit runs
CREATE TABLE IF NOT EXISTS collection_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL, -- 'RUNNING', 'SUCCESS', 'PARTIAL_FAIL', 'FAILED'
    sources_contacted_count INTEGER DEFAULT 0,
    records_collected_count INTEGER DEFAULT 0,
    errors_json TEXT
);

-- Generated daily intelligence reports
CREATE TABLE IF NOT EXISTS daily_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date TEXT NOT NULL UNIQUE, -- YYYY-MM-DD
    file_path TEXT NOT NULL,
    markdown_content TEXT NOT NULL,
    generated_at TEXT NOT NULL
);

-- Indexing for fast dashboard lookups
CREATE INDEX IF NOT EXISTS idx_trend_keyword ON trend_observations (keyword_id, geography);
CREATE INDEX IF NOT EXISTS idx_course_competitor ON course_offerings (competitor_id, category_slug);
CREATE INDEX IF NOT EXISTS idx_audience_category ON audience_insights (category_slug, intent_classification);
CREATE INDEX IF NOT EXISTS idx_opp_scores ON opportunity_scores (category_slug, total_opportunity_score DESC);
"""


class DatabaseManager:
    """Manages SQLite connections and provides typed query operations."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=20.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def init_schema(self) -> None:
        """Creates tables, foreign keys, and indexes if they do not exist."""
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    # --- Keyword Operations ---

    def upsert_keyword(self, term: str, category_slug: str, industry: str = "Online education") -> int:
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO keywords (term, category_slug, industry, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(term, category_slug, industry) DO UPDATE SET term=term
                RETURNING id;
                """,
                (term.strip().lower(), category_slug, industry, now),
            )
            row = cursor.fetchone()
            if row:
                return row[0]
            cursor.execute(
                "SELECT id FROM keywords WHERE term = ? AND category_slug = ? AND industry = ?",
                (term.strip().lower(), category_slug, industry),
            )
            return cursor.fetchone()[0]

    def get_keywords(self, category_slug: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if category_slug:
                cursor.execute("SELECT * FROM keywords WHERE category_slug = ? ORDER BY term", (category_slug,))
            else:
                cursor.execute("SELECT * FROM keywords ORDER BY category_slug, term")
            return [dict(row) for row in cursor.fetchall()]

    # --- Trend Observation Operations ---

    def insert_trend_observations(self, records: List[Dict[str, Any]]) -> int:
        """Batch inserts or replaces trend observations."""
        if not records:
            return 0
        inserted = 0
        sql = """
            INSERT INTO trend_observations 
            (keyword_id, geography, date_observed, relative_interest, momentum, direction, source_url, collected_at, is_demo)
            VALUES (:keyword_id, :geography, :date_observed, :relative_interest, :momentum, :direction, :source_url, :collected_at, :is_demo)
            ON CONFLICT(keyword_id, geography, date_observed) DO UPDATE SET
                relative_interest = excluded.relative_interest,
                momentum = excluded.momentum,
                direction = excluded.direction,
                collected_at = excluded.collected_at,
                is_demo = excluded.is_demo;
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, records)
            inserted = cursor.rowcount
            conn.commit()
        return inserted

    def get_trend_history(self, keyword_id: Optional[int] = None, geography: Optional[str] = None, category_slug: Optional[str] = None) -> pd.DataFrame:
        query = """
            SELECT t.id, t.keyword_id, k.term, k.category_slug, t.geography, t.date_observed, 
                   t.relative_interest, t.momentum, t.direction, t.source_url, t.collected_at, t.is_demo
            FROM trend_observations t
            JOIN keywords k ON t.keyword_id = k.id
            WHERE 1=1
        """
        params: List[Any] = []
        if keyword_id:
            query += " AND t.keyword_id = ?"
            params.append(keyword_id)
        if geography:
            query += " AND t.geography = ?"
            params.append(geography)
        if category_slug:
            query += " AND k.category_slug = ?"
            params.append(category_slug)
        query += " ORDER BY t.date_observed ASC"
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)

    # --- Competitor Operations ---

    def upsert_competitor(self, comp_id: str, name: str, website: str, target_audience: str = "") -> None:
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO competitors (id, name, website, target_audience, last_scraped_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    website = excluded.website,
                    target_audience = excluded.target_audience,
                    last_scraped_at = excluded.last_scraped_at;
                """,
                (comp_id, name, website, target_audience, now),
            )
            conn.commit()

    def insert_course_offerings(self, offerings: List[Dict[str, Any]]) -> int:
        if not offerings:
            return 0
        sql = """
            INSERT INTO course_offerings
            (competitor_id, category_slug, course_title, verified_price, currency, pricing_status, promo_text, cta_text, landing_url, collected_at)
            VALUES (:competitor_id, :category_slug, :course_title, :verified_price, :currency, :pricing_status, :promo_text, :cta_text, :landing_url, :collected_at)
            ON CONFLICT(competitor_id, course_title, category_slug) DO UPDATE SET
                verified_price = excluded.verified_price,
                currency = excluded.currency,
                pricing_status = excluded.pricing_status,
                promo_text = excluded.promo_text,
                cta_text = excluded.cta_text,
                landing_url = excluded.landing_url,
                collected_at = excluded.collected_at;
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, offerings)
            conn.commit()
            return cursor.rowcount

    def get_course_offerings(self, category_slug: Optional[str] = None, competitor_id: Optional[str] = None) -> pd.DataFrame:
        query = """
            SELECT o.*, c.name as competitor_name, c.website as competitor_website, c.target_audience
            FROM course_offerings o
            JOIN competitors c ON o.competitor_id = c.id
            WHERE 1=1
        """
        params: List[Any] = []
        if category_slug:
            query += " AND o.category_slug = ?"
            params.append(category_slug)
        if competitor_id:
            query += " AND o.competitor_id = ?"
            params.append(competitor_id)
        query += " ORDER BY c.name, o.course_title"
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)

    # --- Audience Insights Operations ---

    def insert_audience_insights(self, insights: List[Dict[str, Any]]) -> int:
        if not insights:
            return 0
        sql = """
            INSERT INTO audience_insights
            (category_slug, source_type, title_or_question, body_snippet, intent_classification, pain_point_cluster, confidence_score, source_url, collected_at)
            VALUES (:category_slug, :source_type, :title_or_question, :body_snippet, :intent_classification, :pain_point_cluster, :confidence_score, :source_url, :collected_at)
            ON CONFLICT(source_url, title_or_question) DO UPDATE SET
                intent_classification = excluded.intent_classification,
                pain_point_cluster = excluded.pain_point_cluster,
                confidence_score = excluded.confidence_score,
                collected_at = excluded.collected_at;
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, insights)
            conn.commit()
            return cursor.rowcount

    def get_audience_insights(self, category_slug: Optional[str] = None, intent: Optional[str] = None) -> pd.DataFrame:
        query = "SELECT * FROM audience_insights WHERE 1=1"
        params: List[Any] = []
        if category_slug:
            query += " AND category_slug = ?"
            params.append(category_slug)
        if intent:
            query += " AND intent_classification = ?"
            params.append(intent)
        query += " ORDER BY collected_at DESC"
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)

    # --- Opportunity Scoring Operations ---

    def insert_opportunity_scores(self, scores: List[Dict[str, Any]]) -> List[int]:
        if not scores:
            return []
        ids = []
        sql = """
            INSERT INTO opportunity_scores
            (category_slug, keyword_or_topic, geography, demand_score, relevance_score, momentum_score, competition_score, intent_score, evidence_score, total_opportunity_score, confidence_level, scored_at, calculation_breakdown_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for s in scores:
                cursor.execute(
                    sql,
                    (
                        s["category_slug"],
                        s["keyword_or_topic"],
                        s.get("geography", "IN"),
                        s["demand_score"],
                        s["relevance_score"],
                        s["momentum_score"],
                        s["competition_score"],
                        s["intent_score"],
                        s["evidence_score"],
                        s["total_opportunity_score"],
                        s["confidence_level"],
                        s.get("scored_at", datetime.utcnow().isoformat()),
                        json.dumps(s.get("calculation_breakdown", {})),
                    ),
                )
                ids.append(cursor.lastrowid)
            conn.commit()
        return ids

    def get_latest_opportunity_scores(self, category_slug: Optional[str] = None, limit: int = 50) -> pd.DataFrame:
        query = """
            WITH ranked AS (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY keyword_or_topic, category_slug ORDER BY id DESC) as rn
                FROM opportunity_scores
            )
            SELECT id, category_slug, keyword_or_topic, geography, demand_score, relevance_score, 
                   momentum_score, competition_score, intent_score, evidence_score, 
                   total_opportunity_score, confidence_level, scored_at, calculation_breakdown_json
            FROM ranked
            WHERE rn = 1
        """
        params: List[Any] = []
        if category_slug:
            query += " AND category_slug = ?"
            params.append(category_slug)
        query += " ORDER BY total_opportunity_score DESC, scored_at DESC LIMIT ?"
        params.append(limit)
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)

    # --- Content Opportunities Operations ---

    def insert_content_opportunities(self, content_list: List[Dict[str, Any]]) -> int:
        if not content_list:
            return 0
        sql = """
            INSERT INTO content_opportunities
            (opportunity_score_id, title, target_keyword, category_slug, intended_audience, search_intent, content_format, production_effort, suggested_cta, rationale, supporting_evidence_urls, generated_at, is_ai_generated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for c in content_list:
                cursor.execute(
                    sql,
                    (
                        c.get("opportunity_score_id"),
                        c["title"],
                        c["target_keyword"],
                        c["category_slug"],
                        c["intended_audience"],
                        c["search_intent"],
                        c["content_format"],
                        c["production_effort"],
                        c["suggested_cta"],
                        c["rationale"],
                        json.dumps(c.get("supporting_evidence_urls", [])),
                        c.get("generated_at", datetime.utcnow().isoformat()),
                        1 if c.get("is_ai_generated", False) else 0,
                    ),
                )
            conn.commit()
            return cursor.rowcount

    def get_content_opportunities(self, category_slug: Optional[str] = None) -> pd.DataFrame:
        query = "SELECT * FROM content_opportunities WHERE 1=1"
        params: List[Any] = []
        if category_slug:
            query += " AND category_slug = ?"
            params.append(category_slug)
        query += " ORDER BY id DESC"
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params)

    # --- Collection Runs Operations ---

    def create_collection_run(self) -> int:
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO collection_runs (started_at, status) VALUES (?, 'RUNNING')",
                (now,),
            )
            conn.commit()
            return cursor.lastrowid

    def finish_collection_run(self, run_id: int, status: str, sources_count: int, records_count: int, errors: Optional[List[str]] = None) -> None:
        now = datetime.utcnow().isoformat()
        errors_json = json.dumps(errors or [])
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE collection_runs
                SET completed_at = ?, status = ?, sources_contacted_count = ?, records_collected_count = ?, errors_json = ?
                WHERE id = ?
                """,
                (now, status, sources_count, records_count, errors_json, run_id),
            )
            conn.commit()

    def get_latest_collection_runs(self, limit: int = 10) -> pd.DataFrame:
        query = "SELECT * FROM collection_runs ORDER BY id DESC LIMIT ?"
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=[limit])

    # --- Daily Reports Operations ---

    def save_daily_report(self, report_date: str, file_path: str, markdown_content: str) -> None:
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO daily_reports (report_date, file_path, markdown_content, generated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(report_date) DO UPDATE SET
                    file_path = excluded.file_path,
                    markdown_content = excluded.markdown_content,
                    generated_at = excluded.generated_at;
                """,
                (report_date, file_path, markdown_content, now),
            )
            conn.commit()

    def get_daily_reports(self, limit: int = 15) -> pd.DataFrame:
        query = "SELECT id, report_date, file_path, generated_at FROM daily_reports ORDER BY report_date DESC LIMIT ?"
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=[limit])

    def get_report_content(self, report_date: str) -> Optional[str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT markdown_content FROM daily_reports WHERE report_date = ?", (report_date,))
            row = cursor.fetchone()
            return row[0] if row else None

    # --- System Metrics ---

    def get_database_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM keywords")
            keywords_count = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM trend_observations")
            trends_count = c.fetchone()[0]

            c.execute("SELECT COUNT(DISTINCT competitor_id) FROM course_offerings")
            competitors_count = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM course_offerings")
            offerings_count = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM audience_insights")
            audience_count = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM opportunity_scores")
            opportunities_count = c.fetchone()[0]

            c.execute("SELECT MAX(completed_at) FROM collection_runs WHERE status IN ('SUCCESS', 'PARTIAL_FAIL')")
            last_run = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM daily_reports")
            reports_count = c.fetchone()[0]

            return {
                "keywords_count": keywords_count,
                "trends_count": trends_count,
                "competitors_count": competitors_count,
                "offerings_count": offerings_count,
                "audience_count": audience_count,
                "opportunities_count": opportunities_count,
                "last_run": last_run or "None yet",
                "reports_count": reports_count,
            }
