"""
Analysis package (Refactored).
Provides production-ready data profiling, text analytics, SLA tracking, and insights generation.
"""

from __future__ import annotations

try:
    from .bayesian import (
        BayesianInferenceResult,
        BayesianRegressionEngine,
    )
except ImportError:
    BayesianInferenceResult = None  # type: ignore[assignment,misc]
    BayesianRegressionEngine = None  # type: ignore[assignment,misc]
from .confidence_intervals import (
    bootstrap_confidence_interval,
    mean_confidence_interval,
    wilson_score_confidence_interval,
)
from .dataset_health import (
    DatasetHealthClassifier,
    DatasetHealthMetrics,
    DatasetHealthReport,
    HealthStatus,
    Severity,
)
from .insights import InsightsEngine, InsightsReport, generate_insights, smart_recommendations
from .metrics import (
    AnomalyDetector,
    AnomalyReport,
    AnomalySeverity,
    BusinessRulesEngine,
    DataQualityCatalog,
    DataQualityScore,
    DataQualityTracker,
    DatasetQualityScore,
    DatasetFreshness,
    FreshnessAlert,
    FreshnessTracker,
    MetricPoint,
    MetricsRegistry,
    MetricsTracker,
    PipelineMetrics,
    compute_borough_metrics,
    compute_cycle_times,
    compute_freshness_score,
    compute_program_dashboard,
    compute_sla_metrics,
    compute_sla_trends,
    correlation_heatmap,
    create_map,
    dataframe_to_pdf,
    save_map,
    detect_outliers_iqr,
    detect_outliers_zscore,
    flag_anomalies,
    flag_sla_violations,
    get_global_registry,
    quality_dashboard,
    reset_global_registry,
    time_series_chart,
    time_series_summary,
    validate_defect_applicability,
    validate_geospatial_bounds,
    validate_marking_standards,
    validate_material_coverage,
)
from .profiling import DataProfile, profile_dataframe, quality_report
from .reporting import DashboardSummary, Report, generate_contract_report, generate_inquiry_response
from .text import (
    extract_patterns,
    extract_term_frequencies,
    generate_text_insights,
    parse_sim_complaints,
)
from .viz import bar_chart, box_plot, classify_distribution, histogram, list_available_visualizations

try:
    from .dataset_health_workflow import (
        DatasetHealthWorkflow,
        run_dataset_health_workflow,
    )
except ImportError:
    DatasetHealthWorkflow = None  # type: ignore[assignment,misc]
    run_dataset_health_workflow = None  # type: ignore[assignment]
from .sla_status import (
    ComplianceStatus,
    RootCause,
    SLAComplianceReport,
    SLAMetricSnapshot,
    SLAStatusClassifier,
    SLAStatusRecord,
    SLATier,
    TrendDirection,
)

try:
    from .sla_compliance_workflow import (
        build_sla_compliance_graph,
        run_sla_compliance_workflow,
    )
except ImportError:
    run_sla_compliance_workflow = None  # type: ignore[assignment]
    build_sla_compliance_graph = None  # type: ignore[assignment]
from .legal_hold_classifier import (
    AuditTrailMetrics,
    LegalHoldClassifier,
    LegalHoldMetrics,
    LegalHoldReport,
    RecordType,
    RetentionRequirement,
    Sensitivity,
)

try:
    from .legal_hold_workflow import (
        LegalHoldWorkflow,
        build_legal_hold_graph,
        run_legal_hold_workflow,
    )
except ImportError:
    LegalHoldWorkflow = None  # type: ignore[assignment,misc]
    run_legal_hold_workflow = None  # type: ignore[assignment]
    build_legal_hold_graph = None  # type: ignore[assignment]

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
    "compute_cycle_times",
    "validate_defect_applicability",
    "MetricPoint",
    "DatasetFreshness",
    "MetricsTracker",
    "AnomalyDetector",
    "FreshnessAlert",
    "AnomalyReport",
    "MetricsRegistry",
    "AnomalySeverity",
    "FreshnessTracker",
    "PipelineMetrics",
    "BusinessRulesEngine",
    "correlation_heatmap",
    "detect_outliers_iqr",
    "detect_outliers_zscore",
    "flag_anomalies",
    "get_global_registry",
    "reset_global_registry",
    "DataQualityCatalog",
    "quality_dashboard",
    "compute_program_dashboard",
    "create_map",
    "save_map",
    "dataframe_to_pdf",
    "DatasetQualityScore",
    "time_series_chart",
    "time_series_summary",
    "DataQualityTracker",
    "validate_geospatial_bounds",
    "validate_marking_standards",
    "validate_material_coverage",
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
    "box_plot",
    "list_available_visualizations",
    "classify_distribution",
    "classify_all_distributions",
    "correlation_analysis",
    "detect_all_outliers",
    "wilson_score_confidence_interval",
    "bootstrap_confidence_interval",
    "mean_confidence_interval",
    "RampStatus",
    "BlockerType",
    "RampStatusClassifier",
    "RampClassificationResult",
    "BoroughRampStats",
    "RampProgressState",
    "create_ramp_workflow",
    "run_ramp_workflow",
    "DatasetHealthClassifier",
    "DatasetHealthMetrics",
    "DatasetHealthReport",
    "HealthStatus",
    "Severity",
    "DatasetHealthWorkflow",
    "run_dataset_health_workflow",
    "SLAStatusClassifier",
    "SLAMetricSnapshot",
    "SLAStatusRecord",
    "SLAComplianceReport",
    "ComplianceStatus",
    "SLATier",
    "RootCause",
    "TrendDirection",
    "run_sla_compliance_workflow",
    "build_sla_compliance_graph",
    "LegalHoldClassifier",
    "LegalHoldMetrics",
    "LegalHoldReport",
    "AuditTrailMetrics",
    "RecordType",
    "Sensitivity",
    "RetentionRequirement",
    "LegalHoldWorkflow",
    "run_legal_hold_workflow",
    "build_legal_hold_graph",
    "BayesianInferenceResult",
    "BayesianRegressionEngine",
    "validate_ada_compliance_gates",
    "box_plot",
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


_legacy_import("..quality.anomalies", "Anomaly")
_legacy_import("..quality.sla_tracking", "SLATarget")
_legacy_import("..alerts.manager", "AlertSeverity")
_legacy_import("..metrics", "DataQualityMetrics")
_legacy_import("..quality.validation", "validate_required_columns", "validate_schema_types")
_legacy_import(".viz", "box_plot")
_legacy_import(".reporting", "generate_program_report")
_legacy_import("..relevance", "build_weighted_rank_sql", "websearch_to_tsquery_sql")
_legacy_import("..analyst.ramp_analysis", "compute_borough_completion_rates")
_legacy_import("..engineering.cost_estimator", "estimate_costs")
_legacy_import("..reports.analyst", "ProjectAnalystReports")
_legacy_import("..quality.validation", "validate_ada_compliance_gates")


# Lazy imports for optional NLP/LLM dependencies (spacy, langgraph, langchain)
def __getattr__(name: str):
    """Lazy-load optional analysis modules."""
    if name in ("RampStatus", "BlockerType", "RampStatusClassifier", "RampClassificationResult"):
        from .ramp_status import (
            BlockerType,
            RampClassificationResult,
            RampStatus,
            RampStatusClassifier,
        )
        return {
            "RampStatus": RampStatus,
            "BlockerType": BlockerType,
            "RampStatusClassifier": RampStatusClassifier,
            "RampClassificationResult": RampClassificationResult,
        }[name]
    elif name in ("BoroughRampStats", "RampProgressState", "create_ramp_workflow", "run_ramp_workflow"):
        from .ramp_progress_workflow import (
            BoroughRampStats,
            RampProgressState,
            create_ramp_workflow,
            run_ramp_workflow,
        )
        return {
            "BoroughRampStats": BoroughRampStats,
            "RampProgressState": RampProgressState,
            "create_ramp_workflow": create_ramp_workflow,
            "run_ramp_workflow": run_ramp_workflow,
        }[name]
    elif name in ("VelocityClassifier", "VelocityMetrics", "VelocityClassification", "PerformanceTier", "MetricType", "AnomalyType"):
        from .velocity_classifier import (
            AnomalyType,
            MetricType,
            PerformanceTier,
            VelocityClassification,
            VelocityClassifier,
            VelocityMetrics,
        )
        return {
            "VelocityClassifier": VelocityClassifier,
            "VelocityMetrics": VelocityMetrics,
            "VelocityClassification": VelocityClassification,
            "PerformanceTier": PerformanceTier,
            "MetricType": MetricType,
            "AnomalyType": AnomalyType,
        }[name]
    elif name in ("run_velocity_analysis", "build_velocity_analysis_graph", "VelocityAnalysisContext", "VelocityState"):
        from .velocity_analysis_workflow import (
            VelocityAnalysisContext,
            VelocityState,
            build_velocity_analysis_graph,
            run_velocity_analysis,
        )
        return {
            "run_velocity_analysis": run_velocity_analysis,
            "build_velocity_analysis_graph": build_velocity_analysis_graph,
            "VelocityAnalysisContext": VelocityAnalysisContext,
            "VelocityState": VelocityState,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
