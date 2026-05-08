from .nlp_advanced import analyze_text, translate_text, preprocess_text
from .spatial import spatial_intersects_join, SpatialJoinResult
from .llm_duck_bridge import LLMAugmentConfig, augment_dataframe_with_llm
from .dot_sidewalk import compute_sidewalk_kpis, sql_templates, python_templates
from .text_analytics import generate_text_insights
from .analysis import DataProfile, profile_dataframe, quality_report
from .client import SocrataClient, SocrataConfig
from .models import DatasetMetadata, SearchResult
from .conflict import ConflictResolver, PostGISConflictResolver
from .db_helpers import ensure_fts_index, build_fts_index_sql
from .alerts import AlertManager, CLINotifier, EmailNotifier, DBNotifier, Alert
from .ops import apply_grace_period_updates, permit_lookahead_sql, generate_burndown, flag_high_priority_trigger_sql
from .compliance import check_dcwp_license, check_parks_permit, validate_contractor_for_list
from .relevance import build_weighted_rank_sql, websearch_to_tsquery_sql

__all__ = [
    "SocrataClient",
    "SocrataConfig",
    "DatasetMetadata",
    "SearchResult",
    "DataProfile",
    "profile_dataframe",
    "quality_report",
    "generate_text_insights",
    "compute_sidewalk_kpis",
    "sql_templates",
    "python_templates",
    "LLMAugmentConfig",
    "augment_dataframe_with_llm",
    "spatial_intersects_join",
    "SpatialJoinResult",
    "analyze_text",
    "translate_text",
    "preprocess_text",
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
]
