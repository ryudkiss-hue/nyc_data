"""Analysis package — transparent proxy to legacy ``analysis.py`` monolith."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_MONOLITH_PATH = Path(__file__).resolve().parent.parent / "analysis.py"


def _load_monolith() -> ModuleType:
    name = "socrata_toolkit._analysis_monolith"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _MONOLITH_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load analysis monolith at {_MONOLITH_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_monolith = _load_monolith()

# Eager export of common symbols for static analysis / star imports
profile_dataframe = _monolith.profile_dataframe
quality_report = _monolith.quality_report
generate_text_insights = _monolith.generate_text_insights
InsightsEngine = _monolith.InsightsEngine
DataProfile = _monolith.DataProfile
detect_all_outliers = _monolith.detect_all_outliers
correlation_analysis = _monolith.correlation_analysis
def _from_submod(mod_path: str, attr: str):
    return getattr(__import__(mod_path, fromlist=[attr]), attr)

MetricsTracker = getattr(_monolith, "MetricsTracker", None) or _from_submod("socrata_toolkit.program_metrics", "MetricsTracker")
DashboardSummary = getattr(_monolith, "DashboardSummary", None)
compute_program_dashboard = getattr(_monolith, "compute_program_dashboard", None) or _from_submod("socrata_toolkit.program_metrics", "compute_program_dashboard")
TfidfVectorizer = getattr(_monolith, "TfidfVectorizer", None)
parse_sim_complaints = _monolith.parse_sim_complaints


_VIZ_MAP_NAMES = frozenset({"create_map", "save_map", "cluster_map", "heatmap_map"})

# Matplotlib chart helpers live in the full-featured ``visualization`` module
# (they support path=/horizontal= kwargs and include box_plot/quality_dashboard),
# which supersedes the trimmed versions in the analysis monolith.
_VIZ_FULL_NAMES = frozenset({
    "histogram",
    "bar_chart",
    "box_plot",
    "correlation_heatmap",
    "time_series_chart",
    "quality_dashboard",
})

# Submodule routing for symbols not in the analysis.py monolith
_SUBMODULE_MAP: dict[str, str] = {
    # sla_tracking
    "SLATarget": "socrata_toolkit.sla_tracking",
    "compute_cycle_times": "socrata_toolkit.sla_tracking",
    "compute_sla_metrics": "socrata_toolkit.sla_tracking",
    "flag_sla_violations": "socrata_toolkit.sla_tracking",
    # freshness
    "AlertSeverity": "socrata_toolkit.freshness",
    "DatasetFreshness": "socrata_toolkit.freshness",
    "FreshnessAlert": "socrata_toolkit.freshness",
    "FreshnessTracker": "socrata_toolkit.freshness",
    # metrics
    "DataQualityMetrics": "socrata_toolkit.metrics",
    "MetricPoint": "socrata_toolkit.metrics",
    "MetricsRegistry": "socrata_toolkit.metrics",
    "PipelineMetrics": "socrata_toolkit.metrics",
    "get_global_registry": "socrata_toolkit.metrics",
    "reset_global_registry": "socrata_toolkit.metrics",
    # plotly_charts
    "borough_bar_chart": "socrata_toolkit.plotly_charts",
    "contract_gantt": "socrata_toolkit.plotly_charts",
    "kpi_gauge": "socrata_toolkit.plotly_charts",
    "priority_heatmap": "socrata_toolkit.plotly_charts",
    "save_chart": "socrata_toolkit.plotly_charts",
    "status_donut": "socrata_toolkit.plotly_charts",
    "trend_line": "socrata_toolkit.plotly_charts",
    # quality subpackage
    "BusinessRulesEngine": "socrata_toolkit.quality.rules",
    "QualityRule": "socrata_toolkit.quality.rules",
    "RuleMode": "socrata_toolkit.quality.rules",
    "RuleSeverity": "socrata_toolkit.quality.rules",
    "RuleViolations": "socrata_toolkit.quality.rules",
    "create_311_complaints_rules": "socrata_toolkit.quality.rules",
    "create_sidewalk_rules": "socrata_toolkit.quality.rules",
    "Anomaly": "socrata_toolkit.quality.anomalies",
    "AnomalyDetector": "socrata_toolkit.quality.anomalies",
    "AnomalyReport": "socrata_toolkit.quality.anomalies",
    "AnomalySeverity": "socrata_toolkit.quality.anomalies",
    "DataType": "socrata_toolkit.quality.profiler",
    "DriftReport": "socrata_toolkit.quality.profiler",
    "ProfileGenerator": "socrata_toolkit.quality.profiler",
    "Expectation": "socrata_toolkit.quality.expectations",
    "ExpectationSuite": "socrata_toolkit.quality.expectations",
    "ExpectationType": "socrata_toolkit.quality.expectations",
    "SeverityLevel": "socrata_toolkit.quality.expectations",
    "create_sidewalk_inspections_suite": "socrata_toolkit.quality.expectations",
    "create_311_complaints_suite": "socrata_toolkit.quality.expectations",
    "MetricType": "socrata_toolkit.quality.sla",
    "DataQualityTracker": "socrata_toolkit.quality.sla",
    "Severity": "socrata_toolkit.quality.sla",
    "TrendDirection": "socrata_toolkit.quality.sla",
    "SLADefinition": "socrata_toolkit.quality.sla",
    "create_standard_slas": "socrata_toolkit.quality.sla",
    "DatasetQualityScore": "socrata_toolkit.quality.catalog",
    "DataQualityCatalog": "socrata_toolkit.quality.catalog",
    "QualityReportGenerator": "socrata_toolkit.quality.reports",
    "QualityValidator": "socrata_toolkit.quality.validator",
    "ValidationResult": "socrata_toolkit.quality.validator",
    "ValidationResultsAggregator": "socrata_toolkit.quality.validator",
    # relevance
    "build_weighted_rank_sql": "socrata_toolkit.relevance",
    "websearch_to_tsquery_sql": "socrata_toolkit.relevance",
    # program_metrics (also re-exported via analysis)
    "compute_program_dashboard": "socrata_toolkit.program_metrics",
}


def __getattr__(name: str):
    if name in _VIZ_MAP_NAMES:
        from socrata_toolkit.viz import map as _viz_map

        return getattr(_viz_map, name)
    if name in _VIZ_FULL_NAMES:
        from socrata_toolkit import visualization as _viz

        return getattr(_viz, name)
    if name in _SUBMODULE_MAP:
        import importlib
        mod = importlib.import_module(_SUBMODULE_MAP[name])
        return getattr(mod, name)
    return getattr(_monolith, name)


def __dir__():
    return sorted(set(dir(_monolith) + list(globals().keys())))
