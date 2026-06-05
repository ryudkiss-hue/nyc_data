# Dataset Registry — Entity-Relationship Diagram

> Auto-generated from `src/socrata_toolkit/discovery/registry.py`.
> Re-generate with: `PYTHONPATH=src python -m socrata_toolkit.discovery.registry`

## Key taxonomy

| Symbol | Meaning |
|--------|---------|
| `PK` | Primary key — uniquely identifies a row |
| `UK` | Unique (alternate) key — unique but not the PK |
| `SK` | Secondary / composite key component |
| `FK` | Foreign key — references the PK of another entity |
| `IDX` | Non-unique index column |

## Cardinality notation

| Symbol | Meaning |
|--------|---------|
| `\|\|--\|\|` | Exactly one to exactly one |
| `\|\|--o\|` | Exactly one to zero-or-one |
| `\|\|--o{` | Exactly one to zero-or-many |
| `\|\|--\|{` | Exactly one to one-or-many |
| `}o--o{` | Zero-or-many to zero-or-many |

## Registered entities (29)

| Entity | Columns | Description |
|--------|---------|-------------|
| `DATASET` | 13 | Core Socrata dataset registry — one row per ingested dataset. |
| `DATASET_COLUMN` | 14 | Column-level metadata for every column in every dataset. |
| `DATASET_SCHEMA` | 6 | Versioned schema snapshot for a dataset. |
| `SCHEMA_CHANGE` | 10 | Individual column-level change detected between two schema versions. |
| `DATASET_QUALITY_PROFILE` | 6 | Mutable quality envelope for a dataset — one row per dataset. |
| `QUALITY_SCORE` | 10 | Point-in-time quality score snapshot (0–100 per dimension). |
| `VALIDATION_RESULT` | 10 | Result of a single quality rule evaluated against a dataset. |
| `RULE_VIOLATION` | 9 | Individual business-rule violation record. |
| `SLA_DEFINITION` | 8 | Data-quality SLA contract bound to a dataset and metric dimension. |
| `SLA_BREACH` | 7 | Recorded SLA breach event. |
| `FRESHNESS_LOG` | 9 | Append-only freshness / SLA monitoring log (date-partitioned). |
| `LINEAGE_NODE` | 8 | Node in the data-lineage DAG (source, transformation, or sink). |
| `LINEAGE_NODE_DATASET` | 4 | Junction — maps lineage nodes to the datasets they read or write. |
| `LINEAGE_EDGE` | 13 | Directed edge in the lineage DAG linking two nodes (or two datasets). |
| `EXECUTION_RECORD` | 12 | Immutable record of a single lineage-node execution run. |
| `AUDIT_EVENT` | 7 | Append-only audit log of every actor action on a resource. |
| `FAIR_DATASET` | 25 | FAIR Guiding Principles metadata envelope (Findable, Accessible, Interoperable, Reusable). |
| `SCHEMA_FIELD` | 6 | Individual field entry inside a FAIR dataset schema. |
| `DATA_CONTRACT` | 6 | Named contract that asserts structural and semantic rules on a dataset. |
| `FIELD_CONTRACT` | 11 | Column-level rule within a data contract. |
| `CONTRACT_VIOLATION` | 8 | Violation raised by a field contract during a validation run. |
| `MATERIAL_SPECIFICATION` | 15 | NYC DOT approved sidewalk material specifications. |
| `SPATIAL_BLOCK` | 7 | NYC city block polygon (parent geographic unit for sidewalk segments). |
| `SPATIAL_SEGMENT` | 11 | Individual sidewalk segment — the primary inspectable unit. |
| `SPATIAL_INSPECTION` | 8 | Field inspection event recording a defect at a point on a segment. |
| `SPATIAL_MATERIAL_ZONE` | 6 | Contiguous polygon zone of uniform sidewalk material. |
| `ENTITY_RELATIONSHIP` | 11 | Master-data relationship graph edges between any two entity IDs. |
| `ANALYST_PROFILE` | 10 | Autopilot configuration profile for an analyst workflow run. |
| `SOURCE_CONFIG` | 12 | Named data-source binding within an analyst profile. |

---

## ER Diagram

```mermaid
erDiagram
    DATASET {
        string dataset_id PK "Surrogate PK (fourfour or UUID)"
        string fourfour UK "Socrata 4×4 identifier e.g. 'fjn5-bxwg'"
        string domain IDX "Source domain e.g. 'data.cityofnewyork.us'"
        string name "Human-readable dataset title"
        string description "Long-form dataset description"
        string category "Socrata category tag"
        string tags "Array of keyword tags"
        int row_count "Last-known row count"
        string license "Data license identifier"
        string owner "Publishing agency / owner"
        boolean is_geo "True when dataset exposes geometry columns"
        datetime created_at "First ingestion timestamp"
        datetime updated_at "Most-recent ingestion timestamp"
    }

    DATASET_COLUMN {
        int column_id PK "Surrogate PK"
        string dataset_id FK "Parent dataset"
        string schema_id FK "Schema version this column belongs to"
        string name "Display column name"
        string field_name SK "API field name (unique within dataset)"
        string data_type_name "Socrata / DuckDB type string"
        string description "Column description from metadata"
        int position "Ordinal position in schema"
        boolean is_nullable "Whether nulls are permitted"
        boolean is_primary_key "Column is (part of) the source PK"
        boolean is_foreign_key "Column references another dataset"
        string references_dataset_id FK "FK target dataset (nullable)"
        string references_column "FK target column name (nullable)"
        string sample_value "Representative non-null sample value"
    }

    DATASET_SCHEMA {
        string schema_id PK "Surrogate PK"
        string dataset_id FK "Parent dataset"
        int version SK "Monotone version counter; unique within dataset"
        datetime captured_at "When this snapshot was taken"
        int row_count "Row count at snapshot time"
        string metadata "Arbitrary schema-level metadata"
    }

    SCHEMA_CHANGE {
        int change_id PK "Surrogate PK"
        string schema_id FK "Schema version that introduced the change"
        string dataset_id FK "Parent dataset"
        string change_type "COLUMN_ADDITION | COLUMN_DELETION | TYPE_CHANGE | RENAME | NULL_CONSTRAINT_CHANGE | POSITION_CHANGE"
        string field_name "Affected column name"
        string old_value "Previous value (type, name, position, etc.)"
        string new_value "New value"
        boolean is_breaking "True when change is backward-incompatible"
        string description "Human-readable change description"
        datetime detected_at "Timestamp of detection"
    }

    DATASET_QUALITY_PROFILE {
        string profile_id PK "Surrogate PK"
        string dataset_id UK "One-to-one with DATASET"
        string dataset_name "Denormalised display name"
        datetime last_validation "Most recent validation run"
        string quality_trend "IMPROVING | STABLE | DEGRADING"
        string violation_summary "Aggregated rule violation counts"
    }

    QUALITY_SCORE {
        int score_id PK "Surrogate PK"
        string profile_id FK "Parent quality profile"
        string dataset_id FK "Parent dataset (denorm)"
        float overall "Composite 0–100 quality score"
        float completeness "% non-null values across key columns"
        float validity "% values satisfying business rules"
        float consistency "Cross-dataset consistency score"
        float timeliness "% records within acceptable age"
        float accuracy "% values matching reference data"
        datetime measured_at "Measurement timestamp"
    }

    VALIDATION_RESULT {
        int result_id PK "Surrogate PK"
        string profile_id FK "Parent quality profile"
        string dataset_id FK "Parent dataset (denorm)"
        string rule_id "Business rule identifier"
        string rule_name "Human-readable rule name"
        boolean passed "True when all records satisfy the rule"
        int violation_count "Number of violating records"
        int affected_records "Total records checked"
        string severity "CRITICAL | HIGH | MEDIUM | LOW"
        datetime timestamp "Evaluation timestamp"
    }

    RULE_VIOLATION {
        int violation_id PK "Surrogate PK"
        string dataset_id FK "Affected dataset"
        string rule_id "Business rule identifier"
        string rule_name "Rule name"
        string severity "CRITICAL | HIGH | MEDIUM | LOW"
        int violation_count "Count of violating values"
        int affected_records "Rows checked in this evaluation"
        string suggested_remediation "Recommended corrective action"
        datetime timestamp "Detection timestamp"
    }

    SLA_DEFINITION {
        string sla_id PK "Surrogate PK"
        string dataset_id FK "Target dataset"
        string metric_type "COMPLETENESS | VALIDITY | UNIQUENESS | CONSISTENCY | TIMELINESS | ACCURACY"
        float threshold "Minimum acceptable metric value (0–1)"
        string severity "CRITICAL | HIGH | MEDIUM | LOW"
        int lookback_days "Rolling window for metric evaluation"
        string materialization_mode "HARD (block) | SOFT (warn)"
        datetime created_at "SLA creation timestamp"
    }

    SLA_BREACH {
        string breach_id PK "Surrogate PK (UUID)"
        string sla_id FK "Breached SLA contract"
        string dataset_id FK "Affected dataset (denorm)"
        float actual_value "Observed metric value at breach time"
        float threshold "SLA threshold (denorm for reporting)"
        string severity "Inherited severity from SLA"
        datetime timestamp "Breach detection timestamp"
    }

    FRESHNESS_LOG {
        int id PK "Composite PK with ingestion_timestamp"
        string dataset_id FK "Monitored dataset"
        string dataset_name "Denormalised display name"
        datetime last_updated_utc "Dataset's own last-updated timestamp"
        float expected_update_frequency_hours "Contracted update cadence"
        float sla_threshold_hours "Max acceptable staleness"
        datetime ingestion_timestamp SK "Row insertion timestamp (partition column)"
        boolean sla_violated "True when data exceeds sla_threshold_hours"
        float days_stale "(now − last_updated_utc) in days"
    }

    LINEAGE_NODE {
        string node_id PK "Surrogate PK"
        string name "Human-readable node name"
        string node_type "INGESTION | TRANSFORMATION | SINK | VALIDATION | MATERIALIZATION | AGGREGATION"
        string description "What this node does"
        string owner "Team or person responsible"
        datetime created_at "Creation timestamp"
        datetime last_modified "Last modification timestamp"
        string tags "Classification tags"
    }

    LINEAGE_NODE_DATASET {
        int id PK "Surrogate PK"
        string node_id FK "Lineage node"
        string dataset_id FK "Related dataset"
        string role "input | output"
    }

    LINEAGE_EDGE {
        string edge_id PK "UUID PK"
        string source_node_id FK "Source node"
        string target_node_id FK "Target node"
        string source_dataset_id FK "Source dataset (for dataset-level edges)"
        string target_dataset_id FK "Target dataset"
        string source_columns "Columns read from source"
        string target_columns "Columns written to target"
        string transformation_type "join | filter | aggregate | enrich | copy"
        string transformation_sql "SQL or SOQL expression (parameterised)"
        string edge_type "DEPENDENCY | DATA_FLOW | SCHEMA_DEPENDENCY"
        string cardinality "ONE_TO_ONE | ONE_TO_MANY | MANY_TO_MANY"
        string join_keys "Column names used as join keys"
        datetime created_at "Edge creation timestamp"
    }

    EXECUTION_RECORD {
        string execution_id PK "Surrogate PK"
        string node_id FK "Executed node"
        datetime started_at "Run start timestamp"
        datetime completed_at "Run end timestamp"
        float duration_seconds "Wall-clock duration in seconds"
        string status "RUNNING | SUCCESS | FAILED | PARTIAL | SKIPPED"
        int input_row_count "Rows read"
        int output_row_count "Rows written"
        string error_message "Exception message on failure"
        string run_by "User or service account"
        string data_quality_metrics "Inline quality metrics from the run"
        string notes "Free-form run notes"
    }

    AUDIT_EVENT {
        int event_id PK "Surrogate PK"
        datetime timestamp "Event timestamp"
        string actor "User, service, or system that performed the action"
        string action "read | write | delete | export | query | login"
        string resource_id FK "Affected dataset (nullable for non-dataset resources)"
        string resource_type "dataset | schema | contract | lineage_node"
        string details "Contextual action details"
    }

    FAIR_DATASET {
        string fair_id PK "Surrogate PK"
        string dataset_id UK "1-to-1 with DATASET"
        string persistent_id UK "DOI or persistent identifier"
        string fourfour FK "Socrata fourfour (denorm)"
        string title "FAIR: dataset title"
        string description "FAIR: dataset abstract"
        string keywords "FAIR: discovery keywords"
        string domain "FAIR: source domain"
        string landing_page "FAIR: human-readable landing URL"
        string access_url "FAIR: machine-readable access URL"
        string access_protocol "FAIR: protocol (HTTPS, SOQL, OGC, etc.)"
        string access_rights "FAIR: access level (public, restricted, etc.)"
        string license "FAIR: reuse license"
        string format "FAIR: serialisation format (JSON, CSV, GeoJSON)"
        string conforms_to "FAIR: standard the dataset conforms to"
        string vocabulary "FAIR: controlled vocabulary used"
        string provenance "FAIR: data provenance statement"
        string usage_rights "FAIR: permitted uses"
        string citation "FAIR: recommended citation string"
        float score_overall "Composite FAIR score 0–100"
        float score_findable "Findable sub-score 0–100"
        float score_accessible "Accessible sub-score 0–100"
        float score_interoperable "Interoperable sub-score 0–100"
        float score_reusable "Reusable sub-score 0–100"
        string gaps "FAIR gap descriptions"
    }

    SCHEMA_FIELD {
        int field_id PK "Surrogate PK"
        string fair_id FK "Parent FAIR dataset"
        string name "Column / field name"
        string datatype "Semantic datatype"
        string description "Field-level description"
        string semantic_type "Ontology URI or controlled-vocab term"
    }

    DATA_CONTRACT {
        string contract_id PK "Surrogate PK"
        string dataset_id FK "Target dataset"
        string name UK "Contract name (unique across registry)"
        string primary_key "Column name(s) that form the natural PK"
        string version "Semantic version of the contract"
        datetime created_at "Contract creation timestamp"
    }

    FIELD_CONTRACT {
        int field_contract_id PK "Surrogate PK"
        string contract_id FK "Parent contract"
        string name "Column name this rule applies to"
        string dtype "Expected Python/DuckDB type"
        boolean required "Column must exist"
        boolean nullable "Null values permitted"
        float min_value "Inclusive minimum numeric value"
        float max_value "Inclusive maximum numeric value"
        string allowed_values "Set of permitted discrete values"
        string regex_pattern "Regex pattern values must match"
        boolean is_unique "Values must be unique across the column"
    }

    CONTRACT_VIOLATION {
        int cv_id PK "Surrogate PK"
        int field_contract_id FK "Violated field rule"
        string contract_id FK "Parent contract (denorm)"
        string field "Column name"
        string rule "Rule label (not_null, dtype, min, max, regex, unique, allowed)"
        string detail "Human-readable violation detail"
        int count "Number of violating records"
        datetime detected_at "Validation run timestamp"
    }

    MATERIAL_SPECIFICATION {
        string material_id PK "e.g. 'ASPH_STANDARD'"
        string category "ASPHALT | CONCRETE | BRICK_STONE | METAL | PERMEABLE | COMPOSITE"
        string name "Human-readable material name"
        string description "Material description"
        string design_standards "Thickness, compaction, grades, etc."
        string maintenance_schedule "Routine interval, preventive overlay, lifecycle"
        string environmental_factors "Urban-heat, permeability, runoff attributes"
        float cost_per_sqft "Unit installation cost USD/sq ft"
        float lifecycle_cost_per_sqft "30-year lifecycle cost USD/sq ft"
        float sustainability_score "0–100 sustainability rating"
        float carbon_footprint_kg_per_sqft "Carbon footprint kg CO₂e / sq ft"
        string applicable_ada_rules "ADA rule references"
        string nyc_code_references "NYC Admin Code / DOT Standard references"
        string industry_standards "AASHTO, ACI, ASTM references"
        string maintenance_procedures "Step-by-step maintenance procedure map"
    }

    SPATIAL_BLOCK {
        string block_id PK "DOT block identifier"
        string borough "Manhattan | Brooklyn | Queens | Bronx | Staten Island"
        string district "Community district designation"
        string council_district "NYC Council district number"
        float area_square_meters "Block area in square metres"
        int segments_count "Count of sidewalk segments within block"
        string geometry "WGS-84 polygon"
    }

    SPATIAL_SEGMENT {
        string segment_id PK "DOT segment identifier"
        string block_id FK "Parent block"
        string material_type FK "Surface material"
        string zone_id FK "Material zone (optional)"
        float condition_score "0–100 pavement condition score"
        string borough "Borough (denorm from block)"
        string district "Community district"
        string council_district "Council district"
        float length_meters "Segment length in metres"
        datetime last_inspection "Most recent inspection timestamp"
        string geometry "WGS-84 linestring"
    }

    SPATIAL_INSPECTION {
        string inspection_id PK "Inspection identifier"
        string segment_id FK "Inspected segment"
        string inspector_id "Badge number or service-account ID"
        datetime timestamp "Inspection datetime"
        string defect_type "Defect classification code"
        string severity "low | medium | high | critical"
        string photo_url "URL to field photo (nullable)"
        string geometry "WGS-84 inspection point"
    }

    SPATIAL_MATERIAL_ZONE {
        string zone_id PK "Zone identifier"
        string material_type FK "Zone material"
        float area_square_meters "Zone area in square metres"
        int segment_count "Number of segments in this zone"
        float average_condition "Mean condition score across segments"
        string geometry "WGS-84 zone polygon"
    }

    ENTITY_RELATIONSHIP {
        string relationship_id PK "UUID PK"
        string source_entity_id IDX "Source entity ID (polymorphic)"
        string source_entity_type "Entity type of source (DATASET, BLOCK, SEGMENT, …)"
        string target_entity_id IDX "Target entity ID (polymorphic)"
        string target_entity_type "Entity type of target"
        string relationship_type "CONTAINS | BELONGS_TO | ADJACENT_TO | PART_OF | COMPOSED_OF | INTERSECTS | REFERENCES | DERIVED_FROM"
        float confidence "Match confidence 0–1"
        string attributes "Additional edge attributes"
        datetime created_at "Edge creation timestamp"
        string created_by "User or process that created the edge"
        string notes "Free-form annotation"
    }

    ANALYST_PROFILE {
        string profile_id PK "Surrogate PK"
        string profile_name UK "Unique profile identifier"
        string outputs_dir "Output directory path"
        string output_formats "csv | excel | pdf | pptx"
        string steps "Ordered workflow step config"
        string contract_ids "Associated data contract IDs"
        string duckdb_path "Path to local DuckDB cache file"
        boolean offline "True → skip live Socrata calls"
        string budget_codes_path "Path to budget codes reference file"
        string inquiry_templates_dir "Directory containing inquiry template files"
    }

    SOURCE_CONFIG {
        int source_config_id PK "Surrogate PK"
        string profile_id FK "Parent profile"
        string source_name SK "Source alias (unique within profile)"
        string source_type "excel | sql | socrata | csv | duckdb | postgres"
        string path "File path (for file-based sources)"
        string sheet "Excel worksheet name"
        string domain "Socrata domain"
        string fourfour FK "Socrata dataset 4×4"
        string table_name "SQL table name"
        string dsn_env "Env-var name holding the PostgreSQL DSN"
        int max_rows "Row fetch limit (None = unlimited)"
        string column_map "Source→canonical column name remapping"
    }


    DATASET ||--|{ DATASET_COLUMN : "has columns"
    DATASET ||--o{ DATASET_SCHEMA : "versioned as"
    DATASET_SCHEMA ||--o{ DATASET_COLUMN : "defines"
    DATASET_SCHEMA ||--o{ SCHEMA_CHANGE : "produces changes"
    DATASET ||--o| DATASET_QUALITY_PROFILE : "profiled by"
    DATASET_QUALITY_PROFILE ||--o{ QUALITY_SCORE : "scored as"
    DATASET_QUALITY_PROFILE ||--o{ VALIDATION_RESULT : "produces"
    DATASET ||--o{ RULE_VIOLATION : "violates"
    DATASET ||--o{ SLA_DEFINITION : "governed by"
    SLA_DEFINITION ||--o{ SLA_BREACH : "triggers"
    DATASET ||--o{ FRESHNESS_LOG : "tracked in"
    LINEAGE_NODE ||--o{ LINEAGE_NODE_DATASET : "reads or writes"
    DATASET ||--o{ LINEAGE_NODE_DATASET : "used by"
    LINEAGE_NODE ||--o{ EXECUTION_RECORD : "executed as"
    LINEAGE_NODE ||--o{ LINEAGE_EDGE : "is source of"
    LINEAGE_NODE ||--o{ LINEAGE_EDGE : "is target of"
    DATASET ||--o{ LINEAGE_EDGE : "flows from"
    DATASET ||--o{ AUDIT_EVENT : "audited in"
    DATASET ||--o| FAIR_DATASET : "described by"
    FAIR_DATASET ||--o{ SCHEMA_FIELD : "has fields"
    DATASET ||--o{ DATA_CONTRACT : "validated by"
    DATA_CONTRACT ||--|{ FIELD_CONTRACT : "contains"
    FIELD_CONTRACT ||--o{ CONTRACT_VIOLATION : "raises"
    SPATIAL_BLOCK ||--o{ SPATIAL_SEGMENT : "contains"
    SPATIAL_SEGMENT ||--o{ SPATIAL_INSPECTION : "inspected via"
    MATERIAL_SPECIFICATION ||--o{ SPATIAL_SEGMENT : "used in"
    MATERIAL_SPECIFICATION ||--o{ SPATIAL_MATERIAL_ZONE : "defines"
    SPATIAL_MATERIAL_ZONE ||--o{ SPATIAL_SEGMENT : "groups"
    ANALYST_PROFILE ||--|{ SOURCE_CONFIG : "configures"
    DATASET ||--o{ SOURCE_CONFIG : "referenced by"
```
