"""
Chart Builder / Visualization Spec Generator

Recommends chart types for given data characteristics and generates a
structured visualization specification (JSON) or Matplotlib chart.

Usage:
    python chart_builder.py --recommend --data-type time-series --metric-count 1
    python chart_builder.py --recommend --data-type comparison --categories 6
    python chart_builder.py --plot bar --labels "Jan,Feb,Mar,Apr" \
        --values "12000,15000,11000,18000" --title "Monthly Revenue"
    python chart_builder.py --plot line --labels "W1,W2,W3,W4,W5" \
        --values "800,950,900,1100,1050" --title "Weekly Active Users"
"""

import argparse
import json
import sys


# ---- Chart selection logic ---------------------------------------------------

CHART_RULES = [
    {
        "data_type": "time-series",
        "metric_count": "any",
        "recommendation": "line",
        "rationale": "Line charts show trends over time clearly; use area fill if showing total volume.",
        "avoid": ["pie", "bar (unless comparing few discrete periods)"],
    },
    {
        "data_type": "comparison",
        "categories_max": 7,
        "recommendation": "bar (vertical)",
        "rationale": "Bar charts are best for comparing discrete categories. Keep ≤7 bars for readability.",
        "avoid": ["pie (hard to compare)", "line (implies continuity)"],
    },
    {
        "data_type": "comparison",
        "categories_min": 8,
        "recommendation": "horizontal bar",
        "rationale": "Long category labels read better on horizontal bars.",
        "avoid": ["vertical bar (label clutter)", "pie"],
    },
    {
        "data_type": "part-to-whole",
        "categories_max": 4,
        "recommendation": "pie / donut",
        "rationale": "Suitable only when you have ≤4 segments and the 'part of whole' story is primary.",
        "avoid": ["bar (doesn't show total context)"],
    },
    {
        "data_type": "part-to-whole",
        "categories_min": 5,
        "recommendation": "stacked bar or 100% bar",
        "rationale": "Stacked bars handle more segments and allow period-over-period comparison.",
        "avoid": ["pie (too many slices)"],
    },
    {
        "data_type": "distribution",
        "recommendation": "histogram / box plot",
        "rationale": "Histograms show shape; box plots show median, IQR, and outliers side by side.",
        "avoid": ["bar (bins obscure shape)", "line"],
    },
    {
        "data_type": "correlation",
        "recommendation": "scatter plot",
        "rationale": "Scatter shows relationship between two continuous variables; add a trend line.",
        "avoid": ["bar", "line (implies sequence)"],
    },
    {
        "data_type": "flow",
        "recommendation": "funnel / sankey",
        "rationale": "Funnel shows sequential drop-off; Sankey shows multi-path flows.",
        "avoid": ["bar", "pie"],
    },
]


def recommend_chart(data_type: str, categories: int = 5, metric_count: int = 1) -> dict:
    for rule in CHART_RULES:
        if rule["data_type"] != data_type:
            continue
        if "categories_max" in rule and categories > rule["categories_max"]:
            continue
        if "categories_min" in rule and categories < rule["categories_min"]:
            continue
        return rule
    return {
        "data_type": data_type,
        "recommendation": "bar",
        "rationale": "Default to bar chart; refine based on data characteristics.",
        "avoid": [],
    }


def build_spec(chart_type: str, labels: list, values: list, title: str,
               x_label: str = "", y_label: str = "") -> dict:
    return {
        "chart_type": chart_type,
        "title": title,
        "x_axis": {"label": x_label, "values": labels},
        "y_axis": {"label": y_label},
        "series": [{"name": "primary", "values": values}],
        "annotations": [],
        "design_notes": {
            "max_colors": 3,
            "highlight_max": True,
            "grid": "horizontal only",
            "legend": "top" if chart_type in ("line",) else "none",
        },
    }


def plot_chart(chart_type: str, labels: list, values: list, title: str):
    """Render chart using matplotlib if available, else print ASCII bar."""
    try:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(9, 5))
        if chart_type == "bar":
            ax.bar(labels, values, color="#4C72B0")
        elif chart_type == "line":
            ax.plot(labels, values, marker="o", color="#4C72B0", linewidth=2)
            ax.fill_between(labels, values, alpha=0.1, color="#4C72B0")
        else:
            ax.bar(labels, values)

        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.yaxis.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()
        plt.show()

    except ImportError:
        _ascii_bar(labels, values, title)


def _ascii_bar(labels, values, title):
    """Fallback ASCII bar chart."""
    max_val = max(values) if values else 1
    width = 40
    print(f"\n  {title}")
    print("  " + "-" * (width + 20))
    for label, val in zip(labels, values):
        bar_len = int(val / max_val * width)
        print(f"  {label:<12} {'█' * bar_len} {val:,.0f}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Recommend and build chart specifications.")
    parser.add_argument("--recommend", action="store_true", help="Recommend a chart type")
    parser.add_argument("--data-type",
                        choices=["time-series", "comparison", "part-to-whole",
                                 "distribution", "correlation", "flow"],
                        help="Type of data being visualized")
    parser.add_argument("--categories", type=int, default=5)
    parser.add_argument("--metric-count", type=int, default=1)
    parser.add_argument("--plot", choices=["bar", "line", "horizontal-bar"],
                        help="Chart type to render")
    parser.add_argument("--labels", help="Comma-separated x-axis labels")
    parser.add_argument("--values", help="Comma-separated numeric values")
    parser.add_argument("--title", default="Chart")
    parser.add_argument("--x-label", default="")
    parser.add_argument("--y-label", default="")
    parser.add_argument("--spec-only", action="store_true", help="Print JSON spec without rendering")
    args = parser.parse_args()

    if args.recommend:
        if not args.data_type:
            parser.error("--data-type required with --recommend")
        rule = recommend_chart(args.data_type, args.categories, args.metric_count)
        print(f"\nRecommended chart: {rule['recommendation'].upper()}")
        print(f"Rationale: {rule['rationale']}")
        print(f"Avoid: {', '.join(rule['avoid']) if rule.get('avoid') else 'none'}")
        return

    if args.plot:
        if not (args.labels and args.values):
            parser.error("--labels and --values required with --plot")
        labels = [l.strip() for l in args.labels.split(",")]
        values = [float(v.strip()) for v in args.values.split(",")]

        if args.spec_only:
            spec = build_spec(args.plot, labels, values, args.title, args.x_label, args.y_label)
            print(json.dumps(spec, indent=2))
        else:
            plot_chart(args.plot, labels, values, args.title)
        return

    parser.print_help()


if __name__ == "__main__":
    # Demo: recommendation + ASCII chart
    print("=== Chart Recommendations ===")
    for dt, cats in [("time-series", 12), ("comparison", 5), ("part-to-whole", 3),
                     ("distribution", 1), ("correlation", 1)]:
        r = recommend_chart(dt, categories=cats)
        print(f"  {dt:<20} → {r['recommendation']}")

    print()
    labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    values = [118_000, 124_000, 131_000, 128_000, 142_000, 155_000]
    _ascii_bar(labels, values, "Monthly Revenue ($)")
