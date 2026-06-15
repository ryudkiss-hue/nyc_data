from __future__ import annotations

import base64
import io
from dataclasses import dataclass, field
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .metrics import compute_borough_metrics, compute_sla_trends
from .profiling import profile_dataframe


@dataclass
class ChartResult:
    chart_type: str
    base64_png: str | None = None
    path: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class QualityDashboardResult:
    completeness_score: float
    missing_cells: int
    missing_chart: ChartResult
    duplicate_rows: int = 0


def _render_fig(fig: Any, path: str | None = None) -> tuple[str, str | None]:
    import matplotlib.pyplot as plt

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    if path:
        fig.savefig(path, format="png", bbox_inches="tight", dpi=100)
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    return b64, path


def histogram(
    df: pd.DataFrame, column: str, title: str | None = None, path: str | None = None
) -> ChartResult:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 6))
    data = pd.to_numeric(df[column], errors="coerce").dropna()
    ax.hist(data.values, bins=min(30, max(10, len(data) // 5)), alpha=0.75, edgecolor="white")
    ax.set_xlabel(column)
    ax.set_ylabel("Count")
    ax.set_title(title or f"Distribution: {column}")
    b64, saved_path = _render_fig(fig, path)
    return ChartResult(chart_type="histogram", base64_png=b64, path=saved_path)


def bar_chart(
    df: pd.DataFrame,
    column: str,
    title: str | None = None,
    horizontal: bool = False,
    path: str | None = None,
) -> ChartResult:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    counts = df[column].value_counts().head(15)
    fig, ax = plt.subplots(figsize=(10, 6))
    if horizontal:
        ax.barh(counts.index.astype(str), counts.values)
        ax.set_xlabel("Count")
        ax.set_ylabel(column)
    else:
        ax.bar(counts.index.astype(str), counts.values)
        ax.set_xlabel(column)
        ax.set_ylabel("Count")
        ax.tick_params(axis="x", rotation=45)
    ax.set_title(title or f"Top Categories: {column}")
    b64, saved_path = _render_fig(fig, path)
    return ChartResult(chart_type="bar_chart", base64_png=b64, path=saved_path)


def box_plot(
    df: pd.DataFrame, column: str | list[str], title: str | None = None, path: str | None = None
) -> ChartResult:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if isinstance(column, list):
        cols = column
    else:
        cols = [column]

    data = [pd.to_numeric(df[c], errors="coerce").dropna().values for c in cols]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.boxplot(data)
    ax.set_xticks(range(1, len(cols) + 1))
    ax.set_xticklabels(cols)
    ax.set_title(title or f"Box Plot: {', '.join(cols)}")
    b64, saved_path = _render_fig(fig, path)
    return ChartResult(chart_type="box_plot", base64_png=b64, path=saved_path)


def list_available_visualizations() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "name": "histogram",
                "description": "Distribution histogram with box plot",
                "parameters": "df, column, title=None",
            },
            {
                "name": "bar_chart",
                "description": "Bar chart for categorical data",
                "parameters": "df, column, title=None",
            },
            {
                "name": "box_plot",
                "description": "Box plot for numerical data",
                "parameters": "df, column, title=None",
            },
            {
                "name": "correlation_heatmap",
                "description": "Heatmap of pairwise column correlations",
                "parameters": "df, title=None",
            },
            {
                "name": "metric_status_pie_chart",
                "description": "Pie chart showing the distribution of metric statuses",
                "parameters": "summary, title=None",
            },
            {
                "name": "data_completeness_chart",
                "description": "Bar chart of column completeness rates",
                "parameters": "df, title=None",
            },
        ]
    )


from dataclasses import dataclass as _dc


@_dc
class DistributionClassification:
    classification: str
    sample_size: int
    skewness: float | None = None
    kurtosis: float | None = None


def classify_distribution(df: pd.DataFrame, column: str) -> DistributionClassification:
    data = pd.to_numeric(df[column], errors="coerce").dropna()
    n = len(data)

    if n < 5:
        return DistributionClassification("sparse", n)

    try:
        from scipy import stats

        _, p_normal = stats.normaltest(data)
        _, p_uniform = stats.kstest(data, "uniform", args=(data.min(), data.max() - data.min()))

        skewness = float(stats.skew(data))
        kurtosis_val = float(stats.kurtosis(data))

        if p_normal > 0.05:
            return DistributionClassification("normal", n, skewness, kurtosis_val)
        elif p_uniform > 0.05:
            return DistributionClassification("uniform", n, skewness, kurtosis_val)
        else:
            return DistributionClassification("other", n, skewness, kurtosis_val)
    except Exception:
        return DistributionClassification("unknown", n)
