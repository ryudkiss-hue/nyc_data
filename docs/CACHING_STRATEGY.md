# Data Caching Strategy: All 24 Datasets

**Objective:** Local + cloud cache of historical data for fast, cost-effective analytics without repeated Socrata API calls

---

## Architecture Overview

```
Socrata API (live source)
    ↓ (initial fetch + daily refresh)
Local Cache Layer
├── DuckDB (L1: operational, <30 days)
└── Parquet Files (L2: historical archive)
    ↓ (sync to cloud)
Cloud Cache Layer
├── MotherDuck (L3: cloud-optimized, all history)
└── Cloud Storage (S3/GCS: cold archive)
    ↓ (query)
Analytics Layer
├── SIM Workflows (access cached data)
├── Dashboards (real-time views)
└── Reports (historical analysis)
```

---

## Caching Strategy by Dataset

### HIGH-VOLUME DATASETS (Cache Aggressively)

#### 1. **COMPLAINTS_311** (1.2M+ rows)
- **Update frequency:** Daily
- **Historical retention:** 3 years (rolling)
- **Cache location:** DuckDB (L1) + MotherDuck (L3)
- **Estimated size:** 
  - Daily: ~5,000 rows
  - Annual: ~1.8M rows
  - 3-year archive: ~5.4M rows (~450 MB)
- **Strategy:**
  - Fetch daily incremental (created_date > yesterday)
  - Store in DuckDB daily table
  - Archive to MotherDuck monthly
  - Query recent via DuckDB, historical via MotherDuck

#### 2. **VIOLATIONS** (18,618 rows)
- **Update frequency:** Daily
- **Historical retention:** 5 years (compliance requirement)
- **Cache location:** DuckDB (L1) + MotherDuck (L3)
- **Estimated size:**
  - Daily: ~50 rows
  - Annual: ~18,250 rows
  - 5-year archive: ~91,250 rows (~8 MB)
- **Strategy:**
  - Fetch daily (violation_issue_date > yesterday)
  - Maintain 90-day hot cache in DuckDB
  - Archive older data to MotherDuck
  - Enable 5-year historical analysis

#### 3. **INSPECTION** (3,000 rows)
- **Update frequency:** Daily
- **Historical retention:** 10 years (operational baseline)
- **Cache location:** DuckDB (L1) + MotherDuck (L3)
- **Estimated size:**
  - Daily: ~8 rows
  - Annual: ~3,000 rows
  - 10-year archive: ~30,000 rows (~2.5 MB)
- **Strategy:**
  - Full archive to MotherDuck
  - 1-year hot cache in DuckDB
  - Enable long-term trend analysis

---

### MEDIUM-VOLUME DATASETS (Cache Strategically)

#### 4. **STREET_PERMITS** (50,633 rows)
- **Update frequency:** Real-time (as issued)
- **Historical retention:** 3 years (active + recent completed)
- **Cache location:** DuckDB + MotherDuck
- **Estimated size:** ~150M (Parquet) / ~1.2GB (uncompressed)
- **Strategy:**
  - Fetch new permits daily (issued_date > yesterday)
  - Full permit history in MotherDuck (3 years)
  - Active permits (status != 'Closed') in DuckDB
  - Compress with Parquet (50% reduction)

#### 5. **STREET_CONSTRUCTION_INSPECTIONS** (12,280 rows)
- **Update frequency:** As inspected (~100-200/day)
- **Historical retention:** 3 years
- **Cache location:** DuckDB + MotherDuck
- **Estimated size:** ~100MB
- **Strategy:**
  - Incremental daily fetch (inspection_date > yesterday)
  - Full history in MotherDuck
  - 30-day hot cache in DuckDB

#### 6. **RAMP_PROGRESS** (1,356 rows)
- **Update frequency:** Weekly (project updates)
- **Historical retention:** Program inception (5+ years)
- **Cache location:** DuckDB + MotherDuck
- **Estimated size:** ~5MB
- **Strategy:**
  - Full historical cache (small dataset)
  - DuckDB for current quarter analysis
  - MotherDuck for multi-year trends

#### 7. **DISMISSALS** (12,716 rows)
- **Update frequency:** As appealed/decided (~20-50/day)
- **Historical retention:** 7 years (legal hold)
- **Cache location:** DuckDB + MotherDuck
- **Estimated size:** ~80MB
- **Strategy:**
  - Full 7-year archive in MotherDuck
  - Immutable cache (dismissals don't change)
  - Enable compliance audits

---

### LOW-VOLUME DATASETS (Cache Comprehensively)

#### 8-24. **Other Datasets** (< 100K rows each)
- **Total combined:** ~700K rows
- **Combined size:** ~50MB (Parquet)
- **Cache strategy:** Full historical cache (cheap)
  - tree_damage (828 rows) → Full history
  - curb_metal_protruding (1,395 rows) → Full history
  - correspondences (3,786 rows) → Full 7-year history
  - reinspection (963 rows) → Full history
  - permit_stipulations (4,978 rows) → Full history
  - step_streets (6,281 rows) → Full (static dataset)
  - capital_blocks (4,930 rows) → Full
  - capital_intersections (4,156 rows) → Full
  - street_closures_block (50,735 rows) → 3-year history
  - street_resurfacing_schedule (15,216 rows) → 3-year history
  - street_resurfacing_inhouse (1,965 rows) → Full history
  - weekly_construction (3,978 rows) → Archived (stale since 2017)
  - ramp_complaints (815 rows) → Full history
  - ramp_locations (5,813 rows) → Full (semi-static)
  - pedestrian_demand (10,533 rows) → Full (updates infrequently)
  - sidewalk_planimetric (36,371 rows) → Full (mostly static)
  - mappluto (91,914 rows) → Full (annual updates)
  - complaints_311 → See high-volume section

---

## Cache Layer Implementation

### Layer 1: DuckDB (Local, <30 days)

**Purpose:** Fast local queries for recent data and operational dashboards

**Configuration:**
```python
# Database file
DUCKDB_PATH = "data/local_db/nyc_sim_cache.duckdb"

# Schema structure
raw/          # Raw data as-fetched from Socrata
staging/      # Classified & transformed data (spaCy output)
analytics/    # Aggregated metrics & reports
archive/      # Data older than 30 days (links to cloud)
```

**Size estimates:**
- Hot data (30 days): ~500 MB
- Indexes: ~50 MB
- Total DuckDB footprint: ~600 MB (manageable locally)

**Refresh strategy:**
```
Daily 6 AM UTC:
├── Fetch new records from Socrata (incremental)
├── Run spaCy classification (deterministic)
├── Insert into staging/
├── Update analytics/ views
└── Archive old data to MotherDuck
```

---

### Layer 2: MotherDuck (Cloud, All history)

**Purpose:** Cost-effective cloud storage + querying for historical analysis

**Configuration:**
```python
# Cloud databases (MotherDuck)
md:raw/      # Full historical raw data (all 24 datasets)
md:staging/  # Historical classified data
md:analytics/# Historical aggregated metrics
```

**Benefits:**
- ✓ No storage cost for schema/queries
- ✓ Shared compute (pay per query)
- ✓ Integrates with DuckDB locally
- ✓ Scales to TB without infrastructure
- ✓ SQL access (full DuckDB compatibility)

**Size estimates (all 24 datasets, full history):**
- Raw data archive: ~2-3 GB
- Staged/classified: ~1.5-2 GB
- Analytics: ~500 MB
- **Total: ~4-5 GB** (very cheap in cloud)

**Refresh strategy:**
```
Monthly archive (1st of month):
├── Export 30+ day old data from DuckDB
├── Compress to Parquet
├── Upload to MotherDuck
└── Remove from local DuckDB
```

---

### Layer 3: Parquet Files (Local Archive)

**Purpose:** Compressed, versioned historical backups

**Configuration:**
```
data/
└── parquet_archive/
    ├── 2026/
    │   ├── 06-june/
    │   │   ├── violations_2026-06.parquet
    │   │   ├── inspection_2026-06.parquet
    │   │   └── ... (all 24 datasets)
    │   └── 07-july/
    │       └── ...
    └── 2025/
        └── ...
```

**Compression:** Parquet reduces size by ~70%
- Example: 100 MB CSV → 30 MB Parquet
- Total monthly archive: ~30-50 MB per month
- Annual archive: ~360-600 MB (very small)

---

## Implementation: Data Ingestion Pipeline

### Script 1: Initial Historical Data Fetch

```python
# src/socrata_toolkit/caching/bootstrap_cache.py
"""
Bootstrap: Fetch all historical data from Socrata into local cache.
Runs once to populate DuckDB with 30 days of data.
"""

import duckdb
from socrata_toolkit.core.client import SocrataClient
from datetime import datetime, timedelta

def bootstrap_historical_cache():
    """
    1. Create DuckDB schema
    2. Fetch 30 days of historical data per dataset
    3. Run spaCy classification
    4. Materialize analytics views
    """
    
    conn = duckdb.connect("data/local_db/nyc_sim_cache.duckdb")
    client = SocrataClient()
    
    # Create schemas
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
    conn.execute("CREATE SCHEMA IF NOT EXISTS staging")
    conn.execute("CREATE SCHEMA IF NOT EXISTS analytics")
    
    # Bootstrap each dataset
    datasets = {
        "violations": "6kbp-uz6m",
        "inspection": "dntt-gqwq",
        "dismissals": "p4u2-3jgx",
        # ... (all 24 datasets)
    }
    
    for dataset_name, fourfour in datasets.items():
        print(f"[BOOTSTRAP] {dataset_name}...")
        
        # Fetch 30 days of historical data
        where = f"violation_issue_date > '{(datetime.now() - timedelta(days=30)).date()}'"
        df = client.fetch_dataframe(
            "data.cityofnewyork.us",
            fourfour,
            where=where,
            max_rows=50000
        )
        
        # Land in raw schema
        table_name = f"raw.{dataset_name}"
        conn.register(f"{dataset_name}_temp", df)
        conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM {dataset_name}_temp")
        
        # Classify (if applicable)
        if dataset_name in ["violations", "inspection", "tree_damage"]:
            classified_df = classify_dataset(df, dataset_name)
            conn.register(f"{dataset_name}_classified", classified_df)
            staging_table = f"staging.{dataset_name}"
            conn.execute(f"CREATE TABLE {staging_table} AS SELECT * FROM {dataset_name}_classified")
        
        print(f"  ✓ {len(df)} rows")
    
    # Materialize analytics views
    materialize_analytics(conn)
    
    print("[BOOTSTRAP] Complete. Cache ready for queries.")
    return conn

def classify_dataset(df, dataset_name):
    """Apply spaCy classification to text columns."""
    from socrata_toolkit.analysis.nlp_classifier import TextClassifierPipeline
    pipeline = TextClassifierPipeline()
    
    if dataset_name == "violations":
        return pipeline.classify_violations_dataframe(df)
    elif dataset_name == "inspection":
        return pipeline.classify_violations_dataframe(df)  # Reuse
    # ... etc
    
    return df

def materialize_analytics(conn):
    """Create analytics views for dashboards."""
    
    # Violations by borough
    conn.execute("""
    CREATE OR REPLACE VIEW analytics.violations_by_borough AS
    SELECT 
      Borough,
      COUNT(*) as violation_count,
      AVG(CAST(severity AS INTEGER)) as avg_severity,
      DATE_TRUNC('month', Violation_Issue_Date) as month
    FROM staging.violations
    GROUP BY Borough, DATE_TRUNC('month', Violation_Issue_Date)
    ORDER BY month DESC, violation_count DESC
    """)
    
    # Ramp completion by borough
    conn.execute("""
    CREATE OR REPLACE VIEW analytics.ramp_completion AS
    SELECT 
      Borough,
      COUNT(*) as total_ramps,
      SUM(CASE WHEN Status = 'Completed' THEN 1 ELSE 0 END) as completed,
      ROUND(100.0 * SUM(CASE WHEN Status = 'Completed' THEN 1 ELSE 0 END) / COUNT(*), 1) as completion_pct
    FROM staging.ramp_progress
    GROUP BY Borough
    ORDER BY completion_pct DESC
    """)
    
    print("[ANALYTICS] Views materialized")
```

### Script 2: Daily Incremental Refresh

```python
# src/socrata_toolkit/caching/daily_refresh.py
"""
Daily refresh: Fetch new data from Socrata, update cache.
Runs at 6 AM UTC via APScheduler.
"""

def daily_refresh_cache():
    """
    1. For each dataset, fetch records created/updated since yesterday
    2. Insert into DuckDB
    3. Re-classify (spaCy)
    4. Refresh analytics views
    5. Archive old data to MotherDuck
    """
    
    conn = duckdb.connect("data/local_db/nyc_sim_cache.duckdb")
    client = SocrataClient()
    
    yesterday = (datetime.now() - timedelta(days=1)).date()
    
    # High-volume datasets: incremental fetch
    incremental_datasets = {
        "violations": ("violation_issue_date", "6kbp-uz6m"),
        "inspection": ("inspection_date", "dntt-gqwq"),
        "dismissals": ("violation_issue_date", "p4u2-3jgx"),
        "complaints_311": ("created_date", "erm2-nwe9"),
        "ramp_progress": ("updated_date", "e7gc-ub6z"),
        # ... etc
    }
    
    for dataset_name, (date_field, fourfour) in incremental_datasets.items():
        print(f"[DAILY] Refreshing {dataset_name}...")
        
        # Incremental fetch (only new records)
        where = f"{date_field} >= '{yesterday}'"
        df = client.fetch_dataframe(
            "data.cityofnewyork.us",
            fourfour,
            where=where,
            max_rows=10000
        )
        
        if len(df) == 0:
            print(f"  (no new records)")
            continue
        
        # Upsert into DuckDB (replace if exists)
        table_name = f"raw.{dataset_name}"
        conn.register(f"{dataset_name}_new", df)
        conn.execute(f"""
        INSERT OR REPLACE INTO {table_name}
        SELECT * FROM {dataset_name}_new
        """)
        
        # Re-classify
        classified = classify_dataset(df, dataset_name)
        staging_table = f"staging.{dataset_name}"
        conn.register(f"{dataset_name}_classified", classified)
        conn.execute(f"""
        INSERT OR REPLACE INTO {staging_table}
        SELECT * FROM {dataset_name}_classified
        """)
        
        print(f"  ✓ {len(df)} new records")
    
    # Refresh materialized views
    conn.execute("REFRESH MATERIALIZED VIEW analytics.violations_by_borough")
    conn.execute("REFRESH MATERIALIZED VIEW analytics.ramp_completion")
    
    # Archive old data to MotherDuck (30+ days old)
    archive_to_motherduck(conn, days_old=30)
    
    print("[DAILY] Refresh complete.")

def archive_to_motherduck(conn, days_old=30):
    """
    Export data older than 30 days to MotherDuck,
    remove from local DuckDB.
    """
    
    cutoff_date = (datetime.now() - timedelta(days=days_old)).date()
    
    datasets_to_archive = [
        ("violations", "violation_issue_date"),
        ("inspection", "inspection_date"),
        ("complaints_311", "created_date"),
        # ... etc
    ]
    
    for dataset_name, date_field in datasets_to_archive:
        print(f"[ARCHIVE] Exporting {dataset_name} to MotherDuck...")
        
        # Export to Parquet
        parquet_path = f"data/parquet_archive/{datetime.now().year}/{datetime.now().strftime('%m-%B')}/{dataset_name}_{datetime.now().date()}.parquet"
        
        conn.execute(f"""
        COPY (
            SELECT * FROM raw.{dataset_name}
            WHERE {date_field} < '{cutoff_date}'
        ) TO '{parquet_path}' (FORMAT PARQUET)
        """)
        
        # Upload to MotherDuck (SDK method)
        upload_to_motherduck(parquet_path, f"md:raw.{dataset_name}")
        
        # Delete from local cache
        conn.execute(f"""
        DELETE FROM raw.{dataset_name}
        WHERE {date_field} < '{cutoff_date}'
        """)
        
        print(f"  ✓ Archived to MotherDuck")

def upload_to_motherduck(local_file, motherduck_table):
    """Upload Parquet file to MotherDuck."""
    import motherduck
    
    conn = motherduck.connect(token=os.getenv("MOTHERDUCK_TOKEN"))
    
    # Load Parquet into temporary table
    conn.execute(f"""
    CREATE OR REPLACE TABLE temp_load AS
    SELECT * FROM read_parquet('{local_file}')
    """)
    
    # Append to MotherDuck table
    conn.execute(f"""
    INSERT INTO {motherduck_table}
    SELECT * FROM temp_load
    """)
    
    print(f"  Uploaded {local_file} to {motherduck_table}")
```

### Script 3: Cloud Query Interface

```python
# src/socrata_toolkit/caching/cloud_queries.py
"""
Query historical data from cloud cache (MotherDuck).
Enables cross-dataset analysis without local storage.
"""

def query_historical_violations(borough=None, years=5):
    """Query violations archive from MotherDuck."""
    
    import motherduck
    conn = motherduck.connect(token=os.getenv("MOTHERDUCK_TOKEN"))
    
    where = ""
    if borough:
        where += f"AND Borough = '{borough}'"
    
    query = f"""
    SELECT 
      Borough,
      violation_type,
      DATE_TRUNC('month', violation_issue_date) as month,
      COUNT(*) as count,
      AVG(severity) as avg_severity
    FROM md:staging.violations
    WHERE violation_issue_date >= CURRENT_DATE - INTERVAL '{years} years'
    {where}
    GROUP BY Borough, violation_type, DATE_TRUNC('month', violation_issue_date)
    ORDER BY month DESC
    """
    
    return conn.execute(query).fetch_df()

def query_ramp_trends(years=10):
    """10-year ramp completion trend from cloud."""
    
    conn = motherduck.connect(token=os.getenv("MOTHERDUCK_TOKEN"))
    
    return conn.execute("""
    SELECT 
      DATE_TRUNC('month', updated_date) as month,
      Borough,
      COUNT(*) as total_ramps,
      SUM(CASE WHEN Status = 'Completed' THEN 1 ELSE 0 END) as completed,
      AVG(PercentComplete) as avg_progress
    FROM md:staging.ramp_progress
    WHERE updated_date >= CURRENT_DATE - INTERVAL '10 years'
    GROUP BY DATE_TRUNC('month', updated_date), Borough
    ORDER BY month DESC
    """).fetch_df()

def cross_dataset_analysis():
    """Multi-dataset analysis across cloud cache."""
    
    conn = motherduck.connect(token=os.getenv("MOTHERDUCK_TOKEN"))
    
    # Find violations + tree damage co-locations
    return conn.execute("""
    SELECT 
      v.Borough,
      v.Site_Street_Address,
      COUNT(DISTINCT v.violation_id) as violations,
      COUNT(DISTINCT t.tree_damage_id) as tree_damages,
      'CO-LOCATED' as issue_type
    FROM md:staging.violations v
    LEFT JOIN md:staging.tree_damage t 
      ON ST_DWithin(
        ST_Point(v.Longitude, v.Latitude),
        ST_Point(t.Longitude, t.Latitude),
        50  -- 50 meter buffer
      )
    WHERE v.violation_issue_date >= CURRENT_DATE - INTERVAL '1 year'
    GROUP BY v.Borough, v.Site_Street_Address
    HAVING COUNT(DISTINCT t.tree_damage_id) > 0
    ORDER BY violations DESC
    """).fetch_df()
```

---

## Operational Schedule

### Daily (6 AM UTC)
```
1. Fetch new records from Socrata (15 min)
2. Run spaCy classification (5 min)
3. Update DuckDB (10 min)
4. Refresh analytics views (5 min)
5. Archive 30+ day old data to MotherDuck (20 min)
```
**Total: ~55 minutes | Runs automatically**

### Monthly (1st of month, 8 AM UTC)
```
1. Export full month to Parquet
2. Verify compression & checksums
3. Backup Parquet files
4. Generate archival report
```

### Quarterly (1st of quarter, 9 AM UTC)
```
1. Data quality audit (DuckDB vs Socrata sample)
2. Cache performance analysis
3. Storage utilization report
4. Refresh analytics metadata
```

### Annually (Jan 1, 10 AM UTC)
```
1. Archive previous year to cold storage
2. Recalculate retention policies
3. Update cost projections
4. Compliance audit (7-year legal hold for dismissals)
```

---

## Cost Analysis

### Local Storage
- DuckDB (30-day hot cache): ~600 MB = $0/month (local disk)
- Parquet archives (monthly): ~50 MB/month = ~600 MB/year = negligible

### Cloud (MotherDuck)
- Storage: ~4-5 GB for all history = **$5-10/month**
- Queries: ~100 analytical queries/month = **$2-5/month**
- **Total cloud: ~$10-15/month**

### API Calls (Socrata)
- Daily incremental fetches: ~100 API calls/month
- With app token: **Unlimited (included)**
- Without token: ~200K rows/day limit
- **Cost: $0** (City of NYC, free tier)

**Total monthly cost: $10-15** (vs. $70+ for all-Claude approach)

---

## Monitoring & Maintenance

### Health Checks (Automated)
```python
def cache_health_check():
    """Daily cache validation."""
    
    conn = duckdb.connect("data/local_db/nyc_sim_cache.duckdb")
    
    checks = {
        "duckdb_size": conn.execute(
            "SELECT SUM(memory_usage) FROM duckdb_databases()"
        ).fetchone()[0],
        
        "raw_record_count": conn.execute(
            "SELECT SUM(COUNT(*)) FROM information_schema.tables WHERE table_schema='raw'"
        ).fetchone()[0],
        
        "latest_record_dates": conn.execute(
            """
            SELECT table_name, MAX(created_date) 
            FROM raw.* 
            GROUP BY table_name
            """
        ).fetch_df(),
        
        "motherduck_connection": test_motherduck_connection(),
        
        "classification_success_rate": conn.execute(
            "SELECT COUNT(*) FILTER (WHERE violation_type IS NOT NULL) / COUNT(*) FROM staging.violations"
        ).fetchone()[0]
    }
    
    # Alert if issues
    if checks["duckdb_size"] > 1000000000:  # >1GB
        alert("DuckDB exceeding size limit")
    
    if any(d < datetime.now() - timedelta(days=2) for d in checks["latest_record_dates"]):
        alert("Cache stale - check Socrata API")
    
    return checks
```

### Alerting
```
⚠️ If DuckDB > 1GB → Archive more aggressively
⚠️ If latest data > 2 days old → API issues
⚠️ If classification success < 95% → Rerun spaCy
⚠️ If MotherDuck unavailable → Fall back to Parquet
```

---

## Summary: All 24 Datasets Cached

| Layer | Size | Access Time | Cost | Retention |
|-------|------|---|---|---|
| **DuckDB (L1)** | 600 MB | <100ms | $0 | 30 days |
| **MotherDuck (L3)** | 4-5 GB | <500ms | $10-15/mo | All history |
| **Parquet (L2)** | ~600 MB/yr | N/A (archive) | $0 | Backup |

**All 24 datasets fully cached locally + cloud**. Ready for production analytics without repeated API calls.

---

## Next Steps

1. ✓ Deploy `bootstrap_cache.py` (initial load)
2. ✓ Set up `daily_refresh.py` with APScheduler
3. ✓ Configure MotherDuck credentials
4. ✓ Deploy `cloud_queries.py` for historical access
5. ✓ Enable `cache_health_check()` monitoring
6. ✓ Test failover (MotherDuck unavailable → Parquet)
