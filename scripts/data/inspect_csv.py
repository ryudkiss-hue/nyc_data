#!/usr/bin/env python
"""
inspect_csv.py — Pure-Python CSV profiler and EDA tool for NYC DOT SIM datasets.

Reads any CSV file and produces a complete, useful analytical report to stdout.
No LLM or API calls required — all output is computed from the data using
pandas, numpy, and scipy.

Usage:
    python scripts/data/inspect_csv.py --input data/violations.csv
    python scripts/data/inspect_csv.py --input data/ramp_progress.csv --date-col created_date
    python scripts/data/inspect_csv.py --input data/inspections.csv --borough-col borough --out report.txt

Options:
    --input PATH        Path to CSV file (required)
    --date-col NAME     Date column for freshness and trend analysis
    --borough-col NAME  Borough column for geographic breakdown (default: borough)
    --out PATH          Optional output file path (defaults to stdout)
    --sample N          Number of rows to sample for profiling (default: all)
    --sep CHAR          CSV delimiter (default: comma)
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from scipy import stats as scipy_stats

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BOROUGH_CODES = {
    "MN": "Manhattan",
    "MANHATTAN": "Manhattan",
    "BX": "Bronx",
    "BRONX": "Bronx",
    "BK": "Brooklyn",
    "BROOKLYN": "Brooklyn",
    "QN": "Queens",
    "QUEENS": "Queens",
    "SI": "Staten Island",
    "STATEN ISLAND": "Staten Island",
}

NULL_THRESHOLD_WARN = 10.0  # % nulls that triggers a warning
DUPLICATE_THRESHOLD_WARN = 5.0  # % duplicate rows that triggers a warning
HIGH_CARDINALITY_THRESHOLD = 50  # unique values above which a string col is "high cardinality"
OUTLIER_Z_THRESHOLD = 3.0  # z-score threshold for outlier flagging

# ---------------------------------------------------------------------------
# Core profiling functions — all pure pandas/numpy/scipy
# ---------------------------------------------------------------------------


def _compute_null_stats(df: pd.DataFrame) -> list[dict[str, Any]]:
    null_counts = df.isna().sum()
    n = len(df)
    results = []
    for col in df.columns:
        nc = int(null_counts[col])
        pct = round(nc / max(n, 1) * 100, 2)
        results.append({"column": col, "null_count": nc, "null_pct": pct})
    return sorted(results, key=lambda x: x["null_pct"], reverse=True)


def _compute_dtype_summary(df: pd.DataFrame) -> dict[str, list[str]]:
    numeric_cols = list(df.select_dtypes(include=[np.number]).columns)
    date_cols = list(df.select_dtypes(include=["datetime64"]).columns)
    string_cols = list(df.select_dtypes(include=["object", "string"]).columns)
    bool_cols = list(df.select_dtypes(include=["bool"]).columns)
    return {
        "numeric": numeric_cols,
        "datetime": date_cols,
        "string": string_cols,
        "boolean": bool_cols,
    }


def _compute_numeric_summary(df: pd.DataFrame, numeric_cols: list[str]) -> list[dict[str, Any]]:
    results = []
    for col in numeric_cols:
        s = df[col].dropna()
        if s.empty:
            continue
        q1 = float(s.quantile(0.25))
        q3 = float(s.quantile(0.75))
        iqr = q3 - q1
        outlier_low = q1 - 1.5 * iqr
        outlier_high = q3 + 1.5 * iqr
        n_outliers = int(((s < outlier_low) | (s > outlier_high)).sum())

        skew = 0.0
        if HAS_SCIPY and len(s) >= 3:
            try:
                skew = float(scipy_stats.skew(s))
            except Exception:
                pass

        results.append(
            {
                "column": col,
                "count": int(s.count()),
                "mean": round(float(s.mean()), 4),
                "std": round(float(s.std()), 4),
                "min": round(float(s.min()), 4),
                "p25": round(q1, 4),
                "median": round(float(s.median()), 4),
                "p75": round(q3, 4),
                "max": round(float(s.max()), 4),
                "iqr_outliers": n_outliers,
                "skewness": round(skew, 3),
            }
        )
    return results


def _compute_string_summary(df: pd.DataFrame, string_cols: list[str]) -> list[dict[str, Any]]:
    results = []
    for col in string_cols:
        s = df[col].dropna().astype(str)
        if s.empty:
            continue
        n_unique = int(s.nunique())
        top_vals = s.value_counts().head(5)
        top_list = [{"value": v, "count": int(c)} for v, c in top_vals.items()]
        avg_len = round(s.str.len().mean(), 1)
        results.append(
            {
                "column": col,
                "count": int(s.count()),
                "unique": n_unique,
                "top_values": top_list,
                "avg_length": avg_len,
                "high_cardinality": n_unique > HIGH_CARDINALITY_THRESHOLD,
            }
        )
    return results


def _compute_freshness(df: pd.DataFrame, date_col: str) -> dict[str, Any] | None:
    if date_col not in df.columns:
        return None
    parsed = pd.to_datetime(df[date_col], errors="coerce")
    n_parsed = int(parsed.notna().sum())
    if n_parsed == 0:
        return None
    latest = parsed.dropna().max()
    earliest = parsed.dropna().min()
    now = datetime.now(timezone.utc)
    latest_utc = latest.to_pydatetime()
    if latest_utc.tzinfo is None:
        latest_utc = latest_utc.replace(tzinfo=timezone.utc)
    age_days = (now - latest_utc).days

    # Classify freshness against SLA thresholds (HIGH=14, MED=30, LOW=60)
    if age_days <= 14:
        sla_status = "FRESH (within HIGH SLA of 14 days)"
    elif age_days <= 30:
        sla_status = "OK (within MEDIUM SLA of 30 days)"
    elif age_days <= 60:
        sla_status = "WARNING (within LOW SLA of 60 days)"
    else:
        sla_status = "STALE (exceeds all SLA thresholds)"

    return {
        "date_col": date_col,
        "n_parsed": n_parsed,
        "earliest": str(earliest.date()),
        "latest": str(latest.date()),
        "age_days": age_days,
        "sla_status": sla_status,
        "date_range_days": (latest - earliest).days,
    }


def _compute_borough_breakdown(df: pd.DataFrame, borough_col: str) -> list[dict[str, Any]] | None:
    if borough_col not in df.columns:
        return None
    raw = df[borough_col].dropna().astype(str).str.upper().str.strip()
    norm = raw.map(lambda v: BOROUGH_CODES.get(v, v))
    counts = norm.value_counts()
    total = int(counts.sum())
    results = []
    for borough, cnt in counts.items():
        pct = round(cnt / max(total, 1) * 100, 1)
        results.append({"borough": borough, "count": int(cnt), "pct": pct})
    return sorted(results, key=lambda x: x["count"], reverse=True)


def _compute_duplicates(df: pd.DataFrame) -> dict[str, int]:
    n_full = int(df.duplicated().sum())
    return {"full_duplicate_rows": n_full}


def _compute_quality_score(
    df: pd.DataFrame,
    null_stats: list[dict[str, Any]],
    dup_stats: dict[str, int],
) -> int:
    n = len(df)
    if n == 0:
        return 0

    # Completeness: fraction of non-null cells
    total_cells = n * len(df.columns)
    total_nulls = sum(r["null_count"] for r in null_stats)
    completeness = max(0.0, 1.0 - total_nulls / max(total_cells, 1))

    # Uniqueness: fraction of non-duplicate rows
    n_dupes = dup_stats["full_duplicate_rows"]
    uniqueness = max(0.0, 1.0 - n_dupes / max(n, 1))

    # Composite: 60% completeness, 40% uniqueness
    score = round((completeness * 0.60 + uniqueness * 0.40) * 100)
    return max(0, min(100, score))


def _score_label(score: int) -> str:
    if score >= 90:
        return "EXCELLENT"
    elif score >= 75:
        return "GOOD"
    elif score >= 60:
        return "FAIR"
    elif score >= 40:
        return "POOR"
    else:
        return "CRITICAL"


def _compute_warnings(
    null_stats: list[dict[str, Any]],
    dup_stats: dict[str, int],
    n_rows: int,
    numeric_summary: list[dict[str, Any]],
    string_summary: list[dict[str, Any]],
) -> list[str]:
    warnings: list[str] = []

    # Null warnings
    for col_stat in null_stats:
        if col_stat["null_pct"] > NULL_THRESHOLD_WARN:
            warnings.append(
                f"Column '{col_stat['column']}' has {col_stat['null_pct']}% missing values "
                f"({col_stat['null_count']:,} rows)"
            )

    # Duplicate warning
    dup_pct = dup_stats["full_duplicate_rows"] / max(n_rows, 1) * 100
    if dup_pct > DUPLICATE_THRESHOLD_WARN:
        warnings.append(
            f"{dup_stats['full_duplicate_rows']:,} fully-duplicate rows detected "
            f"({dup_pct:.1f}% of dataset)"
        )

    # High-skew numerics
    for ns in numeric_summary:
        if abs(ns["skewness"]) > 2.0:
            direction = "right" if ns["skewness"] > 0 else "left"
            warnings.append(
                f"Column '{ns['column']}' is heavily {direction}-skewed "
                f"(skewness={ns['skewness']}); consider log transform"
            )

    # Outlier warnings
    for ns in numeric_summary:
        if ns["iqr_outliers"] > 0:
            pct = round(ns["iqr_outliers"] / max(ns["count"], 1) * 100, 1)
            if pct > 5.0:
                warnings.append(
                    f"Column '{ns['column']}' has {ns['iqr_outliers']:,} IQR outliers ({pct}%)"
                )

    # Constant columns
    for ss in string_summary:
        if ss["unique"] == 1 and ss["count"] > 1:
            warnings.append(f"Column '{ss['column']}' is constant — low analytical value")

    return warnings


def _compute_recommendations(
    quality_score: int,
    warnings: list[str],
    freshness: dict[str, Any] | None,
    borough_breakdown: list[dict[str, Any]] | None,
    n_rows: int,
    n_cols: int,
) -> list[str]:
    recs: list[str] = []

    if quality_score < 60:
        recs.append(
            "Quality score is below 60 — run `socrata quality-score` to identify and remediate data issues before analysis."
        )

    high_null_cols = [w for w in warnings if "missing values" in w]
    if high_null_cols:
        recs.append(
            f"{len(high_null_cols)} column(s) have >10% nulls. "
            "Consider imputation or exclusion before modeling."
        )

    if freshness:
        if "STALE" in freshness["sla_status"]:
            recs.append(
                f"Dataset is {freshness['age_days']} days old — exceeds all SLA thresholds. "
                "Run `socrata cache refresh <key>` or contact the data publisher."
            )
        elif "WARNING" in freshness["sla_status"]:
            recs.append(
                f"Dataset is {freshness['age_days']} days old — approaching MEDIUM SLA threshold (30 days). "
                "Monitor for updates."
            )

    if borough_breakdown:
        top_pct = borough_breakdown[0]["pct"] if borough_breakdown else 0
        if top_pct > 70:
            recs.append(
                f"Borough distribution is highly concentrated: {borough_breakdown[0]['borough']} "
                f"represents {top_pct}% of records. Verify this is expected or filter accordingly."
            )

    if n_rows < 1000:
        recs.append(
            f"Small sample ({n_rows:,} rows). Use Wilson Score CIs for rate calculations — "
            "normal approximation will be unreliable."
        )

    if not recs:
        recs.append("No critical issues detected. Dataset appears ready for analysis.")

    return recs


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def _sep(char: str = "-", width: int = 72) -> str:
    return char * width


def _render_report(
    input_path: str,
    df: pd.DataFrame,
    null_stats: list[dict[str, Any]],
    dup_stats: dict[str, int],
    dtype_summary: dict[str, list[str]],
    numeric_summary: list[dict[str, Any]],
    string_summary: list[dict[str, Any]],
    freshness: dict[str, Any] | None,
    borough_breakdown: list[dict[str, Any]] | None,
    quality_score: int,
    warnings: list[str],
    recommendations: list[str],
    sample_note: str,
) -> str:
    lines: list[str] = []
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines.append(_sep("="))
    lines.append("NYC DOT SIM DATA INSPECTION REPORT")
    lines.append(f"Generated: {now_str}")
    lines.append(f"File:      {input_path}")
    lines.append(_sep("="))

    # --- Dataset Overview ---
    lines.append("")
    lines.append("OVERVIEW")
    lines.append(_sep())
    lines.append(f"  Rows:     {len(df):,}{sample_note}")
    lines.append(f"  Columns:  {len(df.columns)}")
    lines.append(f"  Numeric:  {len(dtype_summary['numeric'])} columns")
    lines.append(f"  String:   {len(dtype_summary['string'])} columns")
    lines.append(f"  Datetime: {len(dtype_summary['datetime'])} columns")
    lines.append(f"  Boolean:  {len(dtype_summary['boolean'])} columns")

    # --- Quality Score ---
    lines.append("")
    lines.append("QUALITY SCORE")
    lines.append(_sep())
    bar_filled = int(quality_score / 5)
    bar = "[" + "#" * bar_filled + "." * (20 - bar_filled) + "]"
    lines.append(f"  {quality_score}/100  {bar}  {_score_label(quality_score)}")
    lines.append("  Weights: 60% completeness, 40% uniqueness")

    # --- Freshness ---
    if freshness:
        lines.append("")
        lines.append("DATA FRESHNESS")
        lines.append(_sep())
        lines.append(f"  Date column:  {freshness['date_col']}")
        lines.append(f"  Earliest:     {freshness['earliest']}")
        lines.append(f"  Latest:       {freshness['latest']}")
        lines.append(f"  Age (days):   {freshness['age_days']}")
        lines.append(f"  Date span:    {freshness['date_range_days']} days")
        lines.append(f"  SLA Status:   {freshness['sla_status']}")

    # --- Borough Breakdown ---
    if borough_breakdown:
        lines.append("")
        lines.append("BOROUGH BREAKDOWN")
        lines.append(_sep())
        header = f"  {'Borough':<20} {'Count':>10} {'Pct':>8}"
        lines.append(header)
        lines.append(f"  {'-' * 20} {'-' * 10} {'-' * 8}")
        for row in borough_breakdown:
            lines.append(f"  {row['borough']:<20} {row['count']:>10,} {row['pct']:>7.1f}%")

    # --- Null Analysis ---
    lines.append("")
    lines.append("NULL ANALYSIS (top 15 by null %)")
    lines.append(_sep())
    header = f"  {'Column':<35} {'Nulls':>8} {'Pct':>8}"
    lines.append(header)
    lines.append(f"  {'-' * 35} {'-' * 8} {'-' * 8}")
    for stat in null_stats[:15]:
        flag = " [!]" if stat["null_pct"] > NULL_THRESHOLD_WARN else ""
        lines.append(
            f"  {stat['column']:<35} {stat['null_count']:>8,} {stat['null_pct']:>7.1f}%{flag}"
        )

    # --- Duplicate Analysis ---
    lines.append("")
    lines.append("DUPLICATE ANALYSIS")
    lines.append(_sep())
    n_rows = len(df)
    dup_pct = round(dup_stats["full_duplicate_rows"] / max(n_rows, 1) * 100, 2)
    lines.append(f"  Full duplicate rows: {dup_stats['full_duplicate_rows']:,} ({dup_pct}%)")

    # --- Numeric Summary ---
    if numeric_summary:
        lines.append("")
        lines.append("NUMERIC COLUMN SUMMARY")
        lines.append(_sep())
        lines.append(
            f"  {'Column':<28} {'Count':>7} {'Mean':>12} {'Median':>12} {'Std':>12} "
            f"{'Min':>10} {'Max':>10} {'Outliers':>9} {'Skew':>7}"
        )
        lines.append(
            f"  {'-' * 28} {'-' * 7} {'-' * 12} {'-' * 12} {'-' * 12} "
            f"{'-' * 10} {'-' * 10} {'-' * 9} {'-' * 7}"
        )
        for ns in numeric_summary:
            lines.append(
                f"  {ns['column']:<28} {ns['count']:>7,} {ns['mean']:>12.4f} "
                f"{ns['median']:>12.4f} {ns['std']:>12.4f} "
                f"{ns['min']:>10.4f} {ns['max']:>10.4f} "
                f"{ns['iqr_outliers']:>9,} {ns['skewness']:>7.3f}"
            )

    # --- String Summary ---
    if string_summary:
        lines.append("")
        lines.append("STRING COLUMN SUMMARY (top 5 values each)")
        lines.append(_sep())
        for ss in string_summary:
            cardinality_note = " [HIGH CARDINALITY]" if ss["high_cardinality"] else ""
            lines.append(
                f"  {ss['column']} — {ss['unique']:,} unique, avg len={ss['avg_length']}{cardinality_note}"
            )
            for tv in ss["top_values"]:
                lines.append(f"    {tv['value']:<40} {tv['count']:>8,}")

    # --- Warnings ---
    lines.append("")
    lines.append("WARNINGS")
    lines.append(_sep())
    if warnings:
        for i, w in enumerate(warnings, 1):
            lines.append(f"  {i}. {w}")
    else:
        lines.append("  No warnings — dataset passes all basic checks.")

    # --- Recommendations ---
    lines.append("")
    lines.append("RECOMMENDATIONS")
    lines.append(_sep())
    for i, rec in enumerate(recommendations, 1):
        lines.append(f"  {i}. {rec}")

    lines.append("")
    lines.append(_sep("="))
    lines.append("END OF REPORT")
    lines.append(_sep("="))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pure-Python CSV profiler for NYC DOT SIM datasets. No API keys required.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input", required=True, help="Path to CSV file")
    parser.add_argument("--date-col", default=None, help="Date column for freshness analysis")
    parser.add_argument(
        "--borough-col", default="borough", help="Borough column (default: borough)"
    )
    parser.add_argument("--out", default=None, help="Output file path (defaults to stdout)")
    parser.add_argument("--sample", type=int, default=None, help="Row sample limit")
    parser.add_argument("--sep", default=",", help="CSV delimiter (default: comma)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Load data
    try:
        df = pd.read_csv(str(input_path), sep=args.sep, low_memory=False)
    except Exception as e:
        print(f"ERROR: Failed to read CSV: {e}", file=sys.stderr)
        sys.exit(1)

    # Try to parse datetime columns automatically
    for col in df.columns:
        if "date" in col.lower() or "time" in col.lower():
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            except Exception:
                pass

    total_rows = len(df)
    sample_note = ""
    if args.sample and args.sample < total_rows:
        df = df.sample(args.sample, random_state=42)
        sample_note = f" (sampled from {total_rows:,})"

    # Run all analyses
    null_stats = _compute_null_stats(df)
    dup_stats = _compute_duplicates(df)
    dtype_summary = _compute_dtype_summary(df)
    numeric_summary = _compute_numeric_summary(df, dtype_summary["numeric"])
    string_summary = _compute_string_summary(df, dtype_summary["string"])
    freshness = _compute_freshness(df, args.date_col) if args.date_col else None
    borough_breakdown = _compute_borough_breakdown(df, args.borough_col)
    quality_score = _compute_quality_score(df, null_stats, dup_stats)
    warnings = _compute_warnings(null_stats, dup_stats, len(df), numeric_summary, string_summary)
    recommendations = _compute_recommendations(
        quality_score, warnings, freshness, borough_breakdown, len(df), len(df.columns)
    )

    report = _render_report(
        input_path=str(input_path),
        df=df,
        null_stats=null_stats,
        dup_stats=dup_stats,
        dtype_summary=dtype_summary,
        numeric_summary=numeric_summary,
        string_summary=string_summary,
        freshness=freshness,
        borough_breakdown=borough_breakdown,
        quality_score=quality_score,
        warnings=warnings,
        recommendations=recommendations,
        sample_note=sample_note,
    )

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(f"Report written to {args.out}")
    else:
        print(report)


if __name__ == "__main__":
    main()
