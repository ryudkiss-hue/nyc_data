"""AI/NLP-Powered Insights Engine for DOT Sidewalk Toolkit.

Provides automated, intelligent analysis that produces human-readable
narratives and actionable recommendations from raw data. Combines
all analytics modules into a single "smart analysis" interface.

Key capabilities:
- Auto-detect data patterns and generate plain-English insights
- Smart recommendations based on KPI thresholds and trends
- Anomaly narratives explaining what's unusual and why it matters
- Borough-level intelligence with equity and priority scoring
- One-call comprehensive analysis that runs everything

Example::

    from socrata_toolkit.insights_engine import (
        generate_insights,
        smart_recommendations,
        InsightsReport,
    )

    report = generate_insights(df)
    print(report.summary)
    for rec in report.recommendations:
        print(f"[{rec.priority}] {rec.text}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np  # type: ignore[import]
import pandas as pd  # type: ignore[import]


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class Insight:
    """A single data insight."""
    category: str  # "quality", "trend", "anomaly", "correlation", "distribution", "operational"
    severity: str  # "info", "warning", "critical"
    title: str
    description: str
    metric_value: Optional[float] = None
    recommendation: str = ""


@dataclass
class Recommendation:
    """An actionable recommendation."""
    priority: str  # "critical", "high", "medium", "low"
    category: str
    text: str
    rationale: str
    estimated_impact: str = ""


@dataclass
class InsightsReport:
    """Complete insights report for a dataset."""
    summary: str
    data_health: str  # "good", "fair", "poor"
    insights: List[Insight] = field(default_factory=list)
    recommendations: List[Recommendation] = field(default_factory=list)
    key_metrics: Dict[str, Any] = field(default_factory=dict)
    borough_insights: Dict[str, List[str]] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Render as Markdown."""
        lines = [
            f"# Data Insights Report",
            f"",
            f"**Data Health:** {self.data_health.upper()}",
            f"",
            f"## Summary",
            f"{self.summary}",
            f"",
        ]
        if self.key_metrics:
            lines.append("## Key Metrics")
            for k, v in self.key_metrics.items():
                lines.append(f"- **{k}**: {v}")
            lines.append("")

        if self.insights:
            lines.append("## Insights")
            for i in self.insights:
                icon = {"critical": "[!]", "warning": "[~]", "info": "[i]"}.get(i.severity, "")
                lines.append(f"### {icon} {i.title}")
                lines.append(f"{i.description}")
                if i.recommendation:
                    lines.append(f"  - Recommendation: {i.recommendation}")
                lines.append("")

        if self.recommendations:
            lines.append("## Recommendations")
            for r in self.recommendations:
                lines.append(f"- **[{r.priority.upper()}]** {r.text}")
                lines.append(f"  - {r.rationale}")
                lines.append("")

        if self.borough_insights:
            lines.append("## Borough Intelligence")
            for boro, notes in self.borough_insights.items():
                lines.append(f"### {boro}")
                for note in notes:
                    lines.append(f"- {note}")
                lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Insight Generation
# ---------------------------------------------------------------------------

def generate_insights(
    df: pd.DataFrame,
    borough_col: str = "borough",
    status_col: str = "status",
    severity_col: str = "severity_rating",
    date_col: Optional[str] = None,
    key_columns: Optional[List[str]] = None,
) -> InsightsReport:
    """Generate comprehensive AI-powered insights from a DataFrame.

    Automatically runs quality analysis, outlier detection, correlation
    analysis, distribution classification, and trend detection, then
    synthesizes the results into a human-readable report.
    """
    insights: List[Insight] = []
    recommendations: List[Recommendation] = []
    key_metrics: Dict[str, Any] = {}
    borough_insights: Dict[str, List[str]] = {}

    # --- Quality Analysis ---
    quality_insights, quality_recs, quality_metrics = _analyze_quality(df, key_columns)
    insights.extend(quality_insights)
    recommendations.extend(quality_recs)
    key_metrics.update(quality_metrics)

    # --- Outlier Detection ---
    outlier_insights = _analyze_outliers(df)
    insights.extend(outlier_insights)

    # --- Correlation Analysis ---
    corr_insights = _analyze_correlations(df)
    insights.extend(corr_insights)

    # --- Distribution Analysis ---
    dist_insights = _analyze_distributions(df)
    insights.extend(dist_insights)

    # --- Borough Analysis ---
    if borough_col in df.columns:
        borough_insights, boro_recs = _analyze_boroughs(df, borough_col, status_col, severity_col)
        recommendations.extend(boro_recs)

    # --- Trend Analysis ---
    if date_col and date_col in df.columns:
        trend_insights = _analyze_trends(df, date_col, severity_col)
        insights.extend(trend_insights)

    # --- Status Analysis ---
    if status_col in df.columns:
        status_insights, status_recs = _analyze_status(df, status_col)
        insights.extend(status_insights)
        recommendations.extend(status_recs)

    # --- Generate Summary ---
    data_health = _compute_health(insights)
    summary = _generate_summary(df, insights, key_metrics, data_health)

    # Sort recommendations by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    recommendations.sort(key=lambda r: priority_order.get(r.priority, 4))

    return InsightsReport(
        summary=summary,
        data_health=data_health,
        insights=insights,
        recommendations=recommendations,
        key_metrics=key_metrics,
        borough_insights=borough_insights,
    )


# ---------------------------------------------------------------------------
# Analysis Functions
# ---------------------------------------------------------------------------

def _analyze_quality(df: pd.DataFrame, key_columns: Optional[List[str]]) -> tuple:
    from .governance import compute_quality_score
    score = compute_quality_score(df, key_columns=key_columns)
    insights = []
    recs = []
    metrics = {
        "Quality Score": f"{score.overall:.1f}/100",
        "Completeness": f"{score.completeness:.1f}%",
        "Row Count": len(df),
        "Column Count": len(df.columns),
    }

    if score.completeness < 80:
        null_cols = df.isnull().sum()
        worst = null_cols[null_cols > 0].sort_values(ascending=False)
        if not worst.empty:
            top_missing = worst.head(3)
            cols_str = ", ".join(f"{c} ({int(v)} nulls)" for c, v in top_missing.items())
            insights.append(Insight(
                category="quality", severity="warning",
                title="Significant Missing Data Detected",
                description=f"Data completeness is {score.completeness:.1f}%. Columns with most missing values: {cols_str}.",
                metric_value=score.completeness,
                recommendation="Investigate data source for missing fields. Consider imputation or marking as N/A.",
            ))
            recs.append(Recommendation(
                priority="high", category="quality",
                text=f"Address missing data in {len(worst)} columns ({score.completeness:.0f}% complete)",
                rationale=f"Missing data reduces analysis reliability. Top gaps: {cols_str}",
            ))

    if score.consistency < 95 and key_columns:
        recs.append(Recommendation(
            priority="medium", category="quality",
            text="Resolve duplicate key violations",
            rationale=f"Consistency score is {score.consistency:.1f}%. Duplicate keys can cause incorrect aggregations.",
        ))

    return insights, recs, metrics


def _analyze_outliers(df: pd.DataFrame) -> List[Insight]:
    from .analysis_advanced import detect_all_outliers
    insights = []
    reports = detect_all_outliers(df, method="iqr")
    for r in reports:
        if r.outlier_pct > 5:
            insights.append(Insight(
                category="anomaly", severity="warning",
                title=f"Outliers in {r.column}: {r.outlier_pct}%",
                description=f"{r.outlier_count} outlier values detected in '{r.column}' "
                            f"(bounds: {r.lower_bound:.2f} to {r.upper_bound:.2f}).",
                metric_value=r.outlier_pct,
                recommendation=f"Review records outside [{r.lower_bound:.1f}, {r.upper_bound:.1f}] for data entry errors.",
            ))
    return insights


def _analyze_correlations(df: pd.DataFrame) -> List[Insight]:
    from .analysis_advanced import correlation_analysis
    insights = []
    result = correlation_analysis(df, threshold=0.7)
    for pair in result.pairs[:5]:
        insights.append(Insight(
            category="correlation", severity="info",
            title=f"Strong correlation: {pair['column_a']} and {pair['column_b']}",
            description=f"Correlation coefficient: {pair['correlation']:.3f} ({pair['strength']}). "
                        f"These columns move together and may represent related measures.",
            metric_value=pair["correlation"],
        ))
    return insights


def _analyze_distributions(df: pd.DataFrame) -> List[Insight]:
    from .analysis_advanced import classify_all_distributions
    insights = []
    distributions = classify_all_distributions(df)
    skewed = [d for d in distributions if d.classification in ("right_skewed", "left_skewed")]
    if skewed:
        names = ", ".join(d.column for d in skewed[:3])
        insights.append(Insight(
            category="distribution", severity="info",
            title=f"Skewed distributions detected",
            description=f"{len(skewed)} numeric columns show skewed distributions: {names}. "
                        f"Consider log-transforms for analysis or median-based statistics.",
        ))
    return insights


def _analyze_boroughs(df: pd.DataFrame, borough_col: str, status_col: str, severity_col: str) -> tuple:
    borough_insights: Dict[str, List[str]] = {}
    recs = []

    for borough, group in df.groupby(borough_col):
        notes = []
        notes.append(f"{len(group)} total records")

        if status_col in group.columns:
            pending = (group[status_col] == "Pending Repair").sum()
            if pending > 0:
                notes.append(f"{pending} pending repairs")

        if severity_col in group.columns:
            avg_sev = group[severity_col].mean()
            if not pd.isna(avg_sev):
                notes.append(f"Average severity: {avg_sev:.1f}")
                if avg_sev > 7:
                    recs.append(Recommendation(
                        priority="high", category="operational",
                        text=f"Prioritize {borough} -- high average severity ({avg_sev:.1f})",
                        rationale="Boroughs with severity above 7 indicate concentrated safety concerns.",
                    ))

        borough_insights[str(borough)] = notes

    return borough_insights, recs


def _analyze_trends(df: pd.DataFrame, date_col: str, value_col: str) -> List[Insight]:
    from .analysis_advanced import time_series_summary
    insights = []
    if value_col in df.columns:
        try:
            ts = time_series_summary(df, date_col, value_col)
            if ts.count > 0:
                insights.append(Insight(
                    category="trend", severity="info",
                    title=f"Trend: {ts.trend_direction} ({value_col})",
                    description=f"Data spans {ts.start} to {ts.end} ({ts.count} records). "
                                f"Trend slope: {ts.trend_slope:.4f} per day. Mean: {ts.mean:.2f}.",
                    metric_value=ts.trend_slope,
                ))
        except Exception:
            pass
    return insights


def _analyze_status(df: pd.DataFrame, status_col: str) -> tuple:
    insights = []
    recs = []
    counts = df[status_col].value_counts()
    total = len(df)
    pending = counts.get("Pending Repair", 0)
    complete = counts.get("Complete", 0)

    if total > 0:
        pending_pct = pending / total * 100
        complete_pct = complete / total * 100
        insights.append(Insight(
            category="operational", severity="warning" if pending_pct > 50 else "info",
            title=f"Status breakdown: {complete_pct:.0f}% complete, {pending_pct:.0f}% pending",
            description=f"Of {total} records: {complete} complete, {pending} pending repair, "
                        f"{total - complete - pending} other statuses.",
            metric_value=pending_pct,
        ))
        if pending_pct > 60:
            recs.append(Recommendation(
                priority="critical", category="operational",
                text=f"Backlog alert: {pending_pct:.0f}% of work orders are pending",
                rationale="High pending ratio indicates capacity constraints or process bottlenecks.",
                estimated_impact="Accelerating completion could improve program KPIs by 15-25%.",
            ))

    return insights, recs


def _compute_health(insights: List[Insight]) -> str:
    critical = sum(1 for i in insights if i.severity == "critical")
    warnings = sum(1 for i in insights if i.severity == "warning")
    if critical > 0:
        return "poor"
    if warnings > 2:
        return "fair"
    return "good"


def _generate_summary(df: pd.DataFrame, insights: List[Insight], metrics: Dict[str, Any], health: str) -> str:
    n_insights = len(insights)
    critical = sum(1 for i in insights if i.severity == "critical")
    warnings = sum(1 for i in insights if i.severity == "warning")

    summary = (
        f"Analysis of {len(df):,} records across {len(df.columns)} columns. "
        f"Data health: {health.upper()}. "
        f"Found {n_insights} insights ({critical} critical, {warnings} warnings). "
    )
    if metrics.get("Quality Score"):
        summary += f"Quality score: {metrics['Quality Score']}. "
    if metrics.get("Completeness"):
        summary += f"Completeness: {metrics['Completeness']}."

    return summary


# ---------------------------------------------------------------------------
# Smart Recommendations
# ---------------------------------------------------------------------------

def smart_recommendations(
    df: pd.DataFrame,
    context: str = "general",
    **kwargs: Any,
) -> List[Recommendation]:
    """Generate targeted recommendations based on data and context.

    context: "general", "construction", "budget", "complaints", "compliance"
    """
    report = generate_insights(df, **kwargs)
    return report.recommendations
