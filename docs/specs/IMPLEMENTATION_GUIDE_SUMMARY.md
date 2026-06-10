# Phase 1 Pipeline Implementation Guide — Executive Summary

## What You'll Build

A production data pipeline that loads NYC sidewalk inspection data from Socrata API → cleans & stages it → materializes 5 pre-computed analytics views in DuckDB. The complete pipeline runs in <30 seconds and passes 15+ validation checks.

**Weeks 2-3: 45 hours of implementation (TDD pattern)**

---

## The Big Picture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PHASE 1 PIPELINE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Socrata API                                                   │
│  ├─ Inspections (dntt-gqwq, ~398K rows)                       │
│  ├─ Violations (6kbp-uz6m, ~312K rows)                        │
│  └─ Permits (tqtj-sjs8, ~3.6M rows)                           │
│         ↓                                                       │
│  [LOAD] raw.inspection, raw.violations, raw.street_permits    │
│         ↓                                                       │
│  [STAGE] Deduplicate, type-cast, join related data            │
│  ├─ staging.inspections (~390K deduplicated)                  │
│  ├─ staging.permits (~3.4M deduplicated)                      │
│  └─ staging.ramps (~210K deduplicated)                        │
│         ↓                                                       │
│  [MATERIALIZE] 5 analytics views                              │
│  ├─ analytics.borough_summary (KPIs by borough)               │
│  ├─ analytics.time_series_snapshots (monthly trends)          │
│  ├─ analytics.material_analysis_mart (failure rates by type)  │
│  ├─ analytics.clustering_features (feature matrix)            │
│  └─ analytics.geo_animation_mart (monthly heatmaps)           │
│         ↓                                                       │
│  [VALIDATE] Counts, uniqueness, freshness, business rules     │
│         ↓                                                       │
│  Ready for Streamlit dashboard (Week 4)                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## What's Already Built (Skeleton)

These files exist but are placeholders:

- `src/socrata_toolkit/core/duckdb_pipeline.py` — Orchestrator (empty bodies)
- `src/socrata_toolkit/core/duckdb_analytics_models.py` — View templates
- `src/socrata_toolkit/quality/duckdb_validation.py` — Validation stubs

**Your job: Fill in the complete implementation.**

---

## 6-Part Implementation Plan (Weeks 2-3)

### **PART 1: Raw Data Loading (4 hours)**
- Implement `load_raw_from_socrata()` — fetches full Socrata datasets via API
- Write unit tests for raw loading
- **Commit:** Raw loading + tests

### **PART 2: Staging Transformations (12 hours)**
- Implement `stage_inspections()` — deduplicate, join violations, compute metrics
- Implement `stage_permits()` — deduplicate, add derived columns (days_to_completion)
- Implement `stage_ramps()` — deduplicate, join complaints, map boroughs
- Write tests for each staging function
- **Commit:** All 3 staging functions + tests

### **PART 3: Analytics Views (8 hours)**
- Implement 5 analytics views (borough_summary, time_series, material, clustering, geo_animation)
- Each view is a pre-computed query ready for Streamlit visualization
- Write tests that query each view
- **Commit:** All analytics views + tests

### **PART 4: Validation Framework (8 hours)**
- Implement 4 validation functions:
  - `validate_counts()` — Ensure <5% data loss
  - `validate_uniqueness()` — No duplicates on PKs
  - `validate_business_rules()` — condition_score [0,100], no future dates
  - `validate_freshness()` — Data <24h old
- Write validation tests
- **Commit:** Validation framework + tests

### **PART 5: Integration Tests (10 hours)**
- Write end-to-end test: `test_full_pipeline_execution()` — Complete pipeline <30s
- Write performance tests (raw <15s, staging <10s, analytics <5s)
- Verify row counts match expectations
- Achieve >40% test coverage
- **Commit:** Integration + performance tests

### **PART 6: Documentation (3 hours)**
- Create `docs/PIPELINE_SPECIFICATION.md` — Architecture, data flow, row counts
- Create `docs/PIPELINE_OPERATOR_RUNBOOK.md` — How to run, troubleshoot, recover
- **Commit:** Documentation

---

## Key Data Flows

### Raw → Staging: Inspections

```
raw.inspection (398K rows)
├─ Rank by objectid, keep most recent inspection_date
├─ Cast types: condition_score → INTEGER, lat/lon → DOUBLE
├─ Deduplicate → ~390K rows (2% loss)
└─ JOIN raw.violations to count violations per inspection
    └─ Aggregate: violation_count, first_date, last_date, avg_severity

→ staging.inspections (390K rows)
  Columns: objectid, inspection_date, condition_score, material_type,
           latitude, longitude, borough, violation_count, first_violation_date,
           last_violation_date, avg_violation_severity, staged_at
```

### Staging → Analytics: Borough Summary

```
staging.inspections (390K rows)
├─ GROUP BY borough
├─ COUNT(DISTINCT objectid) → inspection_count
├─ AVG(condition_score) → avg_condition_score
├─ SUM(violation_count) → total_violations
├─ COUNT(CASE WHEN condition_score >= 80) → good_condition_count
└─ Percentage calculations

→ analytics.borough_summary (5 rows: MN, BK, QN, BX, SI)
  Columns: borough, inspection_count, avg_condition_score, total_violations,
           good_condition_count, pct_good_condition, pct_poor_condition,
           last_updated
```

---

## Success Criteria

By end of Week 3, verify:

| Criterion | Target | Check |
|-----------|--------|-------|
| **Pipeline Execution** | <30 seconds end-to-end | `pytest tests/test_pipeline_integration.py::test_full_pipeline_execution -v` |
| **Data Loss** | <5% | Validation log shows loss_pct ≤ 5.0 |
| **Validation Checks** | All pass | `validate_counts`, `validate_uniqueness`, `validate_business_rules` return `valid=True` |
| **Row Counts** | Match expectations | Inspections ~390K, Permits ~3.4M |
| **Tests** | 15+ passing | `pytest tests/test_pipeline_*.py -v` shows 15+ passed |
| **Coverage** | >40% | `pytest tests/test_pipeline_*.py --cov=src/socrata_toolkit` |
| **Idempotence** | Safe to re-run | `test_full_pipeline_execution` can run twice with same result |

---

## Essential SQL Patterns

### Deduplication (Keep Most Recent)

```sql
WITH ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY objectid ORDER BY inspection_date DESC) as rn
    FROM raw.inspection
)
SELECT * FROM ranked WHERE rn = 1
```

### Aggregation with Coalesce

```sql
SELECT 
    objectid,
    COALESCE(violation_count, 0) as violation_count,
    CASE WHEN violation_count > 0 THEN 'has_violations' ELSE 'clean' END
FROM staging.inspections
```

### Window Functions for Trends

```sql
SELECT
    month,
    borough,
    inspection_count,
    LAG(inspection_count) OVER (PARTITION BY borough ORDER BY month) as prev_month,
    ROUND(100.0 * (inspection_count - prev_month) / prev_month, 2) as pct_change
FROM monthly_agg
```

---

## Testing Strategy

**Unit Tests** (each transformation function)
- Verify table created
- Check row counts reasonable
- Validate schema (no null keys)
- Test error handling

**Integration Tests** (full pipeline)
- Load + Stage + Materialize + Validate in one test
- Verify <30 second execution
- Check all 5 analytics views created
- Idempotence: run twice, same result

**Performance Tests**
- Raw loading <15s (Socrata API rate-limited)
- Staging <10s
- Analytics <5s

**Example Test:**
```python
def test_stage_inspections_success(pipeline_with_raw_data):
    result = pipeline_with_raw_data.stage_inspections()
    assert result["status"] == "success"
    assert result["rows"] > 350000
    
    # Verify no null PKs
    null_count = pipeline_with_raw_data.conn.execute(
        "SELECT COUNT(*) FROM staging.inspections WHERE objectid IS NULL"
    ).fetchone()[0]
    assert null_count == 0
```

---

## Environment & Dependencies

**Before Week 2:**

```bash
# Clone repo
git clone <repo>
cd nyc_data

# Set API token (required for >2K rows)
export SOCRATA_APP_TOKEN=<your-token>

# Install dependencies
pip install -e ".[dev]"

# Verify environment
pytest tests/test_import_shims.py
```

**Key libraries:**
- `duckdb` — In-process SQL database
- `pandas` — Fetch Socrata data as DataFrames
- `pytest` — Testing
- `logging` — Debug output

---

## Common Pitfalls & Solutions

| Problem | Solution |
|---------|----------|
| Tests fail with "SOCRATA_APP_TOKEN not set" | `export SOCRATA_APP_TOKEN=<token>` before running tests |
| "Table already exists" error | Ensure `DROP TABLE IF EXISTS` before CREATE |
| Staging takes >10s | May need to partition large datasets; check DuckDB memory |
| Row counts way off | Check if Socrata returned sample instead of full corpus |
| Validation shows >5% loss | Review deduplication logic; may be filtering too aggressively |

---

## Deliverables

**Code (1,300+ lines):**
- `load_raw_from_socrata()` — Socrata API integration
- `stage_inspections()`, `stage_permits()`, `stage_ramps()` — Transformations
- 5 analytics view functions
- 4 validation functions
- 9 test files (15+ tests, >40% coverage)

**Documentation:**
- `PIPELINE_SPECIFICATION.md` — Architecture, data flow, performance targets
- `PIPELINE_OPERATOR_RUNBOOK.md` — How to run, troubleshoot, recover

**Commits (6 total):**
1. Raw loading + tests
2. Staging transformations + tests
3. Analytics views + tests
4. Validation framework + tests
5. Integration + performance tests
6. Documentation

---

## After Week 3: Week 4 Handoff

The pipeline is production-ready. Week 4 engineer will:
- Query analytics views from Streamlit
- Create 30 dashboard charts
- Build interactive filters by borough, material type, date range
- Deploy to production

The pipeline runs nightly via APScheduler (already configured).

---

## Questions Before You Start?

- **DuckDB unfamiliar?** Review `IMPLEMENTATION_GUIDE.md` SQL examples
- **Socrata API questions?** Check `src/socrata_toolkit/core/client.py` docstrings
- **Git workflow?** Each Part has a `git commit` command; follow exactly
- **Test framework?** All test fixtures provided in `IMPLEMENTATION_GUIDE.md`

**You have everything you need. Start with Part 1, commit after each part, move to Part 2.**

Good luck! 🚀
