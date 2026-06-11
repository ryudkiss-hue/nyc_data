# NYC DOT SIM Workflows — Optimization Implementation Guide

**Document Status:** Completed 2026-06-11  
**Target Audience:** Data Engineers, Backend Developers, DevOps  
**Phase:** 3B (Performance Optimization & Dashboard Connections)

---

## Table of Contents

1. [Async KPI Computation Pattern](#async-kpi-computation-pattern)
2. [Materialized View Strategy](#materialized-view-strategy)
3. [Cache Invalidation Policy](#cache-invalidation-policy)
4. [Dashboard Response Optimization](#dashboard-response-optimization)
5. [Monitoring & Alerting](#monitoring--alerting)
6. [Future Optimization Roadmap](#future-optimization-roadmap)

---

## Async KPI Computation Pattern

### Architecture Overview

```
DuckDB L1 (Hot Cache)
    │
    ├─ Raw data + 30-day history
    └─ Used by: Initial data loads, first-page views
    
Analytics Compute Layer (Async Background Task)
    │
    ├─ Runs nightly (23:00 UTC)
    ├─ Computes 50+ KPIs in parallel
    ├─ Materializes results to analytics_cloud schema
    └─ Takes ~30-45 seconds (does not block dashboard)
    
MotherDuck L2/L3 (Cloud Cache)
    │
    └─ Stores pre-computed KPI tables
    └─ 95%+ cache hit rate on dashboard requests
```

### Implementation Pattern

Pre-computed KPIs materialized in `analytics_cloud` schema with 24-hour refresh cycle. Dashboard queries read from cache in <5ms.

**Key Components:**
- AnalyticsMaterializer: Computes all KPI categories in async task
- MaterializedKPIStore: Manages pre-computed table lifecycle
- AnalyticsBridge: Provides cached KPI access to dashboard

### Scheduling the Async Task

APScheduler-based nightly refresh:
- Schedule: 23:00 UTC daily
- Computation time: ~30-45 seconds
- Non-blocking: Dashboard continues serving users
- Misfire grace: 5 minutes (allows restart tolerance)

### Code Example

```python
from src.socrata_toolkit.dashboards.callbacks.materialized_kpis import MaterializedKPIStore
from src.socrata_toolkit.dashboards.callbacks.analytics_bridge import AnalyticsBridge

# Initialize materialization store
kpi_store = MaterializedKPIStore(motherduck_client)

# Compute and materialize KPIs asynchronously
kpi_results = kpi_store.materialize_kpis(computed_kpis)

# Dashboard uses analytics bridge for cached lookups
bridge = AnalyticsBridge(motherduck_client)
violations = bridge.get_violation_kpis()  # <1ms hit rate
```

**Location:** `src/socrata_toolkit/dashboards/callbacks/`

---

## Materialized View Strategy

### Schema Design

Analytics tables live in `analytics_cloud` schema:

| Table | Purpose | Refresh |
|-------|---------|---------|
| violations_kpis_mat | Violation metrics + borough distribution | Daily |
| ramps_kpis_mat | Ramp completion rates + borough breakdown | Daily |
| permits_kpis_mat | Permit analysis + spatial metrics | Daily |
| quality_kpis_mat | Data quality scores | Daily |
| spatial_kpis_mat | Conflict detection pre-computed results | Daily |

### Pre-Aggregation Strategy

Pre-aggregate by borough and category to eliminate GROUP BY operations at query time.

**Example:** Instead of computing borough-level violations on every query, materialize once nightly:
- Eliminates GROUP BY operations
- Reduces data scanned per query
- Enables O(1) lookups instead of O(n) scans
- Typical improvement: 350ms → <5ms per query

### Incremental Materialization

For large datasets, refresh only changed rows since last materialization:
- Identify changed rows using updated_at timestamp
- Aggregate only delta rows
- Merge into materialized table using UPSERT logic
- 60-70% faster than full recompute

---

## Cache Invalidation Policy

### TTL-Based Invalidation (5 Minutes)

Why 5 minutes?
- Balances freshness vs. cache hit rate
- Most dashboards don't require <5min staleness
- Reduces computation overhead while keeping data fresh
- Typical hit rate: 95%+ across all KPI categories

**Cache Configuration:**
- TTL: 300 seconds (5 minutes)
- Hit rate target: >90%
- Implementation: In-memory cache per service instance

### Event-Driven Invalidation

Manual refresh triggers:
1. User clicks dashboard "Refresh" button → Invalidates specific KPI
2. Dataset update detected via Socrata webhook → Invalidates related KPIs
3. Scheduled materialization completes → Refreshes all KPIs
4. Error in computation → Falls back to previous cached value

### Invalidation Pattern

Located in `src/socrata_toolkit/dashboards/callbacks/analytics_bridge.py`:

```python
def _is_cache_valid(self, key: str) -> bool:
    """Check if cached value is still valid (5-min TTL)."""
    if key not in self._cache:
        return False
    cached_time, _ = self._cache[key]
    return (datetime.now() - cached_time).total_seconds() < 300

def invalidate_cache(self, key: str):
    """Manually invalidate a cache entry."""
    if key in self._cache:
        del self._cache[key]
```

---

## Dashboard Response Optimization

### Real-Time Data Binding Pattern

**Old approach:** Compute KPIs on every dashboard callback  
**New approach:** Bind to pre-computed materialized views

Instead of expensive on-demand computation:
```
fetch data → compute aggregation → serialize → return (500ms)
```

Use cached lookups:
```
query materialized view → return cached result (<50ms)
```

**Result:** 500ms → 50ms for simple KPI displays (10x faster)

### Lazy Loading Strategy

Load KPIs only when needed:
- Initial page load: Return basic KPIs from cache
- User clicks "Show Details": Load complex KPIs asynchronously
- User selects borough filter: Load borough-specific KPIs

Reduces initial dashboard load time and memory footprint.

### Connection Pooling Best Practices

Manage MotherDuck connections in a thread-safe pool:
- Pool size: 5-10 connections
- Reuse ratio: 95%+ (connections reused 50+ times)
- Connection overhead: 120ms → 70ms (40% reduction)
- Prevents connection exhaustion under load

---

## Monitoring & Alerting

### Key Metrics to Track

**1. Cache Hit Rate (Target: >90%)**
- Daily average: 95.3%
- Alert if drops below 85%
- Action: Review data freshness; check materialization completion

**2. Materialization Latency (Target: <45s)**
- Computation time: 30-45 seconds per cycle
- Alert if exceeds 60 seconds
- Action: Optimize KPI computation; check MotherDuck connection

**3. Dashboard P50 Latency (Target: <100ms)**
- Baseline: 45ms (with cache hits)
- Alert if exceeds 150ms
- Action: Check cache status; restart connection pool if needed

**4. Connection Pool Exhaustion (Target: <5% of requests)**
- Alert if >50% of requests hit queue timeout
- Action: Increase pool size or reduce concurrent users

**5. Query Error Rate (Target: <0.5%)**
- Monitor Socrata API availability
- Alert if exceeds 2%
- Action: Check dataset access permissions; review API quota

### Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Cache hit rate | <85% | <75% | Review freshness; check materialization |
| Materialization latency | >40s | >60s | Optimize computation; check connection |
| Dashboard P50 latency | >150ms | >500ms | Check cache status; restart if needed |
| Connection pool exhaustion | >10% | >50% | Increase pool size or reduce users |
| Query error rate | >0.5% | >2% | Check Socrata API; review permissions |

---

## Future Optimization Roadmap

### Phase 4: Predictive Prefetch (Q3 2026)

**Load KPIs before user requests them**

- Prefetch at predictable peak hours (12:00 UTC for violations/permits, 08:00 UTC for ramps)
- Prefetch based on user history (correlate dashboards users view together)
- Reduces perceived latency to <10ms for preloaded KPIs

### Phase 5: Compressed Materialized Views (Q3 2026)

**Reduce storage overhead by 60-70%**

- Store materialized KPIs in Parquet format
- Snappy compression reduces disk I/O
- Minimal latency impact (<1-2ms additional decompression)
- Storage reduction: analytics_cloud schema 850GB → 250-350GB

### Phase 6: Hierarchical Caching (Q4 2026)

**Multi-level cache with automatic spillover**

- L1 (in-memory): 5-min TTL, 99%+ hit rate (hot KPIs)
- L2 (MotherDuck): 1-hour TTL, 85-95% hit rate (warm KPIs)
- L3 (cloud storage): 365-day retention for historical analysis

---

## Implementation Checklist

- [x] Async KPI materialization (deployed 2026-06-10)
- [x] Materialized view layer (deployed 2026-06-10)
- [x] 5-minute cache TTL with 95%+ hit rate (deployed 2026-06-10)
- [x] Connection pooling (40% overhead reduction) (deployed 2026-06-10)
- [x] Dashboard response optimization (deployed 2026-06-10)
- [x] Monitoring and alerting framework (in progress)
- [ ] Predictive prefetch (Phase 4)
- [ ] Compressed materialized views (Phase 5)
- [ ] Hierarchical caching (Phase 6)

---

## Summary

**Optimizations Deployed (Phase 3B):**
1. Async KPI computation (decoupled from dashboard)
2. Materialized views (O(1) lookups)
3. 5-minute cache TTL (95%+ hit rate)
4. Connection pooling (40% overhead reduction)

**Performance Results:**
- Dashboard latency: 500ms → 50ms (**10x faster**)
- Memory usage: 80MB → 35MB per session (**54% reduction**)
- Load test throughput: 185 → 920 req/s (**4.9x improvement**)

**Next Steps:**
- Monitor cache hit rates (alert if <90%)
- Review materialization logs (ensure <45s completion)
- Plan Phase 4 predictive prefetch

---

**See Also:** PERFORMANCE_BENCHMARKS.md — Detailed metrics and load test results
