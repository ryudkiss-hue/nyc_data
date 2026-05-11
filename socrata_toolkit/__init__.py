# socrata_toolkit/__init__.py
"""Socrata Toolkit package public exports with lazy imports."""

from importlib import import_module
from typing import Dict, List, TYPE_CHECKING

__version__ = "0.2.0"

# Map public symbol name -> "module:attr" where attr can be a name or omitted to import module
_lazy_map: Dict[str, str] = {
    # core client and models
    "SocrataClient": "client:SocrataClient",
    "SocrataConfig": "client:SocrataConfig",
    "DatasetMetadata": "models:DatasetMetadata",
    "SearchResult": "models:SearchResult",
    # analysis
    "DataProfile": "analysis:DataProfile",
    "profile_dataframe": "analysis:profile_dataframe",
    "quality_report": "analysis:quality_report",
    # text analytics / nlp
    "generate_text_insights": "text_analytics:generate_text_insights",
    "analyze_text": "nlp_advanced:analyze_text",
    "translate_text": "nlp_advanced:translate_text",
    "preprocess_text": "nlp_advanced:preprocess_text",
    # spatial
    "spatial_intersects_join": "spatial:spatial_intersects_join",
    "SpatialJoinResult": "spatial:SpatialJoinResult",
    # llm bridge
    "LLMAugmentConfig": "llm_duck_bridge:LLMAugmentConfig",
    "augment_dataframe_with_llm": "llm_duck_bridge:augment_dataframe_with_llm",
    # dot_sidewalk
    "compute_sidewalk_kpis": "dot_sidewalk:compute_sidewalk_kpis",
    "sql_templates": "dot_sidewalk:sql_templates",
    "python_templates": "dot_sidewalk:python_templates",
    # alerts
    "AlertManager": "alerts:AlertManager",
    "CLINotifier": "alerts:CLINotifier",
    "EmailNotifier": "alerts:EmailNotifier",
    "DBNotifier": "alerts:DBNotifier",
    "Alert": "alerts:Alert",
    # ops and compliance
    "apply_grace_period_updates": "ops:apply_grace_period_updates",
    "permit_lookahead_sql": "ops:permit_lookahead_sql",
    "generate_burndown": "ops:generate_burndown",
    "flag_high_priority_trigger_sql": "ops:flag_high_priority_trigger_sql",
    "check_dcwp_license": "compliance:check_dcwp_license",
    "check_parks_permit": "compliance:check_parks_permit",
    "validate_contractor_for_list": "compliance:validate_contractor_for_list",
    # relevance and search helpers
    "build_weighted_rank_sql": "relevance:build_weighted_rank_sql",
    "websearch_to_tsquery_sql": "relevance:websearch_to_tsquery_sql",
    # conflict resolution and db helpers
    "ConflictResolver": "conflict:ConflictResolver",
    "PostGISConflictResolver": "conflict:PostGISConflictResolver",
    "ensure_fts_index": "db_helpers:ensure_fts_index",
    "build_fts_index_sql": "db_helpers:build_fts_index_sql",
    # advanced analysis
    "detect_outliers_iqr": "analysis_advanced:detect_outliers_iqr",
    "detect_outliers_zscore": "analysis_advanced:detect_outliers_zscore",
    "detect_all_outliers": "analysis_advanced:detect_all_outliers",
    "correlation_analysis": "analysis_advanced:correlation_analysis",
    "time_series_summary": "analysis_advanced:time_series_summary",
    "classify_distribution": "analysis_advanced:classify_distribution",
    "classify_all_distributions": "analysis_advanced:classify_all_distributions",
    "flag_anomalies": "analysis_advanced:flag_anomalies",
    # visualization
    "histogram": "visualization:histogram",
    "bar_chart": "visualization:bar_chart",
    "correlation_heatmap": "visualization:correlation_heatmap",
    "time_series_chart": "visualization:time_series_chart",
    "box_plot": "visualization:box_plot",
    "quality_dashboard": "visualization:quality_dashboard",
    # governance
    "create_lineage": "governance:create_lineage",
    "AuditLogger": "governance:AuditLogger",
    "compute_quality_score": "governance:compute_quality_score",
    "detect_schema_drift": "governance:detect_schema_drift",
    "snapshot_schema": "governance:snapshot_schema",
    "apply_retention_policy": "governance:apply_retention_policy",
}

# Public API list for "from socrata_toolkit import *"
__all__ = [
    "SocrataClient",
    "SocrataConfig",
    "DatasetMetadata",
    "SearchResult",
    "DataProfile",
    "profile_dataframe",
    "quality_report",
    "generate_text_insights",
    "analyze_text",
    "translate_text",
    "preprocess_text",
    "spatial_intersects_join",
    "SpatialJoinResult",
    "LLMAugmentConfig",
    "augment_dataframe_with_llm",
    "compute_sidewalk_kpis",
    "sql_templates",
    "python_templates",
    "AlertManager",
    "CLINotifier",
    "EmailNotifier",
    "DBNotifier",
    "Alert",
    "apply_grace_period_updates",
    "permit_lookahead_sql",
    "generate_burndown",
    "flag_high_priority_trigger_sql",
    "check_dcwp_license",
    "check_parks_permit",
    "validate_contractor_for_list",
    "build_weighted_rank_sql",
    "websearch_to_tsquery_sql",
    "ConflictResolver",
    "PostGISConflictResolver",
    "ensure_fts_index",
    "build_fts_index_sql",
    # advanced analysis
    "detect_outliers_iqr",
    "detect_outliers_zscore",
    "detect_all_outliers",
    "correlation_analysis",
    "time_series_summary",
    "classify_distribution",
    "classify_all_distributions",
    "flag_anomalies",
    # visualization
    "histogram",
    "bar_chart",
    "correlation_heatmap",
    "time_series_chart",
    "box_plot",
    "quality_dashboard",
    # governance
    "create_lineage",
    "AuditLogger",
    "compute_quality_score",
    "detect_schema_drift",
    "snapshot_schema",
    "apply_retention_policy",
]



# Cache for loaded attributes
_loaded_cache: Dict[str, object] = {}

if TYPE_CHECKING:
    # For type checkers, import names so static analysis works.
    # These imports are only evaluated by type checkers and not at runtime.
    from .client import SocrataClient, SocrataConfig  # noqa: F401
    from .models import DatasetMetadata, SearchResult  # noqa: F401
    from .analysis import DataProfile, profile_dataframe, quality_report  # noqa: F401
    from .text_analytics import generate_text_insights  # noqa: F401
    from .nlp_advanced import analyze_text, translate_text, preprocess_text  # noqa: F401
    from .spatial import spatial_intersects_join, SpatialJoinResult  # noqa: F401
    from .llm_duck_bridge import LLMAugmentConfig, augment_dataframe_with_llm  # noqa: F401
    from .dot_sidewalk import compute_sidewalk_kpis, sql_templates, python_templates  # noqa: F401
    from .alerts import AlertManager, CLINotifier, EmailNotifier, DBNotifier, Alert  # noqa: F401
    from .ops import apply_grace_period_updates, permit_lookahead_sql, generate_burndown, flag_high_priority_trigger_sql  # noqa: F401
    from .compliance import check_dcwp_license, check_parks_permit, validate_contractor_for_list  # noqa: F401
    from .relevance import build_weighted_rank_sql, websearch_to_tsquery_sql  # noqa: F401
    from .conflict import ConflictResolver, PostGISConflictResolver  # noqa: F401
    from .db_helpers import ensure_fts_index, build_fts_index_sql  # noqa: F401
    from .analysis_advanced import (  # noqa: F401
        detect_outliers_iqr,
        detect_outliers_zscore,
        detect_all_outliers,
        correlation_analysis,
        time_series_summary,
        classify_distribution,
        classify_all_distributions,
        flag_anomalies,
    )
    from .visualization import (  # noqa: F401
        histogram,
        bar_chart,
        correlation_heatmap,
        time_series_chart,
        box_plot,
        quality_dashboard,
    )
    from .governance import (  # noqa: F401
        create_lineage,
        AuditLogger,
        compute_quality_score,
        detect_schema_drift,
        snapshot_schema,
        apply_retention_policy,
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
        # Provide a clearer error message for optional deps
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

def available_loaded() -> List[str]:
    """Return the list of symbols already loaded into the package namespace."""
    return list(_loaded_cache.keys())
