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

    # engineering (Pillar: engineering)
    "compute_sidewalk_kpis": "engineering:compute_sidewalk_kpis",
    "prioritize_construction_list": "engineering:prioritize_construction_list",
    "classify_scope": "engineering:classify_scope",
    "flag_ada_locations": "engineering:flag_ada_locations",
    "summarize_construction_list": "engineering:summarize_construction_list",
    "analyze_contract_progress": "engineering:analyze_contract_progress",
    "budget_analysis": "engineering:budget_analysis",
    "productivity_metrics": "engineering:productivity_metrics",

    # spatial (Pillar: spatial)
    "spatial_intersects_join": "spatial:spatial_intersects_join",
    "cluster_locations": "spatial:cluster_locations",
    "detect_construction_conflicts": "spatial:detect_construction_conflicts",

    # pipeline (Pillar: pipeline)
    "stream_pipeline": "pipeline:stream_pipeline",
    "ingest_311_complaints": "pipeline:ingest_311_complaints",
    "deduplicate_dataframe": "pipeline:deduplicate_dataframe",
    "generate_program_report": "pipeline:generate_program_report",

    # governance (Pillar: governance)
    "compute_quality_score": "governance:compute_quality_score",
    "AlertManager": "governance:AlertManager",

    # ai (Pillar: ai)
    "sentiment_score": "ai:sentiment_score",
    "enrich_construction_list": "ai:enrich_construction_list",
    "SocrataLLMChatbot": "ai:SocrataLLMChatbot",
    "SQLQueryEngine": "ai:SQLQueryEngine",
    "quantum_search": "ai:quantum_search",
}

# Public API list for "from socrata_toolkit import *"
__all__ = list(_lazy_map.keys())

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
