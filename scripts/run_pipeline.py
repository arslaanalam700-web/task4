"""
CLI Entrypoint to execute the Market Demand & Growth Intelligence Pipeline.
Usage:
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --offline
    python scripts/run_pipeline.py --category python-programming
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

from src.pipeline import MarketIntelligencePipeline


def main():
    parser = argparse.ArgumentParser(description="Run AI Market Demand & Growth Intelligence Pipeline")
    parser.add_argument("--offline", action="store_true", help="Force offline mode using verified fixtures")
    parser.add_argument("--category", type=str, default=None, help="Target a specific category slug (e.g. 'python-programming')")
    args = parser.parse_args()

    print("=================================================================")
    print("[PIPELINE] Starting AI Market Demand & Growth Intelligence Pipeline")
    print("=================================================================")
    if args.offline:
        print("[MODE] Offline Fixture Baseline (Zero Network Dependencies)")
    else:
        print("[MODE] Live Data Collection with Resilient Fallback")

    pipeline = MarketIntelligencePipeline(force_fixtures=args.offline)
    result = pipeline.run(selected_category_slug=args.category)

    print("\n-----------------------------------------------------------------")
    print(f"[STATUS] Pipeline Completed! Run ID: #{result['run_id']} | Status: {result['status']}")
    print(f"[DATA] Sources Contacted: {result['sources_contacted']}")
    print(f"[STORAGE] Records Saved to SQLite: {result['records_saved']}")
    if result.get("errors"):
        print(f"[WARNINGS] {len(result['errors'])} source warnings logged (see database logs)")
    if result.get("report"):
        print(f"[REPORT] Daily Briefing Generated: {result['report']['markdown_path']}")
        print(f"[CSV] Opportunities CSV: {result['report']['csv_path']}")
    print("=================================================================\n")


if __name__ == "__main__":
    main()
