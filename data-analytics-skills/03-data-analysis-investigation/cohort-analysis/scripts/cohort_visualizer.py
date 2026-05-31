"""
Render a retention heatmap and retention curve chart from the retention matrix CSV.

Requires: matplotlib, seaborn

Usage:
    python cohort_visualizer.py --input retention.csv --output heatmap.png
    python cohort_visualizer.py --input retention.csv --chart curves --output curves.png
"""

import argparse
import sys

import pandas as pd


def plot_heatmap(matrix: pd.DataFrame, output: str) -> None:
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ImportError:
        print("matplotlib and seaborn required: pip install matplotlib seaborn")
        return

    # Drop the cohort size column for the heatmap
    heat_data = matrix.drop(columns=["Cohort Size"], errors="ignore")

    fig, ax = plt.subplots(figsize=(max(10, len(heat_data.columns)), max(6, len(heat_data) * 0.6)))
    sns.heatmap(
        heat_data.astype(float),
        annot=True,
        fmt=".0f",
        cmap="Blues",
        linewidths=0.5,
        ax=ax,
        vmin=0,
        vmax=100,
        cbar_kws={"label": "Retention %"},
    )
    ax.set_title("Cohort Retention Heatmap", fontsize=14, fontweight="bold")
    ax.set_xlabel("Period")
    ax.set_ylabel("Cohort")
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches="tight")
    print(f"Heatmap saved to {output}")
    plt.close()


def plot_curves(matrix: pd.DataFrame, output: str) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib required: pip install matplotlib")
        return

    period_cols = [c for c in matrix.columns if c.startswith("Period")]
    fig, ax = plt.subplots(figsize=(12, 6))
    for cohort in matrix.index:
        row = matrix.loc[cohort, period_cols].astype(float)
        ax.plot(range(len(row)), row.values, marker="o", label=str(cohort)[:7])

    ax.set_xlabel("Period Number")
    ax.set_ylabel("Retention %")
    ax.set_title("Retention Curves by Cohort")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    ax.set_ylim(0, 105)
    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches="tight")
    print(f"Curves chart saved to {output}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Visualise cohort retention matrix.")
    parser.add_argument("--input", required=True, help="CSV retention matrix from retention_matrix.py")
    parser.add_argument("--chart", choices=["heatmap", "curves"], default="heatmap")
    parser.add_argument("--output", default="retention_chart.png")
    args = parser.parse_args()

    matrix = pd.read_csv(args.input, index_col=0)
    if args.chart == "heatmap":
        plot_heatmap(matrix, args.output)
    else:
        plot_curves(matrix, args.output)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        import numpy as np
        rng = np.random.default_rng(5)
        cohorts = pd.date_range("2023-01-01", periods=6, freq="MS")
        data = {}
        for i, c in enumerate(cohorts):
            rates = [max(0, 75 - j * 10 + rng.normal(0, 3)) for j in range(7)]
            data[str(c.date())] = rates
        matrix = pd.DataFrame(data, index=[f"Period {i}" for i in range(7)]).T
        matrix.columns = [f"Period {i}" for i in range(7)]
        print("Demo retention matrix:")
        print(matrix.to_string())
        print("\n(Run with --input to visualise from a real CSV)")
    else:
        main()
