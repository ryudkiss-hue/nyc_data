"""
Analysis package (Refactored).
Provides production-ready data profiling, text analytics, SLA tracking, and insights generation.
"""

from __future__ import annotations

from .bayesian import (
    BayesianInferenceResult,
    BayesianRegressionEngine,
    quantify_hiring_yield,
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
from .text import (
    extract_patterns,
    extract_term_frequencies,
    generate_text_insights,
    parse_sim_complaints,
)
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
]

