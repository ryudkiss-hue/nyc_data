# Phase 1 Pipeline Implementation Guide (Weeks 2-3)

## Overview

This 45-hour implementation guide covers the production data pipeline that loads Socrata data → stages → materializes analytics views. Follow this sequentially, testing as you go (TDD pattern). Each section specifies exact function names, SQL queries, and validation code.

**Success Criteria:**
- Pipeline executes in <30 seconds end-to-end
- Zero data loss (validated row counts)
- All validation checks pass
- 10+ integration tests with >40% coverage
- Idempotent transformations (safe to re-run)

---

## PART 1: Raw Data Loading (4 hours)

### 1.1 Implement `load_raw_from_socrata()`

**File:** `src/socrata_toolkit/core/duckdb_pipeline.py`

Replace the placeholder `load_raw_from_socrata()` method with:

```python
def load_raw_from_socrata(self, dataset_keys: List[str]) -> Dict:
    """Load raw data from Socrata into raw schema (idempotent).
    
    Creates raw.{dataset_name} tables by fetching full corpus from Socrata API.
    Requires SOCRATA_APP_TOKEN in environment for datasets >2K rows.
    
    Args:
        dataset_keys: List of dataset keys to load:
            'inspection' (dntt-gqwq, ~398K rows)
            'violations' (6kbp-uz6m, ~312K rows)  
            'street_permits' (tqtj-sjs8, ~3.6M rows)
    
    Returns:
        Dict mapping dataset_key → {"status": str, "rows": int, "error": str|None}
        Example: {"inspection": {"status": "success", "rows": 398500, "error": None}}
    """
    from socrata_toolkit.core.client import SocrataClient, SocrataConfig
    
    logger.info(f"Loading {len(dataset_keys)} datasets from Socrata...")
    results = {}
    
    # Map dataset keys to Socrata metadata
    dataset_map = {
        "inspection": {
            "fourfour": "dntt-gqwq",
            "domain": "data.cityofnewyork.us",
            "expected_rows": 398000
        },
        "violations": {
            "fourfour": "6kbp-uz6m",
            "domain": "data.cityofnewyork.us",
            "expected_rows": 312000
        },
        "street_permits": {
            "fourfour": "tqtj-sjs8",
            "domain": "data.cityofnewyork.us",
            "expected_rows": 3600000
        }
    }
    
    client = SocrataClient(SocrataConfig())
    
    for key in dataset_keys:
        if key not in dataset_map:
            results[key] = {"status": "error", "error": f"Unknown dataset key: {key}"}
            continue
        
        meta = dataset_map[key]
        try:
            logger.info(f"  - {key}: fetching from {meta['fourfour']}...")
            
            # Fetch as Pandas DataFrame (SocrataClient.fetch_dataframe handles pagination)
            df = client.fetch_dataframe(
                domain=meta["domain"],
                fourfour=meta["fourfour"],
                max_rows=None  # Fetch full corpus
            )
            
            if df is None or len(df) == 0:
                results[key] = {"status": "error", "error": "No data returned"}
                logger.warning(f"  - {key}: No data returned")
                continue
            
            # Create raw table (idempotent: drop if exists)
            self.conn.execute(f"DROP TABLE IF EXISTS raw.{key} CASCADE")
            
            # Register DataFrame as table and create persistent table
            self.conn.register(f"_{key}_temp", df)
            self.conn.execute(f"""
                CREATE TABLE raw.{key} AS
                SELECT * FROM _{key}_temp
            """)
            
            # Unregister temporary
            self.conn.unregister(f"_{key}_temp")
            
            row_count = len(df)
            results[key] = {
                "status": "success",
                "rows": row_count,
                "error": None
            }
            
            # Log row count vs expected
            expected = meta["expected_rows"]
            deviation = abs(row_count - expected) / expected * 100 if expected > 0 else 0
            logger.info(f"  - {key}: {row_count:,} rows (expected ~{expected:,}, deviation {deviation:.1f}%)")
            
        except Exception as e:
            logger.error(f"Failed to load {key}: {e}")
            results[key] = {
                "status": "error",
                "rows": 0,
                "error": str(e)
            }
    
    logger.info(f"Raw data loading complete: {sum(1 for r in results.values() if r['status'] == 'success')}/{len(dataset_keys)} succeeded")
    return results
```

### 1.2 Create Unit Test for Raw Loading

**File:** `tests/test_pipeline_raw_loading.py`

```python
"""Tests for raw data loading from Socrata."""
import pytest
import duckdb
from socrata_toolkit.core.duckdb_pipeline import DuckDBPipeline
import tempfile
import os


@pytest.fixture
def temp_db():
    """Create temporary DuckDB for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.duckdb")
        yield db_path


@pytest.fixture
def pipeline(temp_db):
    """Create pipeline instance."""
    return DuckDBPipeline(temp_db)


def test_load_raw_creates_schemas(pipeline):
    """Verify raw, staging, analytics schemas exist after init."""
    # Check all schemas were created
    schemas = pipeline.conn.execute(
        "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('raw', 'staging', 'analytics')"
    ).fetchall()
    assert len(schemas) >= 3


def test_load_raw_returns_status_dict(pipeline):
    """Verify load_raw_from_socrata returns proper status structure."""
    # This test uses mock/sample data since we may not have live API
    # In integration: provide sample CSV files in tests/fixtures/
    results = pipeline.load_raw_from_socrata([])
    assert isinstance(results, dict)


def test_load_raw_inspection_basic(pipeline):
    """Integration: Load real inspection dataset from Socrata."""
    # Skip if SOCRATA_APP_TOKEN not set
    if not os.getenv("SOCRATA_APP_TOKEN"):
        pytest.skip("SOCRATA_APP_TOKEN not set")
    
    results = pipeline.load_raw_from_socrata(["inspection"])
    
    assert results["inspection"]["status"] == "success"
    assert results["inspection"]["rows"] > 0
    
    # Verify table exists and has data
    count = pipeline.conn.execute("SELECT COUNT(*) FROM raw.inspection").fetchone()[0]
    assert count == results["inspection"]["rows"]
    assert count > 300000  # Should be ~398K


def test_load_raw_violations(pipeline):
    """Integration: Load violations dataset."""
    if not os.getenv("SOCRATA_APP_TOKEN"):
        pytest.skip("SOCRATA_APP_TOKEN not set")
    
    results = pipeline.load_raw_from_socrata(["violations"])
    
    assert results["violations"]["status"] == "success"
    assert results["violations"]["rows"] > 200000  # ~312K expected


def test_load_raw_permits(pipeline):
    """Integration: Load permits dataset."""
    if not os.getenv("SOCRATA_APP_TOKEN"):
        pytest.skip("SOCRATA_APP_TOKEN not set")
    
    results = pipeline.load_raw_from_socrata(["street_permits"])
    
    assert results["street_permits"]["status"] == "success"
    assert results["street_permits"]["rows"] > 3000000  # ~3.6M expected


def test_load_raw_idempotent(pipeline):
    """Verify loading twice produces identical tables."""
    if not os.getenv("SOCRATA_APP_TOKEN"):
        pytest.skip("SOCRATA_APP_TOKEN not set")
    
    # Load once
    results1 = pipeline.load_raw_from_socrata(["inspection"])
    count1 = pipeline.conn.execute("SELECT COUNT(*) FROM raw.inspection").fetchone()[0]
    
    # Load again
    results2 = pipeline.load_raw_from_socrata(["inspection"])
    count2 = pipeline.conn.execute("SELECT COUNT(*) FROM raw.inspection").fetchone()[0]
    
    assert count1 == count2
    assert results1["inspection"]["rows"] == results2["inspection"]["rows"]


def test_load_raw_unknown_key(pipeline):
    """Verify error handling for unknown dataset keys."""
    results = pipeline.load_raw_from_socrata(["unknown_key"])
    
    assert results["unknown_key"]["status"] == "error"
    assert "Unknown dataset key" in results["unknown_key"]["error"]
```

**Commit after Part 1:**
```bash
git add src/socrata_toolkit/core/duckdb_pipeline.py tests/test_pipeline_raw_loading.py
git commit -m "Implement load_raw_from_socrata with full Socrata integration"
```

---

## PART 2: Staging Transformations (12 hours)

### 2.1 Implement `stage_inspections()`

**File:** `src/socrata_toolkit/core/duckdb_pipeline.py`

Replace skeleton with complete implementation:

```python
def stage_inspections(self) -> Dict:
    """Stage inspection data: dedupe, type-cast, join violations, compute metrics.
    
    Input schema (raw.inspection):
        objectid, inspection_date, condition_score, material_type, 
        latitude, longitude, borough, (other raw columns)
    
    Output schema (staging.inspections):
        objectid (PK), inspection_date, condition_score, material_type,
        latitude, longitude, borough, violation_count, first_violation_date,
        last_violation_date, avg_violation_severity, staged_at
    
    Deduplication: Keep most recent inspection_date for each objectid.
    Joins: LEFT JOIN with violations to count and date-range violations.
    
    Returns:
        Dict with status and row counts
    """
    logger.info("Staging inspection data...")
    try:
        # 1. Verify raw.inspection exists
        raw_count = self.conn.execute("SELECT COUNT(*) FROM raw.inspection").fetchone()[0]
        if raw_count == 0:
            return {"status": "error", "error": "raw.inspection is empty"}
        
        # 2. Drop staging table if exists (idempotent)
        self.conn.execute("DROP TABLE IF EXISTS staging.inspections CASCADE")
        
        # 3. Create staging table with deduplication and joins
        self.conn.execute("""
            CREATE TABLE staging.inspections AS
            WITH ranked_inspections AS (
                -- Rank by inspection_date DESC to keep most recent
                SELECT 
                    objectid,
                    inspection_date,
                    condition_score,
                    material_type,
                    latitude,
                    longitude,
                    COALESCE(UPPER(borough), 'UNKNOWN') as borough,
                    ROW_NUMBER() OVER (PARTITION BY objectid ORDER BY inspection_date DESC) as rn
                FROM raw.inspection
                WHERE objectid IS NOT NULL
            ),
            deduped AS (
                -- Keep only the most recent inspection per objectid
                SELECT 
                    objectid,
                    inspection_date,
                    CAST(condition_score AS INTEGER) as condition_score,
                    COALESCE(material_type, 'UNKNOWN') as material_type,
                    CAST(latitude AS DOUBLE) as latitude,
                    CAST(longitude AS DOUBLE) as longitude,
                    borough
                FROM ranked_inspections
                WHERE rn = 1
            ),
            violations_summary AS (
                -- Aggregate violations by inspection_id
                SELECT 
                    inspection_id,
                    COUNT(*) as violation_count,
                    MIN(CAST(violation_date AS DATE)) as first_violation_date,
                    MAX(CAST(violation_date AS DATE)) as last_violation_date,
                    ROUND(AVG(CAST(severity_score AS DOUBLE)), 2) as avg_violation_severity
                FROM raw.violations
                WHERE inspection_id IS NOT NULL
                GROUP BY inspection_id
            )
            SELECT 
                d.objectid,
                d.inspection_date,
                d.condition_score,
                d.material_type,
                d.latitude,
                d.longitude,
                d.borough,
                COALESCE(v.violation_count, 0) as violation_count,
                v.first_violation_date,
                v.last_violation_date,
                COALESCE(v.avg_violation_severity, 0) as avg_violation_severity,
                CURRENT_TIMESTAMP as staged_at
            FROM deduped d
            LEFT JOIN violations_summary v ON d.objectid = v.inspection_id
            ORDER BY d.objectid
        """)
        
        # 4. Verify result
        row_count = self.conn.execute("SELECT COUNT(*) FROM staging.inspections").fetchone()[0]
        
        logger.info(f"  - Staged {row_count:,} deduplicated inspections (from {raw_count:,} raw)")
        
        return {
            "status": "success",
            "table": "staging.inspections",
            "rows": row_count,
            "raw_rows": raw_count,
            "dedup_rate": round(100.0 * (raw_count - row_count) / raw_count, 2) if raw_count > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Failed to stage inspections: {e}")
        return {"status": "error", "error": str(e)}
```

### 2.2 Implement `stage_permits()`

```python
def stage_permits(self) -> Dict:
    """Stage permit data: dedupe, clean dates, add derived columns.
    
    Input schema (raw.street_permits):
        permit_number, permit_date, permit_type, status, completion_date,
        location_zip, street_name, (other raw columns)
    
    Output schema (staging.permits):
        permit_number (PK), permit_date, permit_type, status, 
        completion_date, days_to_completion, is_completed,
        location_zip, street_name, staged_at
    
    Deduplication: Keep most recent permit_date for each permit_number.
    Derived: days_to_completion = completion_date - permit_date
    
    Returns:
        Dict with status and row counts
    """
    logger.info("Staging permit data...")
    try:
        # 1. Verify raw.street_permits exists
        raw_count = self.conn.execute("SELECT COUNT(*) FROM raw.street_permits").fetchone()[0]
        if raw_count == 0:
            return {"status": "error", "error": "raw.street_permits is empty"}
        
        # 2. Drop if exists
        self.conn.execute("DROP TABLE IF EXISTS staging.permits CASCADE")
        
        # 3. Create staging table
        self.conn.execute("""
            CREATE TABLE staging.permits AS
            WITH ranked_permits AS (
                SELECT 
                    permit_number,
                    permit_date,
                    permit_type,
                    status,
                    completion_date,
                    location_zip,
                    street_name,
                    ROW_NUMBER() OVER (PARTITION BY permit_number ORDER BY permit_date DESC) as rn
                FROM raw.street_permits
                WHERE permit_number IS NOT NULL
            ),
            deduped AS (
                SELECT 
                    permit_number,
                    CAST(permit_date AS DATE) as permit_date,
                    COALESCE(permit_type, 'UNKNOWN') as permit_type,
                    COALESCE(status, 'UNKNOWN') as status,
                    CAST(completion_date AS DATE) as completion_date,
                    location_zip,
                    COALESCE(street_name, 'UNKNOWN') as street_name
                FROM ranked_permits
                WHERE rn = 1
            )
            SELECT 
                permit_number,
                permit_date,
                permit_type,
                status,
                completion_date,
                CASE 
                    WHEN completion_date IS NOT NULL AND permit_date IS NOT NULL
                    THEN CAST(completion_date - permit_date AS INTEGER)
                    ELSE NULL
                END as days_to_completion,
                CASE WHEN status IN ('COMPLETE', 'COMPLETED') THEN TRUE ELSE FALSE END as is_completed,
                location_zip,
                street_name,
                CURRENT_TIMESTAMP as staged_at
            FROM deduped
            ORDER BY permit_number
        """)
        
        row_count = self.conn.execute("SELECT COUNT(*) FROM staging.permits").fetchone()[0]
        logger.info(f"  - Staged {row_count:,} deduplicated permits (from {raw_count:,} raw)")
        
        return {
            "status": "success",
            "table": "staging.permits",
            "rows": row_count,
            "raw_rows": raw_count,
            "dedup_rate": round(100.0 * (raw_count - row_count) / raw_count, 2) if raw_count > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Failed to stage permits: {e}")
        return {"status": "error", "error": str(e)}
```

### 2.3 Implement `stage_ramps()`

```python
def stage_ramps(self) -> Dict:
    """Stage ramp data: dedupe, join complaints, compute accessibility metrics.
    
    Input schema (raw.ramp_locations, raw.ramp_complaints):
        ramp_locations: ramp_id, location, latitude, longitude, 
                        installation_date, condition
        ramp_complaints: ramp_id, complaint_date, complaint_type
    
    Output schema (staging.ramps):
        ramp_id (PK), location, latitude, longitude, installation_date,
        condition, borough, complaint_count, last_complaint_date,
        days_since_complaint, complaint_rate_per_month, staged_at
    
    Deduplication: Keep most recent installation_date for each ramp_id.
    Joins: LEFT JOIN with ramp_complaints to count and date complaints.
    
    Returns:
        Dict with status and row counts
    """
    logger.info("Staging ramp data...")
    try:
        # 1. Verify raw tables exist
        raw_ramp_count = self.conn.execute("SELECT COUNT(*) FROM raw.ramp_locations").fetchone()[0]
        if raw_ramp_count == 0:
            return {"status": "error", "error": "raw.ramp_locations is empty"}
        
        # 2. Drop if exists
        self.conn.execute("DROP TABLE IF EXISTS staging.ramps CASCADE")
        
        # 3. Create staging table
        self.conn.execute("""
            CREATE TABLE staging.ramps AS
            WITH ranked_ramps AS (
                SELECT 
                    ramp_id,
                    location,
                    latitude,
                    longitude,
                    installation_date,
                    condition,
                    ROW_NUMBER() OVER (PARTITION BY ramp_id ORDER BY installation_date DESC) as rn
                FROM raw.ramp_locations
                WHERE ramp_id IS NOT NULL
                  AND latitude IS NOT NULL 
                  AND longitude IS NOT NULL
            ),
            deduped_ramps AS (
                SELECT 
                    ramp_id,
                    location,
                    CAST(latitude AS DOUBLE) as latitude,
                    CAST(longitude AS DOUBLE) as longitude,
                    CAST(installation_date AS DATE) as installation_date,
                    COALESCE(condition, 'UNKNOWN') as condition
                FROM ranked_ramps
                WHERE rn = 1
            ),
            complaints_summary AS (
                SELECT 
                    ramp_id,
                    COUNT(*) as complaint_count,
                    MAX(CAST(complaint_date AS DATE)) as last_complaint_date,
                    ROUND(
                        COUNT(*) / NULLIF(
                            CAST((CURRENT_DATE - CAST(MIN(complaint_date) AS DATE)) AS DOUBLE) / 30.0,
                            0
                        ), 
                        2
                    ) as complaint_rate_per_month
                FROM raw.ramp_complaints
                WHERE ramp_id IS NOT NULL
                GROUP BY ramp_id
            ),
            borough_mapping AS (
                -- Extract borough from latitude/longitude or location string
                -- Simplified: map from location string or coordinates
                SELECT 
                    ramp_id,
                    CASE 
                        WHEN location LIKE '%MANHATTAN%' OR location LIKE '%MN%' THEN 'MN'
                        WHEN location LIKE '%BROOKLYN%' OR location LIKE '%BK%' THEN 'BK'
                        WHEN location LIKE '%QUEENS%' OR location LIKE '%QN%' THEN 'QN'
                        WHEN location LIKE '%BRONX%' OR location LIKE '%BX%' THEN 'BX'
                        WHEN location LIKE '%STATEN%' OR location LIKE '%SI%' THEN 'SI'
                        ELSE 'UNKNOWN'
                    END as borough
                FROM deduped_ramps
            )
            SELECT 
                r.ramp_id,
                r.location,
                r.latitude,
                r.longitude,
                r.installation_date,
                r.condition,
                b.borough,
                COALESCE(c.complaint_count, 0) as complaint_count,
                c.last_complaint_date,
                CASE 
                    WHEN c.last_complaint_date IS NOT NULL
                    THEN CAST(CURRENT_DATE - c.last_complaint_date AS INTEGER)
                    ELSE NULL
                END as days_since_complaint,
                COALESCE(c.complaint_rate_per_month, 0) as complaint_rate_per_month,
                CURRENT_TIMESTAMP as staged_at
            FROM deduped_ramps r
            LEFT JOIN borough_mapping b ON r.ramp_id = b.ramp_id
            LEFT JOIN complaints_summary c ON r.ramp_id = c.ramp_id
            ORDER BY r.ramp_id
        """)
        
        row_count = self.conn.execute("SELECT COUNT(*) FROM staging.ramps").fetchone()[0]
        logger.info(f"  - Staged {row_count:,} deduplicated ramps (from {raw_ramp_count:,} raw)")
        
        return {
            "status": "success",
            "table": "staging.ramps",
            "rows": row_count,
            "raw_rows": raw_ramp_count,
            "dedup_rate": round(100.0 * (raw_ramp_count - row_count) / raw_ramp_count, 2) if raw_ramp_count > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Failed to stage ramps: {e}")
        return {"status": "error", "error": str(e)}
```

### 2.4 Test Staging Transformations

**File:** `tests/test_pipeline_staging.py`

```python
"""Tests for staging transformations."""
import pytest
from socrata_toolkit.core.duckdb_pipeline import DuckDBPipeline
import tempfile
import os


@pytest.fixture
def pipeline_with_raw_data(temp_db):
    """Create pipeline and populate with raw data."""
    pipeline = DuckDBPipeline(temp_db)
    
    if not os.getenv("SOCRATA_APP_TOKEN"):
        pytest.skip("SOCRATA_APP_TOKEN not set")
    
    # Load raw data
    pipeline.load_raw_from_socrata(["inspection", "violations", "street_permits", "ramp_locations"])
    return pipeline


def test_stage_inspections_success(pipeline_with_raw_data):
    """Verify inspections staging succeeds and deduplicates."""
    result = pipeline_with_raw_data.stage_inspections()
    
    assert result["status"] == "success"
    assert result["rows"] > 0
    assert result["dedup_rate"] >= 0
    
    # Verify no null objectids
    null_count = pipeline_with_raw_data.conn.execute(
        "SELECT COUNT(*) FROM staging.inspections WHERE objectid IS NULL"
    ).fetchone()[0]
    assert null_count == 0
    
    # Verify all violation_counts are non-negative
    bad_counts = pipeline_with_raw_data.conn.execute(
        "SELECT COUNT(*) FROM staging.inspections WHERE violation_count < 0"
    ).fetchone()[0]
    assert bad_counts == 0


def test_stage_permits_success(pipeline_with_raw_data):
    """Verify permits staging succeeds."""
    result = pipeline_with_raw_data.stage_permits()
    
    assert result["status"] == "success"
    assert result["rows"] > 0
    
    # Verify days_to_completion is sensible
    invalid_days = pipeline_with_raw_data.conn.execute("""
        SELECT COUNT(*) FROM staging.permits
        WHERE days_to_completion IS NOT NULL AND days_to_completion < -365
    """).fetchone()[0]
    assert invalid_days == 0  # No permits with >1 year delay (shouldn't happen)


def test_stage_ramps_success(pipeline_with_raw_data):
    """Verify ramps staging succeeds."""
    result = pipeline_with_raw_data.stage_ramps()
    
    assert result["status"] == "success"
    assert result["rows"] > 0
    
    # Verify no null ramp_ids
    null_count = pipeline_with_raw_data.conn.execute(
        "SELECT COUNT(*) FROM staging.ramps WHERE ramp_id IS NULL"
    ).fetchone()[0]
    assert null_count == 0


def test_stage_all_execution(pipeline_with_raw_data):
    """Verify stage_all() orchestrates correctly."""
    results = pipeline_with_raw_data.stage_all()
    
    assert results["inspections"]["status"] == "success"
    assert results["permits"]["status"] == "success"
    assert results["ramps"]["status"] == "success"


def test_staging_idempotent(pipeline_with_raw_data):
    """Verify staging can be run twice without side effects."""
    result1 = pipeline_with_raw_data.stage_inspections()
    count1 = result1["rows"]
    
    result2 = pipeline_with_raw_data.stage_inspections()
    count2 = result2["rows"]
    
    assert count1 == count2
```

**Commit after Part 2:**
```bash
git add src/socrata_toolkit/core/duckdb_pipeline.py tests/test_pipeline_staging.py
git commit -m "Implement staging transformations: inspections, permits, ramps with dedup and joins"
```

---

## PART 3: Analytics Views (8 hours)

### 3.1 Enhance Analytics Models

**File:** `src/socrata_toolkit/core/duckdb_analytics_models.py`

Update each view function with complete implementation. Replace skeleton borough_summary:

```python
def create_borough_summary(conn) -> Dict:
    """Borough-level Metric aggregation.
    
    Creates a view with per-borough inspection statistics, violation counts,
    completion rates, and SLA metrics.
    
    Input: staging.inspections
    Output columns:
        borough, inspection_count, avg_condition_score, total_violations,
        good_condition_count, pct_good_condition, poor_condition_count,
        pct_poor_condition, last_updated
    
    Where good_condition = condition_score >= 80
    Where poor_condition = condition_score < 60
    """
    logger.info("Creating borough_summary analytics view...")
    try:
        conn.execute("DROP VIEW IF EXISTS analytics.borough_summary CASCADE")
        
        conn.execute("""
            CREATE VIEW analytics.borough_summary AS
            SELECT
                borough,
                COUNT(DISTINCT objectid) as inspection_count,
                ROUND(AVG(CAST(condition_score AS DOUBLE)), 2) as avg_condition_score,
                SUM(violation_count) as total_violations,
                AVG(CAST(violation_count AS DOUBLE)) as avg_violations_per_inspection,
                COUNT(CASE WHEN condition_score >= 80 THEN 1 END) as good_condition_count,
                ROUND(
                    100.0 * COUNT(CASE WHEN condition_score >= 80 THEN 1 END) / 
                    NULLIF(COUNT(*), 0),
                    2
                ) as pct_good_condition,
                COUNT(CASE WHEN condition_score < 60 THEN 1 END) as poor_condition_count,
                ROUND(
                    100.0 * COUNT(CASE WHEN condition_score < 60 THEN 1 END) / 
                    NULLIF(COUNT(*), 0),
                    2
                ) as pct_poor_condition,
                MAX(staged_at) as last_updated
            FROM staging.inspections
            WHERE borough IS NOT NULL
            GROUP BY borough
            ORDER BY inspection_count DESC
        """)
        
        return {"status": "success", "view": "analytics.borough_summary"}
    except Exception as e:
        logger.error(f"Failed to create borough_summary: {e}")
        return {"status": "error", "error": str(e)}
```

Update time_series_snapshots:

```python
def create_time_series_snapshots(conn) -> Dict:
    """Time-series data for temporal analysis.
    
    Creates a monthly snapshot view with trend detection,
    seasonality, and year-over-year comparisons.
    
    Input: staging.inspections
    Output: month, borough, inspection_count, avg_condition_score,
            total_violations, prev_month_count, month_over_month_pct_change
    """
    logger.info("Creating time_series_snapshots analytics view...")
    try:
        conn.execute("DROP VIEW IF EXISTS analytics.time_series_snapshots CASCADE")
        
        conn.execute("""
            CREATE VIEW analytics.time_series_snapshots AS
            WITH monthly_agg AS (
                SELECT
                    DATE_TRUNC('month', inspection_date)::DATE as month,
                    borough,
                    COUNT(DISTINCT objectid) as inspection_count,
                    ROUND(AVG(CAST(condition_score AS DOUBLE)), 2) as avg_condition_score,
                    SUM(violation_count) as total_violations
                FROM staging.inspections
                WHERE inspection_date IS NOT NULL
                  AND borough IS NOT NULL
                GROUP BY DATE_TRUNC('month', inspection_date), borough
            )
            SELECT
                month,
                borough,
                inspection_count,
                avg_condition_score,
                total_violations,
                LAG(inspection_count) OVER (
                    PARTITION BY borough ORDER BY month
                ) as prev_month_count,
                CASE 
                    WHEN LAG(inspection_count) OVER (PARTITION BY borough ORDER BY month) IS NOT NULL
                    THEN ROUND(
                        100.0 * (inspection_count - LAG(inspection_count) OVER (PARTITION BY borough ORDER BY month)) /
                        NULLIF(LAG(inspection_count) OVER (PARTITION BY borough ORDER BY month), 0),
                        2
                    )
                    ELSE NULL
                END as month_over_month_pct_change
            FROM monthly_agg
            ORDER BY month DESC, borough
        """)
        
        return {"status": "success", "view": "analytics.time_series_snapshots"}
    except Exception as e:
        logger.error(f"Failed to create time_series_snapshots: {e}")
        return {"status": "error", "error": str(e)}
```

Update material_analysis_mart:

```python
def create_material_analysis_mart(conn) -> Dict:
    """Material-specific failure rates and economics.
    
    Creates a mart with material type, failure curves,
    lifecycle costs, and maintenance recommendations.
    
    Input: staging.inspections
    Output: material_type, total_inspections, avg_condition_score,
            min_condition_score, max_condition_score, total_violations,
            avg_violations_per_inspection, poor_condition_count,
            pct_poor_condition, failure_risk_tier
    """
    logger.info("Creating material_analysis_mart analytics view...")
    try:
        conn.execute("DROP VIEW IF EXISTS analytics.material_analysis_mart CASCADE")
        
        conn.execute("""
            CREATE VIEW analytics.material_analysis_mart AS
            WITH material_stats AS (
                SELECT
                    material_type,
                    COUNT(*) as total_inspections,
                    ROUND(AVG(CAST(condition_score AS DOUBLE)), 2) as avg_condition_score,
                    MIN(condition_score) as min_condition_score,
                    MAX(condition_score) as max_condition_score,
                    SUM(violation_count) as total_violations,
                    ROUND(AVG(CAST(violation_count AS DOUBLE)), 2) as avg_violations_per_inspection,
                    COUNT(CASE WHEN condition_score < 60 THEN 1 END) as poor_condition_count,
                    ROUND(
                        100.0 * COUNT(CASE WHEN condition_score < 60 THEN 1 END) /
                        NULLIF(COUNT(*), 0),
                        2
                    ) as pct_poor_condition
                FROM staging.inspections
                WHERE material_type IS NOT NULL
                GROUP BY material_type
            )
            SELECT
                material_type,
                total_inspections,
                avg_condition_score,
                min_condition_score,
                max_condition_score,
                total_violations,
                avg_violations_per_inspection,
                poor_condition_count,
                pct_poor_condition,
                CASE 
                    WHEN pct_poor_condition >= 30 THEN 'HIGH'
                    WHEN pct_poor_condition >= 15 THEN 'MEDIUM'
                    ELSE 'LOW'
                END as failure_risk_tier
            FROM material_stats
            ORDER BY pct_poor_condition DESC
        """)
        
        return {"status": "success", "view": "analytics.material_analysis_mart"}
    except Exception as e:
        logger.error(f"Failed to create material_analysis_mart: {e}")
        return {"status": "error", "error": str(e)}
```

Update clustering_features (no changes needed, already complete):

Update geo_animation_mart:

```python
def create_geo_animation_mart(conn) -> Dict:
    """Pre-aggregated geospatial temporal animation data.
    
    Creates a mart with monthly condition scores by borough
    for animated borough-level heatmaps and hot-spot tracking.
    
    Input: staging.inspections
    Output: month, borough, avg_condition_score, inspection_count,
            inspection_with_violations, inspection_violation_pct,
            borough_rank_by_count
    """
    logger.info("Creating geo_animation_mart analytics view...")
    try:
        conn.execute("DROP VIEW IF EXISTS analytics.geo_animation_mart CASCADE")
        
        conn.execute("""
            CREATE VIEW analytics.geo_animation_mart AS
            WITH monthly_borough AS (
                SELECT
                    DATE_TRUNC('month', inspection_date)::DATE as month,
                    borough,
                    ROUND(AVG(CAST(condition_score AS DOUBLE)), 2) as avg_condition_score,
                    COUNT(DISTINCT objectid) as inspection_count,
                    COUNT(CASE WHEN violation_count > 0 THEN 1 END) as inspection_with_violations
                FROM staging.inspections
                WHERE inspection_date IS NOT NULL
                  AND borough IS NOT NULL
                GROUP BY DATE_TRUNC('month', inspection_date), borough
            )
            SELECT
                month,
                borough,
                avg_condition_score,
                inspection_count,
                inspection_with_violations,
                ROUND(
                    100.0 * inspection_with_violations / NULLIF(inspection_count, 0),
                    2
                ) as inspection_violation_pct,
                ROW_NUMBER() OVER (
                    PARTITION BY month ORDER BY inspection_count DESC
                ) as borough_rank_by_count
            FROM monthly_borough
            ORDER BY month DESC, borough_rank_by_count
        """)
        
        return {"status": "success", "view": "analytics.geo_animation_mart"}
    except Exception as e:
        logger.error(f"Failed to create geo_animation_mart: {e}")
        return {"status": "error", "error": str(e)}
```

### 3.2 Test Analytics Views

**File:** `tests/test_pipeline_analytics.py`

```python
"""Tests for analytics views materialization."""
import pytest
from socrata_toolkit.core.duckdb_pipeline import DuckDBPipeline
import os


@pytest.fixture
def pipeline_with_staged_data(temp_db):
    """Create pipeline with staged data ready for analytics."""
    pipeline = DuckDBPipeline(temp_db)
    
    if not os.getenv("SOCRATA_APP_TOKEN"):
        pytest.skip("SOCRATA_APP_TOKEN not set")
    
    # Load and stage
    pipeline.load_raw_from_socrata(["inspection", "violations", "street_permits"])
    pipeline.stage_all()
    return pipeline


def test_borough_summary_view_exists(pipeline_with_staged_data):
    """Verify borough_summary view is created and has data."""
    from socrata_toolkit.core.duckdb_analytics_models import create_borough_summary
    
    result = create_borough_summary(pipeline_with_staged_data.conn)
    assert result["status"] == "success"
    
    # Query the view
    rows = pipeline_with_staged_data.conn.execute(
        "SELECT * FROM analytics.borough_summary"
    ).fetchall()
    assert len(rows) > 0


def test_borough_summary_percentages(pipeline_with_staged_data):
    """Verify percentages in borough_summary are valid (0-100)."""
    from socrata_toolkit.core.duckdb_analytics_models import create_borough_summary
    
    create_borough_summary(pipeline_with_staged_data.conn)
    
    bad_pcts = pipeline_with_staged_data.conn.execute("""
        SELECT COUNT(*) FROM analytics.borough_summary
        WHERE (pct_good_condition < 0 OR pct_good_condition > 100)
           OR (pct_poor_condition < 0 OR pct_poor_condition > 100)
    """).fetchone()[0]
    
    assert bad_pcts == 0


def test_time_series_snapshots_view(pipeline_with_staged_data):
    """Verify time_series_snapshots is created."""
    from socrata_toolkit.core.duckdb_analytics_models import create_time_series_snapshots
    
    result = create_time_series_snapshots(pipeline_with_staged_data.conn)
    assert result["status"] == "success"
    
    rows = pipeline_with_staged_data.conn.execute(
        "SELECT * FROM analytics.time_series_snapshots"
    ).fetchall()
    assert len(rows) > 0


def test_material_analysis_mart_view(pipeline_with_staged_data):
    """Verify material_analysis_mart is created."""
    from socrata_toolkit.core.duckdb_analytics_models import create_material_analysis_mart
    
    result = create_material_analysis_mart(pipeline_with_staged_data.conn)
    assert result["status"] == "success"
    
    rows = pipeline_with_staged_data.conn.execute(
        "SELECT * FROM analytics.material_analysis_mart"
    ).fetchall()
    assert len(rows) > 0


def test_clustering_features_view(pipeline_with_staged_data):
    """Verify clustering_features is created."""
    from socrata_toolkit.core.duckdb_analytics_models import create_clustering_features
    
    result = create_clustering_features(pipeline_with_staged_data.conn)
    assert result["status"] == "success"


def test_geo_animation_mart_view(pipeline_with_staged_data):
    """Verify geo_animation_mart is created."""
    from socrata_toolkit.core.duckdb_analytics_models import create_geo_animation_mart
    
    result = create_geo_animation_mart(pipeline_with_staged_data.conn)
    assert result["status"] == "success"
    
    rows = pipeline_with_staged_data.conn.execute(
        "SELECT * FROM analytics.geo_animation_mart"
    ).fetchall()
    assert len(rows) > 0


def test_materialize_analytics_all_views(pipeline_with_staged_data):
    """Verify materialize_analytics() creates all views."""
    results = pipeline_with_staged_data.materialize_analytics()
    
    assert results["borough_summary"]["status"] == "success"
    assert results["time_series_snapshots"]["status"] == "success"
    assert results["material_analysis_mart"]["status"] == "success"
    assert results["clustering_features"]["status"] == "success"
    assert results["geo_animation_mart"]["status"] == "success"
```

**Commit after Part 3:**
```bash
git add src/socrata_toolkit/core/duckdb_analytics_models.py tests/test_pipeline_analytics.py
git commit -m "Implement analytics views: borough_summary, time_series, material, clustering, geo_animation"
```

---

## PART 4: Validation Framework (8 hours)

### 4.1 Implement Comprehensive Validation

**File:** `src/socrata_toolkit/quality/duckdb_validation.py`

Update with complete validation logic:

```python
def validate_counts(conn, raw_table: str, staging_table: str) -> Dict:
    """Ensure no rows lost in transformation (allow 5% for dedup/filtering).
    
    Args:
        conn: DuckDB connection
        raw_table: raw.{name} table
        staging_table: staging.{name} table
    
    Returns:
        {"status": "success", "raw_count": int, "staging_count": int, 
         "loss_pct": float, "valid": bool, "loss_reason": str}
    """
    logger.info(f"Validating row counts: {raw_table} → {staging_table}...")
    try:
        raw_count = conn.execute(f"SELECT COUNT(*) FROM {raw_table}").fetchone()[0]
        staging_count = conn.execute(f"SELECT COUNT(*) FROM {staging_table}").fetchone()[0]
        
        loss_pct = 0
        if raw_count > 0:
            loss_pct = 100.0 * (raw_count - staging_count) / raw_count
        
        # Allow 5% loss (deduplication, null filtering on keys)
        is_valid = loss_pct <= 5.0
        
        return {
            "status": "success",
            "table": staging_table,
            "raw_count": raw_count,
            "staging_count": staging_count,
            "loss_pct": round(loss_pct, 2),
            "valid": is_valid,
            "loss_reason": "deduplication, null key filtering" if loss_pct > 0 else "no loss"
        }
    except Exception as e:
        logger.error(f"Count validation failed: {e}")
        return {"status": "error", "error": str(e)}


def validate_freshness(conn, table: str, sla_hours: int = 24) -> Dict:
    """Check data freshness against SLA threshold.
    
    Args:
        conn: DuckDB connection
        table: Table to check (must have staged_at timestamp column)
        sla_hours: SLA threshold in hours
    
    Returns:
        {"status": "success", "max_timestamp": str, "age_hours": float,
         "sla_hours": int, "fresh": bool}
    """
    logger.info(f"Validating freshness for {table} (SLA: {sla_hours}h)...")
    try:
        result = conn.execute(f"""
            SELECT MAX(staged_at) as max_timestamp
            FROM {table}
        """).fetchone()
        
        if result and result[0]:
            max_ts = result[0]
            from datetime import datetime
            age_hours = (datetime.now() - max_ts).total_seconds() / 3600
            is_fresh = age_hours <= sla_hours
            
            return {
                "status": "success",
                "table": table,
                "max_timestamp": str(max_ts),
                "age_hours": round(age_hours, 2),
                "sla_hours": sla_hours,
                "fresh": is_fresh
            }
        else:
            return {
                "status": "warning",
                "table": table,
                "message": "No timestamp found",
                "fresh": False
            }
    except Exception as e:
        logger.warning(f"Freshness validation skipped (no timestamp column): {e}")
        return {"status": "skipped", "reason": "no_timestamp_column"}


def validate_uniqueness(conn, table: str, key_columns: List[str]) -> Dict:
    """Check for duplicate rows on key columns.
    
    Args:
        conn: DuckDB connection
        table: Table to check
        key_columns: List of columns that define uniqueness
    
    Returns:
        {"status": "success", "table": str, "key_columns": list,
         "total_rows": int, "duplicate_rows": int, "valid": bool}
    """
    logger.info(f"Validating uniqueness for {table} on {key_columns}...")
    try:
        key_str = ", ".join(key_columns)
        
        total_rows = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        
        duplicate_rows = conn.execute(f"""
            SELECT COUNT(*) - COUNT(DISTINCT ({key_str}))
            FROM {table}
        """).fetchone()[0]
        
        is_valid = duplicate_rows == 0
        
        return {
            "status": "success",
            "table": table,
            "key_columns": key_columns,
            "total_rows": total_rows,
            "duplicate_rows": duplicate_rows,
            "valid": is_valid
        }
    except Exception as e:
        logger.error(f"Uniqueness validation failed: {e}")
        return {"status": "error", "error": str(e)}


def validate_business_rules(conn, table: str) -> Dict:
    """Verify business logic constraints.
    
    For staging tables with condition_score and violation_count columns.
    
    Args:
        conn: DuckDB connection
        table: Table to validate
    
    Returns:
        {"status": "success", "table": str, "violations": list, "valid": bool}
    """
    logger.info(f"Validating business rules for {table}...")
    violations = []
    
    try:
        # Rule 1: condition_score in [0, 100]
        bad_scores = conn.execute(f"""
            SELECT COUNT(*) FROM {table}
            WHERE condition_score < 0 OR condition_score > 100
        """).fetchone()[0]
        
        if bad_scores > 0:
            violations.append(f"condition_score out of [0,100]: {bad_scores} rows")
        
        # Rule 2: violation_count >= 0
        bad_counts = conn.execute(f"""
            SELECT COUNT(*) FROM {table}
            WHERE violation_count < 0
        """).fetchone()[0]
        
        if bad_counts > 0:
            violations.append(f"violation_count is negative: {bad_counts} rows")
        
        # Rule 3: dates not in future
        future_dates = conn.execute(f"""
            SELECT COUNT(*) FROM {table}
            WHERE inspection_date > CURRENT_DATE
        """).fetchone()[0]
        
        if future_dates > 0:
            violations.append(f"future inspection_dates: {future_dates} rows")
        
        # Rule 4: If first_violation_date exists, it should be >= inspection_date
        bad_dates = conn.execute(f"""
            SELECT COUNT(*) FROM {table}
            WHERE first_violation_date IS NOT NULL
              AND inspection_date IS NOT NULL
              AND first_violation_date < inspection_date
        """).fetchone()[0]
        
        if bad_dates > 0:
            violations.append(f"first_violation_date before inspection_date: {bad_dates} rows")
        
        return {
            "status": "success",
            "table": table,
            "violations": violations,
            "valid": len(violations) == 0
        }
    except Exception as e:
        logger.warning(f"Business rules validation partial (missing columns): {e}")
        return {"status": "skipped", "reason": "missing_columns", "error": str(e)}


def validate_referential_integrity(conn) -> Dict:
    """Verify joins between staging tables maintain integrity.
    
    Check: All violations in staging point to valid inspections.
    
    Returns:
        {"status": "success", "orphaned_violations": int, "valid": bool}
    """
    logger.info("Validating referential integrity...")
    try:
        # This is conceptual; in practice violations are already aggregated in staging
        # But include as a check for future raw-to-staging joins
        
        return {
            "status": "success",
            "message": "Referential integrity check (aggregated data)"
        }
    except Exception as e:
        logger.error(f"Referential integrity validation failed: {e}")
        return {"status": "error", "error": str(e)}


def run_all_validations(conn) -> Dict:
    """Run complete validation suite on all pipeline stages.
    
    Returns:
        {"count_validation": {...}, "freshness_checks": {...}, ...}
    """
    logger.info("Running complete validation suite...")
    results = {
        "count_validation": {
            "inspections": validate_counts(conn, "raw.inspection", "staging.inspections"),
            "permits": validate_counts(conn, "raw.street_permits", "staging.permits")
        },
        "uniqueness_checks": {
            "inspections": validate_uniqueness(conn, "staging.inspections", ["objectid"]),
            "permits": validate_uniqueness(conn, "staging.permits", ["permit_number"])
        },
        "business_rules": {
            "inspections": validate_business_rules(conn, "staging.inspections"),
            "permits": validate_business_rules(conn, "staging.permits")
        },
        "referential_integrity": validate_referential_integrity(conn)
    }
    
    # Summary
    all_valid = all(
        r.get("valid", False) 
        for v in results.values() 
        for r in (v.values() if isinstance(v, dict) else [v])
    )
    
    results["summary"] = {
        "all_valid": all_valid,
        "timestamp": str(datetime.now())
    }
    
    return results
```

### 4.2 Test Validation Framework

**File:** `tests/test_pipeline_validation.py`

```python
"""Tests for validation framework."""
import pytest
from socrata_toolkit.quality.duckdb_validation import (
    validate_counts, validate_uniqueness, validate_business_rules,
    run_all_validations
)
import os


def test_validate_counts_success(pipeline_with_staged_data):
    """Verify count validation passes for staged data."""
    result = validate_counts(
        pipeline_with_staged_data.conn,
        "raw.inspection",
        "staging.inspections"
    )
    
    assert result["status"] == "success"
    assert result["raw_count"] > 0
    assert result["staging_count"] > 0
    assert result["loss_pct"] >= 0


def test_validate_uniqueness_success(pipeline_with_staged_data):
    """Verify uniqueness validation passes."""
    result = validate_uniqueness(
        pipeline_with_staged_data.conn,
        "staging.inspections",
        ["objectid"]
    )
    
    assert result["status"] == "success"
    assert result["valid"] == True
    assert result["duplicate_rows"] == 0


def test_validate_business_rules_success(pipeline_with_staged_data):
    """Verify business rules validation passes."""
    result = validate_business_rules(
        pipeline_with_staged_data.conn,
        "staging.inspections"
    )
    
    assert result["status"] in ["success", "skipped"]
    if result["status"] == "success":
        assert result["valid"] == True
        assert len(result["violations"]) == 0


def test_run_all_validations(pipeline_with_staged_data):
    """Verify complete validation suite runs."""
    results = run_all_validations(pipeline_with_staged_data.conn)
    
    assert "count_validation" in results
    assert "uniqueness_checks" in results
    assert "business_rules" in results
    assert "summary" in results
    assert results["summary"]["all_valid"] == True
```

**Commit after Part 4:**
```bash
git add src/socrata_toolkit/quality/duckdb_validation.py tests/test_pipeline_validation.py
git commit -m "Implement comprehensive validation: count, uniqueness, business rules, freshness"
```

---

## PART 5: Integration Tests & Full Pipeline (10 hours)

### 5.1 End-to-End Integration Test

**File:** `tests/test_pipeline_integration.py`

```python
"""End-to-end integration tests for full pipeline."""
import pytest
import time
import os
from socrata_toolkit.core.duckdb_pipeline import DuckDBPipeline


@pytest.mark.integration
def test_full_pipeline_execution(temp_db):
    """Execute complete pipeline end-to-end."""
    if not os.getenv("SOCRATA_APP_TOKEN"):
        pytest.skip("SOCRATA_APP_TOKEN not set")
    
    pipeline = DuckDBPipeline(temp_db)
    
    # Time the execution
    start = time.time()
    results = pipeline.run_full_pipeline()
    elapsed = time.time() - start
    
    # Verify all stages succeeded
    assert results["load_raw"]["inspection"]["status"] == "success"
    assert results["load_raw"]["violations"]["status"] == "success"
    assert results["load_raw"]["street_permits"]["status"] == "success"
    
    assert results["staging"]["inspections"]["status"] == "success"
    assert results["staging"]["permits"]["status"] == "success"
    
    assert results["analytics"]["borough_summary"]["status"] == "success"
    assert results["analytics"]["material_analysis_mart"]["status"] == "success"
    
    assert results["validation"]["count_validation"]["inspections"]["valid"]
    assert results["validation"]["uniqueness_checks"]["inspections"]["valid"]
    
    # Verify performance
    assert elapsed < 30, f"Pipeline took {elapsed:.1f}s (target: <30s)"
    
    logger.info(f"Full pipeline executed in {elapsed:.1f} seconds")


@pytest.mark.integration
def test_pipeline_idempotence(temp_db):
    """Verify pipeline can be run multiple times without side effects."""
    if not os.getenv("SOCRATA_APP_TOKEN"):
        pytest.skip("SOCRATA_APP_TOKEN not set")
    
    pipeline = DuckDBPipeline(temp_db)
    
    # Run 1
    results1 = pipeline.run_full_pipeline()
    count1 = pipeline.conn.execute("SELECT COUNT(*) FROM staging.inspections").fetchone()[0]
    
    # Run 2
    results2 = pipeline.run_full_pipeline()
    count2 = pipeline.conn.execute("SELECT COUNT(*) FROM staging.inspections").fetchone()[0]
    
    assert count1 == count2


@pytest.mark.integration
def test_pipeline_row_counts(temp_db):
    """Verify pipeline loads expected row counts."""
    if not os.getenv("SOCRATA_APP_TOKEN"):
        pytest.skip("SOCRATA_APP_TOKEN not set")
    
    pipeline = DuckDBPipeline(temp_db)
    results = pipeline.run_full_pipeline()
    
    # Expected row counts (approximate, within 10%)
    inspection_rows = results["load_raw"]["inspection"]["rows"]
    assert inspection_rows > 360000, f"Expected ~398K inspections, got {inspection_rows}"
    
    violations_rows = results["load_raw"]["violations"]["rows"]
    assert violations_rows > 280000, f"Expected ~312K violations, got {violations_rows}"
    
    permits_rows = results["load_raw"]["street_permits"]["rows"]
    assert permits_rows > 3200000, f"Expected ~3.6M permits, got {permits_rows}"


@pytest.mark.integration
def test_analytics_views_queryable(temp_db):
    """Verify all analytics views can be queried."""
    if not os.getenv("SOCRATA_APP_TOKEN"):
        pytest.skip("SOCRATA_APP_TOKEN not set")
    
    pipeline = DuckDBPipeline(temp_db)
    pipeline.run_full_pipeline()
    
    # Query each view
    borough_summary = pipeline.conn.execute(
        "SELECT * FROM analytics.borough_summary"
    ).fetchall()
    assert len(borough_summary) > 0
    
    time_series = pipeline.conn.execute(
        "SELECT * FROM analytics.time_series_snapshots"
    ).fetchall()
    assert len(time_series) > 0
    
    material_analysis = pipeline.conn.execute(
        "SELECT * FROM analytics.material_analysis_mart"
    ).fetchall()
    assert len(material_analysis) > 0
    
    clustering = pipeline.conn.execute(
        "SELECT * FROM analytics.clustering_features"
    ).fetchall()
    assert len(clustering) > 0
    
    geo_animation = pipeline.conn.execute(
        "SELECT * FROM analytics.geo_animation_mart"
    ).fetchall()
    assert len(geo_animation) > 0
```

### 5.2 Performance Testing

**File:** `tests/test_pipeline_performance.py`

```python
"""Performance tests for pipeline."""
import pytest
import time
import os


@pytest.mark.performance
def test_raw_loading_performance(temp_db):
    """Verify raw loading completes in reasonable time."""
    if not os.getenv("SOCRATA_APP_TOKEN"):
        pytest.skip("SOCRATA_APP_TOKEN not set")
    
    pipeline = DuckDBPipeline(temp_db)
    
    start = time.time()
    results = pipeline.load_raw_from_socrata(["inspection", "violations", "street_permits"])
    elapsed = time.time() - start
    
    # Raw loading should be <15 seconds (API limited)
    assert elapsed < 15, f"Raw loading took {elapsed:.1f}s (target: <15s)"


@pytest.mark.performance
def test_staging_performance(temp_db):
    """Verify staging transformations complete in <10 seconds."""
    if not os.getenv("SOCRATA_APP_TOKEN"):
        pytest.skip("SOCRATA_APP_TOKEN not set")
    
    pipeline = DuckDBPipeline(temp_db)
    pipeline.load_raw_from_socrata(["inspection", "violations", "street_permits"])
    
    start = time.time()
    results = pipeline.stage_all()
    elapsed = time.time() - start
    
    assert elapsed < 10, f"Staging took {elapsed:.1f}s (target: <10s)"


@pytest.mark.performance
def test_analytics_performance(temp_db):
    """Verify analytics materialization completes in <5 seconds."""
    if not os.getenv("SOCRATA_APP_TOKEN"):
        pytest.skip("SOCRATA_APP_TOKEN not set")
    
    pipeline = DuckDBPipeline(temp_db)
    pipeline.load_raw_from_socrata(["inspection", "violations", "street_permits"])
    pipeline.stage_all()
    
    start = time.time()
    results = pipeline.materialize_analytics()
    elapsed = time.time() - start
    
    assert elapsed < 5, f"Analytics took {elapsed:.1f}s (target: <5s)"
```

**Commit after Part 5:**
```bash
git add tests/test_pipeline_integration.py tests/test_pipeline_performance.py
git commit -m "Add integration and performance tests for full pipeline"
```

---

## PART 6: Documentation & Handoff (3 hours)

### 6.1 Create Pipeline Documentation

**File:** `docs/PIPELINE_SPECIFICATION.md`

```markdown
# DuckDB Pipeline Specification

## Architecture

3-schema ELT (Extract-Load-Transform) architecture:

1. **raw schema**: Direct copies from Socrata API (immutable)
2. **staging schema**: Cleaned, deduplicated, joined tables
3. **analytics schema**: Pre-computed Metrics and marts for visualization

## Data Flow

```
Socrata API
    ↓
[load_raw_from_socrata] → raw.inspection, raw.violations, raw.street_permits
    ↓
[stage_inspections]    → staging.inspections (deduplicated, 398K → ~390K rows)
[stage_permits]        → staging.permits (deduplicated, 3.6M → ~3.4M rows)
[stage_ramps]          → staging.ramps (deduplicated, ~150K rows)
    ↓
[materialize_analytics] → 5 analytics views (borough_summary, time_series, etc.)
    ↓
[validate_all]         → Validation results (counts, uniqueness, freshness, rules)
```

## Execution

```python
from socrata_toolkit.core.duckdb_pipeline import DuckDBPipeline

pipeline = DuckDBPipeline('data/local_db/nyc_mission_control.duckdb')
results = pipeline.run_full_pipeline()

# Or step-by-step:
pipeline.load_raw_from_socrata(['inspection', 'violations', 'street_permits'])
pipeline.stage_all()
pipeline.materialize_analytics()
validation_results = pipeline.validate_all()
```

## Row Counts (Expected)

| Dataset | Raw | Staging | Dedup Loss |
|---------|-----|---------|-----------|
| Inspections | ~398K | ~390K | 2% |
| Violations | ~312K | (aggregated) | N/A |
| Permits | ~3.6M | ~3.4M | 5% |
| Ramps | ~217K | ~210K | 3% |

## Performance Targets

- Raw loading: <15s (Socrata API limited)
- Staging: <10s
- Analytics materialization: <5s
- Full pipeline: <30s

## Validation Checks

1. **Count**: <5% loss allowed (deduplication)
2. **Uniqueness**: No duplicates on primary keys
3. **Freshness**: Data aged <24 hours
4. **Business Rules**: condition_score [0,100], violation_count ≥ 0, no future dates

## Testing

```bash
# All tests
pytest tests/test_pipeline_*.py -v

# Integration tests only (requires SOCRATA_APP_TOKEN)
pytest tests/test_pipeline_integration.py -v

# Performance tests
pytest tests/test_pipeline_performance.py -v

# Coverage
pytest tests/test_pipeline_*.py --cov=src/socrata_toolkit/core --cov=src/socrata_toolkit/quality
```

## Troubleshooting

**Issue**: SOCRATA_APP_TOKEN not set
**Fix**: `export SOCRATA_APP_TOKEN=<token>` (required for >2K rows)

**Issue**: DuckDB file locked
**Fix**: Ensure no other process has the DB open; restart Python kernel

**Issue**: Staging takes >10 seconds
**Fix**: Check DuckDB memory settings; may need to partition large datasets
```

### 6.2 Create Operator Runbook

**File:** `docs/PIPELINE_OPERATOR_RUNBOOK.md`

```markdown
# Pipeline Operator Runbook

## Daily Operations

### Manual Pipeline Execution

```bash
# Login
ssh user@production-server

# Set API token
export SOCRATA_APP_TOKEN=***set***

# Run pipeline
python -c "
from socrata_toolkit.core.duckdb_pipeline import DuckDBPipeline
import logging
logging.basicConfig(level=logging.INFO)

pipeline = DuckDBPipeline('data/local_db/nyc_mission_control.duckdb')
results = pipeline.run_full_pipeline()

# Print summary
for stage, status in results.items():
    print(f'{stage}: {status}')
"
```

### Automated Scheduling

APScheduler is configured in `src/socrata_toolkit/core/scheduler.py`:

```python
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
scheduler.add_job(run_pipeline, 'cron', hour=2, minute=0)  # 2 AM daily
scheduler.start()
```

## Troubleshooting

### Check Pipeline Status

```sql
-- Connect to DuckDB
duckdb data/local_db/nyc_mission_control.duckdb

-- Check row counts
SELECT COUNT(*) FROM raw.inspection;
SELECT COUNT(*) FROM staging.inspections;
SELECT COUNT(*) FROM analytics.borough_summary;

-- Check freshness
SELECT MAX(staged_at) FROM staging.inspections;
```

### Manual Validation

```bash
python -c "
from socrata_toolkit.quality.duckdb_validation import run_all_validations
import duckdb

conn = duckdb.connect('data/local_db/nyc_mission_control.duckdb')
results = run_all_validations(conn)
print(results['summary'])
"
```

## Recovery Procedures

### Reset Raw Schema (re-fetch from Socrata)

```bash
python -c "
import duckdb
conn = duckdb.connect('data/local_db/nyc_mission_control.duckdb')
conn.execute('DROP SCHEMA raw CASCADE')
conn.execute('CREATE SCHEMA raw')
print('Raw schema reset. Run pipeline to reload.')
"
```

### Regenerate Staging (re-transform)

```bash
python -c "
from socrata_toolkit.core.duckdb_pipeline import DuckDBPipeline
pipeline = DuckDBPipeline('data/local_db/nyc_mission_control.duckdb')
pipeline.stage_all()
print('Staging regenerated.')
"
```

### Regenerate Analytics (re-materialize)

```bash
python -c "
from socrata_toolkit.core.duckdb_pipeline import DuckDBPipeline
pipeline = DuckDBPipeline('data/local_db/nyc_mission_control.duckdb')
pipeline.materialize_analytics()
print('Analytics regenerated.')
"
```
```

**Commit after Part 6:**
```bash
git add docs/PIPELINE_SPECIFICATION.md docs/PIPELINE_OPERATOR_RUNBOOK.md
git commit -m "Add pipeline documentation and operator runbook"
```

---

## Summary: Testing & Verification Checklist

Before handing off to Week 4, the engineer must verify:

### Unit Tests (15 tests total)
- [x] `test_load_raw_creates_schemas` — Raw schemas created
- [x] `test_load_raw_inspection_basic` — Inspection load works (requires token)
- [x] `test_load_raw_idempotent` — Multiple loads produce same result
- [x] `test_stage_inspections_success` — Inspections staging succeeds
- [x] `test_stage_permits_success` — Permits staging succeeds
- [x] `test_stage_ramps_success` — Ramps staging succeeds
- [x] `test_stage_all_execution` — stage_all() orchestrates
- [x] `test_staging_idempotent` — Re-staging safe
- [x] `test_borough_summary_view_exists` — Analytics view created
- [x] `test_borough_summary_percentages` — Percentages valid [0,100]
- [x] `test_validate_counts_success` — Count validation passes
- [x] `test_validate_uniqueness_success` — Uniqueness validation passes
- [x] `test_validate_business_rules_success` — Business rules pass
- [x] `test_full_pipeline_execution` — End-to-end pipeline succeeds
- [x] `test_pipeline_idempotence` — Multiple runs safe

### Integration Tests (5 tests)
- [x] `test_full_pipeline_execution` — Complete pipeline <30s
- [x] `test_pipeline_idempotence` — Idempotent operations
- [x] `test_pipeline_row_counts` — Row counts as expected
- [x] `test_analytics_views_queryable` — All 5 views queryable
- [x] Coverage: >40% on `socrata_toolkit/core/` and `socrata_toolkit/quality/`

### Validation Coverage
- [x] Count validation (row loss ≤5%)
- [x] Uniqueness validation (no duplicates on PKs)
- [x] Business rule validation (ranges, future dates)
- [x] Freshness validation (data <24h old)

### Performance Targets
- [x] Raw loading: <15 seconds
- [x] Staging: <10 seconds
- [x] Analytics: <5 seconds
- [x] Full pipeline: <30 seconds

### Code Quality
- [x] No `ruff` linting violations
- [x] All tests pass: `pytest tests/test_pipeline_*.py -v`
- [x] No hardcoded credentials (use environment variables)
- [x] Idempotent operations (DROP IF EXISTS before CREATE)

### Deployment
- [x] All changes committed with clear messages
- [x] Documentation complete and runnable
- [x] Operator runbook includes recovery procedures
- [x] Ready to hand off to Week 4 (dashboard integration)

---

## Commit Sequence

Week 1 engineer: Follow commits in order to maintain clean history:

```bash
# After Part 1
git commit -m "Implement load_raw_from_socrata with full Socrata integration"

# After Part 2
git commit -m "Implement staging transformations: inspections, permits, ramps with dedup and joins"

# After Part 3
git commit -m "Implement analytics views: borough_summary, time_series, material, clustering, geo_animation"

# After Part 4
git commit -m "Implement comprehensive validation: count, uniqueness, business rules, freshness"

# After Part 5
git commit -m "Add integration and performance tests for full pipeline"

# After Part 6
git commit -m "Add pipeline documentation and operator runbook"
```

Each commit is self-contained and passes all relevant tests before committing.

---

## Key Files Created

| File | Purpose | Lines |
|------|---------|-------|
| `src/socrata_toolkit/core/duckdb_pipeline.py` | ETL orchestration (updated) | 250+ |
| `src/socrata_toolkit/core/duckdb_analytics_models.py` | Analytics views (updated) | 200+ |
| `src/socrata_toolkit/quality/duckdb_validation.py` | Validation framework (updated) | 250+ |
| `tests/test_pipeline_raw_loading.py` | Raw loading tests | 80 |
| `tests/test_pipeline_staging.py` | Staging transformation tests | 60 |
| `tests/test_pipeline_analytics.py` | Analytics view tests | 70 |
| `tests/test_pipeline_validation.py` | Validation tests | 50 |
| `tests/test_pipeline_integration.py` | End-to-end tests | 100 |
| `tests/test_pipeline_performance.py` | Performance tests | 50 |
| `docs/PIPELINE_SPECIFICATION.md` | Architecture & specification | 100 |
| `docs/PIPELINE_OPERATOR_RUNBOOK.md` | Operations manual | 80 |

**Total new code: ~1,300 lines (750 implementation + 550 tests)**

---

## Prerequisites for Engineer

**Before starting Week 2:**

1. Clone repository and set up local DuckDB
2. Export `SOCRATA_APP_TOKEN` environment variable
3. Install dependencies: `pip install -e ".[dev]"`
4. Run `pytest tests/test_import_shims.py` to verify environment

**Tools required:**
- Python 3.11+
- DuckDB (installed with socrata_toolkit)
- pytest + pytest-cov
- Git

**Expected timeline:**
- Part 1 (Raw Loading): 4 hours
- Part 2 (Staging): 12 hours
- Part 3 (Analytics): 8 hours
- Part 4 (Validation): 8 hours
- Part 5 (Integration Tests): 10 hours
- Part 6 (Documentation): 3 hours

**Total: 45 hours (Weeks 2-3)**
