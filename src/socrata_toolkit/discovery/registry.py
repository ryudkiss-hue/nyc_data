"""
Dataset Registry — canonical column-level metadata store for all toolkit entities.

Every table in the NYC DOT SIM toolkit is modelled here as a Python dataclass with
explicit primary-key (PK), foreign-key (FK), unique-key (UK / alternate key), and
indexed-key (SK) annotations carried as ``KeyMeta`` descriptors.  The module also
exposes ``REGISTRY``, a dict of all entity descriptors, and ``build_er_diagram()``
which returns the Mermaid erDiagram markdown string.

Key classification
------------------
PK  – surrogate or natural primary key; uniquely identifies a row.
UK  – unique (alternate) key; uniquely identifies a row but not the PK.
SK  – secondary / composite key component (meaningful without being PK/UK alone).
FK  – foreign key; references the PK of another entity.
IDX – non-unique index column (carried for documentation, not enforced here).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Key taxonomy ──────────────────────────────────────────────────────────────

class KeyRole(str, Enum):
    """Role of a column in the keying strategy of its entity."""
    PK = "PK"    # Primary key
    UK = "UK"    # Unique (alternate) key
    SK = "SK"    # Secondary / composite key component
    FK = "FK"    # Foreign key
    IDX = "IDX"  # Indexed (non-unique)
    NONE = ""    # Regular column


@dataclass
class KeyMeta:
    """Key annotation attached to a ``ColumnDef``."""
    role: KeyRole
    references: str | None = None   # "EntityName.column_name" for FK / SK
    comment: str | None = None


@dataclass
class ColumnDef:
    """Full metadata for a single column."""
    name: str
    dtype: str                          # SQL-style type string
    nullable: bool = True
    key: KeyMeta = field(default_factory=lambda: KeyMeta(KeyRole.NONE))
    description: str = ""


@dataclass
class EntityDef:
    """Registry entry for a single table / entity."""
    name: str
    description: str
    columns: list[ColumnDef]
    schema: str = "public"             # logical schema namespace


# ── Helper factories ──────────────────────────────────────────────────────────

def pk(dtype: str = "VARCHAR(50)", description: str = "") -> tuple[str, KeyMeta]:
    return dtype, KeyMeta(KeyRole.PK, comment=description)


def uk(dtype: str = "VARCHAR(255)", references: str | None = None, description: str = "") -> tuple[str, KeyMeta]:
    return dtype, KeyMeta(KeyRole.UK, references=references, comment=description)


def fk(dtype: str = "VARCHAR(50)", references: str = "", description: str = "") -> tuple[str, KeyMeta]:
    return dtype, KeyMeta(KeyRole.FK, references=references, comment=description)


def sk(dtype: str = "VARCHAR(50)", references: str | None = None, description: str = "") -> tuple[str, KeyMeta]:
    return dtype, KeyMeta(KeyRole.SK, references=references, comment=description)


def col(dtype: str, nullable: bool = True, description: str = "") -> tuple[str, bool, str]:
    return dtype, nullable, description


def _c(name: str, dtype: str, nullable: bool = True, key: KeyMeta | None = None, description: str = "") -> ColumnDef:
    return ColumnDef(name=name, dtype=dtype, nullable=nullable,
                     key=key or KeyMeta(KeyRole.NONE), description=description)


# ── Entity definitions ────────────────────────────────────────────────────────

DATASET = EntityDef(
    name="DATASET",
    description="Core Socrata dataset registry — one row per ingested dataset.",
    columns=[
        _c("dataset_id",    "VARCHAR(50)",   False, KeyMeta(KeyRole.PK),  "Surrogate PK (fourfour or UUID)"),
        _c("fourfour",      "VARCHAR(9)",    False, KeyMeta(KeyRole.UK),  "Socrata 4×4 identifier e.g. 'fjn5-bxwg'"),
        _c("domain",        "VARCHAR(255)",  False, key=KeyMeta(KeyRole.IDX), description="Source domain e.g. 'data.cityofnewyork.us'"),
        _c("name",          "VARCHAR(512)",  False, description="Human-readable dataset title"),
        _c("description",   "TEXT",          True,  description="Long-form dataset description"),
        _c("category",      "VARCHAR(100)",  True,  description="Socrata category tag"),
        _c("tags",          "TEXT[]",        True,  description="Array of keyword tags"),
        _c("row_count",     "BIGINT",        True,  description="Last-known row count"),
        _c("license",       "VARCHAR(100)",  True,  description="Data license identifier"),
        _c("owner",         "VARCHAR(255)",  True,  description="Publishing agency / owner"),
        _c("is_geo",        "BOOLEAN",       True,  description="True when dataset exposes geometry columns"),
        _c("created_at",    "TIMESTAMPTZ",   True,  description="First ingestion timestamp"),
        _c("updated_at",    "TIMESTAMPTZ",   True,  description="Most-recent ingestion timestamp"),
    ],
)

DATASET_COLUMN = EntityDef(
    name="DATASET_COLUMN",
    description="Column-level metadata for every column in every dataset.",
    columns=[
        _c("column_id",             "BIGSERIAL",    False, KeyMeta(KeyRole.PK),                             "Surrogate PK"),
        _c("dataset_id",            "VARCHAR(50)",  False, KeyMeta(KeyRole.FK, "DATASET.dataset_id"),       "Parent dataset"),
        _c("schema_id",             "VARCHAR(50)",  True,  KeyMeta(KeyRole.FK, "DATASET_SCHEMA.schema_id"), "Schema version this column belongs to"),
        _c("name",                  "VARCHAR(255)", False, description="Display column name"),
        _c("field_name",            "VARCHAR(255)", False, KeyMeta(KeyRole.SK, "DATASET_COLUMN.dataset_id,field_name"), "API field name (unique within dataset)"),
        _c("data_type_name",        "VARCHAR(50)",  False, description="Socrata / DuckDB type string"),
        _c("description",           "TEXT",         True,  description="Column description from metadata"),
        _c("position",              "SMALLINT",     True,  description="Ordinal position in schema"),
        _c("is_nullable",           "BOOLEAN",      False, description="Whether nulls are permitted"),
        _c("is_primary_key",        "BOOLEAN",      False, description="Column is (part of) the source PK"),
        _c("is_foreign_key",        "BOOLEAN",      False, description="Column references another dataset"),
        _c("references_dataset_id", "VARCHAR(50)",  True,  KeyMeta(KeyRole.FK, "DATASET.dataset_id"),       "FK target dataset (nullable)"),
        _c("references_column",     "VARCHAR(255)", True,  description="FK target column name (nullable)"),
        _c("sample_value",          "TEXT",         True,  description="Representative non-null sample value"),
    ],
)

DATASET_SCHEMA = EntityDef(
    name="DATASET_SCHEMA",
    description="Versioned schema snapshot for a dataset.",
    columns=[
        _c("schema_id",   "VARCHAR(50)",  False, KeyMeta(KeyRole.PK),                              "Surrogate PK"),
        _c("dataset_id",  "VARCHAR(50)",  False, KeyMeta(KeyRole.FK, "DATASET.dataset_id"),        "Parent dataset"),
        _c("version",     "INTEGER",      False, KeyMeta(KeyRole.SK, "DATASET_SCHEMA.dataset_id"), "Monotone version counter; unique within dataset"),
        _c("captured_at", "TIMESTAMPTZ",  False, description="When this snapshot was taken"),
        _c("row_count",   "BIGINT",       True,  description="Row count at snapshot time"),
        _c("metadata",    "JSONB",        True,  description="Arbitrary schema-level metadata"),
    ],
)

SCHEMA_CHANGE = EntityDef(
    name="SCHEMA_CHANGE",
    description="Individual column-level change detected between two schema versions.",
    columns=[
        _c("change_id",   "BIGSERIAL",    False, KeyMeta(KeyRole.PK),                                    "Surrogate PK"),
        _c("schema_id",   "VARCHAR(50)",  False, KeyMeta(KeyRole.FK, "DATASET_SCHEMA.schema_id"),        "Schema version that introduced the change"),
        _c("dataset_id",  "VARCHAR(50)",  False, KeyMeta(KeyRole.FK, "DATASET.dataset_id"),              "Parent dataset"),
        _c("change_type", "VARCHAR(50)",  False, description="COLUMN_ADDITION | COLUMN_DELETION | TYPE_CHANGE | RENAME | NULL_CONSTRAINT_CHANGE | POSITION_CHANGE"),
        _c("field_name",  "VARCHAR(255)", False, description="Affected column name"),
        _c("old_value",   "TEXT",         True,  description="Previous value (type, name, position, etc.)"),
        _c("new_value",   "TEXT",         True,  description="New value"),
        _c("is_breaking", "BOOLEAN",      False, description="True when change is backward-incompatible"),
        _c("description", "TEXT",         True,  description="Human-readable change description"),
        _c("detected_at", "TIMESTAMPTZ",  False, description="Timestamp of detection"),
    ],
)

DATASET_QUALITY_PROFILE = EntityDef(
    name="DATASET_QUALITY_PROFILE",
    description="Mutable quality envelope for a dataset — one row per dataset.",
    columns=[
        _c("profile_id",       "VARCHAR(50)", False, KeyMeta(KeyRole.PK),                        "Surrogate PK"),
        _c("dataset_id",       "VARCHAR(50)", False, KeyMeta(KeyRole.UK, "DATASET.dataset_id"),  "One-to-one with DATASET"),
        _c("dataset_name",     "VARCHAR(512)", True, description="Denormalised display name"),
        _c("last_validation",  "TIMESTAMPTZ", True,  description="Most recent validation run"),
        _c("quality_trend",    "VARCHAR(20)",  True,  description="IMPROVING | STABLE | DEGRADING"),
        _c("violation_summary","JSONB",        True,  description="Aggregated rule violation counts"),
    ],
)

QUALITY_SCORE = EntityDef(
    name="QUALITY_SCORE",
    description="Point-in-time quality score snapshot (0–100 per dimension).",
    columns=[
        _c("score_id",      "BIGSERIAL",   False, KeyMeta(KeyRole.PK),                                          "Surrogate PK"),
        _c("profile_id",    "VARCHAR(50)", False, KeyMeta(KeyRole.FK, "DATASET_QUALITY_PROFILE.profile_id"),    "Parent quality profile"),
        _c("dataset_id",    "VARCHAR(50)", False, KeyMeta(KeyRole.FK, "DATASET.dataset_id"),                    "Parent dataset (denorm)"),
        _c("overall",       "FLOAT",       False, description="Composite 0–100 quality score"),
        _c("completeness",  "FLOAT",       True,  description="% non-null values across key columns"),
        _c("validity",      "FLOAT",       True,  description="% values satisfying business rules"),
        _c("consistency",   "FLOAT",       True,  description="Cross-dataset consistency score"),
        _c("timeliness",    "FLOAT",       True,  description="% records within acceptable age"),
        _c("accuracy",      "FLOAT",       True,  description="% values matching reference data"),
        _c("measured_at",   "TIMESTAMPTZ", False, description="Measurement timestamp"),
    ],
)

VALIDATION_RESULT = EntityDef(
    name="VALIDATION_RESULT",
    description="Result of a single quality rule evaluated against a dataset.",
    columns=[
        _c("result_id",         "BIGSERIAL",   False, KeyMeta(KeyRole.PK),                                       "Surrogate PK"),
        _c("profile_id",        "VARCHAR(50)", False, KeyMeta(KeyRole.FK, "DATASET_QUALITY_PROFILE.profile_id"), "Parent quality profile"),
        _c("dataset_id",        "VARCHAR(50)", False, KeyMeta(KeyRole.FK, "DATASET.dataset_id"),                 "Parent dataset (denorm)"),
        _c("rule_id",           "VARCHAR(50)", True,  description="Business rule identifier"),
        _c("rule_name",         "VARCHAR(255)",False, description="Human-readable rule name"),
        _c("passed",            "BOOLEAN",     False, description="True when all records satisfy the rule"),
        _c("violation_count",   "INTEGER",     True,  description="Number of violating records"),
        _c("affected_records",  "BIGINT",      True,  description="Total records checked"),
        _c("severity",          "VARCHAR(20)", True,  description="CRITICAL | HIGH | MEDIUM | LOW"),
        _c("timestamp",         "TIMESTAMPTZ", False, description="Evaluation timestamp"),
    ],
)

RULE_VIOLATION = EntityDef(
    name="RULE_VIOLATION",
    description="Individual business-rule violation record.",
    columns=[
        _c("violation_id",          "BIGSERIAL",    False, KeyMeta(KeyRole.PK),                       "Surrogate PK"),
        _c("dataset_id",            "VARCHAR(50)",  False, KeyMeta(KeyRole.FK, "DATASET.dataset_id"), "Affected dataset"),
        _c("rule_id",               "VARCHAR(50)",  True,  description="Business rule identifier"),
        _c("rule_name",             "VARCHAR(255)", False, description="Rule name"),
        _c("severity",              "VARCHAR(20)",  False, description="CRITICAL | HIGH | MEDIUM | LOW"),
        _c("violation_count",       "INTEGER",      False, description="Count of violating values"),
        _c("affected_records",      "BIGINT",       True,  description="Rows checked in this evaluation"),
        _c("suggested_remediation", "TEXT",         True,  description="Recommended corrective action"),
        _c("timestamp",             "TIMESTAMPTZ",  False, description="Detection timestamp"),
    ],
)

SLA_DEFINITION = EntityDef(
    name="SLA_DEFINITION",
    description="Data-quality SLA contract bound to a dataset and metric dimension.",
    columns=[
        _c("sla_id",              "VARCHAR(50)",  False, KeyMeta(KeyRole.PK),                       "Surrogate PK"),
        _c("dataset_id",          "VARCHAR(50)",  False, KeyMeta(KeyRole.FK, "DATASET.dataset_id"), "Target dataset"),
        _c("metric_type",         "VARCHAR(50)",  False, description="COMPLETENESS | VALIDITY | UNIQUENESS | CONSISTENCY | TIMELINESS | ACCURACY"),
        _c("threshold",           "FLOAT",        False, description="Minimum acceptable metric value (0–1)"),
        _c("severity",            "VARCHAR(20)",  False, description="CRITICAL | HIGH | MEDIUM | LOW"),
        _c("lookback_days",       "INTEGER",      False, description="Rolling window for metric evaluation"),
        _c("materialization_mode","VARCHAR(10)",  False, description="HARD (block) | SOFT (warn)"),
        _c("created_at",          "TIMESTAMPTZ",  False, description="SLA creation timestamp"),
    ],
)

SLA_BREACH = EntityDef(
    name="SLA_BREACH",
    description="Recorded SLA breach event.",
    columns=[
        _c("breach_id",    "VARCHAR(50)",  False, KeyMeta(KeyRole.PK),                             "Surrogate PK (UUID)"),
        _c("sla_id",       "VARCHAR(50)",  False, KeyMeta(KeyRole.FK, "SLA_DEFINITION.sla_id"),    "Breached SLA contract"),
        _c("dataset_id",   "VARCHAR(50)",  False, KeyMeta(KeyRole.FK, "DATASET.dataset_id"),       "Affected dataset (denorm)"),
        _c("actual_value", "FLOAT",        False, description="Observed metric value at breach time"),
        _c("threshold",    "FLOAT",        False, description="SLA threshold (denorm for reporting)"),
        _c("severity",     "VARCHAR(20)",  False, description="Inherited severity from SLA"),
        _c("timestamp",    "TIMESTAMPTZ",  False, description="Breach detection timestamp"),
    ],
)

FRESHNESS_LOG = EntityDef(
    name="FRESHNESS_LOG",
    description="Append-only freshness / SLA monitoring log (date-partitioned).",
    columns=[
        _c("id",                              "BIGSERIAL",    False, KeyMeta(KeyRole.PK),                       "Composite PK with ingestion_timestamp"),
        _c("dataset_id",                      "VARCHAR(255)", False, KeyMeta(KeyRole.FK, "DATASET.dataset_id"), "Monitored dataset"),
        _c("dataset_name",                    "VARCHAR(512)", True,  description="Denormalised display name"),
        _c("last_updated_utc",                "TIMESTAMPTZ",  True,  description="Dataset's own last-updated timestamp"),
        _c("expected_update_frequency_hours", "FLOAT",        True,  description="Contracted update cadence"),
        _c("sla_threshold_hours",             "FLOAT",        True,  description="Max acceptable staleness"),
        _c("ingestion_timestamp",             "TIMESTAMP",    False, KeyMeta(KeyRole.SK, comment="Partition key"),  "Row insertion timestamp (partition column)"),
        _c("sla_violated",                    "BOOLEAN",      False, description="True when data exceeds sla_threshold_hours"),
        _c("days_stale",                      "FLOAT",        True,  description="(now − last_updated_utc) in days"),
    ],
)

LINEAGE_NODE = EntityDef(
    name="LINEAGE_NODE",
    description="Node in the data-lineage DAG (source, transformation, or sink).",
    columns=[
        _c("node_id",       "VARCHAR(50)",  False, KeyMeta(KeyRole.PK),  "Surrogate PK"),
        _c("name",          "VARCHAR(255)", False, description="Human-readable node name"),
        _c("node_type",     "VARCHAR(30)",  False, description="INGESTION | TRANSFORMATION | SINK | VALIDATION | MATERIALIZATION | AGGREGATION"),
        _c("description",   "TEXT",         True,  description="What this node does"),
        _c("owner",         "VARCHAR(255)", True,  description="Team or person responsible"),
        _c("created_at",    "TIMESTAMPTZ",  False, description="Creation timestamp"),
        _c("last_modified", "TIMESTAMPTZ",  True,  description="Last modification timestamp"),
        _c("tags",          "TEXT[]",       True,  description="Classification tags"),
    ],
)

LINEAGE_NODE_DATASET = EntityDef(
    name="LINEAGE_NODE_DATASET",
    description="Junction — maps lineage nodes to the datasets they read or write.",
    columns=[
        _c("id",         "BIGSERIAL",   False, KeyMeta(KeyRole.PK),                             "Surrogate PK"),
        _c("node_id",    "VARCHAR(50)", False, KeyMeta(KeyRole.FK, "LINEAGE_NODE.node_id"),     "Lineage node"),
        _c("dataset_id", "VARCHAR(50)", False, KeyMeta(KeyRole.FK, "DATASET.dataset_id"),       "Related dataset"),
        _c("role",       "VARCHAR(10)", False, description="input | output"),
    ],
)

LINEAGE_EDGE = EntityDef(
    name="LINEAGE_EDGE",
    description="Directed edge in the lineage DAG linking two nodes (or two datasets).",
    columns=[
        _c("edge_id",            "UUID",         False, KeyMeta(KeyRole.PK),                                "UUID PK"),
        _c("source_node_id",     "VARCHAR(50)",  True,  KeyMeta(KeyRole.FK, "LINEAGE_NODE.node_id"),        "Source node"),
        _c("target_node_id",     "VARCHAR(50)",  True,  KeyMeta(KeyRole.FK, "LINEAGE_NODE.node_id"),        "Target node"),
        _c("source_dataset_id",  "VARCHAR(255)", True,  KeyMeta(KeyRole.FK, "DATASET.dataset_id"),          "Source dataset (for dataset-level edges)"),
        _c("target_dataset_id",  "VARCHAR(255)", True,  KeyMeta(KeyRole.FK, "DATASET.dataset_id"),          "Target dataset"),
        _c("source_columns",     "TEXT[]",       True,  description="Columns read from source"),
        _c("target_columns",     "TEXT[]",       True,  description="Columns written to target"),
        _c("transformation_type","VARCHAR(50)",  True,  description="join | filter | aggregate | enrich | copy"),
        _c("transformation_sql", "TEXT",         True,  description="SQL or SOQL expression (parameterised)"),
        _c("edge_type",          "VARCHAR(30)",  True,  description="DEPENDENCY | DATA_FLOW | SCHEMA_DEPENDENCY"),
        _c("cardinality",        "VARCHAR(20)",  True,  description="ONE_TO_ONE | ONE_TO_MANY | MANY_TO_MANY"),
        _c("join_keys",          "TEXT[]",       True,  description="Column names used as join keys"),
        _c("created_at",         "TIMESTAMPTZ",  False, description="Edge creation timestamp"),
    ],
)

EXECUTION_RECORD = EntityDef(
    name="EXECUTION_RECORD",
    description="Immutable record of a single lineage-node execution run.",
    columns=[
        _c("execution_id",         "VARCHAR(50)",  False, KeyMeta(KeyRole.PK),                           "Surrogate PK"),
        _c("node_id",              "VARCHAR(50)",  False, KeyMeta(KeyRole.FK, "LINEAGE_NODE.node_id"),   "Executed node"),
        _c("started_at",           "TIMESTAMPTZ",  False, description="Run start timestamp"),
        _c("completed_at",         "TIMESTAMPTZ",  True,  description="Run end timestamp"),
        _c("duration_seconds",     "FLOAT",        True,  description="Wall-clock duration in seconds"),
        _c("status",               "VARCHAR(20)",  False, description="RUNNING | SUCCESS | FAILED | PARTIAL | SKIPPED"),
        _c("input_row_count",      "BIGINT",       True,  description="Rows read"),
        _c("output_row_count",     "BIGINT",       True,  description="Rows written"),
        _c("error_message",        "TEXT",         True,  description="Exception message on failure"),
        _c("run_by",               "VARCHAR(255)", True,  description="User or service account"),
        _c("data_quality_metrics", "JSONB",        True,  description="Inline quality metrics from the run"),
        _c("notes",                "TEXT",         True,  description="Free-form run notes"),
    ],
)

AUDIT_EVENT = EntityDef(
    name="AUDIT_EVENT",
    description="Append-only audit log of every actor action on a resource.",
    columns=[
        _c("event_id",    "BIGSERIAL",    False, KeyMeta(KeyRole.PK),                       "Surrogate PK"),
        _c("timestamp",   "TIMESTAMPTZ",  False, description="Event timestamp"),
        _c("actor",       "VARCHAR(255)", False, description="User, service, or system that performed the action"),
        _c("action",      "VARCHAR(30)",  False, description="read | write | delete | export | query | login"),
        _c("resource_id", "VARCHAR(255)", True,  KeyMeta(KeyRole.FK, "DATASET.dataset_id"), "Affected dataset (nullable for non-dataset resources)"),
        _c("resource_type","VARCHAR(50)", True,  description="dataset | schema | contract | lineage_node"),
        _c("details",     "JSONB",        True,  description="Contextual action details"),
    ],
)

FAIR_DATASET = EntityDef(
    name="FAIR_DATASET",
    description="FAIR Guiding Principles metadata envelope (Findable, Accessible, Interoperable, Reusable).",
    columns=[
        _c("fair_id",                "VARCHAR(50)",   False, KeyMeta(KeyRole.PK),                        "Surrogate PK"),
        _c("dataset_id",             "VARCHAR(50)",   False, KeyMeta(KeyRole.UK, "DATASET.dataset_id"),  "1-to-1 with DATASET"),
        _c("persistent_id",          "VARCHAR(255)",  True,  KeyMeta(KeyRole.UK),                        "DOI or persistent identifier"),
        _c("fourfour",               "VARCHAR(9)",    True,  KeyMeta(KeyRole.FK, "DATASET.fourfour"),    "Socrata fourfour (denorm)"),
        # Findable
        _c("title",                  "VARCHAR(512)",  True,  description="FAIR: dataset title"),
        _c("description",            "TEXT",          True,  description="FAIR: dataset abstract"),
        _c("keywords",               "TEXT[]",        True,  description="FAIR: discovery keywords"),
        _c("domain",                 "VARCHAR(255)",  True,  description="FAIR: source domain"),
        # Accessible
        _c("landing_page",           "TEXT",          True,  description="FAIR: human-readable landing URL"),
        _c("access_url",             "TEXT",          True,  description="FAIR: machine-readable access URL"),
        _c("access_protocol",        "VARCHAR(50)",   True,  description="FAIR: protocol (HTTPS, SOQL, OGC, etc.)"),
        _c("access_rights",          "VARCHAR(100)",  True,  description="FAIR: access level (public, restricted, etc.)"),
        _c("license",                "VARCHAR(100)",  True,  description="FAIR: reuse license"),
        # Interoperable
        _c("format",                 "VARCHAR(50)",   True,  description="FAIR: serialisation format (JSON, CSV, GeoJSON)"),
        _c("conforms_to",            "TEXT",          True,  description="FAIR: standard the dataset conforms to"),
        _c("vocabulary",             "TEXT",          True,  description="FAIR: controlled vocabulary used"),
        # Reusable
        _c("provenance",             "TEXT",          True,  description="FAIR: data provenance statement"),
        _c("usage_rights",           "TEXT",          True,  description="FAIR: permitted uses"),
        _c("citation",               "TEXT",          True,  description="FAIR: recommended citation string"),
        # Scores
        _c("score_overall",          "FLOAT",         True,  description="Composite FAIR score 0–100"),
        _c("score_findable",         "FLOAT",         True,  description="Findable sub-score 0–100"),
        _c("score_accessible",       "FLOAT",         True,  description="Accessible sub-score 0–100"),
        _c("score_interoperable",    "FLOAT",         True,  description="Interoperable sub-score 0–100"),
        _c("score_reusable",         "FLOAT",         True,  description="Reusable sub-score 0–100"),
        _c("gaps",                   "TEXT[]",        True,  description="FAIR gap descriptions"),
    ],
)

SCHEMA_FIELD = EntityDef(
    name="SCHEMA_FIELD",
    description="Individual field entry inside a FAIR dataset schema.",
    columns=[
        _c("field_id",     "BIGSERIAL",    False, KeyMeta(KeyRole.PK),                         "Surrogate PK"),
        _c("fair_id",      "VARCHAR(50)",  False, KeyMeta(KeyRole.FK, "FAIR_DATASET.fair_id"), "Parent FAIR dataset"),
        _c("name",         "VARCHAR(255)", False, description="Column / field name"),
        _c("datatype",     "VARCHAR(50)",  False, description="Semantic datatype"),
        _c("description",  "TEXT",         True,  description="Field-level description"),
        _c("semantic_type","VARCHAR(255)", True,  description="Ontology URI or controlled-vocab term"),
    ],
)

DATA_CONTRACT = EntityDef(
    name="DATA_CONTRACT",
    description="Named contract that asserts structural and semantic rules on a dataset.",
    columns=[
        _c("contract_id",  "VARCHAR(50)",  False, KeyMeta(KeyRole.PK),                       "Surrogate PK"),
        _c("dataset_id",   "VARCHAR(50)",  False, KeyMeta(KeyRole.FK, "DATASET.dataset_id"), "Target dataset"),
        _c("name",         "VARCHAR(255)", False, KeyMeta(KeyRole.UK),                       "Contract name (unique across registry)"),
        _c("primary_key",  "TEXT[]",       True,  description="Column name(s) that form the natural PK"),
        _c("version",      "VARCHAR(20)",  True,  description="Semantic version of the contract"),
        _c("created_at",   "TIMESTAMPTZ",  False, description="Contract creation timestamp"),
    ],
)

FIELD_CONTRACT = EntityDef(
    name="FIELD_CONTRACT",
    description="Column-level rule within a data contract.",
    columns=[
        _c("field_contract_id", "BIGSERIAL",    False, KeyMeta(KeyRole.PK),                           "Surrogate PK"),
        _c("contract_id",       "VARCHAR(50)",  False, KeyMeta(KeyRole.FK, "DATA_CONTRACT.contract_id"), "Parent contract"),
        _c("name",              "VARCHAR(255)", False, description="Column name this rule applies to"),
        _c("dtype",             "VARCHAR(50)",  False, description="Expected Python/DuckDB type"),
        _c("required",          "BOOLEAN",      False, description="Column must exist"),
        _c("nullable",          "BOOLEAN",      False, description="Null values permitted"),
        _c("min_value",         "FLOAT",        True,  description="Inclusive minimum numeric value"),
        _c("max_value",         "FLOAT",        True,  description="Inclusive maximum numeric value"),
        _c("allowed_values",    "JSONB",        True,  description="Set of permitted discrete values"),
        _c("regex_pattern",     "TEXT",         True,  description="Regex pattern values must match"),
        _c("is_unique",         "BOOLEAN",      True,  description="Values must be unique across the column"),
    ],
)

CONTRACT_VIOLATION = EntityDef(
    name="CONTRACT_VIOLATION",
    description="Violation raised by a field contract during a validation run.",
    columns=[
        _c("cv_id",            "BIGSERIAL",    False, KeyMeta(KeyRole.PK),                                   "Surrogate PK"),
        _c("field_contract_id","BIGINT",        False, KeyMeta(KeyRole.FK, "FIELD_CONTRACT.field_contract_id"), "Violated field rule"),
        _c("contract_id",      "VARCHAR(50)",  False, KeyMeta(KeyRole.FK, "DATA_CONTRACT.contract_id"),       "Parent contract (denorm)"),
        _c("field",            "VARCHAR(255)", False, description="Column name"),
        _c("rule",             "VARCHAR(100)", False, description="Rule label (not_null, dtype, min, max, regex, unique, allowed)"),
        _c("detail",           "TEXT",         True,  description="Human-readable violation detail"),
        _c("count",            "INTEGER",      False, description="Number of violating records"),
        _c("detected_at",      "TIMESTAMPTZ",  False, description="Validation run timestamp"),
    ],
)

MATERIAL_SPECIFICATION = EntityDef(
    name="MATERIAL_SPECIFICATION",
    description="NYC DOT approved sidewalk material specifications.",
    columns=[
        _c("material_id",                   "VARCHAR(50)",  False, KeyMeta(KeyRole.PK),  "e.g. 'ASPH_STANDARD'"),
        _c("category",                      "VARCHAR(50)",  False, description="ASPHALT | CONCRETE | BRICK_STONE | METAL | PERMEABLE | COMPOSITE"),
        _c("name",                          "VARCHAR(100)", False, description="Human-readable material name"),
        _c("description",                   "TEXT",         True,  description="Material description"),
        _c("design_standards",              "JSONB",        True,  description="Thickness, compaction, grades, etc."),
        _c("maintenance_schedule",          "JSONB",        True,  description="Routine interval, preventive overlay, lifecycle"),
        _c("environmental_factors",         "JSONB",        True,  description="Urban-heat, permeability, runoff attributes"),
        _c("cost_per_sqft",                 "FLOAT",        True,  description="Unit installation cost USD/sq ft"),
        _c("lifecycle_cost_per_sqft",       "FLOAT",        True,  description="30-year lifecycle cost USD/sq ft"),
        _c("sustainability_score",          "FLOAT",        True,  description="0–100 sustainability rating"),
        _c("carbon_footprint_kg_per_sqft",  "FLOAT",        True,  description="Carbon footprint kg CO₂e / sq ft"),
        _c("applicable_ada_rules",          "TEXT[]",       True,  description="ADA rule references"),
        _c("nyc_code_references",           "TEXT[]",       True,  description="NYC Admin Code / DOT Standard references"),
        _c("industry_standards",            "TEXT[]",       True,  description="AASHTO, ACI, ASTM references"),
        _c("maintenance_procedures",        "JSONB",        True,  description="Step-by-step maintenance procedure map"),
    ],
)

SPATIAL_BLOCK = EntityDef(
    name="SPATIAL_BLOCK",
    description="NYC city block polygon (parent geographic unit for sidewalk segments).",
    columns=[
        _c("block_id",            "VARCHAR(50)", False, KeyMeta(KeyRole.PK),  "DOT block identifier"),
        _c("borough",             "VARCHAR(20)", False, description="Manhattan | Brooklyn | Queens | Bronx | Staten Island"),
        _c("district",            "VARCHAR(50)", True,  description="Community district designation"),
        _c("council_district",    "VARCHAR(20)", True,  description="NYC Council district number"),
        _c("area_square_meters",  "FLOAT",       True,  description="Block area in square metres"),
        _c("segments_count",      "INTEGER",     True,  description="Count of sidewalk segments within block"),
        _c("geometry",            "GEOMETRY(POLYGON,4326)", True, description="WGS-84 polygon"),
    ],
)

SPATIAL_SEGMENT = EntityDef(
    name="SPATIAL_SEGMENT",
    description="Individual sidewalk segment — the primary inspectable unit.",
    columns=[
        _c("segment_id",       "VARCHAR(50)", False, KeyMeta(KeyRole.PK),                                        "DOT segment identifier"),
        _c("block_id",         "VARCHAR(50)", True,  KeyMeta(KeyRole.FK, "SPATIAL_BLOCK.block_id"),              "Parent block"),
        _c("material_type",    "VARCHAR(50)", True,  KeyMeta(KeyRole.FK, "MATERIAL_SPECIFICATION.material_id"),  "Surface material"),
        _c("zone_id",          "VARCHAR(50)", True,  KeyMeta(KeyRole.FK, "SPATIAL_MATERIAL_ZONE.zone_id"),       "Material zone (optional)"),
        _c("condition_score",  "FLOAT",       False, description="0–100 pavement condition score"),
        _c("borough",          "VARCHAR(20)", False, description="Borough (denorm from block)"),
        _c("district",         "VARCHAR(50)", True,  description="Community district"),
        _c("council_district", "VARCHAR(20)", True,  description="Council district"),
        _c("length_meters",    "FLOAT",       True,  description="Segment length in metres"),
        _c("last_inspection",  "TIMESTAMP",   True,  description="Most recent inspection timestamp"),
        _c("geometry",         "GEOMETRY(LINESTRING,4326)", True, description="WGS-84 linestring"),
    ],
)

SPATIAL_INSPECTION = EntityDef(
    name="SPATIAL_INSPECTION",
    description="Field inspection event recording a defect at a point on a segment.",
    columns=[
        _c("inspection_id", "VARCHAR(50)",  False, KeyMeta(KeyRole.PK),                             "Inspection identifier"),
        _c("segment_id",    "VARCHAR(50)",  False, KeyMeta(KeyRole.FK, "SPATIAL_SEGMENT.segment_id"),"Inspected segment"),
        _c("inspector_id",  "VARCHAR(100)", False, description="Badge number or service-account ID"),
        _c("timestamp",     "TIMESTAMP",    False, description="Inspection datetime"),
        _c("defect_type",   "VARCHAR(100)", True,  description="Defect classification code"),
        _c("severity",      "VARCHAR(20)",  False, description="low | medium | high | critical"),
        _c("photo_url",     "TEXT",         True,  description="URL to field photo (nullable)"),
        _c("geometry",      "GEOMETRY(POINT,4326)", True, description="WGS-84 inspection point"),
    ],
)

SPATIAL_MATERIAL_ZONE = EntityDef(
    name="SPATIAL_MATERIAL_ZONE",
    description="Contiguous polygon zone of uniform sidewalk material.",
    columns=[
        _c("zone_id",           "VARCHAR(50)", False, KeyMeta(KeyRole.PK),                                       "Zone identifier"),
        _c("material_type",     "VARCHAR(50)", False, KeyMeta(KeyRole.FK, "MATERIAL_SPECIFICATION.material_id"), "Zone material"),
        _c("area_square_meters","FLOAT",       True,  description="Zone area in square metres"),
        _c("segment_count",     "INTEGER",     True,  description="Number of segments in this zone"),
        _c("average_condition", "FLOAT",       True,  description="Mean condition score across segments"),
        _c("geometry",          "GEOMETRY(POLYGON,4326)", True, description="WGS-84 zone polygon"),
    ],
)

ENTITY_RELATIONSHIP = EntityDef(
    name="ENTITY_RELATIONSHIP",
    description="Master-data relationship graph edges between any two entity IDs.",
    columns=[
        _c("relationship_id",    "VARCHAR(50)", False, KeyMeta(KeyRole.PK),  "UUID PK"),
        _c("source_entity_id",   "VARCHAR(50)", False, KeyMeta(KeyRole.IDX), "Source entity ID (polymorphic)"),
        _c("source_entity_type", "VARCHAR(50)", False, description="Entity type of source (DATASET, BLOCK, SEGMENT, …)"),
        _c("target_entity_id",   "VARCHAR(50)", False, KeyMeta(KeyRole.IDX), "Target entity ID (polymorphic)"),
        _c("target_entity_type", "VARCHAR(50)", False, description="Entity type of target"),
        _c("relationship_type",  "VARCHAR(30)", False, description="CONTAINS | BELONGS_TO | ADJACENT_TO | PART_OF | COMPOSED_OF | INTERSECTS | REFERENCES | DERIVED_FROM"),
        _c("confidence",         "FLOAT",       True,  description="Match confidence 0–1"),
        _c("attributes",         "JSONB",       True,  description="Additional edge attributes"),
        _c("created_at",         "TIMESTAMPTZ", False, description="Edge creation timestamp"),
        _c("created_by",         "VARCHAR(255)",True,  description="User or process that created the edge"),
        _c("notes",              "TEXT",        True,  description="Free-form annotation"),
    ],
)

ANALYST_PROFILE = EntityDef(
    name="ANALYST_PROFILE",
    description="Autopilot configuration profile for an analyst workflow run.",
    columns=[
        _c("profile_id",             "VARCHAR(50)",  False, KeyMeta(KeyRole.PK),  "Surrogate PK"),
        _c("profile_name",           "VARCHAR(100)", False, KeyMeta(KeyRole.UK),  "Unique profile identifier"),
        _c("outputs_dir",            "VARCHAR(512)", True,  description="Output directory path"),
        _c("output_formats",         "TEXT[]",       True,  description="csv | excel | pdf | pptx"),
        _c("steps",                  "JSONB",        True,  description="Ordered workflow step config"),
        _c("contract_ids",           "TEXT[]",       True,  description="Associated data contract IDs"),
        _c("duckdb_path",            "VARCHAR(512)", True,  description="Path to local DuckDB cache file"),
        _c("offline",                "BOOLEAN",      False, description="True → skip live Socrata calls"),
        _c("budget_codes_path",      "VARCHAR(512)", True,  description="Path to budget codes reference file"),
        _c("inquiry_templates_dir",  "VARCHAR(512)", True,  description="Directory containing inquiry template files"),
    ],
)

SOURCE_CONFIG = EntityDef(
    name="SOURCE_CONFIG",
    description="Named data-source binding within an analyst profile.",
    columns=[
        _c("source_config_id", "BIGSERIAL",    False, KeyMeta(KeyRole.PK),                               "Surrogate PK"),
        _c("profile_id",       "VARCHAR(50)",  False, KeyMeta(KeyRole.FK, "ANALYST_PROFILE.profile_id"), "Parent profile"),
        _c("source_name",      "VARCHAR(100)", False, KeyMeta(KeyRole.SK, "SOURCE_CONFIG.profile_id"),   "Source alias (unique within profile)"),
        _c("source_type",      "VARCHAR(20)",  False, description="excel | sql | socrata | csv | duckdb | postgres"),
        _c("path",             "VARCHAR(512)", True,  description="File path (for file-based sources)"),
        _c("sheet",            "VARCHAR(100)", True,  description="Excel worksheet name"),
        _c("domain",           "VARCHAR(255)", True,  description="Socrata domain"),
        _c("fourfour",         "VARCHAR(9)",   True,  KeyMeta(KeyRole.FK, "DATASET.fourfour"),           "Socrata dataset 4×4"),
        _c("table_name",       "VARCHAR(255)", True,  description="SQL table name"),
        _c("dsn_env",          "VARCHAR(100)", True,  description="Env-var name holding the PostgreSQL DSN"),
        _c("max_rows",         "INTEGER",      True,  description="Row fetch limit (None = unlimited)"),
        _c("column_map",       "JSONB",        True,  description="Source→canonical column name remapping"),
    ],
)


# ── Global registry ───────────────────────────────────────────────────────────

REGISTRY: dict[str, EntityDef] = {
    e.name: e for e in [
        DATASET,
        DATASET_COLUMN,
        DATASET_SCHEMA,
        SCHEMA_CHANGE,
        DATASET_QUALITY_PROFILE,
        QUALITY_SCORE,
        VALIDATION_RESULT,
        RULE_VIOLATION,
        SLA_DEFINITION,
        SLA_BREACH,
        FRESHNESS_LOG,
        LINEAGE_NODE,
        LINEAGE_NODE_DATASET,
        LINEAGE_EDGE,
        EXECUTION_RECORD,
        AUDIT_EVENT,
        FAIR_DATASET,
        SCHEMA_FIELD,
        DATA_CONTRACT,
        FIELD_CONTRACT,
        CONTRACT_VIOLATION,
        MATERIAL_SPECIFICATION,
        SPATIAL_BLOCK,
        SPATIAL_SEGMENT,
        SPATIAL_INSPECTION,
        SPATIAL_MATERIAL_ZONE,
        ENTITY_RELATIONSHIP,
        ANALYST_PROFILE,
        SOURCE_CONFIG,
    ]
}


# ── ER diagram generator ──────────────────────────────────────────────────────

# Relationship edges: (from, cardinality_symbol, to, label)
# Mermaid cardinality tokens:
#   ||--||   exactly-one to exactly-one
#   ||--o|   exactly-one to zero-or-one
#   ||--o{   exactly-one to zero-or-many
#   ||--|{   exactly-one to one-or-many
#   }o--o{   zero-or-many to zero-or-many
_RELATIONSHIPS: list[tuple[str, str, str, str]] = [
    # Core dataset hierarchy
    ("DATASET",                 "||--|{", "DATASET_COLUMN",          "has columns"),
    ("DATASET",                 "||--o{", "DATASET_SCHEMA",          "versioned as"),
    ("DATASET_SCHEMA",          "||--o{", "DATASET_COLUMN",          "defines"),
    ("DATASET_SCHEMA",          "||--o{", "SCHEMA_CHANGE",           "produces changes"),
    # Quality
    ("DATASET",                 "||--o|", "DATASET_QUALITY_PROFILE", "profiled by"),
    ("DATASET_QUALITY_PROFILE", "||--o{", "QUALITY_SCORE",           "scored as"),
    ("DATASET_QUALITY_PROFILE", "||--o{", "VALIDATION_RESULT",       "produces"),
    ("DATASET",                 "||--o{", "RULE_VIOLATION",          "violates"),
    # SLA
    ("DATASET",                 "||--o{", "SLA_DEFINITION",          "governed by"),
    ("SLA_DEFINITION",          "||--o{", "SLA_BREACH",              "triggers"),
    ("DATASET",                 "||--o{", "FRESHNESS_LOG",           "tracked in"),
    # Lineage
    ("LINEAGE_NODE",            "||--o{", "LINEAGE_NODE_DATASET",    "reads or writes"),
    ("DATASET",                 "||--o{", "LINEAGE_NODE_DATASET",    "used by"),
    ("LINEAGE_NODE",            "||--o{", "EXECUTION_RECORD",        "executed as"),
    ("LINEAGE_NODE",            "||--o{", "LINEAGE_EDGE",            "is source of"),
    ("LINEAGE_NODE",            "||--o{", "LINEAGE_EDGE",            "is target of"),
    ("DATASET",                 "||--o{", "LINEAGE_EDGE",            "flows from"),
    # Governance
    ("DATASET",                 "||--o{", "AUDIT_EVENT",             "audited in"),
    # FAIR
    ("DATASET",                 "||--o|", "FAIR_DATASET",            "described by"),
    ("FAIR_DATASET",            "||--o{", "SCHEMA_FIELD",            "has fields"),
    # Contracts
    ("DATASET",                 "||--o{", "DATA_CONTRACT",           "validated by"),
    ("DATA_CONTRACT",           "||--|{", "FIELD_CONTRACT",          "contains"),
    ("FIELD_CONTRACT",          "||--o{", "CONTRACT_VIOLATION",      "raises"),
    # Spatial hierarchy
    ("SPATIAL_BLOCK",           "||--o{", "SPATIAL_SEGMENT",         "contains"),
    ("SPATIAL_SEGMENT",         "||--o{", "SPATIAL_INSPECTION",      "inspected via"),
    ("MATERIAL_SPECIFICATION",  "||--o{", "SPATIAL_SEGMENT",         "used in"),
    ("MATERIAL_SPECIFICATION",  "||--o{", "SPATIAL_MATERIAL_ZONE",   "defines"),
    ("SPATIAL_MATERIAL_ZONE",   "||--o{", "SPATIAL_SEGMENT",         "groups"),
    # Analyst config
    ("ANALYST_PROFILE",         "||--|{", "SOURCE_CONFIG",           "configures"),
    ("DATASET",                 "||--o{", "SOURCE_CONFIG",           "referenced by"),
]

_MERMAID_TYPE_MAP: dict[str, str] = {
    "BIGSERIAL":                "int",
    "BIGINT":                   "int",
    "INTEGER":                  "int",
    "SMALLINT":                 "int",
    "FLOAT":                    "float",
    "BOOLEAN":                  "boolean",
    "TIMESTAMPTZ":              "datetime",
    "TIMESTAMP":                "datetime",
    "UUID":                     "string",
    "TEXT":                     "string",
    "TEXT[]":                   "string",
    "JSONB":                    "string",
    "GEOMETRY(POLYGON,4326)":   "string",
    "GEOMETRY(LINESTRING,4326)":"string",
    "GEOMETRY(POINT,4326)":     "string",
}


def _mermaid_type(dtype: str) -> str:
    base = dtype.split("(")[0].upper().strip()
    if base.startswith("VARCHAR"):
        return "string"
    return _MERMAID_TYPE_MAP.get(dtype.upper().strip(),
           _MERMAID_TYPE_MAP.get(base, "string"))


def build_er_diagram() -> str:
    """Return the full Mermaid erDiagram markdown string for all registered entities."""
    lines: list[str] = ["erDiagram"]

    for entity in REGISTRY.values():
        lines.append(f"    {entity.name} {{")
        for col in entity.columns:
            mtype = _mermaid_type(col.dtype)
            key_token = f" {col.key.role.value}" if col.key.role != KeyRole.NONE else ""
            comment = f' "{col.description}"' if col.description else ""
            lines.append(f"        {mtype} {col.name}{key_token}{comment}")
        lines.append("    }")
        lines.append("")

    lines.append("")
    for src, card, tgt, label in _RELATIONSHIPS:
        lines.append(f'    {src} {card} {tgt} : "{label}"')

    return "\n".join(lines)


def print_er_diagram() -> None:
    """Print the Mermaid erDiagram to stdout."""
    print(build_er_diagram())


if __name__ == "__main__":
    print_er_diagram()
