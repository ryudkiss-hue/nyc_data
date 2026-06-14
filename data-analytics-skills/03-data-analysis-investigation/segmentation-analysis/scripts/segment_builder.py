#!/usr/bin/env python3
"""
segment_builder.py — Segment sidewalk inspection records using k-means or
rule-based segmentation.

Usage:
    python segment_builder.py --input inspections.csv --segment-col borough \
        --n-segments 4 --output segment_summary.csv

    python segment_builder.py --input inspections.csv --n-segments 3 \
        --output segments.csv --method rules

Requirements: pandas, numpy. sklearn is used when available (k-means mode);
falls back to quantile-based rule segmentation if sklearn is not installed.
No LLM or API keys required.
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_data(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        sys.exit(f"ERROR: File not found: {path}")
    suffix = p.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path)
    elif suffix in (".xls", ".xlsx"):
        df = pd.read_excel(path)
    elif suffix == ".parquet":
        df = pd.read_parquet(path)
    else:
        sys.exit(f"ERROR: Unsupported file type '{suffix}'. Use CSV, Excel, or Parquet.")
    print(f"Loaded {len(df):,} rows x {len(df.columns)} columns from {path}")
    return df


def detect_numeric_cols(df: pd.DataFrame) -> list[str]:
    """Return numeric columns with >1 unique value (skip ID-like columns)."""
    candidates = []
    for col in df.select_dtypes(include=[np.number]).columns:
        if df[col].nunique() > 1:
            candidates.append(col)
    return candidates


def detect_categorical_cols(df: pd.DataFrame) -> list[str]:
    return list(df.select_dtypes(include=["object", "category"]).columns)


# ---------------------------------------------------------------------------
# K-Means segmentation
# ---------------------------------------------------------------------------


def run_kmeans(df: pd.DataFrame, feature_cols: list[str], n_segments: int) -> pd.Series:
    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        print("WARNING: sklearn not available. Falling back to quantile-based rules.")
        return run_quantile_rules(df, feature_cols, n_segments)

    X = df[feature_cols].copy()
    # Drop rows with any null in feature columns for fitting
    mask = X.notna().all(axis=1)
    X_clean = X[mask]

    if len(X_clean) < n_segments * 10:
        print(
            f"WARNING: Only {len(X_clean)} complete rows for {n_segments} segments. "
            "Consider fewer segments or cleaning nulls first."
        )

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_clean)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        km = KMeans(n_clusters=n_segments, random_state=42, n_init=10)
        labels = km.fit_predict(X_scaled)

    # Compute silhouette score if enough samples
    try:
        from sklearn.metrics import silhouette_score

        score = silhouette_score(X_scaled, labels)
        print(f"Silhouette score: {score:.3f} (>0.3 = meaningful separation)")
    except Exception:
        pass

    # Assign labels to original index (NaN for rows that had nulls)
    result = pd.Series(index=df.index, dtype="Int64", name="segment")
    result[mask] = labels
    return result


# ---------------------------------------------------------------------------
# Quantile-based rule segmentation
# ---------------------------------------------------------------------------


def run_quantile_rules(df: pd.DataFrame, feature_cols: list[str], n_segments: int) -> pd.Series:
    """
    Assign each row to a segment based on its composite score rank.
    Score = mean of per-column quantile ranks (0–1).
    Segment 0 = lowest composite score, Segment (n-1) = highest.
    """
    print(f"Running quantile-based segmentation into {n_segments} segments ...")
    score = pd.Series(0.0, index=df.index)
    valid_cols = 0
    for col in feature_cols:
        col_data = pd.to_numeric(df[col], errors="coerce")
        if col_data.notna().sum() > 0:
            score += col_data.rank(pct=True, na_option="keep").fillna(0.5)
            valid_cols += 1

    if valid_cols == 0:
        sys.exit("ERROR: No numeric columns found for quantile segmentation.")

    score /= valid_cols
    labels = pd.cut(score, bins=n_segments, labels=False)
    return labels.rename("segment").astype("Int64")


# ---------------------------------------------------------------------------
# Segment profiling
# ---------------------------------------------------------------------------

KNOWN_BOROUGH_COL = "borough"
KNOWN_DEFECT_COL = "defect_type"
KNOWN_STATUS_COL = "status"


def profile_segments(
    df: pd.DataFrame,
    segment_col: str,
    feature_cols: list[str],
    cat_cols: list[str],
) -> pd.DataFrame:
    """Return a summary DataFrame with one row per segment."""
    rows = []
    total = len(df)

    for seg_id in sorted(df[segment_col].dropna().unique()):
        mask = df[segment_col] == seg_id
        seg = df[mask]
        n = len(seg)
        pct = n / total * 100 if total > 0 else 0.0

        row: dict = {
            "segment": int(seg_id),
            "count": n,
            "pct_of_total": round(pct, 1),
        }

        # Dominant categorical features
        for col in [KNOWN_BOROUGH_COL, KNOWN_DEFECT_COL, KNOWN_STATUS_COL]:
            if col in seg.columns:
                top_val = seg[col].value_counts().idxmax() if not seg[col].isna().all() else "N/A"
                row[f"dominant_{col}"] = top_val

        # Numeric feature means
        for col in feature_cols:
            col_data = pd.to_numeric(seg[col], errors="coerce")
            row[f"mean_{col}"] = round(col_data.mean(), 2) if col_data.notna().any() else None

        # Risk classification (rule-based from defect counts if column exists)
        if KNOWN_DEFECT_COL in seg.columns:
            high_defects = {"CRACK_SEVERE", "BROKEN", "UPLIFT"}
            high_risk_n = seg[KNOWN_DEFECT_COL].isin(high_defects).sum()
            high_risk_pct = high_risk_n / n * 100 if n > 0 else 0.0
            if high_risk_pct >= 40:
                risk = "HIGH"
            elif high_risk_pct >= 15:
                risk = "MEDIUM"
            else:
                risk = "LOW"
            row["sidewalk_risk_tier"] = risk
            row["high_severity_defect_pct"] = round(high_risk_pct, 1)

        rows.append(row)

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Segment sidewalk inspection data using k-means or rule-based approach.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # K-means on numeric columns, 4 segments:
  python segment_builder.py --input data.csv --n-segments 4 --output out.csv

  # Rule-based (quantile) segmentation:
  python segment_builder.py --input data.csv --n-segments 3 --method rules --output out.csv

  # Specify a categorical grouping column (bypasses clustering):
  python segment_builder.py --input data.csv --segment-col borough --output out.csv
""",
    )
    parser.add_argument("--input", required=True, help="Input CSV (or Excel/Parquet) file path.")
    parser.add_argument(
        "--segment-col",
        default=None,
        help="If set, use this existing categorical column as the segment label "
        "(no clustering performed). Useful for borough-level profiling.",
    )
    parser.add_argument(
        "--n-segments",
        type=int,
        default=4,
        help="Number of segments to create (default: 4). Ignored if --segment-col is set.",
    )
    parser.add_argument(
        "--method",
        choices=["kmeans", "rules"],
        default="kmeans",
        help="Segmentation method: 'kmeans' (default, requires sklearn) or 'rules' (quantile-based).",
    )
    parser.add_argument(
        "--feature-cols",
        nargs="+",
        default=None,
        help="Numeric columns to use as clustering features. Defaults to all numeric columns.",
    )
    parser.add_argument(
        "--output",
        default="segment_summary.csv",
        help="Output path for the segment summary table (CSV).",
    )
    parser.add_argument(
        "--labeled-output",
        default=None,
        help="Optional: path to write the full input dataset with a 'segment' column appended.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = load_data(args.input)

    # --- Determine segment labels ---
    if args.segment_col:
        if args.segment_col not in df.columns:
            sys.exit(f"ERROR: Column '{args.segment_col}' not found in dataset.")
        print(f"Using existing column '{args.segment_col}' as segment labels.")
        df["segment"] = df[args.segment_col].astype(str)
        segment_col = "segment"
    else:
        # Identify feature columns
        feature_cols = args.feature_cols or detect_numeric_cols(df)
        if not feature_cols:
            sys.exit(
                "ERROR: No numeric columns found. Provide --feature-cols or use --segment-col."
            )
        feature_cols = [c for c in feature_cols if c in df.columns]
        print(f"Feature columns: {feature_cols}")

        if args.method == "rules":
            df["segment"] = run_quantile_rules(df, feature_cols, args.n_segments)
        else:
            df["segment"] = run_kmeans(df, feature_cols, args.n_segments)
        segment_col = "segment"

    # --- Profile each segment ---
    cat_cols = detect_categorical_cols(df)
    num_cols = detect_numeric_cols(df) if not args.segment_col else []
    feature_cols_for_profile = (
        args.feature_cols or num_cols if not args.segment_col else detect_numeric_cols(df)
    )

    summary = profile_segments(df, segment_col, feature_cols_for_profile, cat_cols)

    # --- Output ---
    summary.to_csv(args.output, index=False)
    print(f"\nSegment summary written to: {args.output}")
    print("\n--- Segment Summary ---")
    print(summary.to_string(index=False))

    if args.labeled_output:
        df.to_csv(args.labeled_output, index=False)
        print(f"\nLabeled dataset written to: {args.labeled_output}")

    # Print recommended actions per risk tier
    if "sidewalk_risk_tier" in summary.columns:
        print("\n--- Recommended Actions by Risk Tier ---")
        actions = {
            "HIGH": "Immediate inspection review; prioritise closure within 14 days (HIGH SLA).",
            "MEDIUM": "Schedule follow-up inspection within 30 days (MED SLA).",
            "LOW": "Monitor; routine 60-day inspection cycle (LOW SLA).",
        }
        for _, row in summary.iterrows():
            tier = row.get("sidewalk_risk_tier", "N/A")
            action = actions.get(tier, "Review segment characteristics.")
            print(f"  Segment {row['segment']} ({tier}): {action}")


if __name__ == "__main__":
    main()
