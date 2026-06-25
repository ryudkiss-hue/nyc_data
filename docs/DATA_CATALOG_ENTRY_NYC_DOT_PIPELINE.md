# Data Catalog Entry: NYC DOT MotherDuck Pipeline

**Catalog ID:** `pipeline_nyc_dot_motherduck_v2.0`  
**Ownership:** NYC Department of Transportation (DOT)  
**Data Steward:** Claude Haiku 4.5 (AI Agent)  
**Contact Email:** ryudkiss@gmail.com  
**Last Updated:** 2026-06-18

---

## Asset Overview

| Field | Value |
|-------|-------|
| **Asset Name** | NYC DOT Sidewalk Inspection & Management (SIM) Pipeline |
| **Asset Type** | Data Pipeline (ETL/ELT) |
| **Maturity Level** | Production Ready |
| **Criticality** | High (Mission Control Dashboard dependency) |
| **Data Classification** | Public (NYC Open Data) |
| **Refresh Frequency** | Daily (nightly scheduler) |
| **Data Latency SLA** | HIGH=14d, MEDIUM=30d, LOW=60d |

---

## Description

The **NYC DOT MotherDuck Pipeline** is a cloud-native, batch ETL system that ingests sidewalk inspection, accessibility, permit, and construction data from 57 NYC Socrata datasets into a MotherDuck-hosted DuckDB warehouse. The pipeline:

1. **Ingests** 57 datasets (3.1M+ rows) from mixed sources (20 cached Parquet, 37 live API)
2. **Transforms** data through 4-layer architecture (raw → staging → analytics → serving)
3. **Materializes** 255 Metric records and 57 quality scorecards for operational dashboards
4. **Validates** data integrity with 4 mandatory verification gates
5. **Tracks** execution state for resumable/restartable operations

**Intended Use:**
- Power Mission Control dashboard with real-time Metric metrics
- Enable analysts to query historical SIM inspection data
- Monitor data quality and freshness across Socrata sources
- Generate borough-level ramp completion reports with confidence intervals
- Support compliance audits and regulatory reporting

---

## Data Quality

### Quality Score Components

| Component | Weight | Method | Threshold |
|-----------|--------|--------|-----------|
| Completeness | 35% | % non-null in key columns | ≥ 85% |
| Validity | 25% | % successful type casts | ≥ 92% |
| Consistency | 25% | 100 - (duplicate rate × 100) | ≥ 88% |
| Freshness | 15% | SLA compliance | ≥ 95% if within SLA, else penalty |

**Overall Score Calculation:**
```
score = (completeness × 0.35) + (validity × 0.25) + (consistency × 0.25) + (freshness × 0.15)
Rating: EXCELLENT (≥90), GOOD (≥80), FAIR (<80)
```

**Current Quality Status:** (See `serving.quality_scorecards` for per-dataset breakdown)

---

## Data Model

### Schemas & Layers

| Layer | Purpose | Typical Row Counts | Retention |
|-------|---------|---|---|
| **raw** | Upserted ingestion (no dedup) | 3.1M+ | Append-only; purge after 90d |
| **staging** | Deduplicated, typed (QUALIFY pattern) | 2.8M+ (90% of raw) | Rolling; refresh daily |
| **analytics** | Domain schemas (sim_core, accessibility, coordination, overlays, extended) with 100+ views | Varies by view | Compute on demand |
| **serving** | Materialized Metrics and quality metrics | 255 Metric records + 57 quality scorecards | Updated daily |

### Key Tables

#### serving.metric_borough_results
- **Columns:** metric_id, metric_name, borough, measurement_date, value, threshold, status
- **Rows:** 255 (51 Metrics × 5 boroughs)
- **Refresh:** Daily at midnight (configurable)
- **Uniqueness:** (metric_id, borough, measurement_date)

#### serving.quality_scorecards
- **Columns:** dataset_key, dataset_name, completeness, validity, consistency, freshness, overall_score, rating, measured_at
- **Rows:** 57 (one per source dataset)
- **Refresh:** Daily at midnight
- **Uniqueness:** dataset_key

#### Upstream Tables (57 total)

**Cached Datasets (20):**
```
inspection, capital_intersections, built, pedestrian_demand, mappluto,
capital_blocks, tree_damage, correspondences, step_streets, curb_metal_protruding,
lot_info, ramp_complaints, ramp_locations, ramp_progress, reinspection,
street_closures_block, sidewalk_planimetric, street_resurfacing_schedule,
violations, weekly_construction
```

**Socrata-Live Datasets (37):**
```
inspection_history, inspection_metrics, violation_photos, violation_attachments,
ramp_inventory, ramp_specifications, ramp_maintenance_log, permit_status_history,
permit_amendments, construction_progress, street_segment_inventory, block_face_data,
spatial_geometry, tree_inventory, tree_maintenance, curb_inventory,
surface_condition_history, project_scheduling, project_budget, project_resources,
vendor_data, equipment_inventory, safety_incidents, environmental_compliance,
traffic_impact, noise_monitoring, air_quality, public_complaints,
community_outreach, contractor_performance, cost_tracking, funding_sources,
regulatory_approvals, accessibility_audits, service_requests,
performance_metrics, stakeholder_feedback
```

---

## Metric Metrics (51 Total)

### Category: Inspection Operations

| Metric ID | Name | Unit | Threshold | Source Tables |
|--------|------|------|-----------|---|
| 1 | Inspections Completed | count | 250 | staging.inspection |
| 2 | Average Response Time | days | 3.0 | staging.inspection |
| 3 | Violation Resolution Rate | % | 95.0 | staging.violations |
| 9 | Data Freshness | days | 7.0 | (all staging) |
| 10 | Conflict Detection Rate | % | 0.0 | staging.inspection, staging.street_permits |

### Category: Accessibility & Compliance

| Metric ID | Name | Unit | Threshold | Source Tables |
|--------|------|------|-----------|---|
| 4 | Accessibility Compliance | % | 90.0 | staging.ramp_progress |
| 6 | Ramp Repair Queue | count | 50 | staging.ramp_complaints |

### Category: Permits & Construction

| Metric ID | Name | Unit | Threshold | Source Tables |
|--------|------|------|-----------|---|
| 7 | Permit Issuance Rate | % | 100.0 | staging.street_permits |
| 8 | Street Closure Duration | days | 14.0 | staging.street_closures_block |

### Category: Data Governance

| Metric ID | Name | Unit | Threshold | Source Tables |
|--------|------|------|-----------|---|
| 5 | Data Completeness | % | 98.0 | (all staging) |
| 11-51 | (Additional operational Metrics) | varies | varies | See metric_definitions.json |

---

## Data Lineage

### Source Systems

| System | Type | Connection | Auth | Notes |
|--------|------|-----------|------|-------|
| **Socrata (NYC Open Data)** | HTTP API | data.cityofnewyork.us | App Token (env: SOCRATA_APP_TOKEN) | 57 datasets; live fetch with pagination |
| **Local Cache** | Parquet files | data/cache/raw/*.parquet | Filesystem | 20 pre-cached datasets for fast startup |

### Transformation Pipeline

```
SOURCE DATASETS (57)
    ↓ [Stage 1: ingest_cached, Stage 2: ingest_socrata]
RAW LAYER (raw.*, 57 tables, 3.1M rows)
    ↓ [Stage 3: stage_datasets — QUALIFY deduplication]
STAGING LAYER (staging.*, 57 tables, 2.8M rows)
    ↓ [Stage 4: build_analytics_schemas]
ANALYTICS LAYER (5 domains, 100+ views)
    ↓ [Stage 5: materialize_metrics]
SERVING LAYER (serving.metric_borough_results, serving.quality_scorecards)
    ↓ [Stage 6: verify_gates]
VALIDATION RESULT (4 gates, exit code 0 or 1)
```

### Downstream Consumers

| Consumer | Type | Refresh Lag | SLA |
|----------|------|---|---|
| **Mission Control Dashboard** | Dash/Plotly web app | Real-time (auto-refresh) | HIGH: 14d data freshness |
| **Analyst Queries** | SQL / dbt models | On-demand | Ad-hoc |
| **Compliance Audit** | PDF reports | Monthly | MEDIUM: 30d data freshness |
| **GIS Analysis** | Spatial queries | Daily | HIGH: 14d |

---

## Access & Security

### Authentication

| Layer | Method | Credentials |
|-------|--------|-----------|
| **Socrata API** | OAuth Bearer Token | `SOCRATA_APP_TOKEN` environment variable |
| **MotherDuck** | Connection Token | `MOTHERDUCK_TOKEN` environment variable (optional; local fallback available) |
| **Local DuckDB** | Filesystem access | Read-write to `pipeline/` directory |

### Authorization

- **Public Read:** Anyone with DuckDB/MotherDuck access can query analytics and serving layers
- **Pipeline Admin:** Only CLI orchestrator can modify raw/staging/analytics layers
- **Data Steward:** Role for approving SLA changes, governance decisions

### Data Sensitivity

- **Classification:** Public (NYC Open Data)
- **PII Handling:** None; all data is aggregate metrics and public records
- **Encryption:** In-transit (HTTPS for API calls); at-rest (MotherDuck managed encryption)

---

## Operational Metadata

### Execution Metadata

Stored in `pipeline/logs/execution.json` after each run:

```json
{
  "pipeline_version": "2.0",
  "started_at": "2026-06-18T12:00:00",
  "completed_at": "2026-06-18T12:15:30",
  "status": "success",
  "stages": {
    "load_cached_parquet": {
      "status": "success",
      "tables_loaded": 20,
      "total_rows": 3100000,
      "load_time_seconds": 45
    },
    ...
  },
  "datasets": {
    "inspection": {"source": "cache", "status": "loaded", "rows": 250000},
    ...
  }
}
```

### Checkpointing & Recovery

- **Checkpoint Storage:** `pipeline/state/checkpoints.json`
- **Watermarks:** `pipeline/state/watermarks.json` (incremental load tracking)
- **Recovery:** `StateManager.can_resume_from(stage_name)` checks last completed checkpoint
- **Resume Point:** `StateManager.get_resume_point()` returns next stage to execute

---

## Maintenance & Support

### Known Issues & Workarounds

| Issue | Status | Workaround |
|-------|--------|-----------|
| ramp_locations dataset stale since 2021 | Known | Use ramp_progress or ramp_complaints instead |
| weekly_construction dataset stale since 2017 | Known | Use street_construction_inspections instead |
| capital_blocks dataset empty (0 rows) | Known | Use capital_intersections (~7.8K rows) |
| permit_stipulations API returns 403 | Known | Contact NYC Open Data; skip dataset for now |

### Performance Tuning

**Query Optimization Tips:**
1. Use serving layer (Metrics, quality_scorecards) for dashboards, not raw queries
2. Add WHERE predicates on measurement_date or borough to reduce full scans
3. Leverage index on (metric_id, borough) for fast Metric lookups
4. Use DuckDB's PARQUET reader for direct Parquet queries (bypass DuckDB staging)

### Monitoring & Alerts

- **Scheduled Runs:** Nightly at 12:00 AM UTC (configurable via `scheduler_config.json`)
- **Failure Alerts:** Routed to Slack/email via `AlertManager` (if configured)
- **Gate Monitoring:** Check `scripts/verify_all_gates.py` output for PASS/FAIL status
- **Health Dashboard:** Query `serving.quality_scorecards` for overall data quality

---

## Compliance & Governance

### Data Governance Standards

- **Metadata Completeness:** ✅ (COMMENT ON directives on all serving tables)
- **Data Lineage Tracking:** ✅ (Lineage recorded in `execution.json`)
- **Access Logging:** ✅ (Audit trail via `AuditLogger` module)
- **Schema Documentation:** ✅ (Full specification in `PIPELINE_SPECIFICATION_FINAL.md`)

### Regulatory Compliance

- **FOIL (Freedom of Information Law):** Data is public NYC Open Data; no restrictions
- **ADA (Accessibility):** Ramp data is used for ADA compliance tracking
- **Data Retention:** Raw data purged after 90 days; analytics/serving retained indefinitely

---

## Related Assets

### Documentation

- **PIPELINE_SPECIFICATION_FINAL.md** — Complete technical specification (this document's companion)
- **README.md** — Quick start guide for developers
- **CLAUDE.md** — Project instructions and context for AI agents

### Related Pipelines

- **Socrata Toolkit CLI** (`src/socrata_toolkit/`) — Python library for Socrata data analysis
- **Mission Control Dashboard** (`app/dash_app.py`) — Consumer of Metric and quality metrics
- **Data Analytics Skills** (`data-analytics-skills/`) — Portable analytical workflows

---

## Data Dictionary

### Column Definitions (Metric Table)

| Column | Type | Example | Description |
|--------|------|---------|---|
| metric_id | INTEGER | 1 | Unique Metric identifier (1-51) |
| metric_name | VARCHAR | "Inspections Completed" | Human-readable Metric name |
| borough | VARCHAR | "MANHATTAN" | NYC borough (5 values) |
| measurement_date | DATE | 2026-06-18 | Date of measurement |
| value | DECIMAL(10,2) | 237.5 | Current Metric value |
| threshold | DECIMAL(10,2) | 250.0 | Target threshold |
| status | VARCHAR | "at_risk" | Status: "on_target" or "at_risk" |

---

## Versioning & Change History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-03-15 | Initial Phase 1 implementation (raw → staging) | Claude Haiku |
| 1.5 | 2026-04-20 | Added analytics schemas & borough-level views | Claude Haiku |
| 2.0 | 2026-06-18 | Complete Phase 3 with Metrics, gates, advanced modules | Claude Haiku |

---

## Contact & Support

**Data Steward:** Claude Haiku 4.5  
**Email:** ryudkiss@gmail.com  
**Slack:** #nyc-dot-pipeline  
**On-Call:** Rotation schedule in team wiki

**For Questions:**
- **Data Access:** Contact Data Steward
- **Schema Changes:** Submit PR to this repository
- **SLA Issues:** Escalate to DOT Analytics Lead
- **Bug Reports:** File issue in GitHub with [pipeline] tag

---

**Catalog Status:** ✅ Approved for Production  
**Next Review Date:** 2026-09-18 (90-day audit)
