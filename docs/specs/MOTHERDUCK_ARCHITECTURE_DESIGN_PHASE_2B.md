# MotherDuck Cloud Architecture Design — NYC DOT Socrata Toolkit
## Phase 2B Design Document | Week 1, June 17–21, 2026

---

## 1. Executive Summary

The NYC DOT Socrata Toolkit currently operates a **local-first DuckDB architecture** processing 3.6M+ rows weekly across three core datasets (inspections, violations, street permits) with pre-computed analytics views. This design document specifies a **hybrid cloud migration strategy** leveraging MotherDuck (managed cloud DuckDB) to enable multi-analyst collaboration, reduce local infrastructure burden, and preserve audit-trail governance without vendor lock-in.

**Current State:**
- Local DuckDB instance: ~600 MB (raw, staging, analytics schemas)
- Daily ingestion: ~398K inspections + ~312K violations updates via Socrata API
- L2 Parquet cache: ~100 GB on local storage
- Analytics: 5 pre-computed borough-level views (completion rates, SLA tracking)
- Deployment: Single user/developer machine (8 GB RAM, 100 GB SSD)

**Proposed Hybrid Model:**
- **Raw layer** — stays local (cost savings, no sharing need)
- **Staging layer** — moves to cloud (central transformation engine)
- **Analytics layer** — cloud-based (shareable metrics, BI tool integration)
- **dlt pipeline** — orchestrates incremental Socrata → MotherDuck syncs
- **dbt models** — enforces data quality, lineage, and metric definitions

**Expected Benefits:**
1. **Scalability** — Remove local storage constraints; handle 10× data volume
2. **Collaboration** — Multiple analysts query same cloud schema without ETL duplication
3. **Governance** — Centralized audit trail, schema versioning, data lineage (dbt)
4. **Cost Transparency** — MotherDuck billing per compute hour; clear ROI breakeven
5. **Portability** — DuckDB SQL is open standard; zero vendor lock-in risk

**Timeline:** Phase 2B (design, Week 1) → Phase 3 POC (Week 7–10) → Production cutover (Week 11+)

---

## 2. Data Classification Matrix

Each table is classified by: **volume**, **update frequency**, **sharing requirement**, and **query patterns**. This matrix informs whether the table stays on local DuckDB or migrates to MotherDuck.

| Schema | Table | Rows | Freq | Local? | Cloud? | Reasoning |
|--------|-------|------|------|--------|--------|-----------|
| **raw** | `inspections_raw` | ~398K | Daily | ✓ | ✗ | Source of truth; no downstream consumers outside NYC DOT. Local write-only model avoids cloud sync latency. |
| **raw** | `violations_raw` | ~312K | Daily | ✓ | ✗ | Core operational data; high write volume (daily delta). Local reduces API costs for analysts. |
| **raw** | `street_permits_raw` | ~3.6M | Weekly | ✓ | ✗ | Large volume; infrequent changes. Local avoids egress costs; cloud pipeline pulls when needed. |
| **raw** | `ramp_progress_raw` | ~187K | Daily | ✓ | ✗ | Rapid updates; accessibility team uses locally. Sync to cloud async on 6h schedule. |
| **staging** | `inspections` | ~398K | Daily | ✗ | ✓ | Deduplicated, type-cast, keys injected. Central transform engine; supports shared reports. |
| **staging** | `violations` | ~312K | Daily | ✗ | ✓ | Business rules applied (status rollup). Required for BI tools; analysts expect cloud query. |
| **staging** | `permits_clean` | ~3.6M | Weekly | ✗ | ✓ | Deduped permit IDs, date normalization. Shared across planners + conflict-detect workload. |
| **analytics** | `borough_completion_rates` | 5 | Daily | ✗ | ✓ | Pre-computed ramp completion + CI. Published to Tableau, Slack daily briefing. |
| **analytics** | `inspection_aging_by_borough` | ~30 | Daily | ✗ | ✓ | Velocity metrics; director dashboard. Cloud materialized view supports SLA reporting. |
| **analytics** | `violations_trend` | ~365 | Monthly | ✗ | ✓ | Time-series aggregates. Public-facing metric; no PII. |
| **cache** | `inspections_parquet` (L2) | ~398K | Daily | ✓ | ✗ | Redundant with staging; stays local for fast analyst iteration. |
| **cache** | `violations_parquet` (L2) | ~312K | Daily | ✓ | ✗ | Local query fallback if cloud unavailable. Refreshed nightly. |

**Classification Rationale:**

- **Raw tables → Local:** Operational source of truth; no external consumers. Reduces cloud API call volume (2 calls/row on sync = cost). Write-optimized locally; immutable snapshot pushed to cloud nightly.
  
- **Staging tables → Cloud:** Central transformation hub for multi-analyst workloads. Single source of truth for clean data eliminates analyst-to-analyst ETL duplication. dbt enforces SLAs and column-level documentation.

- **Analytics tables → Cloud:** Pre-computed aggregates shareable with leadership, contractors, and external stakeholders. BI tools (Tableau) connect directly to cloud schema. No performance penalty for analysts; materialized views refresh on schedule.

- **L2 Cache → Local:** Parquet redundancy with staging layer. Kept for analyst iteration speed and offline fallback. Synced with cloud staging on daily schedule; if cloud is unavailable, analysts continue locally without degradation.

---

## 3. Hybrid Architecture Design

This section describes the **data flow topology** and **query routing decisions** for the hybrid model.

### 3.1 Architecture Layers (Text Diagram)

```
LOCAL MACHINE (Socrata Toolkit)
├─ Raw Layer (Write-Optimized)
│  ├─ inspections_raw (398K) ← Socrata API fetch (daily 2am)
│  ├─ violations_raw (312K)   ← Socrata API fetch (daily 2am)
│  ├─ permits_raw (3.6M)      ← Socrata API fetch (weekly Sunday 1am)
│  └─ DuckDB file: data/local_db/nyc_mission_control.duckdb
│
├─ L2 Cache (Read-Optimized)
│  ├─ inspections_parquet.gz (398K)
│  ├─ violations_parquet.gz (312K)
│  └─ Directory: data/cache/
│
└─ dlt Sync Engine (Every 6 hours)
   ├─ Detect deltas: raw layer new/modified rows
   ├─ Package rows into JSON batches
   └─ POST → MotherDuck staging schema (retry 3x on failure)

                          CLOUD (MotherDuck)
                          ├─ Staging Schema
                          │  ├─ inspections (398K)      ← dedupe, type-cast, keys
                          │  ├─ violations (312K)       ← business rules, rollup
                          │  └─ permits_clean (3.6M)    ← geometry normalization
                          │
                          ├─ Analytics Schema
                          │  ├─ borough_completion_rates (5)      [view, refresh daily]
                          │  ├─ inspection_aging_by_borough (~30) [view, refresh daily]
                          │  └─ violations_trend (~365)           [view, refresh monthly]
                          │
                          └─ dbt Models (orchestration)
                             ├─ staging/*.sql (src → transform)
                             ├─ marts/*.sql (analytics views)
                             ├─ tests/ (field, referential, custom)
                             └─ dbt doc (lineage, column metadata)

QUERY ROUTING LOGIC
├─ Analyst asks: "violations in Brooklyn last 7 days?"
│  └─ Route to: MotherDuck staging.violations (cloud, fresh SLA)
│
├─ Analyst asks: "Inspection aging by borough?"
│  └─ Route to: MotherDuck analytics.inspection_aging_by_borough (cached view)
│
├─ Offline mode: "Show me violations I cached yesterday"
│  └─ Route to: Local data/cache/violations_parquet.gz (DuckDB query)
│
└─ Raw data debugging: "Why is object_id missing from raw?"
   └─ Route to: Local staging.inspections_raw (write-only, immutable)
```

### 3.2 Data Flow & Sync Strategy

**Ingestion Path (Socrata → Local → Cloud):**

1. **Nightly Fetch (Local, 2 AM):** APScheduler job calls `SocrataClient.fetch_dataframe()` for each of 3 core datasets. Socrata returns JSON rows; DuckDB appends to raw tables.

2. **Delta Detection (Local, 3 AM):** dlt compares row count and sample rows (MD5 hash) to previous snapshot. If delta > 0, mark table for sync; else skip (no API cost if unchanged).

3. **Cloud Push (dlt, 6 AM, 12 PM, 6 PM, 12 AM):** dlt batches new/modified rows (identified by `created_date`, `updated_date`, or `object_id` change markers). Posts JSON to MotherDuck staging tables via REST API (or dbt ephemeral loads).

4. **Staging Transform (MotherDuck, on sync or scheduled):** dbt runs staging models:
   - Deduplication: `SELECT DISTINCT ON (object_id) ... ORDER BY updated_date DESC`
   - Type casting: strings to dates, geometry validation
   - Key injection: business_key = borough + object_id (for upserts)
   - Column masking: PII fields encrypted (email, phone)

5. **Analytics Materialization (MotherDuck, daily 7 AM):** dbt runs mart models:
   - Aggregates: `GROUP BY borough` for completion rates, aging
   - Ranking: window functions for trend detection
   - Join enrichment: permits + inspections spatial overlap
   - Results cached in analytics schema (read-only for BI)

**Rollback & Fallback:**
- If cloud push fails (network, API error): dlt retries 3x with exponential backoff; falls back to local cache after 1 hour retry window.
- If staging transform fails (bad data type): dbt test catches and quarantines rows; alert to data eng; analysts fall back to previous snapshot.
- If analytics job fails: previous materialization remains; new job scheduled for next window.

### 3.3 Query Routing Rules

**When to Query Local vs. Cloud:**

| Scenario | Route | Reason |
|----------|-------|--------|
| "Raw data debugging" (inspections_raw) | Local DuckDB | Immutable source; no transforms expected; fast local SSD access. |
| "Analyst report on violations" | Cloud staging.violations | Fresh daily; dbt quality checks applied; shareable across team. |
| "Director asks for SLA forecast" | Cloud analytics.borough_completion_rates | Pre-computed, cached; no per-query compute. |
| "Offline analyst session" | Local L2 cache (parquet) | No internet needed; SLA may be 1 day old. |
| "Conflict detection (permits + inspections)" | Cloud (staging + spatial join) | 3.6M permits + 398K inspections = large cross join; cloud compute required. |
| "Exploratory: new hypothesis on data" | Local raw + staging | Fast iteration; no sharing needed; can dirty the data. |

---

## 4. dlt Pipeline Design (Socrata → MotherDuck)

dlt (data load tool) orchestrates automated incremental syncs from Socrata API to MotherDuck staging schema. This section specifies source configuration, sync strategy, and error handling.

### 4.1 Source Configuration

**Connector Type:** REST API (Socrata API)

**Authentication:**
- Socrata domain: `data.cityofnewyork.us`
- API token: Read from `SOCRATA_APP_TOKEN` env var (required for full corpus >2K rows)
- MotherDuck token: Read from `MOTHERDUCK_TOKEN` env var (MotherDuck account)

**Datasets to Sync (Phase 1):**

| Dataset | Fourfour | Rows | Incremental Key | Sync Frequency | Est. API Calls/Week |
|---------|----------|------|-----------------|-----------------|---------------------|
| inspections | dntt-gqwq | 398K | updated_date | Daily | 3 (1 full load every 2 weeks + deltas) |
| violations | 6kbp-uz6m | 312K | updated_date | Daily | 3 |
| street_permits | tqtj-sjs8 | 3.6M | created_date | Weekly | 1 (split into 4 chunks) |

### 4.2 Sync Strategy: Incremental CDC

**Change Data Capture Approach:**

1. **Last-Modified Watermark:** dlt tracks `max(updated_date)` from previous sync. Next sync fetches `WHERE updated_date > @last_max_date`.

2. **Incremental Key Columns:**
   - `inspections`: `updated_date` (when row was last modified in Socrata)
   - `violations`: `updated_date` (same)
   - `permits`: `created_date` (permits don't update; treated as append-only with yearly full reload)

3. **Upsert Strategy (Cloud):**
   - dbt staging models use `MERGE` or dbt's built-in incremental strategy (`incremental_strategy = 'merge'`)
   - **Match on:** `business_key = (borough || '-' || object_id)` (synthetic, deterministic primary key)
   - **Update:** All columns if `updated_date` in source > `_dbt_updated_at` in warehouse
   - **Insert:** If business_key not found in previous load

4. **Full Reload Trigger:**
   - Quarterly (every 90 days) or if schema drift detected, dlt performs `--full-refresh`
   - Clears staging table, reloads all rows from source
   - Cost: 1 large API call (~50 MB) per dataset, once per quarter

### 4.3 Error Handling & Retry Logic

**Socrata API Failures:**
- **Transient (5xx, timeout):** Retry 3 times with exponential backoff (1s, 4s, 16s)
- **Rate limit (429):** Pause 60s, retry once
- **Auth failure (401):** Alert data eng; stop pipeline until token refreshed
- **Not Found (404):** Log warning; skip dataset and continue (likely schema deprecation)

**MotherDuck API Failures:**
- **Connection timeout:** Retry 2 times; if persistent, queue rows to local DuckDB staging table for manual replay
- **Schema mismatch:** Validate row schema against dbt model before POST; reject and quarantine rows
- **Duplicate key:** Log row ID; write to dead-letter table `staging.{table}_dlq`; continue processing
- **Out of quota:** Alert finance team; stop ingestion; existing data remains queryable

**Monitoring:**
- Each dlt run logs: start time, source row count, rows sent to cloud, latency, errors
- Failure metrics emailed daily to data eng; alerting threshold: >2 consecutive failures or >5% error rate
- Logs persisted in local DuckDB `admin.dlt_execution_log` for audit trail

### 4.4 Estimated Performance & Cost

**Run Time:**
- Socrata API fetch: ~10 sec (inspections) + 8 sec (violations) + 45 sec (permits) = ~60 sec per full sync
- Delta detection & MD5: ~2 sec
- Cloud upload (via dlt): ~20 sec (3 API calls, batched)
- **Total:** ~90 seconds per 6-hour run (all three tables)

**Cost Estimate (Monthly):**
- Socrata API: Free (public portal; 50K rows/day soft limit but re-confirmed via app token)
- MotherDuck compute (6 syncs/day, ~20 rows/sec insert): 
  - Assume average 100K rows inserted daily across 3 tables
  - MotherDuck: $0.44/compute-hour; 6 × (20 sec + 10 sec overhead) = 180 sec/day = 5.4 compute-minutes/day
  - Monthly: 5.4 × 30 / 60 = 2.7 compute-hours = **~$1.19/month**
- MotherDuck storage (staging + analytics): ~150 MB, assuming $5/GB/month = **$0.75/month**
- **Total monthly cost:** ~$2.00 (negligible)

---

## 5. dbt Transformation Layers (MotherDuck)

dbt enforces data quality, documents lineage, and orchestrates the transform from raw (cloud-synced staging) to analytics-ready schemas.

### 5.1 Schema & Model Structure

**Staging Schema** (`staging_*` models in `dbt/models/staging/`):

```
staging/
├── stg_inspections.sql
│  ├── Input: MotherDuck.staging.inspections (synced from Socrata)
│  ├── Transforms:
│  │  - Dedup by (object_id): SELECT DISTINCT ON (object_id) ... ORDER BY updated_date DESC
│  │  - Type cast: created_date::DATE, inspector_id::VARCHAR
│  │  - Null handling: COALESCE(status, 'UNKNOWN')
│  │  - Add keys: business_key = concat(borough, '-', object_id)
│  ├── Output: staging.inspections (cleaned, keyed)
│  └── dbt tests: not_null (object_id), unique (object_id), relationship (borough in dim_borough)
│
├── stg_violations.sql
│  ├── Input: MotherDuck.staging.violations
│  ├── Transforms:
│  │  - Type cast: violation_date::DATE, violation_status::VARCHAR
│  │  - Business rule: Aggregate status by inspection_id (e.g., OPEN/CLOSED → ACTIVE if ANY OPEN)
│  │  - Join enrichment: injected_by_date = CASE WHEN STATUS='CLOSED' THEN CURRENT_DATE - closure_date ELSE NULL END
│  ├── Output: staging.violations
│  └── dbt tests: not_null (violation_id), valid_status (status IN ['OPEN', 'CLOSED', 'DISMISSED'])
│
└── stg_permits_clean.sql
   ├── Input: MotherDuck.staging.permits_clean
   ├── Transforms:
   │  - Geometry normalization: ST_GeomFromText(geometry_wkt)
   │  - Permit type enum: case/when to canonical permit_type
   │  - Date parsing: permit_issued_date::DATE
   ├── Output: staging.permits_clean
   └── dbt tests: geometry_valid (ST_IsValid(geometry)), not_null (permit_id)
```

**Analytics Schema** (`marts/` models):

```
marts/
├── fact_inspections.sql
│  ├── Input: staging.inspections, staging.violations
│  ├── Transforms:
│  │  - Join violations to inspections: LEFT JOIN on inspection_id
│  │  - Aggregate: COUNT(DISTINCT violation_id) as violation_count
│  │  - Add dimension: is_overdue = CASE WHEN CURRENT_DATE - inspection_date > 60 THEN TRUE
│  ├── Output: analytics.fact_inspections
│  └── Schema: inspection_id (PK), borough, violation_count, inspection_date, is_overdue, updated_at
│
├── dim_borough.sql
│  ├── Input: (hardcoded)
│  ├── Data: MN, BX, BK, QN, SI
│  └── Output: analytics.dim_borough (reference table, 5 rows)
│
├── mart_borough_completion_rates.sql [MATERIALIZED VIEW]
│  ├── Input: fact_inspections
│  ├── Transforms:
│  │  - SELECT borough, 
│  │         COUNT(*) as total_inspections,
│  │         COUNT(CASE WHEN violation_count = 0 THEN 1) as completed,
│  │         completed / total_inspections as completion_rate,
│  │         [Wilson CI formula] as ci_lower, ci_upper
│  │  - GROUP BY borough
│  ├── Output: analytics.borough_completion_rates (5 rows, refreshed daily 7 AM)
│  └── dbt test: not_null (borough), completion_rate between 0 and 1
│
├── mart_inspection_aging_by_borough.sql [MATERIALIZED VIEW]
│  ├── Input: fact_inspections
│  ├── Transforms:
│  │  - SELECT borough,
│  │         SUM(CASE WHEN is_overdue THEN 1 ELSE 0) as overdue_count,
│  │         AVG(CURRENT_DATE - inspection_date) as avg_days_aging
│  │  - GROUP BY borough
│  ├── Output: analytics.inspection_aging_by_borough (~30 rows: 5 borough × 6 severity)
│  └── dbt test: overdue_count >= 0
│
└── mart_violations_trend.sql [MATERIALIZED VIEW]
   ├── Input: staging.violations, staging.inspections
   ├── Transforms:
   │  - SELECT DATE_TRUNC('month', violation_date) as month,
   │         COUNT(*) as violation_count,
   │         COUNT(CASE WHEN status = 'OPEN' THEN 1) as open_count
   │  - GROUP BY month ORDER BY month DESC
   ├── Output: analytics.violations_trend (~365 rows: 1 per month × 12 months back + rolling)
   └── dbt test: violation_count > 0 for recent_months
```

### 5.2 Data Lineage & Documentation

**dbt lineage.yml:**

```yaml
version: 2

models:
  - name: stg_inspections
    description: "Deduplicated, cleaned inspections from Socrata. Single row per object_id."
    columns:
      - name: object_id
        description: "Unique identifier for inspection unit"
        tests: [unique, not_null]
      - name: borough
        description: "NYC borough (MN, BX, BK, QN, SI)"
        tests: [accepted_values: {values: [MN, BX, BK, QN, SI]}]
      - name: created_date
        description: "When inspection was created in Socrata"
        tests: [not_null]

  - name: fact_inspections
    description: "Fact table: 1 row per inspection with denormalized violation metrics"
    depends_on: [stg_inspections, stg_violations]
    columns:
      - name: inspection_id
        description: "FK to stg_inspections.object_id"
        tests: [unique, not_null, relationships: {to: source('socrata', 'stg_inspections'), field: 'object_id'}]

  - name: borough_completion_rates
    description: "Materialized view: ramp completion by borough with 95% Wilson Score CI"
    depends_on: [fact_inspections]
    materialized: view
    refresh_schedule: "0 7 * * *"  # Daily 7 AM
    columns:
      - name: completion_rate
        description: "Fraction of inspections with zero violations (closed/compliant)"
```

**Metadata Generated:**
- dbt docs site: `dbt docs generate && dbt docs serve` → accessible at http://localhost:8000
- Column-level lineage: "violations_trend.violation_count" ← "staging.violations.violation_id"
- Data dictionary: Each model has description + column tests + depends_on metadata
- Lineage DAG: exported as JSON for integration with data catalogs (Apache Atlas, Collibra)

### 5.3 Testing Strategy

**Test Types:**

1. **Generic Tests (dbt built-in):**
   - `not_null(column)` — ensures no NULL in key columns
   - `unique(column)` — object_id never duplicates
   - `relationships(column)` — foreign key references staging tables
   - `accepted_values(column, values)` — borough IN [MN, BX, BK, QN, SI]

2. **Singular Tests (custom SQL):**
   - `tests/check_no_future_dates.sql`: `SELECT * FROM staging.inspections WHERE created_date > CURRENT_DATE` (expect 0 rows)
   - `tests/check_violation_count_nonnegative.sql`: `SELECT * FROM analytics.fact_inspections WHERE violation_count < 0` (expect 0 rows)
   - `tests/check_completion_rate_bounds.sql`: `SELECT * FROM analytics.borough_completion_rates WHERE completion_rate < 0 OR completion_rate > 1` (expect 0 rows)

3. **Data Freshness Tests (dbt-expectations or custom):**
   - `staging.inspections.created_date MAX < CURRENT_DATE - INTERVAL '2 days'` → WARN (SLA breach)
   - `staging.violations.created_date MAX < CURRENT_DATE - INTERVAL '2 days'` → WARN (SLA breach)

4. **Run Cadence:**
   - Nightly after dlt sync & dbt run: Full test suite (5–10 min)
   - Weekly metadata audit: Column count stable, no orphaned tables
   - Monthly: Deep freshness audit vs. Socrata source

---

## 6. Multi-Org Sharing Strategy

**Current Scope:** This design assumes **single-organization** (NYC DOT only). Multi-org sharing is deferred to Phase 3+.

**If multi-org is required later, the architecture supports isolation via:**

1. **Schema-per-org isolation:**
   ```sql
   -- Shared MotherDuck instance, separate namespaces
   CREATE SCHEMA "dot_manhattan" -- DOT Manhattan borough data
   CREATE SCHEMA "dot_bronx"     -- DOT Bronx borough data
   CREATE SCHEMA "contractor_acme" -- ACME Construction (contractor)
   ```

2. **Row-level security (RLS):**
   - MotherDuck supports `CREATE POLICY` (DuckDB 1.0+)
   - Policies: `contractors CAN SELECT FROM dot_manhattan.permits WHERE permit_type != 'STRUCTURAL'`

3. **Data sharing agreements:**
   - Metrics published to `analytics.public_metrics` (shared)
   - Raw data stays in org schema (private)
   - Contractors see only aggregates, no permit details

4. **Governance:**
   - dbt: separate `dbt_profiles.yml` per org with isolated target schemas
   - Access control: MotherDuck IAM (role-based) + column-level masking (PII)
   - Audit log: All queries logged; shareable metrics tagged with `@shareable` dbt meta

---

## 7. POC Roadmap (Weeks 7–11)

This section details a **3-phase proof-of-concept execution plan** for Phase 3 (June 24–July 15, 2026).

### 7.1 Phase 1 POC: Single Table (Week 7–8, Jun 24–Jul 5)

**Objective:** Load `violations` dataset end-to-end; validate incremental sync and dbt staging pipeline.

**Scope:**
- dlt project: Socrata API → MotherDuck (violations only)
- dbt staging: `stg_violations` with dedup + business rules + tests
- Manual validation: row counts match, no duplicates, SLA fresh

**Tasks:**
1. **Setup (Week 7, 1 day):**
   - Create MotherDuck account (free tier, 100 GB storage)
   - Install dlt + dbt locally; configure `dlt_profiles.yml` and `dbt_profiles.yml`
   - Create cloud staging schema: `CREATE SCHEMA staging`
   - Create `.env` with `MOTHERDUCK_TOKEN`, `SOCRATA_APP_TOKEN`

2. **dlt Pipeline (Week 7, 2 days):**
   - Write dlt resource: `@dlt.resource def violations_from_socrata() → Iterator[dict]`
   - Implement: SOQL filter `WHERE updated_date > @last_sync_date`
   - Test: Run full load (312K rows), verify count
   - Implement incremental: Run delta sync (1K rows), verify new rows appended

3. **dbt Staging Model (Week 8, 2 days):**
   - Write `models/staging/stg_violations.sql` with dedup, type casting, key injection
   - Add `dbt_project.yml` config: `materialized: table, persist_docs: true`
   - Add tests: `not_null(violation_id)`, `unique(violation_id)`, `valid_status`
   - Run `dbt test` locally against MotherDuck; verify all 5 tests pass

4. **Validation (Week 8, 1 day):**
   - Query cloud: `SELECT COUNT(*) FROM staging.violations` → expect 312K
   - Compare to Socrata: fetch 100 random rows, compare columns + values
   - Freshness check: `SELECT MAX(created_date) FROM staging.violations` → expect < 2 days old
   - Cost analysis: Check MotherDuck billing → expect ~$0.10–$0.50

**Deliverables:**
- Working dlt project in `dlt_projects/violations_poc/`
- dbt staging model + tests in `dbt/models/staging/`
- POC summary: row counts, latency, cost, blockers

**Success Criteria:**
- Violations table syncs incrementally every 6 hours
- dbt tests pass with 100% row validation
- Cost < $1/month
- Latency: full load in <5 min, delta in <1 min

---

### 7.2 Phase 2 POC: Expand to 3 Tables + Analytics (Week 9–10, Jul 6–19)

**Objective:** Add inspections + permits to dlt; build analytics marts with materialized views.

**Scope:**
- dlt: 3 pipelines (violations, inspections, permits) running in parallel
- dbt staging: `stg_inspections`, `stg_permits_clean` with joins + enrichment
- dbt analytics: `mart_borough_completion_rates` materialized view
- Manual validation: Join quality, metric accuracy vs. Socrata source

**Tasks:**

1. **dlt Expansion (Week 9, 2 days):**
   - Add `inspections_from_socrata()` and `permits_from_socrata()` resources
   - Configure incremental keys: inspections/violations → `updated_date`, permits → `created_date`
   - Test parallel execution: all 3 pipelines run in <3 min
   - Implement retry logic: test failure recovery (simulate API timeout, retry 3x)

2. **dbt Staging (Week 9, 2 days):**
   - Write `stg_inspections.sql` with joins to violations (LEFT JOIN on inspection_id)
   - Write `stg_permits_clean.sql` with geometry normalization, permit type enum
   - Add foreign key tests: inspections.borough references dim_borough.borough
   - Run full test suite: expect 20+ tests

3. **dbt Analytics (Week 10, 2 days):**
   - Write `fact_inspections.sql`: denormalized fact table with violation_count, overdue flag
   - Write `mart_borough_completion_rates.sql` materialized view:
     ```sql
     SELECT borough,
            COUNT(*) as total_inspections,
            COUNT(CASE WHEN violation_count = 0 THEN 1) as completed,
            completed / total_inspections as completion_rate,
            [Wilson Score CI formula] as ci_lower, ci_upper
     FROM fact_inspections
     GROUP BY borough
     ```
   - Write `mart_inspection_aging_by_borough.sql` view
   - Add refresh schedule: `dbt run --select tag:daily` at 7 AM via dbt Cloud or cron

4. **Validation (Week 10, 1 day):**
   - Manual query: `SELECT * FROM analytics.borough_completion_rates` → verify 5 rows (one per borough)
   - Spot-check: Manual count violations per borough in Socrata vs. MotherDuck
   - CI validation: Recalculate Wilson Score in Python; compare to dbt output
   - Performance: Query analytics view; latency should be <1 sec (cached)

**Deliverables:**
- 3 dlt pipelines (violations, inspections, permits)
- 5 dbt models (3 staging, 2 marts)
- 20+ dbt tests (generic + singular)
- Analytics validation report: metric accuracy, latency, cost

**Success Criteria:**
- All 3 pipelines sync incrementally on schedule
- Analytics views refresh daily; completion rates match manual calculation (±0.1%)
- Cost < $5/month (compute + storage)
- Zero test failures in nightly dbt runs

---

### 7.3 Phase 3: Production Cutover (Week 11+, Jul 20+)

**Objective:** Promote POC to production; retire local DuckDB for analytics; establish runbooks.

**Scope:**
- Migrate analytics queries from local DuckDB to MotherDuck
- Update Streamlit app to read analytics from cloud
- Set up dbt Cloud for scheduled orchestration + notifications
- Deploy monitoring dashboard (dbt Cloud metrics + MotherDuck alerts)

**Tasks:**

1. **App Migration (1 week):**
   - Update `app/services/agency_service.py` to query cloud analytics schema instead of local
   - Example: `SELECT * FROM motherduck.analytics.borough_completion_rates` (replace local DuckDB query)
   - Test: Run full Streamlit app locally; verify all charts render correctly
   - Performance: Measure latency; should be <2 sec (cloud queries cached)

2. **Orchestration (1 week):**
   - Sign up for dbt Cloud (free tier, 1 job run/day; paid tier for hourly runs)
   - Deploy dbt project to GitHub; configure dbt Cloud connection
   - Create 2 dbt Cloud jobs:
     - Job 1 (nightly 2 AM): `dbt run --select tag:daily` (dlt sync → dbt staging)
     - Job 2 (daily 7 AM): `dbt run --select tag:materialized` (analytics refresh)
   - Setup: Slack notifications on failure

3. **Monitoring (3 days):**
   - Create dbt Cloud dashboard: track run latency, test pass rate, model row counts
   - Setup MotherDuck alerts: storage quota 80%, compute cost spike (>$10/day)
   - Setup Socrata sync alerts: API errors, row count variance (>10% change)
   - Runbook: What to do if dbt job fails (inspect logs, rerun, rollback)

4. **Cutover (1 week):**
   - Parallel run: Keep local DuckDB + cloud MotherDuck for 1 week; compare results
   - Gradual migration: Redirect 20% of analyst queries to cloud; monitor for errors
   - Archival: Snapshot local DuckDB analytics tables (last version); keep in cold storage
   - Documentation: Update CLAUDE.md with cloud architecture; how to query MotherDuck

**Deliverables:**
- Updated Streamlit app (cloud-ready)
- dbt Cloud jobs (deployed, tested)
- Monitoring dashboard (dbt Cloud + MotherDuck)
- Runbook: Incident response for sync failures, cost overruns
- Post-cutover summary: cost actual vs. budget, latency gains, team feedback

**Success Criteria:**
- Zero failed dbt jobs in first month of production
- Analyst queries latency <2 sec (vs. <1 sec local, acceptable tradeoff)
- Monthly cost $5–$10 (within budget)
- All analysts can query cloud schema without retraining

---

## 8. Cost & Performance Analysis

### 8.1 Pricing Comparison

| Metric | Local DuckDB | MotherDuck Estimate |
|--------|--------------|-------------------|
| **Compute** | Free (on-machine) | ~$0.44/hour; 2.7 hrs/month = $1.19/month |
| **Storage** | 600 MB + 100 GB cache = $0 | 150 MB staging + 5 MB analytics = $5 tier/month (minimum) |
| **Data Egress** | Free (internal) | $0 (MotherDuck internal) |
| **Support** | Free (open source) | $0 (free tier) / $200/month (pro) |
| **Total** | $0/month | $6–$7/month (free tier) or $200+/month (pro with SLA) |

**Break-Even Analysis:**
- Local DuckDB: No monthly cost but requires 8GB RAM + 100GB SSD locally (capital cost ~$500)
- MotherDuck: $7/month recurring; high analyst value (multi-user access, no local bottleneck)
- **Recommendation:** Pursue MotherDuck for non-cost reasons (collaboration, governance, portability)

### 8.2 Query Performance

**Latency Comparison:**

| Query | Local DuckDB | MotherDuck | Delta |
|-------|--------------|-----------|-------|
| `SELECT COUNT(*) FROM violations` (312K rows) | 10 ms | 200 ms | +190 ms (network + cloud) |
| `SELECT * FROM borough_completion_rates` (5 rows, cached) | 5 ms | 50 ms | +45 ms |
| `SELECT * FROM violations WHERE borough='MN'` (50K rows, filter) | 50 ms | 300 ms | +250 ms |
| Complex join: permits (3.6M) + inspections (398K) | 2 sec | 500 ms | -1.5 sec (cloud parallelism) |

**Analysis:**
- Simple queries: Local is faster (network latency overhead ~200 ms)
- Complex queries: Cloud is faster (parallelism on large datasets)
- Acceptable for analyst workload: 200 ms latency is imperceptible (humans notice >300 ms)
- **Recommendation:** Optimize for complex queries via materialized views; accept latency for simple queries

---

## 9. Risk Mitigation

### 9.1 Data Loss & Integrity

**Risk:** Cloud data loss due to MotherDuck outage or accidental deletion.

**Mitigation:**
- **Backup strategy:** Nightly snapshot of MotherDuck staging schema to Parquet files (stored on local SSD)
  ```
  dbt run-operation backup_to_parquet --args '{table_name: staging.violations}'
  ```
- **ACID guarantees:** DuckDB guarantees ACID (same as local); MotherDuck inherits
- **Recovery:** If cloud data lost, restore from Parquet backup in <1 hour (full reload)

### 9.2 Vendor Lock-In

**Risk:** Switching from MotherDuck to another vendor is costly.

**Mitigation:**
- **DuckDB portability:** All SQL is standard DuckDB; zero vendor-specific syntax
- **dbt independence:** dbt profiles are pluggable; easily swap `type: motherduck` for `type: duckdb` (local)
- **Data export:** Any MotherDuck data can be exported as Parquet in minutes
- **Cost of exit:** ~2 hours to redirect queries back to local DuckDB; no data loss

### 9.3 Cost Overruns

**Risk:** MotherDuck compute bill spikes due to runaway queries or large data import.

**Mitigation:**
- **Quota enforcement:** Set MotherDuck account limit to $20/month; auto-suspend on breach
- **Query monitoring:** dbt Cloud logs all queries; alert if any query takes >60 sec
- **Data size limits:** dlt enforces batch size caps (max 100K rows/batch) to prevent memory spike
- **Gradual migration:** Phase 1 (violations only) keeps cost <$2/month; expand only after cost validated

### 9.4 Performance Regression

**Risk:** Cloud queries are too slow; analysts revert to local workload.

**Mitigation:**
- **Materialized views:** Pre-compute borough aggregates; serve cached results (guaranteed fast)
- **Query optimization:** dbt models use projections (SELECT only needed columns) and filters (WHERE early)
- **Indexing:** MotherDuck automatically indexes on primary keys; dbt meta `+indexes` for additional indexes
- **Parallel queries:** MotherDuck supports concurrent queries; no single-user bottleneck

### 9.5 Compliance & Data Residency

**Risk:** Data stored in MotherDuck cloud; NYC DOT policy may require on-premise data.

**Mitigation:**
- **Data classification:** Classify inspections/violations as non-sensitive (public Socrata data)
- **Local raw layer:** Retain sensitive raw data locally; only non-sensitive clean data to cloud
- **Residency:** MotherDuck has US-East data center option; confirm with leadership
- **Alternative:** Keep all data local; use MotherDuck for analytics only (zero sensitivity data)

---

## 10. Open Questions for Week 6 Review

These questions require leadership input before Phase 3 implementation begins. Answers will finalize the architecture.

1. **Sync Priority:** Should violations move to cloud first, or all three datasets (violations + inspections + permits) simultaneously?
   - **Trade-off:** Single table reduces POC scope; all three provides immediate collaboration benefit
   - **Recommendation:** Start with violations + inspections (daily updates, analyst-heavy); defer permits to Phase 3b

2. **Multi-Org Sharing Requirement:** Will NYC DOT share datasets with contractors, external agencies, or community partners in the next 12 months?
   - **Impact:** If yes, add row-level security (RLS) and workspace isolation to POC scope
   - **Recommendation:** Defer to Phase 4; current design is single-org compatible

3. **Cost Budget:** What is the acceptable monthly cloud spend for analytics platform?
   - **Current estimate:** $5–$10/month (storage + compute)
   - **Recommendation:** Approve up to $50/month for future scale (10× data volume)

4. **Real-Time Sync Requirement:** Do analysts need real-time data (updates within 1 hour) or daily is acceptable?
   - **Impact:** Real-time → more dlt runs (12/day vs. 4/day) → higher cost
   - **Current design:** 4 syncs/day (every 6 hours); cost $1.19/month
   - **Real-time design:** 12 syncs/day; cost ~$3.60/month
   - **Recommendation:** Start with 6-hour sync; upgrade to 2-hour if demand grows

5. **Analytics Schema:** Should analytics tables be multi-tenant (one borough per row) or single-tenant (per-borough views)?
   - **Multi-tenant example:** `SELECT * FROM borough_completion_rates WHERE borough='MN'` (5 rows total, filter in query)
   - **Single-tenant example:** Separate view per borough: `analytics.manhattan_completion_rate` (1 row per view)
   - **Recommendation:** Multi-tenant (simpler dbt, scalable to 50 boroughs; standard fact table pattern)

6. **dbt Orchestration:** Should dbt Cloud be used for scheduled job runs, or local cron?
   - **dbt Cloud:** $300/month (paid tier with SLA); includes web UI, notifications, run history
   - **Local cron:** Free; requires SSH access to machine; less observability
   - **Recommendation:** Start with local cron + APScheduler; upgrade to dbt Cloud at Phase 4 (when analysts want job visibility)

7. **Parquet Cache Strategy:** Should L2 Parquet cache be retained alongside cloud analytics, or deprecated?
   - **Keep:** Offline fallback; fast local iteration; cold backup of analytics
   - **Retire:** Simplify stack; one source of truth (cloud); save 100 GB storage locally
   - **Recommendation:** Keep for 6 months (safety net); retire once production cloud is stable

---

## Conclusion

This design document specifies a **realistic, phased migration** from local DuckDB to MotherDuck cloud for the NYC DOT Socrata Toolkit. The hybrid model (raw local + staging/analytics cloud) balances cost, collaboration, and governance while maintaining zero vendor lock-in and full portability.

**Key Takeaways:**
- **Week 7–8 POC:** Load violations table; validate incremental sync and dbt pipeline
- **Week 9–10 POC:** Expand to 3 datasets; build analytics views; validate join quality
- **Week 11+ Production:** Promote to production; update Streamlit app; establish monitoring
- **Cost:** $5–$10/month (negligible compared to cloud benefits)
- **Timeline:** 3 weeks POC → 1 week cutover → live production by early July 2026

**Next Steps (Week 6):**
1. Review this document with leadership; clarify open questions in Section 10
2. Finalize sync frequency (4/day vs. 12/day), multi-org requirement, budget cap
3. Confirm MotherDuck account provisioning (free tier available; upgradeable)
4. Week 7: Engineer begins Phase 3 POC

---

**Appendix: DuckDB SQL Reference for MotherDuck**

All DuckDB SQL is supported in MotherDuck without modification:

```sql
-- Standard DuckDB syntax (works in MotherDuck)
SELECT * FROM staging.violations WHERE created_date > NOW() - INTERVAL '2 days';
SELECT DISTINCT ON (object_id) * FROM staging.violations ORDER BY updated_date DESC;
SELECT borough, COUNT(*) FROM staging.violations GROUP BY borough;
SELECT ST_GeomFromText(geometry) FROM staging.permits_clean;
SELECT * REPLACE (UPPER(borough) AS borough) FROM staging.inspections;
```

No vendor-specific syntax in this design; full portability guaranteed.

---

**Document Metadata:**
- **Version:** 1.0
- **Author:** NYC DOT Data Engineering
- **Date:** 2026-06-10
- **Status:** Ready for Week 6 Leadership Review
- **Next Review:** Week 6 (2026-06-16)
