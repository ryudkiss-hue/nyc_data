"""
segmentation_engine.py — K-means or rule-based segmentation for NYC DOT inspection data.

Usage:
    python segmentation_engine.py --input data.csv --mode kmeans --n-segments 4 --output segments.csv
    python segmentation_engine.py --input data.csv --mode rules --output segments.csv
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Rule-based segmentation (no sklearn required)
# ---------------------------------------------------------------------------

RISK_RULES = {
    "high_risk": {
        "description": "High defect density, recurring violations, poor material condition",
        "action": "Prioritise for immediate inspection and repair",
    },
    "medium_risk": {
        "description": "Moderate defect count, within SLA but approaching threshold",
        "action": "Schedule for next inspection cycle",
    },
    "low_risk": {
        "description": "Few defects, timely closures, good material condition",
        "action": "Maintain routine monitoring cadence",
    },
    "new_or_unknown": {
        "description": "Insufficient inspection history",
        "action": "Flag for initial baseline inspection",
    },
}

BOROUGH_LABELS = {
    "MN": "Manhattan",
    "BX": "Bronx",
    "BK": "Brooklyn",
    "QN": "Queens",
    "SI": "Staten Island",
}


def rule_based_segment(
    df: pd.DataFrame, defect_col: str = "defect_count", status_col: str | None = None
) -> pd.Series:
    """Assign risk-tier segments using threshold rules."""
    if defect_col not in df.columns:
        print(f"[WARN] '{defect_col}' not found; using first numeric column as proxy.")
        numeric_cols = df.select_dtypes(include="number").columns
        if numeric_cols.empty:
            return pd.Series(["new_or_unknown"] * len(df), index=df.index)
        defect_col = numeric_cols[0]

    q33 = df[defect_col].quantile(0.33)
    q66 = df[defect_col].quantile(0.66)

    def assign(row):
        val = row[defect_col]
        if pd.isna(val):
            return "new_or_unknown"
        if val > q66:
            return "high_risk"
        if val > q33:
            return "medium_risk"
        return "low_risk"

    return df.apply(assign, axis=1)


def kmeans_segment(df: pd.DataFrame, numeric_cols: list[str], n_segments: int) -> pd.Series:
    """K-means clustering; falls back to rule-based if sklearn is unavailable."""
    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        print("[WARN] sklearn not installed — falling back to rule-based segmentation.")
        return rule_based_segment(df)

    X = df[numeric_cols].fillna(df[numeric_cols].median())
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    km = KMeans(n_clusters=n_segments, random_state=42, n_init=10)
    labels = km.fit_predict(X_scaled)

    try:
        from sklearn.metrics import silhouette_score

        score = silhouette_score(X_scaled, labels)
        print(
            f"[INFO] Silhouette score: {score:.3f} ({'OK' if score >= 0.3 else 'POOR — consider fewer segments'})"
        )
    except Exception:
        pass

    return pd.Series([f"cluster_{i}" for i in labels], index=df.index)


def profile_segments(df: pd.DataFrame, segment_col: str = "segment") -> pd.DataFrame:
    """Compute per-segment descriptive stats."""
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        return pd.DataFrame()

    rows = []
    total = len(df)
    for seg, group in df.groupby(segment_col):
        row = {
            "segment": seg,
            "count": len(group),
            "pct_of_total": round(100 * len(group) / total, 1),
        }
        for col in numeric_cols[:5]:
            row[f"{col}_mean"] = round(group[col].mean(), 2)
        if "borough" in df.columns:
            row["top_borough"] = (
                group["borough"].mode().iloc[0] if not group["borough"].mode().empty else "N/A"
            )
        rows.append(row)
    return pd.DataFrame(rows).sort_values("count", ascending=False)


def print_summary(profile: pd.DataFrame) -> None:
    print("\n=== SEGMENT SUMMARY ===")
    print(profile.to_string(index=False))

    print("\n=== STRATEGIC ACTIONS ===")
    for _, row in profile.iterrows():
        seg = row["segment"]
        rule = RISK_RULES.get(seg, {"action": "Review segment definition"})
        print(f"  [{seg}] n={row['count']} ({row['pct_of_total']}%) — {rule['action']}")


def main():
    parser = argparse.ArgumentParser(description="Segment NYC DOT inspection records.")
    parser.add_argument("--input", required=True, help="Path to input CSV")
    parser.add_argument("--mode", choices=["kmeans", "rules"], default="rules")
    parser.add_argument("--n-segments", type=int, default=4, help="Number of k-means clusters")
    parser.add_argument(
        "--segment-col", default="defect_count", help="Primary column for rule-based segmentation"
    )
    parser.add_argument("--output", default="segments_output.csv", help="Path to output CSV")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    print(f"[INFO] Loaded {len(df):,} rows from {args.input}")

    if args.mode == "rules":
        df["segment"] = rule_based_segment(df, defect_col=args.segment_col)
    else:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if not numeric_cols:
            print("[ERROR] No numeric columns found for k-means. Use --mode rules instead.")
            sys.exit(1)
        df["segment"] = kmeans_segment(df, numeric_cols, args.n_segments)

    profile = profile_segments(df)
    print_summary(profile)

    df.to_csv(args.output, index=False)
    profile.to_csv(args.output.replace(".csv", "_profile.csv"), index=False)
    print(f"\n[DONE] Segmented data written to {args.output}")


if __name__ == "__main__":
    main()
