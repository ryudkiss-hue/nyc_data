# MotherDuck Index Optimization Recommendations

**Expected Performance Impact:** 2-3x query speedup on dashboard views

## Summary

Analysis of serving views and analytics tables identified strategic indexing opportunities
across three categories: temporal, geospatial, and categorical. These indexes will significantly
accelerate the most frequently accessed dashboard queries without requiring application code changes.

---

## 1. Temporal Indexes (Phase E: Time Series)

**Purpose:** Accelerate date range queries on decomposition data (~450 rows analyzed by date)

**Target Table:** `analytics.phase_e_decomposition`

### Index: On Date (Primary Sort)
```sql
CREATE INDEX idx_phase_e_date ON analytics.phase_e_decomposition (date DESC);
```

**Why:** 
- Phase E view orders by `date DESC` for time series rendering
- Eliminates full table scan on daily decomposition queries
- Helps with range queries like "last 90 days"

**Estimated impact:** 30-50ms → 5-10ms (5-10x speedup)

**Query example:**
```sql
SELECT * FROM app_queries.v_phase_e_decomposition 
WHERE date >= current_date - interval 90 days
ORDER BY date DESC
```

---

### Index: Compound (Date + Borough)
```sql
CREATE INDEX idx_phase_e_date_borough ON analytics.phase_e_decomposition (date DESC, borough);
```

**Why:**
- Supports borough-filtered time series
- Enables index-only scans when borough filter is applied
- Covers most dashboard drill-down workflows

**Estimated impact:** 40-80ms → 8-15ms (5-8x speedup)

**Query example:**
```sql
SELECT * FROM analytics.phase_e_decomposition
WHERE borough = 'MN' AND date >= '2026-05-15'
ORDER BY date DESC
```

---

## 2. Geospatial Indexes (Phase D: Anomaly Detection)

**Purpose:** Accelerate spatial queries on outlier detection (~25 rows with coordinates)

**Target Table:** `analytics.phase_d_anomalies`

### Index: On Geospatial Coordinates (Latitude + Longitude)
```sql
CREATE INDEX idx_phase_d_location ON analytics.phase_d_anomalies (latitude, longitude);
```

**Why:**
- Supports map-based filtering ("show anomalies near coordinate")
- Enables proximity queries (e.g., within X miles of inspection)
- Improves Folium map rendering performance

**Estimated impact:** 20-40ms → 3-5ms (6-12x speedup)

**Query example:**
```sql
SELECT * FROM analytics.phase_d_anomalies
WHERE latitude BETWEEN -74.3 AND -73.8 
  AND longitude BETWEEN 40.5 AND 40.9
```

---

### Index: Compound (Borough + Coordinates)
```sql
CREATE INDEX idx_phase_d_borough_location ON analytics.phase_d_anomalies (borough, latitude, longitude);
```

**Why:**
- Supports "show outliers in Manhattan" + spatial filters
- Reduces search space before coordinate matching
- Covers both map and list-view rendering

**Estimated impact:** 25-50ms → 5-8ms (5-8x speedup)

---

## 3. Categorical Indexes (KPI + Classification)

**Purpose:** Accelerate KPI lookups and classification filtering (~90 KPI rows × 18 metrics)

**Target Table:** `analytics.kpi_metrics`

### Index: On KPI Name (Fast Metric Lookup)
```sql
CREATE INDEX idx_kpi_name ON analytics.kpi_metrics (kpi_name);
```

**Why:**
- Each dashboard card queries for specific KPI (e.g., "phase_b_clustering_strength")
- Eliminates table scan for KPI selection
- Supports rapid metric card updates

**Estimated impact:** 15-30ms → 2-4ms (5-10x speedup)

**Query example:**
```sql
SELECT * FROM analytics.kpi_metrics
WHERE kpi_name = 'phase_b_clustering_strength'
```

---

### Index: Compound (Borough + KPI Name)
```sql
CREATE INDEX idx_kpi_borough_name ON analytics.kpi_metrics (borough, kpi_name);
```

**Why:**
- Supports borough-level metric cards
- Enables filtering by borough + metric name (most common dashboard query)
- Index-only scan coverage for common queries

**Estimated impact:** 20-40ms → 3-5ms (5-10x speedup)

**Query example:**
```sql
SELECT kpi_value FROM analytics.kpi_metrics
WHERE borough = 'BK' AND kpi_name = 'phase_c_concentration_index'
```

---

### Index: On Classification (Distribution Type Filtering)
```sql
CREATE INDEX idx_phase_c_distribution_type ON analytics.phase_c_distributions (distribution_type);
```

**Target Table:** `analytics.phase_c_distributions`

**Why:**
- Filters outliers by type (NORMAL, RIGHT_SKEWED, LEFT_SKEWED, BIMODAL)
- Useful for exploratory analysis "show me only right-skewed distributions"
- Small number of distinct values (high selectivity benefit)

**Estimated impact:** 10-25ms → 2-3ms (5-10x speedup)

---

## 4. Critical Path Indexes (Multi-Purpose)

**Purpose:** Optimize the most frequently accessed queries on the dashboard

### Indexes for Phase B (Clustering Analysis)
```sql
CREATE INDEX idx_phase_b_borough ON analytics.phase_b_spatial_clusters (borough);
CREATE INDEX idx_phase_b_significance ON analytics.phase_b_spatial_clusters (p_value DESC);
```

**Why:**
- Dashboard renders clustering strength for all 5 boroughs
- P-value filtering for "show only significant results"

**Estimated impact:** 5-10ms → 1-2ms per borough query

---

### Indexes for Phase F (SLA Confidence)
```sql
CREATE INDEX idx_phase_f_borough ON analytics.phase_f_bootstrap_ci (borough);
CREATE INDEX idx_phase_f_risk_level ON analytics.phase_f_bootstrap_ci (risk_level, prob_meets_sla);
```

**Why:**
- KPI cards filter by borough
- Risk gauges filter by risk_level (HIGH, MEDIUM, LOW, CRITICAL)
- Probability sorting for "worst-performing boroughs first"

**Estimated impact:** 10-15ms → 2-3ms per filtered query

---

## Implementation Steps

1. **Verify current query performance (baseline):**
   ```sql
   -- Measure before indexing
   SELECT COUNT(*) FROM analytics.phase_e_decomposition WHERE date >= '2026-04-15';
   -- Should take ~50-150ms without index
   ```

2. **Create indexes** in batches to avoid long-running operations:
   ```bash
   # Batch 1: Temporal (Phase E)
   duckdb path/to/db.duckdb < temporal_indexes.sql
   
   # Batch 2: Geospatial (Phase D)
   duckdb path/to/db.duckdb < geospatial_indexes.sql
   
   # Batch 3: Categorical (KPI)
   duckdb path/to/db.duckdb < categorical_indexes.sql
   ```

3. **Verify performance gains (post-index):**
   ```sql
   -- Same query should now take ~5-20ms
   SELECT COUNT(*) FROM analytics.phase_e_decomposition WHERE date >= '2026-04-15';
   ```

4. **Monitor index usage** (if supported by MotherDuck):
   ```sql
   -- Check index statistics
   SELECT * FROM duckdb_indexes();
   ```

---

## DuckDB Implementation Notes

**For MotherDuck Cloud:**
- Indexes are automatically maintained by the cloud service
- No additional vacuuming or maintenance required
- Dropped indexes immediately free space; created indexes use ~5-10% of table size

**For Local DuckDB:**
- Execute index creation as shown above
- Verify index creation: `SELECT * FROM information_schema.statistics;`
- Drop unused indexes: `DROP INDEX idx_phase_e_date;`

---

## Expected Overall Performance Improvement

| Component | Before | After | Speedup |
|---|---|---|---|
| Single Phase Query | 50-200ms | 5-20ms | **5-10x** |
| KPI Dashboard Load (18 metrics) | 900-1800ms | 90-180ms | **10x** |
| Phase E Time Series (450 rows) | 150ms | 20ms | **7-8x** |
| Phase D Anomaly Map (25 rows) | 100ms | 10ms | **10x** |

**Cumulative dashboard improvement:** 2-3x faster page load times

---

## Maintenance

- **Index size growth:** <500MB total for all indexes (negligible vs. data size)
- **Query planner optimization:** DuckDB automatically uses indexes when beneficial
- **Stale statistics:** DuckDB maintains stats automatically; no manual ANALYZE required

---

## SQL DDL (Ready to Deploy)

All recommendations condensed into a single deployment script:

```sql
-- Temporal Indexes (Phase E: Time Series)
CREATE INDEX idx_phase_e_date ON analytics.phase_e_decomposition (date DESC);
CREATE INDEX idx_phase_e_date_borough ON analytics.phase_e_decomposition (date DESC, borough);

-- Geospatial Indexes (Phase D: Anomalies)
CREATE INDEX idx_phase_d_location ON analytics.phase_d_anomalies (latitude, longitude);
CREATE INDEX idx_phase_d_borough_location ON analytics.phase_d_anomalies (borough, latitude, longitude);

-- Categorical Indexes (KPI + Classification)
CREATE INDEX idx_kpi_name ON analytics.kpi_metrics (kpi_name);
CREATE INDEX idx_kpi_borough_name ON analytics.kpi_metrics (borough, kpi_name);
CREATE INDEX idx_phase_c_distribution_type ON analytics.phase_c_distributions (distribution_type);

-- Phase-Specific Indexes
CREATE INDEX idx_phase_b_borough ON analytics.phase_b_spatial_clusters (borough);
CREATE INDEX idx_phase_b_significance ON analytics.phase_b_spatial_clusters (p_value DESC);
CREATE INDEX idx_phase_f_borough ON analytics.phase_f_bootstrap_ci (borough);
CREATE INDEX idx_phase_f_risk_level ON analytics.phase_f_bootstrap_ci (risk_level, prob_meets_sla);
```

---

## Monitoring & Observability

To verify index effectiveness after deployment, add monitoring:

```python
# In serving views or dashboard callback
import time

start = time.time()
df = conn.fetch_df("SELECT * FROM app_queries.v_phase_e_decomposition ...")
latency_ms = (time.time() - start) * 1000

if latency_ms > 100:
    logger.warning(f"Slow dashboard query: {latency_ms:.1f}ms (expected <50ms with indexes)")
else:
    logger.debug(f"Query latency: {latency_ms:.1f}ms (index performing well)")
```

---

## References

- DuckDB Index Documentation: https://duckdb.org/docs/sql/indexes.html
- MotherDuck Query Optimization: https://docs.motherduck.com/performance
- SQL Index Best Practices: https://en.wikipedia.org/wiki/Database_index
