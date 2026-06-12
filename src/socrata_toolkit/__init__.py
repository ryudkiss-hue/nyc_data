# socrata_toolkit/__init__.py
"""Socrata Toolkit package public exports with lazy imports (Pillar Architecture)."""

from importlib import import_module
from typing import TYPE_CHECKING

__version__ = "0.5.0"

# Map public symbol name -> "module:attr" where attr can be a name or omitted to import module
_lazy_map: dict[str, str] = {
    # core (Pillar: core)
    "SocrataClient": "core:SocrataClient",
    "SocrataConfig": "core:SocrataConfig",
    "DatasetMetadata": "core.models:DatasetMetadata",
    "SearchResult": "core.models:SearchResult",
    "DuckDBExporter": "core:DuckDBExporter",
    "DuckDBManager": "core:DuckDBManager",
    "DuckDBRepository": "core:DuckDBRepository",
    "ensure_fts_index": "core.db_helpers:ensure_fts_index",
    "SchemaRegistry": "core:SchemaRegistry",
    "SchemaValidator": "core:SchemaValidator",
    "search_nyc_datasets": "core:search_nyc_datasets",
    "SoQLBuilder": "core:SoQLBuilder",

    # analysis (Pillar: analysis - Refactored)
    "DataProfile": "analysis:DataProfile",
    "profile_dataframe": "analysis:profile_dataframe",
    "quality_report": "analysis:quality_report",
    "InsightsEngine": "analysis:InsightsEngine",
    "InsightsReport": "analysis:InsightsReport",
    "generate_insights": "analysis:generate_insights",
    "BayesianRegressionEngine": "analysis:BayesianRegressionEngine",
    "BayesianInferenceResult": "analysis:BayesianInferenceResult",
    "compute_sla_metrics": "analysis:compute_sla_metrics",
    "compute_borough_metrics": "analysis:compute_borough_metrics",
    "compute_sla_trends": "analysis:compute_sla_trends",
    "flag_sla_violations": "analysis:flag_sla_violations",
    "Report": "analysis:Report",

    # engineering (Pillar: engineering)
    "AssetCondition": "engineering:AssetCondition",
    "MarkovDeteriorationModel": "engineering:MarkovDeteriorationModel",
    "LifeCycleCostAnalysis": "engineering:LifeCycleCostAnalysis",
    "NYSDOTPavementEngine": "engineering:NYSDOTPavementEngine",
    "GeometricAuditResult": "material:GeometricAuditResult",
    "run_vision_zero_audit": "material:run_vision_zero_audit",

    # ... (other mappings remain consistent)
}

# Public API list
__all__ = [
    "SocrataClient",
    "SocrataConfig",
    "DataProfile",
    "profile_dataframe",
    "InsightsEngine",
    "InsightsReport",
    "generate_insights",
    "BayesianRegressionEngine",
    "AssetCondition",
    "MarkovDeteriorationModel",
    "LifeCycleCostAnalysis",
    "NYSDOTPavementEngine",
    "run_vision_zero_audit",
    "Report",
]

# Cache for loaded attributes
_loaded_cache: dict[str, object] = {}

if TYPE_CHECKING:
    from . import api  # noqa: F401
    from .alerts.rules import Alert, Rule, RulesEngine  # noqa: F401
    from .analysis import (  # noqa: F401
        DashboardSummary,
        DataProfile,
        InsightsReport,
        MetricsTracker,
        SLATarget,
        classify_all_distributions,
        classify_distribution,
        compute_borough_metrics,
        compute_cycle_times,
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
        generate_insights,
        generate_semantic_network_map,
        list_available_visualizations,
        profile_dataframe,
        quality_report,
        smart_recommendations,
        time_series_summary,
    )
    from .core import (  # noqa: F401
        DATASETS,
        DataDictionary,
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
        list_available_datasets,
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
    from .viz import (  # noqa: F401
        animated_scatter_chart,
        bar_chart,
        correlation_heatmap,
        data_completeness_chart,
        gauge_chart,
        histogram,
        hotspot_density_mapbox,
        material_borough_subplots,
        material_breakdown_pie_chart,
        metric_status_pie_chart,
        operations_gantt_chart,
        plot_ada_compliance_map,
        plot_geospatial_compliance_map,
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
    # Special case: _analysis_monolith for test mocking
    if name == "_analysis_monolith":
        from .analysis import _monolith
        return _monolith

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
