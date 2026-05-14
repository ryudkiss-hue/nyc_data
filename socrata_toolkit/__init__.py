# socrata_toolkit/__init__.py
"""Socrata Toolkit package public exports with lazy imports (Pillar Architecture)."""

from importlib import import_module
from typing import Dict, List, TYPE_CHECKING

__version__ = "0.3.0"

# Map public symbol name -> "module:attr" where attr can be a name or omitted to import module
_lazy_map: Dict[str, str] = {
    # core (Pillar: core)
    "SocrataClient": "core:SocrataClient",
    "SocrataConfig": "core:SocrataConfig",
    "DatasetMetadata": "core:DatasetMetadata",
    "SearchResult": "core:SearchResult",
    "DuckDBExporter": "core:DuckDBExporter",
    "DuckDBManager": "core:DuckDBManager",
    "DuckDBRepository": "core:DuckDBRepository",
    "ensure_fts_index": "core:ensure_fts_index",
    "SchemaRegistry": "core:SchemaRegistry",
    "SchemaValidator": "core:SchemaValidator",
    "search_nyc_datasets": "core:search_nyc_datasets",
    "generate_data_dictionary": "core:generate_data_dictionary",
    "SoQLBuilder": "core:SoQLBuilder",

    # analysis (Pillar: analysis)
    "DataProfile": "analysis:DataProfile",
    "profile_dataframe": "analysis:profile_dataframe",
    "MetricsTracker": "analysis:MetricsTracker",
    "compute_program_dashboard": "analysis:compute_program_dashboard",
    "histogram": "analysis:histogram",
    "bar_chart": "analysis:bar_chart",
    "correlation_heatmap": "analysis:correlation_heatmap",
    "compute_borough_metrics": "analysis:compute_borough_metrics",
    "compute_sla_trends": "analysis:compute_sla_trends",
    "time_series_chart": "analysis:time_series_chart",
    "sunburst_chart": "analysis:sunburst_chart",
    "treemap_chart": "analysis:treemap_chart",
    "gauge_chart": "analysis:gauge_chart",
    "animated_scatter_chart": "analysis:animated_scatter_chart",
    "violin_plot": "analysis:violin_plot",
    "quality_radar_chart": "analysis:quality_radar_chart",
    "generate_analysis_results": "analysis:generate_analysis_results",
    "generate_executive_briefing_automated": "analysis:generate_executive_briefing_automated",
    "generate_semantic_network_map": "analysis:generate_semantic_network_map",
    "detect_outliers_iqr": "analysis:detect_outliers_iqr",
    "detect_outliers_zscore": "analysis:detect_outliers_zscore",
    "detect_all_outliers": "analysis:detect_all_outliers",
    "correlation_analysis": "analysis:correlation_analysis",
    "time_series_summary": "analysis:time_series_summary",
    "classify_distribution": "analysis:classify_distribution",
    "classify_all_distributions": "analysis:classify_all_distributions",
    "flag_anomalies": "analysis:flag_anomalies",
    "detect_anomalies": "analysis:detect_anomalies",
    "detect_data_drift": "analysis:detect_data_drift",

    # engineering (Pillar: engineering)
    "compute_sidewalk_kpis": "engineering:compute_sidewalk_kpis",
    "prioritize_construction_list": "engineering:prioritize_construction_list",
    "classify_scope": "engineering:classify_scope",
    "flag_ada_locations": "engineering:flag_ada_locations",
    "summarize_construction_list": "engineering:summarize_construction_list",
    "analyze_contract_progress": "engineering:analyze_contract_progress",
    "budget_analysis": "engineering:budget_analysis",
    "productivity_metrics": "engineering:productivity_metrics",
    "project_spending": "engineering:project_spending",
    "calculate_completion_dates": "engineering:calculate_completion_dates",
    "calculate_roi_spot_vs_block": "engineering:calculate_roi_spot_vs_block",
    "enforce_smart_contract_slas": "engineering:enforce_smart_contract_slas",
    "simulate_contractor_bids": "engineering:simulate_contractor_bids",
    "burndown_calculation": "engineering:burndown_calculation",

    # spatial (Pillar: spatial)
    "spatial_intersects_join": "spatial:spatial_intersects_join",
    "cluster_locations": "spatial:cluster_locations",
    "detect_construction_conflicts": "spatial:detect_construction_conflicts",
    "create_geopackage": "spatial:create_geopackage",
    "load_geopackage": "spatial:load_geopackage",
    "generate_qgs_project": "spatial:generate_qgs_project",

    # pipeline (Pillar: pipeline)
    "stream_pipeline": "pipeline:stream_pipeline",
    "ingest_311_complaints": "pipeline:ingest_311_complaints",
    "deduplicate_dataframe": "pipeline:deduplicate_dataframe",
    "generate_program_report": "pipeline:generate_program_report",
    "Workflow": "pipeline:Workflow",
    "WorkflowStep": "pipeline:WorkflowStep",

    # governance (Pillar: governance)
    "compute_quality_score": "governance:compute_quality_score",
    "AlertManager": "governance:AlertManager",

    # ai (Pillar: ai)
    "sentiment_score": "ai:sentiment_score",
    "enrich_construction_list": "ai:enrich_construction_list",
    "SocrataLLMChatbot": "ai:SocrataLLMChatbot",
    "SQLQueryEngine": "ai:SQLQueryEngine",
    "LegalPolicyEngine": "ai:LegalPolicyEngine",
    "quantum_search": "ai:quantum_search",
    "api": "api",
}

# Public API list for "from socrata_toolkit import *"
__all__ = [
    # core
    "SocrataClient", "SocrataConfig", "DatasetMetadata", "SearchResult",
    "DuckDBExporter", "DuckDBManager", "DuckDBRepository", "ensure_fts_index",
    "SchemaRegistry", "SchemaValidator", "search_nyc_datasets",
    "generate_data_dictionary", "SoQLBuilder",
    # analysis
    "DataProfile", "profile_dataframe", "MetricsTracker", "compute_program_dashboard",
    "histogram", "bar_chart", "correlation_heatmap", "compute_borough_metrics",
    "compute_sla_trends", "time_series_chart", "sunburst_chart", "treemap_chart",
    "gauge_chart", "animated_scatter_chart", "generate_analysis_results",
    "violin_plot", "quality_radar_chart",
    "generate_executive_briefing_automated",
    "generate_semantic_network_map",
    "detect_outliers_iqr", "detect_outliers_zscore", "detect_all_outliers",
    "correlation_analysis", "time_series_summary", "classify_distribution",
    "classify_all_distributions", "flag_anomalies", "detect_anomalies",
    "detect_data_drift",
    # engineering
    "compute_sidewalk_kpis", "prioritize_construction_list", "classify_scope",
    "flag_ada_locations", "summarize_construction_list", "analyze_contract_progress",
    "budget_analysis", "productivity_metrics", "project_spending",
    "calculate_completion_dates", "burndown_calculation",
    "calculate_roi_spot_vs_block", "enforce_smart_contract_slas", "simulate_contractor_bids",
    # spatial
    "spatial_intersects_join", "cluster_locations", "detect_construction_conflicts",
    "create_geopackage", "load_geopackage", "generate_qgs_project",
    # pipeline
    "stream_pipeline", "ingest_311_complaints", "deduplicate_dataframe",
    "generate_program_report", "Workflow", "WorkflowStep",
    # governance
    "compute_quality_score", "AlertManager",
    # ai
    "sentiment_score", "enrich_construction_list", "SocrataLLMChatbot",
    "SQLQueryEngine", "LegalPolicyEngine", "quantum_search",
    # api
    "api"
]

# Cache for loaded attributes
_loaded_cache: Dict[str, object] = {}

if TYPE_CHECKING:
    from .core import SocrataClient, SocrataConfig, DatasetMetadata, SearchResult  # noqa: F401
    from .analysis import DataProfile, profile_dataframe, quality_report  # noqa: F401
    from .engineering import compute_material_aware_kpis, estimate_costs  # noqa: F401
    from .spatial import spatial_intersects_join, SpatialIndex  # noqa: F401
    from .pipeline import stream_pipeline, CDCEvent, ExcelWorkbookBuilder  # noqa: F401
    from .governance import GovernanceProcessor, compute_quality_score  # noqa: F401
    from .ai import sentiment_score, enrich_construction_list  # noqa: F401

def _import_target(target: str):
    """Import a target string like 'module:attr' or 'module' and return the attribute/module."""
    if ":" in target:
        module_name, attr = target.split(":", 1)
    else:
        module_name, attr = target, None
    module = import_module(f".{module_name}", package=__name__)
    return getattr(module, attr) if attr else module

def __getattr__(name: str):
    """Lazy-load public symbols on attribute access."""
    if name in _loaded_cache:
        return _loaded_cache[name]

    if name not in _lazy_map:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    target = _lazy_map[name]
    try:
        obj = _import_target(target)
    except Exception as exc:
        msg = (
            f"Failed to import {name!r} from {target!r}. "
            "This may be because an optional dependency is not installed or "
            "because the module raised an error during import. "
            f"Original error: {exc!r}"
        )
        raise ImportError(msg) from exc

    _loaded_cache[name] = obj
    globals()[name] = obj
    return obj

def available_exports() -> List[str]:
    """Return the list of public symbols that are defined in __all__."""
    return list(__all__)
