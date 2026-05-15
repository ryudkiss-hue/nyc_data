# socrata_toolkit/__init__.py
"""Socrata Toolkit package public exports with lazy imports (Pillar Architecture)."""

from importlib import import_module
from typing import TYPE_CHECKING

__version__ = "0.3.0"

# Map public symbol name -> "module:attr" where attr can be a name or omitted to import module
_lazy_map: dict[str, str] = {
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
    "compute_borough_metrics": "analysis:compute_borough_metrics",
    "compute_sla_trends": "analysis:compute_sla_trends",
    "generate_analysis_results": "analysis:generate_analysis_results",
    "generate_executive_briefing_automated": "analysis:generate_executive_briefing_automated",
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
    "quality_report": "analysis:quality_report",
    "DashboardSummary": "analysis:DashboardSummary",
    # viz (Pillar: viz) - Consolidated into analysis
    "histogram": "analysis:histogram",
    "bar_chart": "analysis:bar_chart",
    "correlation_heatmap": "analysis:correlation_heatmap",
    "time_series_chart": "analysis:time_series_chart",
    "sunburst_chart": "analysis:sunburst_chart",
    "treemap_chart": "analysis:treemap_chart",
    "gauge_chart": "analysis:gauge_chart",
    "animated_scatter_chart": "analysis:animated_scatter_chart",
    "violin_plot": "analysis:violin_plot",
    "quality_radar_chart": "analysis:quality_radar_chart",
    "generate_semantic_network_map": "analysis:generate_semantic_network_map",
    "hotspot_density_mapbox": "analysis:hotspot_density_mapbox",
    "material_breakdown_pie_chart": "analysis:material_breakdown_pie_chart",
    "material_borough_subplots": "analysis:material_borough_subplots",
    "operations_gantt_chart": "analysis:operations_gantt_chart",
    "triage_funnel_chart": "analysis:triage_funnel_chart",
    "plot_sidewalk_anatomy": "analysis:plot_sidewalk_anatomy",
    "plot_ada_compliance_map": "analysis:plot_ada_compliance_map",
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
    "estimate_costs": "engineering:estimate_costs",
    "summarize_costs": "engineering:summarize_costs",
    "CostSummary": "engineering:CostSummary",
    # spatial (Pillar: spatial)
    "BoundingBox": "spatial:BoundingBox",
    "geometry_bounds": "spatial:geometry_bounds",
    "geometry_area": "spatial:geometry_area",
    "geometry_length": "spatial:geometry_length",
    "geometry_centroid": "spatial:geometry_centroid",
    "union_geometries": "spatial:union_geometries",
    "validate_geometry": "spatial:validate_geometry",
    "spatial_join_candidates": "spatial:spatial_join_candidates",
    # pipeline (Pillar: pipeline)
    "stream_pipeline": "pipeline:stream_pipeline",
    "ingest_311_complaints": "pipeline:ingest_311_complaints",
    "deduplicate_dataframe": "pipeline:deduplicate_dataframe",
    "Workflow": "pipeline:Workflow",
    "WorkflowStep": "pipeline:WorkflowStep",
    # governance (Pillar: governance)
    "compute_quality_score": "governance:compute_quality_score",
    "AlertManager": "governance:AlertManager",
    "GovernanceProcessor": "governance:GovernanceProcessor",
    "AuditLogger": "governance:AuditLogger",
    "create_lineage": "governance:create_lineage",
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
    "SocrataClient",
    "SocrataConfig",
    "DatasetMetadata",
    "SearchResult",
    "DuckDBExporter",
    "DuckDBManager",
    "DuckDBRepository",
    "ensure_fts_index",
    "SchemaRegistry",
    "SchemaValidator",
    "search_nyc_datasets",
    "generate_data_dictionary",
    "SoQLBuilder",
    # analysis
    "DataProfile",
    "profile_dataframe",
    "MetricsTracker",
    "compute_program_dashboard",
    "compute_borough_metrics",
    "compute_sla_trends",
    "generate_analysis_results",
    "generate_executive_briefing_automated",
    "detect_outliers_iqr",
    "detect_outliers_zscore",
    "detect_all_outliers",
    "correlation_analysis",
    "time_series_summary",
    "classify_distribution",
    "classify_all_distributions",
    "flag_anomalies",
    "detect_anomalies",
    "detect_data_drift",
    "quality_report",
    "DashboardSummary",
    # viz
    "histogram",
    "bar_chart",
    "correlation_heatmap",
    "time_series_chart",
    "sunburst_chart",
    "treemap_chart",
    "gauge_chart",
    "animated_scatter_chart",
    "violin_plot",
    "quality_radar_chart",
    "generate_semantic_network_map",
    "hotspot_density_mapbox",
    "material_breakdown_pie_chart",
    "material_borough_subplots",
    "operations_gantt_chart",
    "triage_funnel_chart",
    "plot_sidewalk_anatomy",
    "plot_ada_compliance_map",
    # engineering
    "compute_sidewalk_kpis",
    "prioritize_construction_list",
    "classify_scope",
    "flag_ada_locations",
    "summarize_construction_list",
    "analyze_contract_progress",
    "budget_analysis",
    "productivity_metrics",
    "project_spending",
    "calculate_completion_dates",
    "burndown_calculation",
    "calculate_roi_spot_vs_block",
    "enforce_smart_contract_slas",
    "simulate_contractor_bids",
    "estimate_costs",
    "summarize_costs",
    "CostSummary",
    # spatial
    "BoundingBox",
    "geometry_bounds",
    "geometry_area",
    "geometry_length",
    "geometry_centroid",
    "union_geometries",
    "validate_geometry",
    "spatial_join_candidates",
    # pipeline
    "stream_pipeline",
    "ingest_311_complaints",
    "deduplicate_dataframe",
    "Workflow",
    "WorkflowStep",
    # governance
    "compute_quality_score",
    "AlertManager",
    "GovernanceProcessor",
    "AuditLogger",
    "create_lineage",
    # ai
    "sentiment_score",
    "enrich_construction_list",
    "SocrataLLMChatbot",
    "SQLQueryEngine",
    "LegalPolicyEngine",
    "quantum_search",
    # api
    "api",
]

# Cache for loaded attributes
_loaded_cache: dict[str, object] = {}

if TYPE_CHECKING:
    from . import api  # noqa: F401
    from .ai import (  # noqa: F401
        LegalPolicyEngine,
        SocrataLLMChatbot,
        SQLQueryEngine,
        enrich_construction_list,
        quantum_search,
        sentiment_score,
    )
    from .analysis import (  # noqa: F401
        DashboardSummary,
        DataProfile,
        MetricsTracker,
        classify_all_distributions,
        classify_distribution,
        compute_borough_metrics,
        compute_program_dashboard,
        compute_sla_trends,
        correlation_analysis,
        detect_all_outliers,
        detect_anomalies,
        detect_data_drift,
        detect_outliers_iqr,
        detect_outliers_zscore,
        flag_anomalies,
        generate_analysis_results,
        generate_executive_briefing_automated,
        profile_dataframe,
        quality_report,
        time_series_summary,
    )
    from .core import (  # noqa: F401
        DatasetMetadata,
        DuckDBExporter,
        DuckDBManager,
        DuckDBRepository,
        SchemaRegistry,
        SchemaValidator,
        SearchResult,
        SocrataClient,
        SocrataConfig,
        SoQLBuilder,
        ensure_fts_index,
        generate_data_dictionary,
        search_nyc_datasets,
    )
    from .engineering import (  # noqa: F401
        CostSummary,
        analyze_contract_progress,
        budget_analysis,
        burndown_calculation,
        calculate_completion_dates,
        calculate_roi_spot_vs_block,
        classify_scope,
        compute_material_aware_kpis,
        compute_sidewalk_kpis,
        enforce_smart_contract_slas,
        estimate_costs,
        flag_ada_locations,
        prioritize_construction_list,
        productivity_metrics,
        project_spending,
        simulate_contractor_bids,
        summarize_construction_list,
        summarize_costs,
    )
    from .governance import (  # noqa: F401
        AlertManager,
        AuditLogger,
        GovernanceProcessor,
        compute_quality_score,
        create_lineage,
    )
    from .pipeline import (  # noqa: F401
        CDCEvent,
        ExcelWorkbookBuilder,
        Workflow,
        WorkflowStep,
        deduplicate_dataframe,
        ingest_311_complaints,
        stream_pipeline,
    )
    from .spatial import (  # noqa: F401
        BoundingBox,
        geometry_area,
        geometry_bounds,
        geometry_centroid,
        geometry_length,
        spatial_join_candidates,
        union_geometries,
        validate_geometry,
    )
    from .viz.charts import (  # noqa: F401
        animated_scatter_chart,
        bar_chart,
        correlation_heatmap,
        export_plotly_figure,
        gauge_chart,
        generate_semantic_network_map,
        histogram,
        hotspot_density_mapbox,
        material_borough_subplots,
        material_breakdown_pie_chart,
        operations_gantt_chart,
        plot_ada_compliance_map,
        plot_sidewalk_anatomy,
        quality_radar_chart,
        sunburst_chart,
        time_series_chart,
        treemap_chart,
        triage_funnel_chart,
        violin_plot,
    )


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


def available_exports() -> list[str]:
    """Return the list of public symbols that are defined in __all__."""
    return list(__all__)


"""Visualization and charting components for the NYC DOT Toolkit."""
