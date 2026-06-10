# Task 8: Report/Export Integration Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire reports to read from analytics marts (not live API), add 9am scheduled report generation, and enable dashboard CSV/GeoJSON exports for analyst workflows.

**Architecture:** Reports query DuckDB analytics views (not Socrata API). Scheduled job generates nightly reports. Dashboard export buttons serialize conflict lists and accessibility heatmaps as downloadable files.

**Tech Stack:** DuckDB analytics queries, WeasyPrint (PDF), openpyxl (Excel), GeoJSON serialization, APScheduler

---

## Tasks

### Task 1: Refactor Reports to Query Analytics Marts

**Files:**
- Modify: `src/socrata_toolkit/analyst/reporting.py`
- Create: `tests/test_report_analytics_integration.py`

- [ ] **Step 1: Write test for reports reading from analytics**

```python
def test_contract_report_from_analytics(db_fixture):
    """Contract report should query analytics.contract_performance_dashboard, not live API."""
    from socrata_toolkit.analyst.reporting import generate_contract_report
    
    # First materialize analytics
    from socrata_toolkit.core.duckdb_analytics_models import create_borough_summary
    create_borough_summary()
    
    # Then generate report
    report_data = generate_contract_report(borough="MANHATTAN", format="dict")
    
    assert report_data["status"] == "success"
    assert "borough" in report_data
    assert "contract_count" in report_data
    assert report_data["data_freshness_date"] is not None
```

- [ ] **Step 2: Implement report functions reading from analytics views**

```python
def generate_contract_report(borough: str = None, format: str = "excel") -> dict:
    """
    Generate contract performance report from analytics marts.
    
    Reference: DuckDB aggregation functions (SUM, AVG, COUNT)
    """
    from socrata_toolkit.core.duckdb_pipeline import get_duckdb_connection
    from datetime import datetime
    
    conn = get_duckdb_connection()
    
    # Query analytics marts (not live Socrata)
    query = """
        SELECT 
            borough,
            COUNT(*) as contract_count,
            SUM(budget_total) as budget_total,
            SUM(budget_spent) as budget_spent,
            ROUND(100.0 * SUM(budget_spent) / SUM(budget_total), 1) as budget_pct,
            AVG(days_in_contract) as avg_days_in_contract,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_count
        FROM analytics.contract_performance_dashboard
    """
    
    if borough:
        query += f" WHERE borough = '{borough}'"
    
    query += " GROUP BY borough ORDER BY budget_total DESC"
    
    result = conn.execute(query).df()
    
    if format == "excel":
        return _export_to_excel(result, f"contract_report_{datetime.now().strftime('%Y%m%d')}.xlsx")
    elif format == "pdf":
        return _export_to_pdf(result, f"contract_report_{datetime.now().strftime('%Y%m%d')}.pdf")
    else:
        return {
            "status": "success",
            "borough": borough,
            "data_freshness_date": datetime.now().isoformat(),
            "data": result.to_dict(orient="records")
        }

def generate_ramp_progress_report(borough: str = None, format: str = "excel") -> dict:
    """Generate ramp completion report from analytics.ramp_completion_rates."""
    conn = get_duckdb_connection()
    
    query = """
        SELECT 
            borough,
            total_ramps,
            completed_ramps,
            ROUND(100.0 * completed_ramps / total_ramps, 1) as completion_pct,
            ci_lower,
            ci_upper,
            reliability
        FROM analytics.ramp_completion_rates
    """
    
    if borough:
        query += f" WHERE borough = '{borough}'"
    
    query += " ORDER BY completion_pct DESC"
    
    result = conn.execute(query).df()
    
    if format == "excel":
        return _export_to_excel(result, f"ramp_progress_{datetime.now().strftime('%Y%m%d')}.xlsx")
    else:
        return {"status": "success", "data": result.to_dict(orient="records")}
```

- [ ] **Step 3: Test + commit**

```bash
pytest tests/test_report_analytics_integration.py -v
git add src/socrata_toolkit/analyst/reporting.py tests/test_report_analytics_integration.py
git commit -m "feat(reports): Wire reports to query analytics marts instead of live API"
```

---

### Task 2: Add Scheduled Report Generation

**Files:**
- Modify: `src/socrata_toolkit/core/scheduler.py`
- Modify: `data/scheduler_config.json`

- [ ] **Step 1: Add report generation job to scheduler**

```python
def run_generate_reports(self):
    """Generate nightly reports at 9am UTC."""
    logger.info("Generating nightly reports...")
    
    from socrata_toolkit.analyst.reporting import (
        generate_contract_report,
        generate_ramp_progress_report
    )
    from pathlib import Path
    
    reports_dir = Path("data/reports")
    reports_dir.mkdir(exist_ok=True)
    
    results = {}
    
    # Contract report
    try:
        result = generate_contract_report(format="excel")
        results["contract_report"] = result
        logger.info(f"Generated contract report: {result.get('path')}")
    except Exception as e:
        logger.error(f"Contract report failed: {e}")
        results["contract_report"] = {"status": "error", "error": str(e)}
    
    # Ramp progress report
    try:
        result = generate_ramp_progress_report(format="excel")
        results["ramp_report"] = result
        logger.info(f"Generated ramp report: {result.get('path')}")
    except Exception as e:
        logger.error(f"Ramp report failed: {e}")
        results["ramp_report"] = {"status": "error", "error": str(e)}
    
    return results
```

- [ ] **Step 2: Register job in scheduler config**

```json
{
  "jobs": {
    "generate_reports": {
      "enabled": true,
      "cron": "0 9 * * *",
      "timezone": "UTC",
      "description": "Generate nightly contract and ramp progress reports (9am UTC)"
    }
  }
}
```

- [ ] **Step 3: Add to job registry in run_scheduler.py**

```python
job_registry = {
    ...existing jobs...,
    "generate_reports": runner.run_generate_reports,
}
```

- [ ] **Step 4: Commit**

```bash
git add src/socrata_toolkit/core/scheduler.py data/scheduler_config.json
git commit -m "feat(scheduler): Add 9am scheduled report generation job"
```

---

### Task 3: Add Dashboard Export Functions

**Files:**
- Modify: `app/views/construction_planning_dashboard.py`
- Create: `src/socrata_toolkit/analyst/exports.py`

- [ ] **Step 1: Create export functions for conflict lists and heatmaps**

```python
# src/socrata_toolkit/analyst/exports.py

def export_conflicts_as_csv(conflicts: list, include_columns: list = None) -> bytes:
    """Export conflict list as CSV bytes."""
    import csv
    import io
    
    if not include_columns:
        include_columns = ["permit_id", "inspection_id", "distance_meters", "severity", "borough"]
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=include_columns)
    writer.writeheader()
    
    for conflict in conflicts:
        writer.writerow({col: conflict.get(col) for col in include_columns})
    
    return output.getvalue().encode("utf-8")

def export_conflicts_as_geojson(conflicts: list) -> dict:
    """Export conflict list as GeoJSON FeatureCollection.
    
    Reference: GeoJSON spec (RFC 7946) for feature geometry.
    """
    features = []
    
    for conflict in conflicts:
        # Extract coordinates from conflict location data
        # Assume conflict has lat/lon or geometry
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [conflict["lon"], conflict["lat"]]  # GeoJSON is [lon, lat]
            },
            "properties": {
                "permit_id": conflict.get("permit_id"),
                "severity": conflict.get("severity"),
                "distance_meters": conflict.get("distance_meters"),
                "recommendation": conflict.get("recommendation")
            }
        }
        features.append(feature)
    
    return {
        "type": "FeatureCollection",
        "features": features
    }

def export_accessibility_heatmap_as_geojson(heatmap_data: list) -> dict:
    """Export accessibility coverage heatmap as choropleth GeoJSON."""
    # Similar pattern to conflicts but with polygon features for blocks
    # Reference: DuckDB-docs for geometry functions, GeoJSON spec
    features = []
    
    for block_data in heatmap_data:
        feature = {
            "type": "Feature",
            "geometry": block_data.get("geometry"),  # Assuming GeoJSON geometry from DuckDB
            "properties": {
                "block_id": block_data.get("block_id"),
                "coverage_pct": block_data.get("coverage_pct"),
                "demand_score": block_data.get("demand_score"),
                "equity_score": block_data.get("equity_score")
            }
        }
        features.append(feature)
    
    return {"type": "FeatureCollection", "features": features}
```

- [ ] **Step 2: Add export buttons to dashboard**

```python
# app/views/construction_planning_dashboard.py

def render_construction_planning_page():
    """..existing code..."""
    
    st.subheader("Conflict Resolution")
    
    # Get conflicts from analytics
    conn = get_duckdb_connection()
    conflicts = conn.execute("""
        SELECT * FROM analytics.construction_conflict_index
        ORDER BY severity DESC, distance_meters ASC
    """).df().to_dict(orient="records")
    
    # Display table
    st.dataframe(conflicts)
    
    # Export buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Download as CSV"):
            csv_data = exports.export_conflicts_as_csv(conflicts)
            st.download_button(
                label="conflicts.csv",
                data=csv_data,
                file_name=f"conflicts_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("📥 Download as GeoJSON"):
            geojson_data = exports.export_conflicts_as_geojson(conflicts)
            st.download_button(
                label="conflicts.geojson",
                data=json.dumps(geojson_data),
                file_name=f"conflicts_{datetime.now().strftime('%Y%m%d')}.geojson",
                mime="application/json"
            )
```

- [ ] **Step 3: Commit**

```bash
git add src/socrata_toolkit/analyst/exports.py app/views/construction_planning_dashboard.py
git commit -m "feat(exports): Add CSV and GeoJSON export functions for dashboard downloads"
```

---

### Task 4: Integration Tests

**Files:**
- Create: `tests/test_analyst_workflow.py`

- [ ] **Step 1: Test end-to-end analyst workflows**

```python
def test_role1_contract_analyst_workflow(db_fixture):
    """Simulate Role 1 (Contract Analyst) complete workflow."""
    from socrata_toolkit.analyst.reporting import generate_contract_report
    from socrata_toolkit.analyst.exports import export_conflicts_as_csv
    
    # Step 1: Analyst views construction planning dashboard
    # Step 2: Queries conflict list
    # Step 3: Exports as CSV for engineering team
    
    result = generate_contract_report(borough="BROOKLYN", format="excel")
    assert result["status"] == "success"
    assert "contract_count" in result
    
    # Step 4: Analyst creates report for supervisor
    report = result
    assert report["data_freshness_date"] is not None

def test_role2_ramp_analyst_workflow(db_fixture):
    """Simulate Role 2 (Ramp Analyst) complete workflow."""
    from socrata_toolkit.analyst.reporting import generate_ramp_progress_report
    from socrata_toolkit.analyst.exports import export_accessibility_heatmap_as_geojson
    
    # Step 1: Analyst views ramp progress dashboard
    # Step 2: Generates IFA justification report
    result = generate_ramp_progress_report(format="excel")
    assert result["status"] == "success"
    assert len(result["data"]) > 0
```

- [ ] **Step 2: Test + commit**

```bash
pytest tests/test_analyst_workflow.py -v
git add tests/test_analyst_workflow.py
git commit -m "test(analysts): End-to-end workflow tests for both analyst roles"
```

---

## Summary

**Task 8 Delivers:**
- ✅ Reports query analytics marts (not live API) — consistent with dashboard
- ✅ 9am scheduled report generation (contract + ramp progress)
- ✅ CSV + GeoJSON export buttons in dashboard
- ✅ Analyst workflow integration tests
- ✅ Foundation for Phase 2B MotherDuck migration (clean separation of data layer)

**Future: Phase 2B MotherDuck Migration**
When migrating to MotherDuck, only the connection layer changes:
- DuckDB local → MotherDuck cloud (`md:` connection)
- All queries remain identical (DuckDB SQL is compatible)
- Reports and exports work unchanged
- Scalable to 50+ concurrent analysts

---

**PLAN COMPLETE**

Three implementation plans ready for execution:
1. **Task 6B**: Extensible 26-dataset architecture
2. **Task 7**: Orchestration + documentation  
3. **Task 8**: Report/export integration

**Execution options:**
1. **Subagent-Driven** — Fresh subagent per task
2. **Inline Execution** — Execute here with checkpoints

Which approach?
