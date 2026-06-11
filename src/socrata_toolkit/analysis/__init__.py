"""
Analysis package (Refactored).
Provides production-ready data profiling, text analytics, SLA tracking, and insights generation.
"""

from __future__ import annotations

from .bayesian import BayesianInferenceResult, BayesianRegressionEngine
from .confidence_intervals import bootstrap_confidence_interval, mean_confidence_interval, wilson_score_confidence_interval
from .insights import InsightsEngine, InsightsReport, generate_insights, smart_recommendations
from .metrics import compute_borough_metrics, compute_freshness_score, compute_sla_metrics, compute_sla_trends, flag_sla_violations
from .profiling import DataProfile, profile_dataframe, quality_report
from .reporting import DashboardSummary, Report, generate_contract_report, generate_inquiry_response
from .text import extract_patterns, extract_term_frequencies, generate_text_insights, parse_sim_complaints
from .viz import bar_chart, histogram

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
]


# Re-export advanced analysis helpers from the top-level analysis_advanced
# module so that `socrata_toolkit.analysis.correlation_analysis` and the
# `socrata_toolkit.analysis.advanced` shim resolve correctly.
from ..analysis_advanced import (
    classify_all_distributions,
    correlation_analysis,
    detect_all_outliers,
)


# Legacy aliases for tests. Each import is independent so that a single
# unavailable optional symbol does not suppress the rest (a shared try/except
# would silently skip every alias after the first failing import).
def _legacy_import(module: str, *names: str) -> None:
    import importlib

    try:
        mod = importlib.import_module(module, __name__)
    except Exception:
        return
    for name in names:
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)


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
