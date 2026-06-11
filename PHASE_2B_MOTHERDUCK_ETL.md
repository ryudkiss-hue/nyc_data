# Phase 2B: MotherDuck Integration + Generic ETL

**Status:** PLANNING  
**Created:** 2026-06-11  
**Depends on:** Phase 2A (Dash consolidation complete)  

---

## Overview

Phase 2B focuses on:
1. **MotherDuck Integration** — Permanent L3 cloud cache (12-month retention)
2. **Generic ETL Framework** — Extensible stage_dataset() for all 24 datasets
3. **Advanced Analytics** — Materialized analytics layer with 50+ KPIs

---

## Deliverables

### 2B.1: MotherDuck Cloud Integration
**Files to create:**
- `src/socrata_toolkit/motherduck/` — MD client wrapper
  - `__init__.py`
  - `client.py` — MotherDuck API client
  - `schema.py` — Schema management
  - `query.py` — Query execution
  - `cache.py` — Cloud cache management
- `src/socrata_toolkit/core/motherduck_sync.py` — Sync orchestration

**Specifications:**
- Authentication via MOTHERDUCK_TOKEN
- Create 3 databases: raw_cloud, staging_cloud, analytics_cloud
- Initial sync: 12-month historical data
- Daily incremental sync (delta fetch)
- 99.9% uptime SLA
- Cost monitoring & optimization

### 2B.2: Generic stage_dataset() Function
**Files to create:**
- `src/socrata_toolkit/pipeline/generic_staging.py` — Core staging
  - `stage_dataset(dataset_key, source_format, transformations)`
  - Auto-detect schema from sample
  - Apply transformations (class mapping, value mapping)
  - Deduplication & type casting
  - Validation rules

**Design Pattern:**
```python
def stage_dataset(
    dataset_key: str,
    raw_table: str,
    staging_table: str,
    transformations: Dict[str, Any] = None,
    dedup_cols: List[str] = None
) -> StagingResult:
    """
    Generic staging function for all 24 datasets.
    
    - Load from raw_* table
    - Apply transformations (classification, mapping, derivations)
    - Deduplicate and validate
    - Materialize to staging_* table
    - Return metrics (rows in/out, errors)
    """
```

**Transformations Registry:**
- Classification: Violations, Dismissals, Ramp Status, etc.
- Mapping: Borough codes, Material codes, Status enums
- Derivations: Days elapsed, Cost per unit, Completion pct
- Filtering: Remove test records, filter by date

### 2B.3: Analytics Materialization Layer
**Files to create:**
- `src/socrata_toolkit/analytics/materialization.py` — Mart builder
  - `create_violation_mart()` — Violations KPIs
  - `create_ramp_mart()` — Ramp completion KPIs
  - `create_permit_mart()` — Permit coordination KPIs
  - `create_quality_mart()` — Data quality KPIs
  - `create_spatial_mart()` — Geographic analysis

**KPI Categories (50+ total):**

**Violation Analytics:**
- Violation count by borough/month/material
- Open violations trend
- Average time-to-completion
- Cost per violation
- Rework rate (violations reopened)
- SLA compliance rate

**Ramp Accessibility:**
- Completion rate (% of ramps completed)
- 95% confidence interval (Wilson Score)
- Ramps completed this month
- Cost per ramp completion
- Predicted completion date
- Equity analysis (which neighborhoods lagging)

**Permit Coordination:**
- Active permits count
- Permit-to-inspection conflicts (spatial)
- Overlap detection (permits + ongoing work)
- Average permit duration
- Permit approval time trend

**Quality Metrics:**
- Completeness (% non-null)
- Uniqueness (% duplicate records)
- Validity (% valid values per column)
- Timeliness (age of newest record)
- Composite quality score (0-100)

**Spatial Analytics:**
- Violation density (per km²)
- Hotspot clusters (DBSCAN)
- Coverage gaps (neighborhoods without data)
- Distance-to-nearest-inspector
- Routing optimization (TSP)

### 2B.4: Data Validation & Quality Gates
**Files to create:**
- `src/socrata_toolkit/quality/validation_rules.py` — Quality rules
  - Row count assertions
  - Schema validation
  - Business rule checks
  - Freshness validation

**Quality Gates:**
- After each stage: count before/after
- After staging: null % per column
- After analytics: KPI reasonableness checks
- SLA compliance: data age vs. threshold

### 2B.5: Incremental Sync Strategy
**Implementation:**
- Track `last_fetch_time` per dataset
- Use SOQL `$where` filter: `updated_at > last_fetch_time`
- Load delta into raw staging table
- Merge into existing raw tables
- Archive removed rows (soft delete)
- Detect schema changes (drift detection)

---

## Testing

### Unit Tests
- `tests/test_motherduck_client.py` — MD connectivity
- `tests/test_generic_staging.py` — Staging logic
- `tests/test_analytics_mart.py` — KPI calculations
- `tests/test_delta_sync.py` — Incremental fetch

### Integration Tests
- Full sync cycle: 24 datasets to MD (1 hour)
- Quality gate validation
- KPI calculation correctness
- Cross-dataset referential integrity

### Data Quality Tests
- Null % within acceptable range
- Duplicate count within threshold
- Freshness: data age < SLA
- Schema matches expected (no drift)

---

## Technical Stack

### MotherDuck
- Connection: Postgres endpoint or native DuckDB
- Authentication: MOTHERDUCK_TOKEN env var
- Query engine: DuckDB SQL
- Storage: Native MD or DuckLake (TBD)

### ETL Framework
- Python 3.11+
- pandas for transformations
- DuckDB for local staging
- MotherDuck for cloud persistence
- APScheduler for nightly runs

### Monitoring
- Metrics: rows processed, errors, duration, cost
- Alerts: Slack webhook for failures
- Dashboard: refresh metrics visible in Dash

---

## Success Criteria

✅ MotherDuck connected & authenticated  
✅ All 24 datasets synced to MD (12-month history)  
✅ Generic stage_dataset() works for all 24 datasets  
✅ 50+ KPIs materialized and accurate  
✅ Delta sync completes in <10 minutes nightly  
✅ Quality gates enforced (no invalid data ships)  
✅ Zero data loss in sync cycles  
✅ All 109+ tests pass  

---

## Next Steps

1. **Set up MotherDuck account** — Sign up, get token
2. **Create MD databases** — raw_cloud, staging_cloud, analytics_cloud
3. **Implement generic staging** — Test with 3 sample datasets
4. **Build analytics marts** — KPI definitions & SQL
5. **Incremental sync** — Delta fetch implementation
6. **Validation framework** — Quality gates & assertions
7. **Testing & QA** — Full cycle testing
8. **Documentation** — User guide + developer docs

---

## Estimated Effort

- MD setup & client: 1 day
- Generic staging framework: 2 days
- Analytics materialization: 2 days
- Delta sync & validation: 1 day
- Testing & QA: 1 day
- Documentation: 1 day
- **Total: ~1 week**

---

## Risk Mitigation

**Risk:** Data loss in sync  
**Mitigation:** Backup raw data locally, validate counts before/after

**Risk:** Schema drift undetected  
**Mitigation:** Schema change detection + alerts

**Risk:** MD quota exceeded  
**Mitigation:** Monitor query costs, set alerts at 80% budget

**Risk:** Incremental sync misses updates  
**Mitigation:** Periodic full resync (weekly), validate overlap

---

## Future Enhancements (Phase 3+)

- Real-time streaming (Kafka → MotherDuck)
- Data sharing (publish curated datasets)
- Advanced analytics (ML-based forecasting)
- Federated queries (query multiple MD databases)
- Time-travel (temporal queries of historical snapshots)

---

**Owner:** Claude (Phase 2B lead)  
**Status:** Ready for implementation  
**Priority:** P0 (infrastructure foundation for Phase 3+)
