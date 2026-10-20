"""
CLI Entrypoint to generate daily intelligence reports.
Usage:
    python scripts/generate_report.py
    python scripts/generate_report.py --date 2026-10-20
"""

import argparse
import sys
from pathlib import Path

# Ensure UTF-8 output encoding on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_config
from src.reporting.daily_report import DailyReportGenerator
from src.storage.database import DatabaseManager


def main():
    parser = argparse.ArgumentParser(description="Generate Daily Market Intelligence Report")
    parser.add_argument("--date", type=str, default=None, help="Specific report date (YYYY-MM-DD)")
    args = parser.parse_args()

    config = load_config()
    db = DatabaseManager(config.storage.absolute_db_path)
    reporter = DailyReportGenerator(db, output_dir=config.reporting.absolute_output_dir)

    print(f"[REPORT] Generating Daily Report for date: {args.date or 'today'}...")
    res = reporter.generate_daily_report(report_date=args.date)

    print("[SUCCESS] Daily Report Generated Successfully!")
    print(f"[PATH] Markdown Report: {res['markdown_path']}")
    print(f"[CSV] Opportunities CSV: {res['csv_path']}")


if __name__ == "__main__":
    main()
