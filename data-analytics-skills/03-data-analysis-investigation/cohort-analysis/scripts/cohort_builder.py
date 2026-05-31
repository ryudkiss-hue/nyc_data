"""
Build a cohort membership table from user event data.

Input: CSV with columns user_id, cohort_date, activity_date
Output: CSV with user_id, cohort_period, activity_period, period_number

Usage:
    python cohort_builder.py --input events.csv --granularity monthly --output cohort_table.csv
    python cohort_builder.py --input events.csv --granularity weekly
"""

import argparse
import sys

import pandas as pd


FREQ_MAP = {
    "daily": "D",
    "weekly": "W-MON",
    "monthly": "MS",
}


def truncate_to_period(series: pd.Series, granularity: str) -> pd.Series:
    freq = FREQ_MAP[granularity]
    return series.dt.to_period(freq).dt.to_timestamp()


def build_cohort_table(df: pd.DataFrame, granularity: str = "monthly") -> pd.DataFrame:
    df = df.copy()
    df["cohort_date"] = pd.to_datetime(df["cohort_date"])
    df["activity_date"] = pd.to_datetime(df["activity_date"])

    df["cohort_period"] = truncate_to_period(df["cohort_date"], granularity)
    df["activity_period"] = truncate_to_period(df["activity_date"], granularity)

    # Period number: how many periods after cohort start did this activity occur?
    if granularity == "monthly":
        df["period_number"] = (
            (df["activity_period"].dt.year - df["cohort_period"].dt.year) * 12
            + (df["activity_period"].dt.month - df["cohort_period"].dt.month)
        )
    elif granularity == "weekly":
        df["period_number"] = ((df["activity_period"] - df["cohort_period"]).dt.days // 7)
    else:  # daily
        df["period_number"] = (df["activity_period"] - df["cohort_period"]).dt.days

    # Keep only non-negative periods (ignore activity before cohort date)
    df = df[df["period_number"] >= 0]

    return df[["user_id", "cohort_period", "activity_period", "period_number"]].drop_duplicates()


def main():
    parser = argparse.ArgumentParser(description="Build cohort membership table from event data.")
    parser.add_argument("--input", required=True, help="CSV with user_id, cohort_date, activity_date")
    parser.add_argument("--granularity", choices=list(FREQ_MAP.keys()), default="monthly")
    parser.add_argument("--output", help="Output CSV path (default: print summary)")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    result = build_cohort_table(df, granularity=args.granularity)
    print(f"Built cohort table: {len(result):,} rows, {result['cohort_period'].nunique()} cohorts")
    print(result.head(10).to_string(index=False))

    if args.output:
        result.to_csv(args.output, index=False)
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        import numpy as np
        rng = np.random.default_rng(5)
        n_users = 500
        signup_dates = pd.date_range("2023-01-01", periods=12, freq="MS").repeat(n_users // 12)
        user_ids = range(n_users)

        records = []
        for uid, signup in zip(user_ids, signup_dates):
            # Simulate retention: probability decreases each month
            for month_offset in range(12):
                if rng.random() < max(0.05, 0.7 - month_offset * 0.08):
                    activity = signup + pd.DateOffset(months=month_offset)
                    records.append({"user_id": uid, "cohort_date": signup, "activity_date": activity})

        demo = pd.DataFrame(records)
        result = build_cohort_table(demo, granularity="monthly")
        print(f"Demo: {len(result):,} rows, {result['cohort_period'].nunique()} cohorts")
        print(result.head(15).to_string(index=False))
    else:
        main()
