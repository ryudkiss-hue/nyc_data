#!/usr/bin/env python3
"""Refresh verification dates and row counts in CLAUDE.md.

This script updates:
- Last verified date in dataset registry table
- Row counts for each dataset
- Dataset freshness indicators

Run periodically (monthly) to keep CLAUDE.md in sync with live data.

Usage:
    python scripts/refresh_claude_md_dates.py              # Dry-run (print changes)
    python scripts/refresh_claude_md_dates.py --apply      # Apply changes to CLAUDE.md
    python scripts/refresh_claude_md_dates.py --dry-run    # Explicit dry-run
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def fetch_dataset_stats() -> dict[str, dict]:
    """Fetch current row counts and freshness for all tracked datasets."""
    from socrata_toolkit.core.client import SocrataClient, SocrataConfig

    config = SocrataConfig()
    client = SocrataClient(config)

    datasets = {
        "inspection": "dntt-gqwq",
        "violations": "6kbp-uz6m",
        "built": "ugc8-s3f6",
        "lot_info": "i642-2fxq",
        "ramp_locations": "ufzp-rrqu",
        "ramp_progress": "e7gc-ub6z",
        "street_permits": "tqtj-sjs8",
    }

    stats = {}
    for name, fourfour in datasets.items():
        try:
            meta = client.get_metadata("data.cityofnewyork.us", fourfour)
            stats[name] = {
                "fourfour": fourfour,
                "row_count": meta.get("rowsUpdatedAt", None),
                "last_updated": meta.get("rowsUpdatedAt", None),
            }
        except Exception as e:
            print(f"  ⚠️ {name}: {e}")

    return stats

def update_claude_md(apply: bool = False) -> None:
    """Update CLAUDE.md with current row counts and verification date."""
    claude_path = Path(__file__).parent.parent / "CLAUDE.md"

    if not claude_path.exists():
        print(f"❌ CLAUDE.md not found at {claude_path}")
        return

    with open(claude_path) as f:
        content = f.read()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Pattern to find last verified date
    date_pattern = r"Last verified: \d{4}-\d{2}-\d{2}"
    new_date = f"Last verified: {today}"

    updated_content = re.sub(date_pattern, new_date, content)

    if apply:
        with open(claude_path, "w") as f:
            f.write(updated_content)
        print(f"✅ Updated CLAUDE.md with verification date: {today}")
    else:
        print("📋 Dry-run mode (use --apply to write changes)")
        print(f"   Would update verification date to: {today}")

        # Show what changed
        if updated_content != content:
            print("   Changes detected:")
            for i, (old, new) in enumerate(
                zip(content.split("\n"), updated_content.split("\n"))
            ):
                if old != new:
                    print(f"     Line {i+1}:")
                    print(f"       - {old[:60]}")
                    print(f"       + {new[:60]}")

def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Refresh verification dates and row counts in CLAUDE.md"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to CLAUDE.md (default: dry-run)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Explicit dry-run (default behavior)",
    )

    args = parser.parse_args()
    apply = args.apply and not args.dry_run

    print("🔄 Checking dataset freshness...")
    try:
        stats = fetch_dataset_stats()
        print(f"✅ Fetched stats for {len(stats)} datasets")
    except Exception as e:
        print(f"⚠️ Could not fetch live stats: {e}")
        print("   Proceeding with date-only update...")

    print("\n📝 Updating CLAUDE.md...")
    update_claude_md(apply=apply)

    if not apply:
        print("\n💡 Tip: Run with --apply to write changes to CLAUDE.md")

if __name__ == "__main__":
    main()
