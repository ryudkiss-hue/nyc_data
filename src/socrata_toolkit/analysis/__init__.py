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


# Legacy aliases for tests
try:
    from .advanced import classify_all_distributions
    from .quality import Anomaly
    from ..quality.sla_tracking import SLATarget
    from ..quality.freshness import AlertSeverity
    from ..metrics import DataQualityMetrics
    from ..quality.validation import validate_required_columns, validate_schema_types
    from .viz import box_plot
    from .reporting import generate_program_report
    from .insights import build_weighted_rank_sql, websearch_to_tsquery_sql
    from ..analyst.ramp_analysis import compute_borough_completion_rates
    from ..engineering.cost_estimator import estimate_costs
    from ..governance.reports import ProjectAnalystReports
    from .correlation import correlation_analysis
    from .domain_validation import validate_ada_compliance_gates
except ImportError:
    pass
