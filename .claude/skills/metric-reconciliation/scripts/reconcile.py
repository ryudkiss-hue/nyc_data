#!/usr/bin/env python3
"""
reconcile.py — Compare a metric across two NYC DOT data sources or time periods.

Typical use cases:
  - Dashboard violation count vs. Socrata API count
  - DuckDB cache totals vs. live API totals
  - Ramp completion this month vs. last month by borough

Usage:
    # Compare live API to local Parquet cache for violations
    python reconcile.py --key violations --metric-col objectid --agg count \
        --source-a api --source-b cache:data/cache/violations.parquet

    # Compare two time windows within the same dataset
    python reconcile.py --key inspection --metric-col objectid --agg count \
        --period-a "2026-05-01,2026-05-31" --period-b "2026-04-01,2026-04-30" \
        --date-col inspection_date --group-by borough

    # Tolerance 0.5% — anything beyond that is flagged
    python reconcile.py --key violations --metric-col objectid --agg count \
        --source-a api --source-b cache:data/cache/violations.parquet \
        --tolerance 0.5 --output recon_report.md
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, "src")

DATASET_KEYS = {
    "inspection": ("data.cityofnewyork.us", "dntt-gqwq"),
    "violations": ("data.cityofnewyork.us", "6kbp-uz6m"),
    "ramp_progress": ("data.cityofnewyork.us", "e7gc-ub6z"),
    "dismissals": ("data.cityofnewyork.us", "p4u2-3jgx"),
}

AGG_FUNCS = {
    "count": lambda s: s.count(),
    "sum": lambda s: s.sum(),
    "mean": lambda s: s.mean(),
    "nunique": lambda s: s.nunique(),
}


def fetch_api(key: str, rows: int = 50000) -> pd.DataFrame:
    from socrata_toolkit.core.client import SocrataClient, SocrataConfig

    domain, fourfour = DATASET_KEYS[key]
    client = SocrataClient(SocrataConfig())
    print(f"Fetching {key} from API (max {rows} rows)...", flush=True)
    return client.fetch_dataframe(domain, fourfour, max_rows=rows)


def load_source(source_spec: str, key: str, rows: int) -> pd.DataFrame:
    if source_spec == "api":
        return fetch_api(key, rows)
    if source_spec.startswith("cache:"):
        path = source_spec.split(":", 1)[1]
        print(f"Loading cache: {path}", flush=True)
        if path.endswith(".parquet"):
            return pd.read_parquet(path)
        return pd.read_csv(path)
    raise ValueError(f"Unknown source spec: {source_spec!r}. Use 'api' or 'cache:<path>'")


def filter_period(df: pd.DataFrame, period: str, date_col: str) -> pd.DataFrame:
    start, end = period.split(",")
    mask = (df[date_col] >= start) & (df[date_col] <= end)
    return df[mask]


def aggregate(df: pd.DataFrame, metric_col: str, agg: str, group_by: str | None) -> pd.Series:
    agg_fn = AGG_FUNCS[agg]
    if group_by and group_by in df.columns:
        return df.groupby(group_by)[metric_col].agg(agg)
    return pd.Series({"total": agg_fn(df[metric_col])})


def compare(
    series_a: pd.Series, series_b: pd.Series, label_a: str, label_b: str, tolerance: float
) -> pd.DataFrame:
    combined = pd.DataFrame({label_a: series_a, label_b: series_b}).fillna(0)
    combined["abs_diff"] = (combined[label_a] - combined[label_b]).abs()
    combined["pct_diff"] = (
        combined["abs_diff"] / combined[label_a].replace(0, float("nan")) * 100
    ).round(4)
    combined["status"] = combined["pct_diff"].apply(
        lambda p: (
            "CRITICAL"
            if p > tolerance * 5
            else ("INVESTIGATE" if p > tolerance else "ok")
            if pd.notna(p)
            else "MISSING"
        )
    )
    return combined.reset_index()


def render_report(args, combined: pd.DataFrame, label_a: str, label_b: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    critical_rows = combined[combined["status"] == "CRITICAL"]
    investigate_rows = combined[combined["status"] == "INVESTIGATE"]

    lines = [
        f"# Metric Reconciliation Report — {args.key}",
        f"**Generated:** {now}",
        f"**Metric:** `{args.metric_col}` ({args.agg})",
        f"**Source A:** {label_a}",
        f"**Source B:** {label_b}",
        f"**Tolerance:** {args.tolerance}%",
        f"**Group by:** {args.group_by or 'total only'}",
        "",
        "## Summary",
        f"- {len(critical_rows)} rows CRITICAL (diff > {args.tolerance * 5:.1f}%)",
        f"- {len(investigate_rows)} rows INVESTIGATE (diff > {args.tolerance:.1f}%)",
        f"- {len(combined) - len(critical_rows) - len(investigate_rows)} rows within tolerance",
        "",
        "## Detail",
        combined.to_markdown(index=False),
        "",
        "## Root Cause Checklist",
        "- [ ] Timing difference — was source A fetched before source B?",
        "- [ ] Filter difference — do both sources apply the same WHERE clause?",
        "- [ ] Definition difference — is the metric computed identically in both?",
        "- [ ] Deduplication — does one source deduplicate on objectid and the other does not?",
        "- [ ] Cache staleness — is the cache older than the SLA window?",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Metric reconciliation for NYC DOT datasets")
    parser.add_argument("--key", required=True, choices=list(DATASET_KEYS))
    parser.add_argument("--metric-col", required=True, help="Column to aggregate (e.g. objectid)")
    parser.add_argument("--agg", default="count", choices=list(AGG_FUNCS))
    parser.add_argument("--source-a", default="api", help="'api' or 'cache:<path>'")
    parser.add_argument("--source-b", help="'api' or 'cache:<path>'")
    parser.add_argument("--period-a", help="Date range for source A: 'YYYY-MM-DD,YYYY-MM-DD'")
    parser.add_argument("--period-b", help="Date range for source B (for period comparison)")
    parser.add_argument("--date-col", default="created_date")
    parser.add_argument("--group-by", default="borough")
    parser.add_argument(
        "--tolerance", type=float, default=0.5, help="Acceptable %% diff (default 0.5)"
    )
    parser.add_argument("--rows", type=int, default=50000)
    parser.add_argument("--output", help="Save Markdown report to this path")
    args = parser.parse_args()

    df_a = load_source(args.source_a, args.key, args.rows)
    label_a = args.source_a if not args.period_a else f"{args.source_a} ({args.period_a})"

    if args.period_a and args.period_b:
        # Same source, two time windows
        df_b = df_a.copy()
        df_a = filter_period(df_a, args.period_a, args.date_col)
        df_b = filter_period(df_b, args.period_b, args.date_col)
        label_b = f"period {args.period_b}"
    elif args.source_b:
        df_b = load_source(args.source_b, args.key, args.rows)
        label_b = args.source_b
        if args.period_a:
            df_a = filter_period(df_a, args.period_a, args.date_col)
    else:
        parser.error("Provide --source-b or --period-b for comparison target.")

    series_a = aggregate(df_a, args.metric_col, args.agg, args.group_by)
    series_b = aggregate(df_b, args.metric_col, args.agg, args.group_by)

    combined = compare(series_a, series_b, label_a, label_b, args.tolerance)
    report = render_report(args, combined, label_a, label_b)

    print(report)
    if args.output:
        Path(args.output).write_text(report)
        print(f"\nReport saved to {args.output}")


if __name__ == "__main__":
    main()
