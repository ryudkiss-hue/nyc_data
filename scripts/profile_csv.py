#!/usr/bin/env python3
"""
profile_csv.py — Deterministic EDA profiler for any CSV file.

Usage:
    python scripts/profile_csv.py --input data.csv
    python scripts/profile_csv.py --input data.csv --out report.txt
    python scripts/profile_csv.py --input data.csv --format json --out report.json

Produces:
    - Row/column counts and dtypes
    - Null rates per column (flags >10% as warnings)
    - Cardinality and duplicate detection
    - Four statistical moments for numeric columns (mean, variance, skewness, kurtosis)
    - Composite quality score (0-100)
    - Actionable recommendations via rule-based templates

No LLM or API calls required. Pure pandas/numpy/scipy.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
NULL_WARN_THRESHOLD = 10.0  # % missing that triggers a warning
SKEW_WARN_THRESHOLD = 2.0  # |skewness| above this is flagged
KURT_WARN_THRESHOLD = 7.0  # |excess kurtosis| above this is flagged
DUPLICATE_WARN_THRESHOLD = 5.0  # % duplicates that triggers a warning
LOW_CARDINALITY_THRESHOLD = 5  # unique values ≤ this suggests categorical encoding


# ---------------------------------------------------------------------------
# Core profiling logic
# ---------------------------------------------------------------------------


def _detect_dtype_class(series: pd.Series) -> str:
    """Classify a Series into a human-readable type bucket."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    # Try to sniff datetime-looking strings
    col_lower = str(series.name).lower()
    if any(kw in col_lower for kw in ("date", "time", "created", "updated", "modified")):
        return "datetime_string"
    return "string"


def _numeric_moments(series: pd.Series) -> dict:
    """Compute the four statistical moments for a numeric series."""
    clean = series.dropna()
    if len(clean) < 2:
        return {}
    return {
        "mean": float(clean.mean()),
        "std": float(clean.std()),
        "variance": float(clean.var()),
        "skewness": float(scipy_stats.skew(clean)),
        "kurtosis": float(scipy_stats.kurtosis(clean)),  # excess kurtosis
        "min": float(clean.min()),
        "p25": float(np.percentile(clean, 25)),
        "median": float(np.median(clean)),
        "p75": float(np.percentile(clean, 75)),
        "max": float(clean.max()),
        "iqr": float(np.percentile(clean, 75) - np.percentile(clean, 25)),
    }


def profile_dataframe(df: pd.DataFrame, table_name: str = "dataset") -> dict:
    """
    Profile a DataFrame and return a structured report dict.

    Quality score formula:
        completeness_score  = 1 - (total_nulls / total_cells)          [weight 0.50]
        uniqueness_score    = 1 - (duplicate_rows / total_rows)        [weight 0.30]
        warning_penalty     = min(len(warnings) * 3, 20) points        [cap 20]
        quality_score       = round((completeness*50 + uniqueness*30) - penalty)
        clamped to [0, 100]
    """
    row_count = len(df)
    col_count = df.shape[1]

    if row_count == 0:
        return {
            "table_name": table_name,
            "row_count": 0,
            "column_count": col_count,
            "columns": [],
            "quality_score": 0,
            "warnings": ["Dataset is empty — no rows to profile."],
            "recommendations": ["Verify the data source and re-export."],
            "duplicate_rows": 0,
            "duplicate_pct": 0.0,
        }

    null_counts = df.isna().sum()
    null_pcts = (null_counts / row_count * 100).round(2)
    unique_counts = df.nunique()
    duplicate_rows = int(df.duplicated().sum())
    duplicate_pct = round(duplicate_rows / row_count * 100, 2)

    columns = []
    warnings: list[str] = []
    moments_map: dict[str, dict] = {}

    for col in df.columns:
        col_str = str(col)
        series = df[col]
        dtype_class = _detect_dtype_class(series)
        null_pct = float(null_pcts[col])
        unique_count = int(unique_counts[col])
        sample_vals = series.dropna().head(3).astype(str).tolist()

        col_info: dict = {
            "name": col_str,
            "dtype": str(series.dtype),
            "dtype_class": dtype_class,
            "null_count": int(null_counts[col]),
            "null_pct": null_pct,
            "unique_count": unique_count,
            "cardinality_ratio": round(unique_count / max(row_count, 1), 4),
            "sample_values": sample_vals,
        }

        # Warnings
        if null_pct > NULL_WARN_THRESHOLD and dtype_class not in ("datetime_string",):
            warnings.append(
                f"Column '{col_str}' has {null_pct:.1f}% missing values — exceeds {NULL_WARN_THRESHOLD}% threshold."
            )
        if unique_count == 1 and row_count > 1 and null_pct < 50:
            warnings.append(
                f"Column '{col_str}' is constant (all non-null values identical) — likely low information."
            )
        if dtype_class == "datetime_string":
            warnings.append(
                f"Column '{col_str}' looks like a date but is stored as string — consider parsing with pd.to_datetime()."
            )
        if dtype_class == "string" and unique_count <= LOW_CARDINALITY_THRESHOLD and row_count > 20:
            col_info["low_cardinality"] = True

        # Numeric moments
        if dtype_class == "numeric":
            m = _numeric_moments(series)
            col_info["moments"] = m
            moments_map[col_str] = m
            if m and abs(m.get("skewness", 0)) > SKEW_WARN_THRESHOLD:
                warnings.append(
                    f"Column '{col_str}' is highly skewed (skewness={m['skewness']:.2f}) — consider log transform."
                )
            if m and abs(m.get("kurtosis", 0)) > KURT_WARN_THRESHOLD:
                warnings.append(
                    f"Column '{col_str}' has extreme kurtosis ({m['kurtosis']:.2f}) — heavy tails or outlier spikes."
                )

        columns.append(col_info)

    if duplicate_pct > DUPLICATE_WARN_THRESHOLD:
        warnings.append(
            f"{duplicate_rows} duplicate rows detected ({duplicate_pct:.1f}%) — deduplicate before analysis."
        )

    # Quality score
    total_cells = row_count * col_count
    total_nulls = int(null_counts.sum())
    completeness = (1 - total_nulls / max(total_cells, 1)) * 50
    uniqueness = (1 - duplicate_rows / max(row_count, 1)) * 30
    warning_penalty = min(len(warnings) * 3, 20)
    quality_score = max(0, min(100, round(completeness + uniqueness - warning_penalty)))

    # Recommendations (rule-based)
    recommendations = _build_recommendations(warnings, df, duplicate_rows, null_pcts, columns)

    return {
        "table_name": table_name,
        "row_count": row_count,
        "column_count": col_count,
        "columns": columns,
        "duplicate_rows": duplicate_rows,
        "duplicate_pct": duplicate_pct,
        "quality_score": quality_score,
        "warnings": warnings,
        "recommendations": recommendations,
    }


def _build_recommendations(
    warnings: list[str],
    df: pd.DataFrame,
    duplicate_rows: int,
    null_pcts: pd.Series,
    columns: list[dict],
) -> list[str]:
    """Generate deterministic, template-driven recommendations."""
    recs: list[str] = []

    high_null_cols = [c["name"] for c in columns if c["null_pct"] > 30]
    if high_null_cols:
        recs.append(
            f"Columns with >30% nulls ({', '.join(high_null_cols[:5])}) may need imputation "
            "or should be excluded from completeness-sensitive analyses."
        )

    date_string_cols = [c["name"] for c in columns if c["dtype_class"] == "datetime_string"]
    if date_string_cols:
        recs.append(
            f"Parse date columns ({', '.join(date_string_cols[:5])}) with "
            "`pd.to_datetime(..., errors='coerce')` before any time-series analysis."
        )

    if duplicate_rows > 0:
        recs.append(
            f"Remove {duplicate_rows} duplicate rows with `df.drop_duplicates()` "
            "before aggregation to avoid double-counting."
        )

    skewed_cols = [
        c["name"]
        for c in columns
        if c.get("moments") and abs(c["moments"].get("skewness", 0)) > SKEW_WARN_THRESHOLD
    ]
    if skewed_cols:
        recs.append(
            f"Apply log1p transform to skewed numeric columns ({', '.join(skewed_cols[:5])}) "
            "before regression or clustering to improve model stability."
        )

    const_cols = [c["name"] for c in columns if c["unique_count"] == 1 and len(df) > 1]
    if const_cols:
        recs.append(
            f"Drop constant columns ({', '.join(const_cols[:5])}) — "
            "they carry zero information for predictive or discriminant analysis."
        )

    if not recs:
        recs.append("Dataset appears clean. Proceed to domain-specific analysis.")

    return recs


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def _quality_label(score: int) -> str:
    if score >= 80:
        return "GOOD"
    if score >= 60:
        return "FAIR"
    if score >= 40:
        return "POOR"
    return "CRITICAL"


def format_text_report(profile: dict) -> str:
    """Render the profile as a human-readable text report."""
    lines: list[str] = []
    sep = "=" * 72

    lines += [
        sep,
        f"  EDA PROFILE REPORT — {profile['table_name'].upper()}",
        sep,
        f"  Rows          : {profile['row_count']:,}",
        f"  Columns       : {profile['column_count']}",
        f"  Duplicate rows: {profile['duplicate_rows']:,} ({profile['duplicate_pct']:.1f}%)",
        f"  Quality score : {profile['quality_score']}/100  [{_quality_label(profile['quality_score'])}]",
        "",
    ]

    # Column table
    lines.append("COLUMN SUMMARY")
    lines.append("-" * 72)
    header = f"{'Column':<30} {'Type':<14} {'Null%':>6}  {'Unique':>8}  {'Sample'}"
    lines.append(header)
    lines.append("-" * 72)
    for col in profile["columns"]:
        sample = ", ".join(col["sample_values"])[:24]
        lines.append(
            f"{col['name'][:30]:<30} {col['dtype_class']:<14} {col['null_pct']:>5.1f}%  "
            f"{col['unique_count']:>8,}  {sample}"
        )
    lines.append("")

    # Numeric moments
    numeric_cols = [c for c in profile["columns"] if c.get("moments")]
    if numeric_cols:
        lines.append("NUMERIC MOMENTS")
        lines.append("-" * 72)
        hdr = f"{'Column':<28} {'Mean':>10} {'Std':>10} {'Skew':>8} {'Kurt':>8} {'Min':>10} {'Max':>10}"
        lines.append(hdr)
        lines.append("-" * 72)
        for col in numeric_cols:
            m = col["moments"]
            lines.append(
                f"{col['name'][:28]:<28} {m['mean']:>10.2f} {m['std']:>10.2f} "
                f"{m['skewness']:>8.2f} {m['kurtosis']:>8.2f} {m['min']:>10.2f} {m['max']:>10.2f}"
            )
        lines.append("")

    # Warnings
    if profile["warnings"]:
        lines.append(f"WARNINGS ({len(profile['warnings'])})")
        lines.append("-" * 72)
        for i, w in enumerate(profile["warnings"], 1):
            lines.append(f"  [{i}] {w}")
        lines.append("")

    # Recommendations
    lines.append(f"RECOMMENDATIONS ({len(profile['recommendations'])})")
    lines.append("-" * 72)
    for i, r in enumerate(profile["recommendations"], 1):
        lines.append(f"  [{i}] {r}")
    lines.append("")
    lines.append(sep)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deterministic EDA profiler for CSV files (no API keys required).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input", required=True, help="Path to input CSV file")
    parser.add_argument("--out", default=None, help="Output file path (default: stdout)")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format: 'text' (default) or 'json'",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Dataset name for the report header (default: input filename stem)",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="CSV encoding (default: utf-8)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        return 1

    table_name = args.name or input_path.stem

    try:
        df = pd.read_csv(input_path, low_memory=False, encoding=args.encoding)
    except Exception as exc:
        print(f"ERROR: Could not read CSV: {exc}", file=sys.stderr)
        return 1

    profile = profile_dataframe(df, table_name=table_name)

    if args.format == "json":
        # Make numpy types JSON-serialisable
        output = json.dumps(
            profile,
            indent=2,
            default=lambda o: (
                float(o)
                if isinstance(o, (np.floating,))
                else int(o)
                if isinstance(o, (np.integer,))
                else str(o)
            ),
        )
    else:
        output = format_text_report(profile)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"Report written to {out_path}")
    else:
        print(output)

    # Exit 1 if quality is critical (useful for CI pipelines)
    return 0 if profile["quality_score"] >= 40 else 1


if __name__ == "__main__":
    sys.exit(main())
