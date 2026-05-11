# socrata_toolkit/__init__.py
"""Socrata Toolkit package public exports with lazy imports."""

from importlib import import_module
from typing import Dict, List, TYPE_CHECKING

__version__ = "0.3.0"

# Map public symbol name -> "module:attr" where attr can be a name or omitted to import module
_lazy_map: Dict[str, str] = {
    # core client and models
    "SocrataClient": "core.client:SocrataClient",
    "SocrataConfig": "core.client:SocrataConfig",
    "DatasetMetadata": "core.models:DatasetMetadata",
    "SearchResult": "core.models:SearchResult",
    # analysis
    "DataProfile": "analysis.core:DataProfile",
    "profile_dataframe": "analysis.core:profile_dataframe",
    "quality_report": "analysis.core:quality_report",
    # text analytics / nlp
    "generate_text_insights": "analysis.text:generate_text_insights",
    "analyze_text": "nlp.advanced:analyze_text",
    "translate_text": "nlp.advanced:translate_text",
    "preprocess_text": "nlp.advanced:preprocess_text",
    # spatial
    "spatial_intersects_join": "spatial.core:spatial_intersects_join",
    "SpatialJoinResult": "spatial.core:SpatialJoinResult",
    # llm bridge
    "LLMAugmentConfig": "llm.duck_bridge:LLMAugmentConfig",
    "augment_dataframe_with_llm": "llm.duck_bridge:augment_dataframe_with_llm",
    # dot_sidewalk (engineering)
    "compute_sidewalk_kpis": "engineering.dot_sidewalk:compute_sidewalk_kpis",
    "sql_templates": "engineering.dot_sidewalk:sql_templates",
    "python_templates": "engineering.dot_sidewalk:python_templates",
    # alerts
    "AlertManager": "alerts.manager:AlertManager",
    "CLINotifier": "alerts.manager:CLINotifier",
    "EmailNotifier": "alerts.manager:EmailNotifier",
    "DBNotifier": "alerts.manager:DBNotifier",
    "Alert": "alerts.manager:Alert",
    # ops and compliance
    "apply_grace_period_updates": "ops.core:apply_grace_period_updates",
    "permit_lookahead_sql": "ops.core:permit_lookahead_sql",
    "generate_burndown": "ops.core:generate_burndown",
    "flag_high_priority_trigger_sql": "ops.core:flag_high_priority_trigger_sql",
    "check_dcwp_license": "governance.compliance:check_dcwp_license",
    "check_parks_permit": "governance.compliance:check_parks_permit",
    "validate_contractor_for_list": "governance.compliance:validate_contractor_for_list",
    # relevance and search helpers
    "build_weighted_rank_sql": "analysis.relevance:build_weighted_rank_sql",
    "websearch_to_tsquery_sql": "analysis.relevance:websearch_to_tsquery_sql",
    # conflict resolution and db helpers
    "ConflictResolver": "sql.conflict:ConflictResolver",
    "PostGISConflictResolver": "sql.conflict:PostGISConflictResolver",
    "ensure_fts_index": "core.db_helpers:ensure_fts_index",
    "build_fts_index_sql": "core.db_helpers:build_fts_index_sql",
    # advanced analysis
    "detect_outliers_iqr": "analysis.advanced:detect_outliers_iqr",
    "detect_outliers_zscore": "analysis.advanced:detect_outliers_zscore",
    "detect_all_outliers": "analysis.advanced:detect_all_outliers",
    "correlation_analysis": "analysis.advanced:correlation_analysis",
    "time_series_summary": "analysis.advanced:time_series_summary",
    "classify_distribution": "analysis.advanced:classify_distribution",
    "classify_all_distributions": "analysis.advanced:classify_all_distributions",
    "flag_anomalies": "analysis.advanced:flag_anomalies",
    # visualization
    "histogram": "viz.core:histogram",
    "bar_chart": "viz.core:bar_chart",
    "correlation_heatmap": "viz.core:correlation_heatmap",
    "time_series_chart": "viz.core:time_series_chart",
    "box_plot": "viz.core:box_plot",
    "quality_dashboard": "viz.core:quality_dashboard",
    # governance
    "create_lineage": "governance.core:create_lineage",
    "AuditLogger": "governance.core:AuditLogger",
    "compute_quality_score": "governance.core:compute_quality_score",
    "detect_schema_drift": "governance.core:detect_schema_drift",
    "snapshot_schema": "governance.core:snapshot_schema",
    "apply_retention_policy": "governance.core:apply_retention_policy",
}

# Public API list for "from socrata_toolkit import *"
__all__ = list(_lazy_map.keys())

# Cache for loaded attributes
_loaded_cache: Dict[str, object] = {}

if TYPE_CHECKING:
    # For type checkers, import names so static analysis works.
    from .core.client import SocrataClient, SocrataConfig  # noqa: F401
    from .core.models import DatasetMetadata, SearchResult  # noqa: F401
    from .analysis.core import DataProfile, profile_dataframe, quality_report  # noqa: F401
    from .analysis.text import generate_text_insights  # noqa: F401
    from .nlp.advanced import analyze_text, translate_text, preprocess_text  # noqa: F401
    from .spatial.core import spatial_intersects_join, SpatialJoinResult  # noqa: F401
    from .llm.duck_bridge import LLMAugmentConfig, augment_dataframe_with_llm  # noqa: F401
    from .engineering.dot_sidewalk import compute_sidewalk_kpis, sql_templates, python_templates  # noqa: F401
    from .alerts.manager import AlertManager, CLINotifier, EmailNotifier, DBNotifier, Alert  # noqa: F401
    from .ops.core import apply_grace_period_updates, permit_lookahead_sql, generate_burndown, flag_high_priority_trigger_sql  # noqa: F401
    from .governance.compliance import check_dcwp_license, check_parks_permit, validate_contractor_for_list  # noqa: F401
    from .analysis.relevance import build_weighted_rank_sql, websearch_to_tsquery_sql  # noqa: F401
    from .sql.conflict import ConflictResolver, PostGISConflictResolver  # noqa: F401
    from .core.db_helpers import ensure_fts_index, build_fts_index_sql  # noqa: F401
    from .analysis.advanced import (  # noqa: F401
        detect_outliers_iqr,
        detect_outliers_zscore,
        detect_all_outliers,
        correlation_analysis,
        time_series_summary,
        classify_distribution,
        classify_all_distributions,
        flag_anomalies,
    )
    from .viz.core import (  # noqa: F401
        histogram,
        bar_chart,
        correlation_heatmap,
        time_series_chart,
        box_plot,
        quality_dashboard,
    )
    from .governance.core import (  # noqa: F401
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
