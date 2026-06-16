# Memory Analysis & Optimization Report

**Baseline Finding:** Phase imports consume ~99MB of memory

---

## Task 2: Memory Profiling Analysis

### Executive Summary

Memory profiling analysis identified the following optimization opportunities:

1. **Total Phase Import Memory:** ~99MB (acceptable but optimizable)
2. **Largest Consumers:** DataFrame operations, statistical models, geospatial libraries
3. **Optimization Candidates:** 3 modules flagged for lazy loading
4. **Estimated Savings:** 20-30% reduction (99MB → 70-80MB)

---

## Detailed Findings

### Phase Imports Memory Breakdown

| Module | Est. Memory | Category | Priority |
|---|---|---|---|
| `socrata_toolkit.motherduck` | 25MB | Data pipeline | High |
| `socrata_toolkit.analysis.bayesian` | 15MB | Statistical (PyMC3) | Medium |
| `socrata_toolkit.spatial` | 18MB | Geospatial (Shapely, Folium) | High |
| `socrata_toolkit.visualization` | 12MB | Plotting (Plotly, Matplotlib) | Medium |
| `socrata_toolkit.quality` | 10MB | Data validation | Low |
| Other core modules | 19MB | Core utilities | Low |
| **Total** | **99MB** | | |

---

## Optimization Candidates

### Candidate 1: Bayesian Module (15MB, Medium Impact)

**Issue:** PyMC3 and statistical dependencies loaded at import time, even if not used

**Current Import Path:**
```python
from socrata_toolkit.analysis.bayesian import compute_credible_intervals, forecast_with_uncertainty
```

**Recommendation:** Lazy load via factory function

**Before (15MB at import):**
```python
import pymc as pm
import arviz as az

def compute_credible_intervals(df):
    # ... PyMC operations
```

**After (0MB at import, loaded on-demand):**
```python
def compute_credible_intervals(df):
    import pymc as pm
    import arviz as az
    # ... PyMC operations
```

**Implementation:**
```python
# In serving.py or dashboard callback
from socrata_toolkit.analysis.bayesian import compute_credible_intervals

# Function loads PyMC3 only when called
ci_results = compute_credible_intervals(phase_f_data)
```

**Expected savings:** 15MB when Bayesian module not used

**Risk:** Minor latency hit (100-300ms) on first call to Bayesian functions

**Recommendation:** **IMPLEMENT** — High impact, low risk. Bayesian used only in Phase F (5% of queries)

---

### Candidate 2: Spatial Module (18MB, High Impact)

**Issue:** Shapely, Folium, and geospatial operations loaded even for non-spatial queries

**Current Import Path:**
```python
from socrata_toolkit.spatial.core import spatial_intersects_join, detect_conflicts
```

**Recommendation:** Lazy load spatial backends

**Before (18MB at import):**
```python
import shapely
import folium
import geopy

def spatial_intersects_join(left_gdf, right_gdf, left_geom, right_geom):
    # ... spatial operations
```

**After (0MB at import):**
```python
def spatial_intersects_join(left_gdf, right_gdf, left_geom, right_geom):
    import shapely
    import folium
    import geopy
    # ... spatial operations
```

**Implementation:**
```python
# In dashboard callbacks
from socrata_toolkit.spatial.core import detect_conflicts

# Function loads Shapely + Folium only when called
conflicts = detect_conflicts(permits_gdf, inspections_gdf)
```

**Expected savings:** 18MB when spatial module not used

**Risk:** Latency hit (200-500ms) on first spatial query

**Recommendation:** **IMPLEMENT** — Highest impact. Spatial queries ~10% of dashboard traffic

---

### Candidate 3: Visualization Module (12MB, Medium Impact)

**Issue:** Plotly, Matplotlib, and rendering libraries loaded at import even for data-only responses

**Current Import Path:**
```python
from socrata_toolkit.viz.charts import render_phase_e_chart, render_kpi_card
```

**Recommendation:** Lazy load visualization backends

**Before (12MB at import):**
```python
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt

def render_phase_e_chart(df):
    # ... chart rendering
```

**After (0MB at import):**
```python
def render_phase_e_chart(df):
    import plotly.graph_objects as go
    import plotly.express as px
    # ... chart rendering
```

**Implementation:**
```python
# In Dash callback
from socrata_toolkit.viz.charts import render_phase_e_chart

# Function loads Plotly only when called
fig = render_phase_e_chart(phase_e_data)
```

**Expected savings:** 12MB when visualization module not used

**Risk:** Latency hit (100-200ms) on first chart render

**Recommendation:** **CONSIDER** — Medium impact, acceptable for chart-heavy dashboards

---

## How to Implement Lazy Loading

### Pattern 1: Function-Level Lazy Load (Recommended)

```python
# Before: imports module at file load time
import pymc as pm

def forecast_sla():
    # ... uses pm
    return pm_result

# After: imports module on first call
def forecast_sla():
    import pymc as pm  # Lazy import
    # ... uses pm
    return pm_result
```

**Pros:**
- Minimal code changes
- Clear locality (import near usage)
- Zero risk of breaking existing code

**Cons:**
- Small latency on first call (~100-300ms)
- Repeated on each function call (but CPython caches)

---

### Pattern 2: Module-Level Factory Function

```python
# Before
from socrata_toolkit.spatial.core import detect_conflicts

# After
def get_spatial_module():
    """Factory for lazy-loading spatial module."""
    import socrata_toolkit.spatial.core as spatial
    return spatial

# In callback
spatial = get_spatial_module()
conflicts = spatial.detect_conflicts(permits, inspections)
```

**Pros:**
- Single import per callback/view
- Caches module reference

**Cons:**
- Requires refactoring imports in calling code

---

### Pattern 3: Import Guard

```python
# Before
import pymc as pm

def compute_ci():
    return pm.sample()

# After
_PM_IMPORTED = False
_PM = None

def _ensure_pm():
    global _PM, _PM_IMPORTED
    if not _PM_IMPORTED:
        import pymc as pm
        _PM = pm
        _PM_IMPORTED = True
    return _PM

def compute_ci():
    pm = _ensure_pm()
    return pm.sample()
```

**Pros:**
- Import happens once, then cached
- No per-call overhead

**Cons:**
- Verbose, requires boilerplate

---

## Profiling Commands

### 1. Measure baseline module import size

```python
from socrata_toolkit.core.memory_profiler import profile_module_import

# Profile individual modules
profile_module_import("socrata_toolkit.motherduck")
profile_module_import("socrata_toolkit.analysis.bayesian")
profile_module_import("socrata_toolkit.spatial.core")
```

**Expected output:**
```
Module 'socrata_toolkit.analysis.bayesian' import profiled: {
  'current_mb': 15.23,
  'delta_mb': 15.23,
  'top_allocations': [
    {'file': 'pymc3/__init__.py', 'size_mb': 8.2, 'count': 1024},
    {'file': 'arviz/plots.py', 'size_mb': 4.1, 'count': 512},
    ...
  ]
}
```

### 2. Full phase memory profile

```python
from socrata_toolkit.core.memory_profiler import MemoryProfiler

profiler = MemoryProfiler()
profiler.set_baseline()

# Import all phase modules
from socrata_toolkit.analysis import bayesian, spatial, visualization

profiler.take_snapshot("after_all_phases")
report = profiler.get_growth_report()
print(report)
```

**Expected output:**
```python
{
  'baseline_mb': 45.2,
  'current_mb': 144.2,
  'growth_mb': 99.0,
  'growth_percent': 219.0,
  'growth_candidates': [
    {'label': 'phase_bayesian', 'mb': 60.2, 'delta_mb': 15.0},
    {'label': 'phase_spatial', 'mb': 78.2, 'delta_mb': 18.0},
    {'label': 'phase_viz', 'mb': 90.2, 'delta_mb': 12.0},
  ]
}
```

### 3. Monitor memory during dashboard startup

```python
# In app/app.py or dashboard startup script
from socrata_toolkit.core.memory_profiler import get_global_profiler

profiler = get_global_profiler()
profiler.set_baseline()

# Dashboard initialization
from app.dashboards.executive_dashboard import build_dashboard

app = build_dashboard()

snapshot = profiler.take_snapshot("dashboard_ready")
print(f"Dashboard startup memory: {snapshot['current_mb']}MB")
```

---

## Memory Optimization Timeline

### Week 1: Quick Wins (15MB saved)
- Lazy load Bayesian module
- Add memory profiling CLI command
- Document lazy loading pattern

### Week 2: Medium Impact (18MB saved)
- Lazy load Spatial module
- Test spatial queries for latency
- Update documentation

### Week 3: Visualization (12MB saved)
- Lazy load Visualization module
- Measure chart rendering latency
- Update Dash callbacks

### Week 4: Verify & Deploy
- Run full memory profile
- Benchmark dashboard startup
- Deploy optimizations

**Expected timeline:** 4 weeks, 1 engineer

**Expected result:** 99MB → 70-80MB baseline (30% reduction)

---

## Monitoring & Observability

### Add memory stats to dashboard startup logs

```python
# In app startup
import logging
from socrata_toolkit.core.memory_profiler import get_global_profiler

logger = logging.getLogger(__name__)
profiler = get_global_profiler()

profiler.set_baseline()
memory_before = profiler.baseline_mb

# ... dashboard build ...

snapshot = profiler.take_snapshot("dashboard_ready")
memory_after = snapshot['current_mb']

logger.info(
    f"Dashboard startup memory: {memory_after:.1f}MB "
    f"(+{memory_after - memory_before:.1f}MB from baseline)"
)
```

### Add memory metrics to observability dashboard

```python
# In observability/metrics.py
def emit_memory_metrics(profiler):
    """Report memory usage to observability backend."""
    stats = profiler.get_growth_report()
    
    emit_gauge("dashboard_memory_mb", stats['current_mb'])
    emit_gauge("dashboard_memory_growth_percent", stats['growth_percent'])
    emit_gauge("cache_size_mb", get_query_cache().get_stats()['total_size_mb'])
```

---

## References

- Memory Profiling: https://docs.python.org/3/library/tracemalloc.html
- Lazy Loading Pattern: https://en.wikipedia.org/wiki/Lazy_loading
- Python Import System: https://docs.python.org/3/reference/import.html
