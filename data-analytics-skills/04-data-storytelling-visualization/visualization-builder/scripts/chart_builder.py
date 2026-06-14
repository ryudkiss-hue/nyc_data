"""
chart_builder.py — Recommend and build professional charts for NYC DOT data.

Usage:
    python chart_builder.py --input data.csv --recommend          # print chart type recommendations
    python chart_builder.py --input data.csv --chart bar --x borough --y violation_count --out chart.png
    python chart_builder.py --input data.csv --chart line --x inspection_date --y count --out trend.png
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Chart type recommendation (no plotting required)
# ---------------------------------------------------------------------------

MESSAGE_TYPE_MAP = {
    "comparison": ("bar", "Compare values across categories (boroughs, defect types)"),
    "trend": ("line", "Show change over time (daily inspections, rolling violations)"),
    "distribution": ("histogram", "Show spread of a single numeric variable"),
    "part_of_whole": ("stacked_bar", "Show how a total breaks into parts (borough share)"),
    "relationship": ("scatter", "Show correlation between two numeric variables"),
    "geo": ("choropleth", "Map metric values to geographic areas (borough-level)"),
}


def infer_message_type(df: pd.DataFrame, x_col: str, y_col: str | None) -> str:
    """Guess message type from column dtypes."""
    x_dtype = df[x_col].dtype if x_col in df.columns else None
    is_datetime = pd.api.types.is_datetime64_any_dtype(x_dtype)
    is_categorical = pd.api.types.is_object_dtype(x_dtype) or pd.api.types.is_categorical_dtype(
        x_dtype
    )

    if is_datetime:
        return "trend"
    if is_categorical and y_col:
        return "comparison"
    if is_categorical and not y_col:
        return "part_of_whole"
    if y_col and pd.api.types.is_numeric_dtype(df[y_col].dtype if y_col in df.columns else None):
        return "relationship"
    return "distribution"


def recommend_charts(df: pd.DataFrame, target_col: str | None = None) -> None:
    print("\n=== CHART RECOMMENDATIONS ===\n")
    print(f"Dataset: {len(df):,} rows × {len(df.columns)} columns\n")

    datetime_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    print("Detected columns:")
    print(f"  Datetime: {datetime_cols or ['none']}")
    print(f"  Numeric:  {numeric_cols[:5] or ['none']}")
    print(f"  Category: {cat_cols[:5] or ['none']}")
    print()

    suggestions = []

    if datetime_cols and numeric_cols:
        suggestions.append(
            f"  LINE CHART — {numeric_cols[0]} over {datetime_cols[0]}\n"
            f"    Message: trend over time\n"
            f"    Command: --chart line --x {datetime_cols[0]} --y {numeric_cols[0]}"
        )

    if cat_cols and numeric_cols:
        suggestions.append(
            f"  BAR CHART — {numeric_cols[0]} by {cat_cols[0]}\n"
            f"    Message: compare across {cat_cols[0]} categories\n"
            f"    Command: --chart bar --x {cat_cols[0]} --y {numeric_cols[0]}"
        )

    if len(numeric_cols) >= 2:
        suggestions.append(
            f"  SCATTER — {numeric_cols[0]} vs {numeric_cols[1]}\n"
            f"    Message: correlation / relationship\n"
            f"    Command: --chart scatter --x {numeric_cols[0]} --y {numeric_cols[1]}"
        )

    if len(numeric_cols) >= 1:
        suggestions.append(
            f"  HISTOGRAM — distribution of {numeric_cols[0]}\n"
            f"    Message: spread and outliers\n"
            f"    Command: --chart histogram --x {numeric_cols[0]}"
        )

    if suggestions:
        for s in suggestions:
            print(s)
            print()
    else:
        print("  No clear chart recommendations — check column types.")

    print(
        "Reference: data-analytics-skills/04-data-storytelling-visualization/visualization-builder/references/chart_selection_guide.md"
    )


def build_chart(
    df: pd.DataFrame, chart_type: str, x_col: str, y_col: str | None, output: str
) -> None:
    """Build and save a chart using matplotlib with professional styling."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError:
        print("[ERROR] matplotlib not installed. Install with: pip install matplotlib")
        sys.exit(1)

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.3,
            "figure.dpi": 150,
        }
    )

    NYC_BLUE = "#003087"
    NYC_ORANGE = "#FF6319"
    fig, ax = plt.subplots(figsize=(10, 5))

    if chart_type == "bar":
        data = (
            df.groupby(x_col)[y_col].sum().sort_values(ascending=False)
            if y_col
            else df[x_col].value_counts()
        )
        ax.bar(data.index, data.values, color=NYC_BLUE, edgecolor="white")
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col or "count")
        title = f"{y_col or 'Count'} by {x_col}"

    elif chart_type == "line":
        df_plot = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df_plot[x_col]):
            df_plot[x_col] = pd.to_datetime(df_plot[x_col], errors="coerce")
        df_plot = df_plot.sort_values(x_col)
        ax.plot(df_plot[x_col], df_plot[y_col], color=NYC_BLUE, linewidth=1.5)
        ax.fill_between(df_plot[x_col], df_plot[y_col], alpha=0.1, color=NYC_BLUE)
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        title = f"{y_col} over time"

    elif chart_type == "histogram":
        ax.hist(df[x_col].dropna(), bins=30, color=NYC_BLUE, edgecolor="white")
        ax.set_xlabel(x_col)
        ax.set_ylabel("frequency")
        title = f"Distribution of {x_col}"

    elif chart_type == "scatter":
        ax.scatter(df[x_col], df[y_col], alpha=0.5, color=NYC_BLUE, s=20)
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        title = f"{x_col} vs {y_col}"

    else:
        print(f"[ERROR] Unknown chart type: {chart_type}. Use: bar, line, histogram, scatter")
        sys.exit(1)

    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    fig.text(0.99, 0.01, "Source: NYC DOT Socrata Toolkit", ha="right", fontsize=7, color="gray")
    plt.tight_layout()
    plt.savefig(output, bbox_inches="tight")
    plt.close()
    print(f"[DONE] Chart saved to {output}")


def main():
    parser = argparse.ArgumentParser(description="Recommend or build charts for NYC DOT data.")
    parser.add_argument("--input", required=True, help="Path to CSV")
    parser.add_argument(
        "--recommend", action="store_true", help="Print chart recommendations and exit"
    )
    parser.add_argument(
        "--chart", choices=["bar", "line", "histogram", "scatter"], help="Chart type to build"
    )
    parser.add_argument("--x", dest="x_col", help="X-axis column")
    parser.add_argument("--y", dest="y_col", help="Y-axis column (not needed for histogram)")
    parser.add_argument("--target-col", help="Column of interest for recommendations")
    parser.add_argument("--out", default="chart.png", help="Output file (.png)")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    for col in df.columns:
        if "date" in col.lower() or "time" in col.lower():
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if args.recommend:
        recommend_charts(df, target_col=args.target_col)
        return

    if not args.chart or not args.x_col:
        parser.error("--chart and --x are required when not using --recommend")

    build_chart(df, args.chart, args.x_col, args.y_col, args.out)


if __name__ == "__main__":
    main()
