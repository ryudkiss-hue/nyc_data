"""
Check whether a dataset is fresh — i.e. the most recent record timestamp is within the expected lag.

Usage:
    python freshness_check.py --input data.csv --timestamp-col updated_at --max-lag-hours 25
    python freshness_check.py --input data.csv --timestamp-col event_date --max-lag-hours 2 --tz UTC
"""

import argparse
import sys
from datetime import datetime, timezone, timedelta

import pandas as pd


def check_freshness(
    df: pd.DataFrame,
    timestamp_col: str,
    max_lag_hours: float = 25.0,
    tz: str = "UTC",
) -> dict:
    if timestamp_col not in df.columns:
        return {"status": "ERROR", "message": f"Column '{timestamp_col}' not found"}

    ts = pd.to_datetime(df[timestamp_col], utc=True, errors="coerce")
    valid = ts.dropna()

    if valid.empty:
        return {"status": "FAIL", "message": "No valid timestamps found"}

    latest = valid.max()
    now = datetime.now(timezone.utc)
    lag = now - latest.to_pydatetime()
    lag_hours = lag.total_seconds() / 3600

    return {
        "timestamp_col": timestamp_col,
        "latest_record": latest.isoformat(),
        "current_time_utc": now.isoformat(),
        "lag_hours": round(lag_hours, 2),
        "max_lag_hours": max_lag_hours,
        "status": "PASS" if lag_hours <= max_lag_hours else "FAIL",
        "message": (
            f"Data is fresh — lag {lag_hours:.1f}h ≤ {max_lag_hours}h"
            if lag_hours <= max_lag_hours
            else f"Data is STALE — lag {lag_hours:.1f}h > {max_lag_hours}h limit"
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Check dataset freshness against expected lag.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--timestamp-col", required=True, help="Column containing the latest update timestamp")
    parser.add_argument("--max-lag-hours", type=float, default=25.0,
                        help="Maximum acceptable lag in hours (default: 25, i.e. daily pipeline with 1h buffer)")
    parser.add_argument("--tz", default="UTC", help="Timezone label for display (timestamps normalised to UTC)")
    args = parser.parse_args()

    df = pd.read_csv(args.input) if args.input.endswith(".csv") else pd.read_parquet(args.input)
    result = check_freshness(df, args.timestamp_col, max_lag_hours=args.max_lag_hours, tz=args.tz)

    for k, v in result.items():
        print(f"  {k}: {v}")

    sys.exit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        demo = pd.DataFrame({
            "event_id": range(100),
            "updated_at": [
                (now - timedelta(hours=h)).isoformat()
                for h in range(100, 0, -1)
            ]
        })
        # Last record is 1 hour ago — should PASS for 25h threshold
        result = check_freshness(demo, "updated_at", max_lag_hours=25)
        print(f"Status: {result['status']} — {result['message']}")

        # Simulate stale data (latest record is 30h ago)
        old_demo = pd.DataFrame({
            "updated_at": [(now - timedelta(hours=30)).isoformat()]
        })
        result2 = check_freshness(old_demo, "updated_at", max_lag_hours=25)
        print(f"Status: {result2['status']} — {result2['message']}")
    else:
        main()
