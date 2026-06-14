#!/usr/bin/env python3
"""
chart_recommender.py — Inspect a CSV's column types and print recommended
chart types with rationale. Pure text output — no plotting library required.

Usage:
    python chart_recommender.py --input inspections.csv
    python chart_recommender.py --input violations.csv --target-col closure_rate

Requirements: pandas, numpy only. No LLM or API keys required.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Column type classifier
# ---------------------------------------------------------------------------

DATETIME_HINTS = {
    "date",
    "time",
    "created",
    "updated",
    "modified",
    "inspection",
    "completion",
    "submitted",
    "closed",
    "opened",
    "timestamp",
}
GEO_HINTS = {
    "geom",
    "geometry",
    "latitude",
    "longitude",
    "lat",
    "lon",
    "lng",
    "the_geom",
    "location",
    "coordinates",
    "point",
    "polygon",
    "borough_geom",
}
ID_HINTS = {"id", "objectid", "uid", "key", "code", "fid"}
BOROUGH_HINTS = {"borough", "boro", "district", "neighborhood", "community_board"}


def classify_column(series: pd.Series, name: str) -> str:
    """
    Returns: 'datetime', 'geo', 'categorical_low', 'categorical_high',
             'numeric_continuous', 'numeric_count', 'boolean', or 'id'
    """
    lower_name = name.lower()

    # Check for geo
    if any(hint in lower_name for hint in GEO_HINTS):
        return "geo"

    # Check for ID columns (skip these for visualisation)
    if any(lower_name == hint or lower_name.endswith(hint) for hint in ID_HINTS):
        return "id"

    # Check for datetime
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if any(hint in lower_name for hint in DATETIME_HINTS):
        try:
            pd.to_datetime(series.dropna().head(50), infer_datetime_format=True)
            return "datetime"
        except Exception:
            pass

    # Boolean
    unique_vals = series.dropna().unique()
    if len(unique_vals) == 2:
        str_vals = {str(v).lower() for v in unique_vals}
        if str_vals <= {"true", "false", "yes", "no", "1", "0", "y", "n"}:
            return "boolean"

    # Numeric
    if pd.api.types.is_numeric_dtype(series):
        n_unique = series.nunique()
        if n_unique <= 20 and series.dropna().apply(lambda x: x == int(x)).all():
            return "numeric_count"
        return "numeric_continuous"

    # Categorical (object / string)
    n_unique = series.nunique()
    n_total = series.notna().sum()
    if n_unique / max(n_total, 1) > 0.8:
        return "id"  # High cardinality string = likely an ID
    if n_unique <= 15:
        return "categorical_low"
    return "categorical_high"


def classify_all_columns(df: pd.DataFrame) -> dict[str, str]:
    return {col: classify_column(df[col], col) for col in df.columns}


# ---------------------------------------------------------------------------
# Chart recommendation engine
# ---------------------------------------------------------------------------

CHART_RULES = [
    # (description, condition_fn, chart_type, rationale, dot_example)
    (
        "Single datetime column + single numeric column",
        lambda types, target: (
            "datetime" in types.values() and "numeric_continuous" in types.values()
        ),
        "Line chart",
        "Trend over time. Use a line chart when the x-axis is a continuous time dimension "
        "and you want to show how a metric changes. Add a rolling average to smooth noise.",
        "Daily inspection count over time → line chart with 7-day rolling average.",
    ),
    (
        "Datetime + numeric_count",
        lambda types, target: (
            "datetime" in types.values()
            and "numeric_count" in types.values()
            and "numeric_continuous" not in types.values()
        ),
        "Bar chart (time series)",
        "Discrete counts over time periods. Use bars when values are counts per period "
        "(week, month) rather than a continuous measurement. Easier to compare periods than lines.",
        "Monthly violation closures per borough → grouped bar chart by month.",
    ),
    (
        "One or two categorical_low columns",
        lambda types, target: (
            sum(1 for t in types.values() if t == "categorical_low") >= 1
            and "numeric_continuous" in types.values()
        ),
        "Bar chart (comparison)",
        "Comparing a metric across categories. Use a horizontal bar chart when category "
        "labels are long (borough names, defect types). Sort bars by value for readability.",
        "Average days to close a violation per borough → horizontal bar chart, sorted descending.",
    ),
    (
        "Part-of-whole (categorical_low + count)",
        lambda types, target: (
            sum(1 for t in types.values() if t == "categorical_low") == 1
            and "numeric_count" in types.values()
            and "datetime" not in types.values()
        ),
        "Stacked bar or 100% stacked bar",
        "Part-of-whole composition. Use when you need to show how a total is distributed "
        "across categories AND how that distribution changes across another dimension. "
        "Avoid pie charts for more than 3 categories.",
        "Violation status (OPEN/CLOSED/DISMISSED) by borough → 100% stacked bar chart.",
    ),
    (
        "Two numeric_continuous columns",
        lambda types, target: (
            sum(1 for t in types.values() if t == "numeric_continuous") >= 2
            and "datetime" not in types.values()
        ),
        "Scatter plot",
        "Relationship between two numeric variables. Use scatter to show correlation, "
        "clusters, or outliers. Add a trend line (OLS) if the relationship is roughly linear. "
        "Color by a categorical column to reveal segment-level patterns.",
        "Days since last inspection vs. open violation count per unit → scatter with borough color.",
    ),
    (
        "Single numeric_continuous column (distribution)",
        lambda types, target: (
            sum(1 for t in types.values() if t == "numeric_continuous") == 1
            and sum(1 for t in types.values() if t in ("categorical_low", "datetime")) == 0
        ),
        "Histogram or box plot",
        "Distribution of a single numeric variable. Histogram shows the full shape. "
        "Box plot shows median, IQR, and outliers — use when comparing distributions across groups.",
        "Distribution of days-to-close across all violations → histogram with mean/median lines.",
    ),
    (
        "One categorical_low + one numeric (comparison across groups)",
        lambda types, target: (
            sum(1 for t in types.values() if t == "categorical_low") >= 1
            and "numeric_continuous" in types.values()
            and "datetime" not in types.values()
        ),
        "Box plot (grouped)",
        "Distribution comparison across categories. Use grouped box plots when you want to "
        "show both the typical value and spread for each group, not just the mean.",
        "Days-to-close distribution by defect_type → grouped box plot with outlier markers.",
    ),
    (
        "Geo column present",
        lambda types, target: "geo" in types.values(),
        "Choropleth map or dot map",
        "Geospatial data. Use a choropleth (shaded polygon) map for borough/district-level "
        "aggregates. Use a dot/point map for individual event locations. "
        "Folium or Plotly are recommended for interactive maps in this toolkit.",
        "Violation count per borough → choropleth map. Individual violation locations → dot map.",
    ),
    (
        "Boolean column",
        lambda types, target: "boolean" in types.values(),
        "Bar chart or waffle chart",
        "Binary comparison. A simple two-bar chart (True vs. False) with counts and percentages "
        "is the clearest. Avoid pie charts — bar charts are easier to compare.",
        "Ramp completion status (completed / not completed) → bar chart with % labels.",
    ),
    (
        "Multiple categorical_low columns",
        lambda types, target: sum(1 for t in types.values() if t == "categorical_low") >= 3,
        "Heatmap",
        "Cross-tabulation of two categorical variables. A heatmap (color-coded table) "
        "reveals which category combinations have high/low values. Use when the two-way "
        "table has more than 4×4 cells.",
        "Borough × defect_type × average closure rate → heatmap grid.",
    ),
]


def recommend_charts(types: dict[str, str], target_col: str | None, df: pd.DataFrame) -> list[dict]:
    recommendations = []
    seen_chart_types: set[str] = set()

    for desc, condition, chart_type, rationale, example in CHART_RULES:
        if condition(types, target_col):
            if chart_type not in seen_chart_types:
                recommendations.append(
                    {
                        "chart_type": chart_type,
                        "trigger": desc,
                        "rationale": rationale,
                        "nyc_dot_example": example,
                    }
                )
                seen_chart_types.add(chart_type)

    if not recommendations:
        recommendations.append(
            {
                "chart_type": "Table / Summary statistics",
                "trigger": "No strong chart signal detected",
                "rationale": "The dataset's column types do not strongly suggest a standard chart. "
                "Consider whether a summary statistics table or a bespoke visual is more appropriate.",
                "nyc_dot_example": "Metadata table showing dataset name, row count, last updated, SLA tier.",
            }
        )

    return recommendations


# ---------------------------------------------------------------------------
# Column type summary
# ---------------------------------------------------------------------------


def build_column_summary(df: pd.DataFrame, types: dict[str, str]) -> pd.DataFrame:
    rows = []
    for col, col_type in types.items():
        series = df[col]
        rows.append(
            {
                "column": col,
                "detected_type": col_type,
                "dtype": str(series.dtype),
                "null_pct": round(series.isna().mean() * 100, 1),
                "n_unique": series.nunique(),
                "sample_values": ", ".join(str(v) for v in series.dropna().unique()[:3]),
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect CSV column types and recommend chart types. Pure text output.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python chart_recommender.py --input inspections.csv
  python chart_recommender.py --input violations.csv --target-col closure_rate
""",
    )
    parser.add_argument("--input", required=True, help="Input CSV file path.")
    parser.add_argument(
        "--target-col",
        default=None,
        help="Optional: the primary metric column you want to visualise. "
        "Helps narrow chart recommendations.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    p = Path(args.input)
    if not p.exists():
        sys.exit(f"ERROR: File not found: {args.input}")

    df = pd.read_csv(args.input, nrows=5000)
    # Try to parse datetime columns
    for col in df.columns:
        if any(hint in col.lower() for hint in DATETIME_HINTS):
            try:
                df[col] = pd.to_datetime(df[col], infer_datetime_format=True, errors="coerce")
            except Exception:
                pass

    print(f"\nDataset: {args.input}")
    print(f"Shape:   {len(df):,} rows x {len(df.columns)} columns (preview capped at 5,000 rows)")

    types = classify_all_columns(df)

    # Column type summary
    col_summary = build_column_summary(df, types)
    print("\n--- Column Types ---")
    print(col_summary.to_string(index=False))

    # Type distribution
    type_counts = col_summary["detected_type"].value_counts()
    print("\n--- Type Distribution ---")
    for t, n in type_counts.items():
        print(f"  {t}: {n} column(s)")

    if args.target_col:
        if args.target_col not in df.columns:
            print(f"\nWARNING: --target-col '{args.target_col}' not found in dataset. Ignoring.")
            args.target_col = None
        else:
            print(f"\nTarget column: {args.target_col} (type: {types[args.target_col]})")

    # Chart recommendations
    recs = recommend_charts(types, args.target_col, df)

    print(f"\n--- Chart Recommendations ({len(recs)} found) ---")
    for i, rec in enumerate(recs, 1):
        print(f"\n[{i}] {rec['chart_type']}")
        print(f"    Trigger:   {rec['trigger']}")
        print(f"    Rationale: {rec['rationale']}")
        print(f"    DOT example: {rec['nyc_dot_example']}")

    print(
        "\nTip: Use scripts/chart_builder.py to build the recommended chart with "
        "pre-set professional styling. Fill assets/chart_spec_template.yaml to document "
        "the chart specification before building."
    )


if __name__ == "__main__":
    main()
