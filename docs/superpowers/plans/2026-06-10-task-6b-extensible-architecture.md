# Task 6B: Extensible 26-Dataset Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the 4-dataset pipeline to a generic architecture where adding any of the remaining 22 datasets requires only a single-line registry entry (zero code changes).

**Architecture:** Generic `stage_dataset(key)` function using defensive column discovery (DESCRIBE-based schema detection). Config-driven analytics marts (instead of hardcoded `create_*` functions). Parameterized validation with DuckDB's `DESCRIBE`, `COLUMNS()`, and column introspection patterns.

**Tech Stack:** DuckDB (SQL + extensions), Python 3.11+, pytest, APScheduler, Socrata API

---

## File Structure

**Core refactoring:**
- `src/socrata_toolkit/core/duckdb_pipeline.py` — Modify: Add `stage_dataset()` generic function, keep `stage_inspections/permits/ramps` as thin wrappers for backward compatibility
- `src/socrata_toolkit/core/duckdb_analytics_models.py` — Modify: Add analytics factory, config-based mart generation
- `src/socrata_toolkit/quality/duckdb_validation.py` — Modify: Parameterize thresholds, make validation checks dataset-agnostic
- `src/socrata_toolkit/core/scheduler.py` — Modify: Update jobs to loop SOCRATA_DATASETS
- `data/dataset_config.json` — Create: Registry + dataset-specific metadata (key columns, date columns, tolerance thresholds)
- `data/analytics_config.json` — Create: Analytics marts definition (which columns to aggregate, which datasets they need)
- `tests/test_duckdb_extensibility.py` — Create: Tests for new generic functions with 10+ datasets

---

## Tasks

### Task 1: Expand SOCRATA_DATASETS Registry

**Files:**
- Modify: `src/socrata_toolkit/core/duckdb_pipeline.py:30-65`

- [ ] **Step 1: Add all 22 missing datasets to SOCRATA_DATASETS**

```python
SOCRATA_DATASETS = {
    # Core SIM (already present)
    "inspection": "dntt-gqwq",
    "violations": "6kbp-uz6m",
    "permits": "tqtj-sjs8",
    "ramp_progress": "e7gc-ub6z",
    
    # Add 22 more
    "built": "ugc8-s3f6",
    "lot_info": "i642-2fxq",
    "reinspection": "gx72-kirf",
    "tree_damage": "j6v2-6uxq",
    "dismissals": "p4u2-3jgx",
    "correspondences": "bheb-sjfi",
    "curb_metal_protruding": "i2y3-sx2e",
    "ramp_locations": "ufzp-rrqu",
    "ramp_complaints": "jagj-gttd",
    "weekly_construction": "r528-jcks",
    "capital_blocks": "jvk9-k4re",
    "capital_intersections": "97nd-ff3i",
    "street_construction_inspections": "ydkf-mpxb",
    "street_closures_block": "i6b5-j7bu",
    "street_resurfacing_schedule": "xnfm-u3k5",
    "street_resurfacing_inhouse": "ffaf-8mrv",
    "step_streets": "u9au-h79y",
    "sidewalk_planimetric": "vfx9-tbb6",
    "pedestrian_demand": "fwpa-qxaf",
    "mappluto": "64uk-42ks",
    "complaints_311": "erm2-nwe9",
}
```

- [ ] **Step 2: Verify no typos**

Run: `python -c "from socrata_toolkit.core.duckdb_pipeline import SOCRATA_DATASETS; print(f'{len(SOCRATA_DATASETS)} datasets registered')"`
Expected: `57 datasets registered`

- [ ] **Step 3: Commit**

```bash
git add src/socrata_toolkit/core/duckdb_pipeline.py
git commit -m "feat(pipeline): Register all 26 Socrata datasets in SOCRATA_DATASETS map"
```

---

### Task 2: Create Dataset Configuration Files

**Files:**
- Create: `data/dataset_config.json`
- Create: `data/analytics_config.json`

- [ ] **Step 1: Create dataset_config.json with metadata for all 57 datasets**

```json
{
  "inspection": {
    "fourfour": "dntt-gqwq",
    "key_candidates": ["objectid", "object_id", "id"],
    "date_candidates": ["created_date", "inspection_date", ":updated_at"],
    "expected_row_count_min": 350000,
    "expected_row_count_max": 450000,
    "tolerance_pct": 0.10,
    "roles": ["contract_analyst", "ramp_analyst"]
  },
  "violations": {
    "fourfour": "6kbp-uz6m",
    "key_candidates": ["violation_id", "id"],
    "date_candidates": ["created_date", "violation_date", ":updated_at"],
    "expected_row_count_min": 280000,
    "expected_row_count_max": 380000,
    "tolerance_pct": 0.10,
    "roles": ["contract_analyst"]
  },
  "permits": {
    "fourfour": "tqtj-sjs8",
    "key_candidates": ["permit_number", "permit_id", "id"],
    "date_candidates": ["permit_issue_date", "issue_date", "created_date", ":updated_at"],
    "expected_row_count_min": 3400000,
    "expected_row_count_max": 3900000,
    "tolerance_pct": 0.05,
    "roles": ["contract_analyst"]
  },
  "ramp_progress": {
    "fourfour": "e7gc-ub6z",
    "key_candidates": ["ramp_id", "rampid", "id"],
    "date_candidates": ["status_date", "updated_date", "created_date", ":updated_at"],
    "expected_row_count_min": 170000,
    "expected_row_count_max": 220000,
    "tolerance_pct": 0.10,
    "roles": ["ramp_analyst"]
  },
  "ramp_complaints": {
    "fourfour": "jagj-gttd",
    "key_candidates": ["complaint_id", "id"],
    "date_candidates": ["created_date", "complaint_date", ":updated_at"],
    "expected_row_count_min": 5000,
    "expected_row_count_max": 10000,
    "tolerance_pct": 0.20,
    "roles": ["ramp_analyst"]
  },
  "street_construction_inspections": {
    "fourfour": "ydkf-mpxb",
    "key_candidates": ["inspection_id", "id"],
    "date_candidates": ["created_date", "inspection_date", ":updated_at"],
    "expected_row_count_min": 10000000,
    "expected_row_count_max": 13000000,
    "tolerance_pct": 0.05,
    "roles": ["contract_analyst"]
  },
  "_template": {
    "fourfour": "required_string",
    "key_candidates": ["list of candidate column names for primary key"],
    "date_candidates": ["list of candidate column names for date/timestamp"],
    "expected_row_count_min": "min_expected_rows",
    "expected_row_count_max": "max_expected_rows",
    "tolerance_pct": "acceptable_variance_as_fraction",
    "roles": ["which_analyst_roles_use_this"]
  }
}
```

- [ ] **Step 2: Create analytics_config.json defining marts**

```json
{
  "universal_marts": [
    {
      "name": "raw_counts_summary",
      "datasets": ["all"],
      "query": "SELECT dataset, COUNT(*) as row_count FROM raw.{dataset} GROUP BY 1"
    }
  ],
  "role1_marts": [
    {
      "name": "sidewalk_repair_matrix",
      "datasets": ["inspection", "violations", "built"],
      "description": "Sidewalk condition by material × borough for contract planning"
    },
    {
      "name": "construction_conflict_index",
      "datasets": ["street_permits", "inspection"],
      "description": "Spatial conflict matrix for scheduling"
    }
  ],
  "role2_marts": [
    {
      "name": "ramp_completion_rates",
      "datasets": ["ramp_progress"],
      "description": "Ramp completion by borough with Wilson Score CI"
    },
    {
      "name": "accessibility_coverage_heatmap",
      "datasets": ["ramp_locations", "pedestrian_demand", "mappluto"],
      "description": "Geographic × demographic accessibility gaps"
    }
  ]
}
```

- [ ] **Step 3: Commit**

```bash
git add data/dataset_config.json data/analytics_config.json
git commit -m "feat(config): Add dataset and analytics configuration files for 26-dataset extensibility"
```

---

### Task 3: Implement Generic stage_dataset() Function

**Files:**
- Modify: `src/socrata_toolkit/core/duckdb_pipeline.py`
- Create: `tests/test_duckdb_extensibility.py`

- [ ] **Step 1: Write failing test for stage_dataset with any dataset**

```python
def test_stage_dataset_generic(db_fixture):
    """Generic stage_dataset should work for any dataset, discovering schema defensively."""
    from socrata_toolkit.core.duckdb_pipeline import stage_dataset
    
    # First load a dataset
    load_raw_from_socrata("inspection", max_rows=10000)
    
    # Then stage it generically
    result = stage_dataset("inspection")
    
    assert result["status"] == "success"
    assert result["table"] == "staging.inspection"
    assert result["row_count_raw"] > 0
    assert result["row_count_staged"] > 0
    assert result["dedup_key"] in ["objectid", "object_id", "id"]
    assert result["dedup_date"] in ["created_date", "inspection_date", ":updated_at"]
```

- [ ] **Step 2: Implement stage_dataset() function using DuckDB's DESCRIBE and column discovery**

**Reference:** DuckDB docs on DESCRIBE, COLUMNS(), and schema introspection. See: https://duckdb.org/docs/sql/metadata/overview

```python
def stage_dataset(dataset_key: str) -> dict:
    """
    Generic staging function: deduplicate any dataset using defensive column discovery.
    
    Uses DuckDB's DESCRIBE to discover schema, then candidate lists to pick dedup key/date.
    Works for any of the 57 datasets without code changes.
    
    Reference: duckdb-docs skill for DESCRIBE syntax and column introspection patterns.
    """
    if dataset_key not in SOCRATA_DATASETS:
        raise ValueError(f"Unknown dataset: {dataset_key}")
    
    conn = get_duckdb_connection()
    raw_table = f"raw.{dataset_key}"
    staging_table = f"staging.{dataset_key}"
    
    # Load config
    with open("data/dataset_config.json") as f:
        config = json.load(f)
    
    dataset_config = config.get(dataset_key, config["_template"])
    key_candidates = dataset_config["key_candidates"]
    date_candidates = dataset_config["date_candidates"]
    
    try:
        # Discover which columns exist
        columns_result = conn.execute(f"DESCRIBE {raw_table}").fetchall()
        existing_columns = {col[0] for col in columns_result}
        
        # Pick dedup key and date from candidates
        dedup_key = _pick_column(existing_columns, key_candidates)
        dedup_date = _pick_column(existing_columns, date_candidates)
        
        if not dedup_key:
            # No key = use DISTINCT (expensive)
            conn.execute(f"DROP TABLE IF EXISTS {staging_table}")
            conn.execute(f"CREATE TABLE {staging_table} AS SELECT DISTINCT * FROM {raw_table}")
            staged_count = conn.execute(f"SELECT COUNT(*) FROM {staging_table}").fetchone()[0]
            return {
                "status": "success",
                "table": staging_table,
                "row_count_raw": conn.execute(f"SELECT COUNT(*) FROM {raw_table}").fetchone()[0],
                "row_count_staged": staged_count,
                "dedup_key": None,
                "dedup_date": None,
                "note": "No key column found; used SELECT DISTINCT"
            }
        
        # DuckDB SQL: use ROW_NUMBER() window function to deduplicate
        # Reference: DuckDB docs on window functions
        raw_count = conn.execute(f"SELECT COUNT(*) FROM {raw_table}").fetchone()[0]
        
        conn.execute(f"DROP TABLE IF EXISTS {staging_table}")
        conn.execute(f"""
            CREATE TABLE {staging_table} AS
            SELECT * EXCEPT (rn) FROM (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY "{dedup_key}" ORDER BY "{dedup_date}" DESC NULLS LAST) AS rn
                FROM {raw_table}
            )
            WHERE rn = 1
        """)
        
        staged_count = conn.execute(f"SELECT COUNT(*) FROM {staging_table}").fetchone()[0]
        
        # Audit log
        audit_logger = _get_audit_logger()
        audit_logger.log_check(
            check_type="stage_dataset",
            table_name=dataset_key,
            status="success",
            rows_affected=staged_count,
            details={"dedup_key": dedup_key, "dedup_date": dedup_date, "dedup_loss_pct": (raw_count - staged_count) / raw_count * 100}
        )
        
        return {
            "status": "success",
            "table": staging_table,
            "row_count_raw": raw_count,
            "row_count_staged": staged_count,
            "dedup_key": dedup_key,
            "dedup_date": dedup_date,
            "dedup_loss_pct": round((raw_count - staged_count) / raw_count * 100, 2)
        }
    except Exception as e:
        logger.error(f"Failed to stage {dataset_key}: {e}")
        return {"status": "error", "error": str(e), "table": staging_table}
```

- [ ] **Step 3: Test with 5 different datasets**

Run: `pytest tests/test_duckdb_extensibility.py -v -k "stage_dataset"`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add src/socrata_toolkit/core/duckdb_pipeline.py tests/test_duckdb_extensibility.py
git commit -m "feat(pipeline): Implement generic stage_dataset() for all 57 datasets"
```

---

### Task 4: Parameterize Analytics Marts (Config-Driven)

**Files:**
- Modify: `src/socrata_toolkit/core/duckdb_analytics_models.py`
- Create: `tests/test_analytics_extensibility.py`

- [ ] **Step 1: Create analytics factory function**

```python
def create_marts_from_config() -> dict:
    """
    Materialize analytics marts based on analytics_config.json.
    Zero hardcoded marts; all defined in config.
    
    Reference: DuckDB docs for SELECT COLUMNS(), EXCLUDE, and aggregation patterns.
    """
    with open("data/analytics_config.json") as f:
        config = json.load(f)
    
    conn = get_duckdb_connection()
    results = {}
    
    # Universal marts
    for mart in config.get("universal_marts", []):
        mart_name = mart["name"]
        datasets = mart["datasets"]
        
        if datasets == ["all"]:
            datasets = list(SOCRATA_DATASETS.keys())
        
        # Implement per-mart logic
        if mart_name == "raw_counts_summary":
            conn.execute(f"DROP TABLE IF EXISTS analytics.{mart_name}")
            # Loop all raw tables and get counts
            ...
        
        results[mart_name] = {"status": "success"}
    
    return results
```

- [ ] **Step 2-4: Implement role-specific marts with DuckDB SQL**

Reference: https://duckdb.org/docs/sql/functions/aggregates for aggregate functions, COLUMNS() for dynamic column selection.

- [ ] **Step 5: Commit**

```bash
git add src/socrata_toolkit/core/duckdb_analytics_models.py tests/test_analytics_extensibility.py
git commit -m "feat(analytics): Config-driven analytics mart generation for all datasets"
```

---

### Task 5: Parameterize Validation Checks

**Files:**
- Modify: `src/socrata_toolkit/quality/duckdb_validation.py`

- [ ] **Step 1: Make validate_raw_counts() loop all datasets from config**

```python
def validate_raw_counts() -> list:
    """Validate raw counts for all 57 datasets using config thresholds."""
    with open("data/dataset_config.json") as f:
        config = json.load(f)
    
    conn = get_duckdb_connection()
    results = []
    
    for dataset_key, dataset_config in config.items():
        if dataset_key == "_template":
            continue
        
        try:
            raw_table = f"raw.{dataset_key}"
            count = conn.execute(f"SELECT COUNT(*) FROM {raw_table}").fetchone()[0]
            
            min_expected = dataset_config["expected_row_count_min"]
            max_expected = dataset_config["expected_row_count_max"]
            
            if min_expected <= count <= max_expected:
                status = "PASS"
            else:
                status = "FAIL"
            
            results.append({
                "check_name": f"validate_raw_counts_{dataset_key}",
                "table_name": dataset_key,
                "status": status,
                "details": {"count": count, "expected_min": min_expected, "expected_max": max_expected},
                "rows_affected": count
            })
        except Exception as e:
            results.append({
                "check_name": f"validate_raw_counts_{dataset_key}",
                "table_name": dataset_key,
                "status": "FAIL",
                "error": str(e),
                "rows_affected": 0
            })
    
    return results
```

- [ ] **Step 2-3: Test + commit**

```bash
git add src/socrata_toolkit/quality/duckdb_validation.py
git commit -m "feat(validation): Parameterize validation checks using dataset_config.json"
```

---

### Task 6: Update Scheduler to Loop All Datasets

**Files:**
- Modify: `src/socrata_toolkit/core/scheduler.py`

- [ ] **Step 1: Update run_load_raw_data to loop SOCRATA_DATASETS (already done in Task 3)**

Verify it's already there from earlier task.

- [ ] **Step 2: Update run_stage_data to loop all datasets**

```python
def run_stage_data(self):
    """Stage all datasets generically."""
    logger.info("Starting staging...")
    from socrata_toolkit.core.duckdb_pipeline import SOCRATA_DATASETS, stage_dataset
    
    results = {}
    for dataset_key in SOCRATA_DATASETS:
        result = stage_dataset(dataset_key)
        results[dataset_key] = result
        if result["status"] == "success":
            logger.info(f"  {dataset_key}: staged {result['row_count_staged']} rows")
        else:
            logger.warning(f"  {dataset_key}: failed - {result.get('error')}")
    
    return results
```

- [ ] **Step 3: Update run_materialize_analytics to use config-driven factory**

```python
def run_materialize_analytics(self):
    """Materialize all analytics marts from config."""
    from socrata_toolkit.core.duckdb_analytics_models import create_marts_from_config
    
    results = create_marts_from_config()
    logger.info(f"Materialized {len(results)} analytics marts")
    return results
```

- [ ] **Step 4: Commit**

```bash
git add src/socrata_toolkit/core/scheduler.py
git commit -m "feat(scheduler): Loop all 57 datasets in load/stage/materialize jobs"
```

---

### Task 7: End-to-End Integration Test (All 57 datasets)

**Files:**
- Create: `tests/test_duckdb_26dataset_pipeline.py`

- [ ] **Step 1: Write comprehensive test loading, staging, and materializing all 57 datasets**

```python
def test_full_26dataset_pipeline_e2e(db_fixture):
    """Load → stage → materialize all 57 datasets in <5 minutes."""
    import time
    from socrata_toolkit.core.duckdb_pipeline import SOCRATA_DATASETS, load_raw_from_socrata, stage_dataset
    from socrata_toolkit.core.duckdb_analytics_models import create_marts_from_config
    
    start = time.time()
    
    # Load all datasets (sample mode: 50K rows max to keep test fast)
    load_results = {}
    for key in SOCRATA_DATASETS:
        result = load_raw_from_socrata(key, max_rows=50000)
        load_results[key] = result
        assert result["status"] == "success", f"Load failed for {key}"
    
    # Stage all datasets
    stage_results = {}
    for key in SOCRATA_DATASETS:
        result = stage_dataset(key)
        stage_results[key] = result
        assert result["status"] == "success", f"Stage failed for {key}"
    
    # Materialize all analytics
    materialize_results = create_marts_from_config()
    assert len(materialize_results) > 0, "No analytics marts materialized"
    
    elapsed = time.time() - start
    
    assert elapsed < 300, f"Full pipeline took {elapsed:.1f}s, expected <300s (5 min)"
    
    return {
        "status": "success",
        "elapsed_seconds": round(elapsed, 2),
        "datasets_loaded": len(load_results),
        "datasets_staged": len(stage_results),
        "analytics_marts": len(materialize_results)
    }
```

- [ ] **Step 2-4: Run test, fix issues, commit**

```bash
pytest tests/test_duckdb_26dataset_pipeline.py -v
git add tests/test_duckdb_26dataset_pipeline.py
git commit -m "test(pipeline): End-to-end integration test for all 57 datasets"
```

---

## Summary

**Task 6B Delivers:**
- ✅ Generic `stage_dataset()` function (zero code changes to add a dataset)
- ✅ Config-driven analytics marts (no more hardcoded `create_*` functions)
- ✅ Parameterized validation using dataset_config.json
- ✅ Scheduler loops all 57 datasets
- ✅ Tests for extensibility (10+ datasets in single test)

**Success Criteria:**
- Adding a 27th dataset = 1 line in SOCRATA_DATASETS + 1 entry in dataset_config.json
- Full 26-dataset pipeline runs in <5 minutes
- All validation checks scale automatically
- Audit logs capture all 57 datasets

---

## Execution Handoff

Plan complete. Two execution options:

**1. Subagent-Driven (recommended)** - Fresh subagent per task, review between tasks

**2. Inline Execution** - Execute tasks in this session using executing-plans

Which approach?


