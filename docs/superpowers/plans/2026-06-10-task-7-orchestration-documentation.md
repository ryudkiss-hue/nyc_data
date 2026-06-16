# Task 7: Orchestration & Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the run_full_pipeline() orchestrator and comprehensive documentation for both analyst roles (Role 1: Contract Planning, Role 2: Ramp Program).

**Architecture:** Single `run_full_pipeline(mode="all"|"sample")` orchestrator that coordinates load → stage → materialize → validate for all 26 datasets. Documentation maps workflows to datasets and commands for each role.

**Tech Stack:** Python orchestration, Markdown documentation, APScheduler config reference

---

## Tasks

### Task 1: Implement run_full_pipeline() Orchestrator

**Files:**
- Modify: `src/socrata_toolkit/core/duckdb_pipeline.py`
- Create: `tests/test_orchestrator.py`

- [ ] **Step 1: Write test for orchestrator**

```python
def test_run_full_pipeline_all_datasets(db_fixture):
    """Orchestrator should coordinate full pipeline for all 26 datasets."""
    from socrata_toolkit.core.duckdb_pipeline import run_full_pipeline
    
    result = run_full_pipeline(mode="sample", max_rows=50000)
    
    assert result["status"] == "success"
    assert result["datasets_loaded"] == 26
    assert result["datasets_staged"] == 26
    assert result["analytics_materialized"] > 0
    assert result["validations_passed"]
    assert result["elapsed_seconds"] < 300
```

- [ ] **Step 2: Implement orchestrator**

```python
def run_full_pipeline(mode: str = "sample", max_rows: int = 50000, include_datasets: list = None) -> dict:
    """
    Orchestrate complete ETL pipeline: load → stage → materialize → validate → report.
    
    Args:
        mode: "sample" (limited rows for testing), "incremental" (fetch since last run), or "full" (all rows)
        max_rows: row limit per dataset (sample mode only)
        include_datasets: list of dataset keys to include; None = all
    
    Returns comprehensive status dict with timings, validation results, alerts.
    """
    import time
    from datetime import datetime
    
    start_time = time.time()
    
    # Determine which datasets to process
    if include_datasets is None:
        datasets_to_process = list(SOCRATA_DATASETS.keys())
    else:
        datasets_to_process = include_datasets
    
    logger.info("=" * 70)
    logger.info(f"NYC DOT Sidewalk Pipeline Starting: {datetime.now().isoformat()}")
    logger.info(f"Mode: {mode}, Datasets: {len(datasets_to_process)}")
    logger.info("=" * 70)
    
    # Phase 1: Load raw data
    logger.info("Phase 1: Loading raw data...")
    load_start = time.time()
    load_results = {}
    for dataset_key in datasets_to_process:
        result = load_raw_from_socrata(dataset_key, max_rows=max_rows if mode == "sample" else None)
        load_results[dataset_key] = result
        if result["status"] == "success":
            logger.info(f"  ✓ {dataset_key}: {result['row_count']} rows")
        else:
            logger.warning(f"  ✗ {dataset_key}: {result.get('error')}")
    load_elapsed = time.time() - load_start
    
    # Phase 2: Stage data
    logger.info(f"Phase 2: Staging data ({load_elapsed:.1f}s)...")
    stage_start = time.time()
    stage_results = {}
    for dataset_key in datasets_to_process:
        result = stage_dataset(dataset_key)
        stage_results[dataset_key] = result
        if result["status"] == "success":
            logger.info(f"  ✓ {dataset_key}: deduplicated {result['row_count_staged']} rows")
    stage_elapsed = time.time() - stage_start
    
    # Phase 3: Materialize analytics
    logger.info(f"Phase 3: Materializing analytics ({stage_elapsed:.1f}s)...")
    materialize_start = time.time()
    analytics_results = create_marts_from_config()
    materialize_elapsed = time.time() - materialize_start
    logger.info(f"  ✓ {len(analytics_results)} analytics marts materialized")
    
    # Phase 4: Validate
    logger.info(f"Phase 4: Validating ({materialize_elapsed:.1f}s)...")
    validate_start = time.time()
    validation_results = run_all_validations()
    validate_elapsed = time.time() - validate_start
    failed_checks = [r for r in validation_results if r.get("status") == "FAIL"]
    logger.info(f"  ✓ {len(validation_results)} checks passed, {len(failed_checks)} failed")
    
    total_elapsed = time.time() - start_time
    
    logger.info("=" * 70)
    logger.info(f"Pipeline completed: {total_elapsed:.1f}s")
    logger.info("=" * 70)
    
    return {
        "status": "success" if not failed_checks else "warning",
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "datasets_loaded": len([r for r in load_results.values() if r["status"] == "success"]),
        "datasets_staged": len([r for r in stage_results.values() if r["status"] == "success"]),
        "analytics_materialized": len(analytics_results),
        "validations_total": len(validation_results),
        "validations_passed": len([r for r in validation_results if r.get("status") != "FAIL"]),
        "validations_failed": len(failed_checks),
        "elapsed_seconds": round(total_elapsed, 2),
        "phase_timings": {
            "load": round(load_elapsed, 2),
            "stage": round(stage_elapsed, 2),
            "materialize": round(materialize_elapsed, 2),
            "validate": round(validate_elapsed, 2)
        }
    }
```

- [ ] **Step 3: Test + commit**

```bash
pytest tests/test_orchestrator.py -v
git add src/socrata_toolkit/core/duckdb_pipeline.py tests/test_orchestrator.py
git commit -m "feat(orchestration): Implement run_full_pipeline() for all 26 datasets"
```

---

### Task 2: Create Analyst Quick-Start Guides

**Files:**
- Create: `docs/analysts/role1-contract-analyst-guide.md`
- Create: `docs/analysts/role2-ramp-analyst-guide.md`

- [ ] **Step 1: Create Role 1 (Contract Analyst) guide**

```markdown
# Contract Analyst Quick Start Guide

## Your Role
Analyze sidewalk repairs, construction conflicts, contracts, and productivity for the Sidewalk Program.

## Core Datasets You Use
- `inspection` — Sidewalk condition ratings
- `violations` — Violation counts
- `street_permits` — Construction permits (for conflict detection)
- `street_construction_inspections` — Active construction tracking
- `street_resurfacing_schedule` — Contract timelines

## Key Analytics Products
1. **Sidewalk Repair Matrix** — Conditions by material × borough
2. **Construction Conflict Index** — Spatial overlaps (permits vs inspections)
3. **Contract Performance Dashboard** — Budget variance, timelines
4. **Material Failure Analysis** — Repair rates by material type
5. **Productivity Trends** — Contractor efficiency metrics

## How to Use the Toolkit

### View Your Dashboard
```bash
streamlit run app/app.py
```
Navigate to "Construction Planning" → select your analysis type

### Query Data Directly
```python
from socrata_toolkit.core.duckdb_pipeline import get_duckdb_connection

conn = get_duckdb_connection()
# Query sidewalk repairs in Manhattan
inspections = conn.execute("""
    SELECT * FROM analytics.sidewalk_repair_matrix
    WHERE borough = 'MANHATTAN'
    ORDER BY violation_rate DESC
""").df()
```

### Generate a Report
```bash
socrata report contract --output report.xlsx --borough BROOKLYN
```
This generates a contract performance report in Excel.

## Common Workflows

### Find high-conflict areas for scheduling
1. Go to "Construction Planning" → "Conflict Resolution"
2. Filter by Borough and Severity
3. Export the list for your engineering team

### Analyze material performance
1. View "Material Analysis Mart" in dashboard
2. Sort by violation_rate
3. Recommend material changes based on failure patterns

### Track contract progress
1. View "Contract Performance Dashboard"
2. Monitor budget variance weekly
3. Alert supervisor if variance > 10%
```

- [ ] **Step 2: Create Role 2 (Ramp Analyst) guide**

```markdown
# Ramp Program Analyst Quick Start Guide

## Your Role
Support pedestrian ramp program, manage high-priority requests, GIS analysis, and IFA justifications.

## Core Datasets You Use
- `ramp_progress` — Ramp completion tracking
- `ramp_complaints` — High-priority requests
- `ramp_locations` — Ramp locations
- `pedestrian_demand` — Demand hotspots (for equity analysis)
- `mappluto` — Demographic data (for IFA business case)

## Key Analytics Products
1. **Ramp Completion Rates** — Borough-level progress with 95% CI
2. **High-Priority Queue** — Age-ranked requests
3. **Accessibility Coverage Heatmap** — Geographic + demographic gaps
4. **IFA Business Case** — Equity scoring, impact estimates
5. **Curb Metal Protruding Status** — Remediation tracking

## How to Use the Toolkit

### View Ramp Progress
```bash
streamlit run app/app.py
```
Navigate to "Operational Status" → filter by borough

### Find high-priority requests
```python
from socrata_toolkit.core.duckdb_pipeline import get_duckdb_connection

conn = get_duckdb_connection()
# Complaints oldest first
complaints = conn.execute("""
    SELECT * FROM analytics.high_priority_queue
    WHERE days_old > 30
    ORDER BY days_old DESC
""").df()
```

### Create IFA justification report
```bash
socrata report ifa --output ifa_business_case.xlsx --equity-scoring true
```

## Common Workflows

### Respond to high-priority request
1. Dashboard → "Operational Status" → Filter by CREATED_DATE < -30 days
2. Get location from ramp_complaints
3. Check ramp_progress for nearby existing ramps
4. Recommend action: install new ramp or repair existing

### Analyze accessibility gaps
1. View "Accessibility Coverage Heatmap"
2. Identify blocks with high demand but low ramp coverage
3. Use pedestrian_demand + mappluto to score by equity
4. Present findings to supervisor for budget request

### Track curb metal protruding remediation
1. Go to dashboard "Curb Metal Protruding Status"
2. Filter by status = "open"
3. Export for field crews
```

- [ ] **Step 3: Commit**

```bash
git add docs/analysts/
git commit -m "docs(analysts): Create quick-start guides for both analyst roles"
```

---

### Task 3: Create Scheduling Documentation

**Files:**
- Create: `docs/SCHEDULER_OPERATIONS.md`

- [ ] **Step 1: Document complete scheduler reference**

```markdown
# Scheduler Operations Guide

## Overview
The NYC DOT Sidewalk Pipeline runs nightly using APScheduler.

## Default Schedule (UTC)
- 2:00 AM: Load raw data (all 26 datasets)
- 3:00 AM: Stage data (deduplication + joins)
- 4:00 AM: Materialize analytics (all marts)
- 5:00 AM: Validate quality
- 6:00 AM: Reconciliation checks
- 7:00 AM: Domain business rules
- 8:00 AM: Conflict detection
- Every 30 min: Alert checks

## Monitor Pipeline

```bash
# View logs
tail -f logs/scheduler.log

# Check current job status
duckdb data/local_db/nyc_mission_control.duckdb -c "SELECT * FROM apscheduler_jobs ORDER BY next_run_time"

# Force a job to run immediately
python -c "from socrata_toolkit.core.scheduler import PipelineScheduler; s = PipelineScheduler(); s.initialize(); s.scheduler.start(); ScheduleRunner().run_load_raw_data()"
```

## Configuration
Edit `data/scheduler_config.json` to:
- Enable/disable jobs
- Change cron times
- Adjust executor settings
- Configure notifications
```

- [ ] **Step 2: Commit**

```bash
git add docs/SCHEDULER_OPERATIONS.md
git commit -m "docs(scheduler): Add complete operations guide for pipeline scheduling"
```

---

### Task 4: Update CLI Help Text

**Files:**
- Modify: `src/socrata_toolkit/core/cli.py`

- [ ] **Step 1: Add new CLI commands for 26-dataset pipeline**

```python
@click.command()
@click.option('--mode', default='sample', type=click.Choice(['sample', 'incremental', 'full']))
@click.option('--datasets', multiple=True, help='Limit to specific datasets')
def pipeline(mode, datasets):
    """Run full ETL pipeline: load → stage → materialize → validate.
    
    Modes:
    - sample: Limited rows (50K per dataset) for testing
    - incremental: Fetch only since last run (fast)
    - full: All rows from Socrata (slow, requires SOCRATA_APP_TOKEN)
    
    Examples:
    
        socrata pipeline --mode sample
        socrata pipeline --mode full --datasets inspection violations
    """
    from socrata_toolkit.core.duckdb_pipeline import run_full_pipeline
    result = run_full_pipeline(mode=mode, include_datasets=list(datasets) if datasets else None)
    print(json.dumps(result, indent=2))
```

- [ ] **Step 2: Commit**

```bash
git add src/socrata_toolkit/core/cli.py
git commit -m "feat(cli): Add 'pipeline' command for orchestrated execution"
```

---

## Summary

**Task 7 Delivers:**
- ✅ run_full_pipeline() orchestrator with timing breakdown
- ✅ Role 1 quick-start guide (Contract Analyst workflows)
- ✅ Role 2 quick-start guide (Ramp Analyst workflows)
- ✅ Scheduler operations documentation
- ✅ CLI command for on-demand pipeline execution

---

Plan complete. Execution options:

**1. Subagent-Driven (recommended)**
**2. Inline Execution**
