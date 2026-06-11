"""Analysis package - Production-ready data profiling, analytics, and insights."""

from __future__ import annotations

from .bayesian import BayesianInferenceResult, BayesianRegressionEngine
from .confidence_intervals import (
    bootstrap_confidence_interval,
    mean_confidence_interval,
    wilson_score_confidence_interval,
)
from .insights import InsightsEngine, InsightsReport, generate_insights, smart_recommendations
from .metrics import (
    compute_borough_metrics,
    compute_freshness_score,
    compute_sla_metrics,
    compute_sla_trends,
    flag_sla_violations,
)
from .profiling import DataProfile, profile_dataframe, quality_report
from .reporting import DashboardSummary, Report, generate_contract_report, generate_inquiry_response
from .text import extract_patterns, extract_term_frequencies, generate_text_insights, parse_sim_complaints
from .viz import bar_chart, histogram, box_plot

__all__ = [
    "profile_dataframe",
    "quality_report",
    "DataProfile",
    "generate_text_insights",
    "extract_term_frequencies",
    "extract_patterns",
    "parse_sim_complaints",
    "compute_sla_metrics",
    "compute_borough_metrics",
    "compute_sla_trends",
    "flag_sla_violations",
    "compute_freshness_score",
    "Report",
    "DashboardSummary",
    "generate_contract_report",
    "generate_inquiry_response",
    "InsightsEngine",
    "InsightsReport",
    "generate_insights",
    "smart_recommendations",
    "histogram",
    "bar_chart",
    "classify_all_distributions",
    "correlation_analysis",
    "detect_all_outliers",
    "wilson_score_confidence_interval",
    "bootstrap_confidence_interval",
    "mean_confidence_interval",
    "BayesianInferenceResult",
    "BayesianRegressionEngine",
    "list_available_visualizations",
    "validate_ada_compliance_gates",
    "box_plot",
]

from ..analysis_advanced import (
    classify_all_distributions,
    correlation_analysis,
    detect_all_outliers,
)


def _legacy_import(module: str, *names: str) -> None:
    """Import optional legacy modules without failing if unavailable."""
    import importlib
    try:
        mod = importlib.import_module(module, __name__)
        for name in names:
            if hasattr(mod, name):
                globals()[name] = getattr(mod, name)
    except Exception:
        pass


_legacy_import(".quality", "Anomaly")
_legacy_import("..quality.sla_tracking", "SLATarget")
_legacy_import("..quality.freshness", "AlertSeverity")
_legacy_import("..metrics", "DataQualityMetrics")
_legacy_import("..quality.validation", "validate_required_columns", "validate_schema_types")
_legacy_import(".viz", "box_plot")
_legacy_import(".reporting", "generate_program_report")
_legacy_import(".insights", "build_weighted_rank_sql", "websearch_to_tsquery_sql")
_legacy_import("..analyst.ramp_analysis", "compute_borough_completion_rates")
_legacy_import("..engineering.cost_estimator", "estimate_costs")
_legacy_import("..reports.analyst", "ProjectAnalystReports")
_legacy_import(".domain_validation", "validate_ada_compliance_gates")
