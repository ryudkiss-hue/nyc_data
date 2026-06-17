# Dash Architecture Deep Dive
## Callback Patterns, Session State, and Performance Optimization

---

## Table of Contents
1. [Callback Execution Model](#callback-execution-model)
2. [Session State Persistence](#session-state-persistence)
3. [Performance Optimization Patterns](#performance-optimization-patterns)
4. [Code Organization & Naming Conventions](#code-organization--naming-conventions)
5. [Multi-User Concurrency](#multi-user-concurrency)
6. [Troubleshooting Guide](#troubleshooting-guide)

---

## Callback Execution Model

### How Dash Callbacks Work (vs Streamlit Reruns)

**Streamlit (Script-Based):**
```
User clicks filter → Full script rerun from top
├─ Initialize data manager
├─ Fetch all datasets (even if not needed)
├─ Re-render all widgets
├─ Re-compute all charts
└─ Send entire page to browser (2-15 seconds)
```

**Dash (Callback-Based):**
```
User clicks filter → Callback function triggered
├─ Identify affected Output components
├─ Load Input values
├─ Run callback function only (2-500ms)
└─ Update only affected DOM elements (network cost minimal)
```

### Callback Dependency Graph

```
Input: "borough-filter" value="BROOKLYN"
  ↓
Callback 1: update_global_filters()
  ├─ Output: "store-global-filters" (Redis sync)
  └─ ~50ms
  
Callback 2: update_ramp_heatmap() [depends on store-global-filters]
  ├─ Fetch data from DuckDB
  ├─ Filter by borough
  ├─ Create figure
  └─ ~200ms
  
Callback 3: update_density_clusters() [depends on store-global-filters]
  ├─ Fetch data from DuckDB
  ├─ Run DBSCAN (spatial)
  ├─ Create figure
  └─ ~300ms

Total: max(50, 200, 300) = 300ms (callbacks run in parallel for same Input)
Streamlit: would be 5000-15000ms (everything sequential)
```

### Multiple Inputs per Callback (Filtering Pattern)

```python
@app.callback(
    Output("viz-ramp-heatmap", "figure"),
    Input("store-global-filters", "data"),      # From Redis sync
    Input("season-filter", "value"),            # User select
    Input("damage-type-filter", "value"),       # User multi-select
    prevent_initial_call=False
)
def update_heatmap(global_filters, season, damage_type):
    """
    Triggered whenever ANY Input changes.
    Dash compares old vs new Input values; only reruns if changed.
    """
    df = dm.fetch_dataset("ramp_locations")
    
    # Apply cascading filters
    borough = global_filters.get("borough", "ALL")
    if borough != "ALL":
        df = df[df["borough"] == borough]
    
    if season != "ALL":
        df = df[df["season"] == season]
    
    if damage_type:
        df = df[df["damage_type"].isin(damage_type)]
    
    return create_heatmap_figure(df)
```

### Pattern Matchers (Flexible Component IDs)

**Use case:** Generate 50 identical charts with different data.

```python
# Layout: Create charts dynamically based on dataset registry
def layout_gis():
    charts = []
    for viz_key in ["ramp_heatmap", "density_clusters", "tsp_routes", ...]:
        charts.append(
            dcc.Graph(id={"type": "viz-chart", "index": viz_key})
        )
    return dmc.Stack(charts)

# Callback: Handle ALL charts with one function
@app.callback(
    Output({"type": "viz-chart", "index": dash.ALL}, "figure"),  # Match pattern
    Input("store-global-filters", "data"),
    Input({"type": "viz-chart", "index": dash.ALL}, "id"),       # Get all IDs
)
def update_all_charts(global_filters, chart_ids):
    """
    Triggered once per filter change.
    Returns list of figures (one per chart ID).
    """
    figures = []
    for chart_id in chart_ids:
        viz_key = chart_id["index"]
        fig = generate_chart(viz_key, global_filters)
        figures.append(fig)
    return figures
```

**Benefits:**
- Single callback handles 50 charts
- No copy-paste callback code
- Easy to add new charts (just add to layout)

---

## Session State Persistence

### Dash Session Model

```
Browser ↔ Dash Server (FastAPI) ↔ Redis (optional) ↔ DuckDB
```

**Three tiers:**

1. **Browser (dcc.Store):** Transient UI state
   ```python
   dcc.Store(id="store-ui-state", storage_type="session")  # Cleared on browser close
   dcc.Store(id="store-persist", storage_type="local")     # Survives restarts
   ```

2. **Server Memory:** Request-scoped (reset per page load)
   ```python
   @app.callback(...)
   def my_callback(input_val):
       # Local variables are request-scoped (not persisted)
       data = expensive_computation()
       return data
   ```

3. **Redis:** Session-scoped (shared across page loads)
   ```python
   redis_store.update_session(session_id, {"borough": "BROOKLYN"})
   # Persists for session TTL (1 hour)
   ```

### Session ID Lifecycle

```
Session Creation:
├─ User opens app → FastAPI middleware generates session_id
├─ Session ID stored in browser cookie (HttpOnly, Secure)
└─ Redis: CREATE session:{session_id} with TTL=3600

During Session:
├─ User makes requests → middleware reads session_id from cookie
├─ Access/update Redis: session:{session_id}
├─ On each access, extend TTL (sliding window)
└─ DuckDB: log analysis results to analysis_history (append-only)

Session Expiration:
├─ Inactivity >1 hour → Redis deletes session:{session_id}
├─ User logs back in → new session_id generated
└─ Previous analysis_history in DuckDB persists (user sees history)
```

### State Sync: Streamlit ↔ Dash

**Scenario:** User sets borough in Streamlit Settings tab, then navigates to Dash GIS Dashboard.

```python
# Streamlit: User changes borough
st.session_state.borough = "BROOKLYN"

# Streamlit: POST to Dash to sync
response = requests.post(
    "http://localhost:8012/api/session/sync",
    json={
        "borough": "BROOKLYN",
        "timestamp": datetime.now().isoformat()
    },
    cookies={"session_id": st.session_state.session_id}
)

# Dash backend: FastAPI endpoint
@server.post("/api/session/sync")
async def sync_session_state(request: Request, body: dict):
    session_id = request.cookies.get("session_id")
    redis_store.update_session(session_id, body)
    return {"status": "synced"}

# Dash frontend: On page load, pull from Redis
@app.callback(
    Output("store-global-filters", "data"),
    Input("url", "pathname"),
    prevent_initial_call=False
)
def load_session_from_redis(pathname):
    session_id = dash.ctx.session.session_id
    filters = redis_store.get_session(session_id)
    return filters
```

### Best Practices: What to Store Where

| State | Where | Why | TTL |
|-------|-------|-----|-----|
| **User ID / Auth** | Redis | Validate on every request | 1 hour |
| **Global filters** (borough, date) | Redis | Shared across Streamlit + Dash | 1 hour |
| **Tab selections** | dcc.Store (local) | UI preference, no compute needed | Session |
| **Chart data** | Callback output (computed) | Always fresh, cached by @memoize | 10-30 min |
| **Analysis history** | DuckDB | Immutable audit trail | Forever |
| **User preferences** | DuckDB + Redis | Display settings, theme | Forever (DB) + 1h (cache) |

---

## Performance Optimization Patterns

### Pattern 1: Memoization with TTL

```python
# Problem: Feature importance ranking is expensive (RandomForest on 100k rows)
# Solution: Cache result for 10 minutes

from functools import lru_cache
import time

def memoize_with_ttl(seconds=600):
    def decorator(func):
        cache = {}
        
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < seconds:
                    return result
            
            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            return result
        
        return wrapper
    return decorator

@app.callback(Output("viz-feature-importance", "figure"), Input("dataset-select", "value"))
@timer_callback
@memoize_with_ttl(seconds=600)  # Cache for 10 minutes
def update_feature_importance(dataset):
    """Expensive: ~2s without cache, ~50ms with cache."""
    df = dm.fetch_dataset(dataset)
    return VisualizationEngine.create_feature_importance(df)
```

### Pattern 2: Lazy Loading (Virtual Scrolling)

```python
# Problem: 50 charts all load at once → 20s initial render
# Solution: Load visible charts only, render others on scroll

from dash import callback, Input, Output, State

@app.callback(
    Output("chart-container", "children"),
    Input("scroll-position", "value"),  # Track scroll position
    State("all-chart-ids", "data"),      # List of all 50 charts
)
def lazy_load_charts(scroll_pos, all_chart_ids):
    """Only render 5-10 visible charts at a time."""
    viewport_height = 800  # pixels
    chart_height = 400
    charts_per_screen = viewport_height // chart_height
    
    # Calculate which charts are visible
    first_visible = int(scroll_pos / chart_height)
    last_visible = first_visible + charts_per_screen + 2  # Buffer
    
    visible_chart_ids = all_chart_ids[first_visible:last_visible]
    
    # Render only visible charts
    charts = [
        dcc.Graph(id={"type": "viz-chart", "index": cid})
        for cid in visible_chart_ids
    ]
    return charts
```

### Pattern 3: Pre-Computed Aggregations

```python
# Problem: Computing SLA freshness matrix from 37 datasets takes 5 seconds
# Solution: Pre-compute nightly, cache result

# app/services/scheduled_tasks.py
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('cron', hour=2, minute=0)  # 2 AM daily
def precompute_sla_matrix():
    """Run expensive computations off-peak (2 AM)."""
    from app.services.quality_service import compute_sla_matrix
    
    sla_matrix = compute_sla_matrix(dm)
    
    # Cache result in Redis
    redis_store.client.setex(
        "precomputed:sla_matrix",
        ttl=86400,  # 24 hours
        value=pickle.dumps(sla_matrix)
    )
    logger.info("SLA matrix precomputed")

# app/callbacks/analytics_stats.py
@app.callback(Output("viz-sla-freshness", "figure"), Input("url", "pathname"))
@timer_callback
def update_sla_freshness(pathname):
    """Load precomputed result from Redis (~50ms)."""
    cached = redis_store.client.get("precomputed:sla_matrix")
    
    if cached:
        sla_matrix = pickle.loads(cached)
    else:
        # Fallback: compute on demand (slower but works)
        sla_matrix = compute_sla_matrix(dm)
    
    return create_sla_figure(sla_matrix)
```

### Pattern 4: Debouncing (Avoid Callback Storms)

```python
# Problem: User typing in search box triggers callback 100x/sec
# Solution: Debounce with dcc.Interval

@app.callback(
    Output("search-results", "children"),
    Input("search-debounce", "n_intervals"),  # Debounce interval
    State("search-input", "value"),
)
def debounced_search(n_intervals, search_query):
    if not search_query:
        return dmc.Text("Enter search query")
    
    # Only runs every 500ms even if user is typing rapidly
    results = dm.search_datasets(search_query)
    return render_results(results)

# HTML side
dcc.Interval(id="search-debounce", interval=500, disabled=True),
dmc.Input(
    id="search-input",
    placeholder="Search...",
    # Trigger interval when value changes
    n_submit=0
)
```

### Pattern 5: Async Callbacks for Long-Running Tasks

```python
# Problem: Exporting 100k rows to PDF takes 30 seconds
# Solution: Run async, show progress bar

from dash.long_callback import DiskcacheLongCallbackManager

long_callback_manager = DiskcacheLongCallbackManager(cache)

@app.long_callback(
    Output("export-progress", "children"),
    Input("btn-export-pdf", "n_clicks"),
    running=[
        (Output("btn-export-pdf", "disabled"), True, False),
        (Output("export-progress", "children"), 
         dmc.Spinner(children=dmc.Text("Generating PDF...")), 
         dmc.Text("Ready")),
    ],
    manager=long_callback_manager,
)
def export_pdf_async(n_clicks):
    """Run in background, update progress."""
    df = dm.fetch_dataset("violations")
    pdf_bytes = generate_pdf_report(df)
    
    return dcc.Download(base64=pdf_bytes, filename="report.pdf")
```

---

## Code Organization & Naming Conventions

### Directory Structure

```
app/
├── callbacks/
│   ├── __init__.py                    # export register_all_callbacks()
│   ├── base.py                        # @timer_callback, @memoize
│   ├── _registry.py                   # Callback metadata for debugging
│   ├── gis_spatial.py                 # GIS callbacks
│   ├── gis_3d.py
│   ├── analytics_stats.py
│   ├── contracts_labor.py
│   ├── navigation.py
│   ├── export.py
│   └── cache.py                       # Cache invalidation helpers
│
├── services/
│   ├── gis_service.py                 # Spatial queries, DBSCAN, TSP
│   ├── analytics_service.py           # Quality audits, statistics
│   ├── labor_service.py               # Contractor performance
│   ├── cache_service.py               # DuckDB + diskcache integration
│   ├── session_service.py             # Redis session management
│   └── scheduled_tasks.py             # APScheduler tasks
│
├── middleware/
│   ├── redis_session.py               # RedisSessionStore class
│   ├── session_sync.py                # Streamlit ↔ Dash bridge
│   └── timing.py                      # Request timing instrumentation
│
├── cache/
│   ├── callback_cache.py              # Callback-level LRU cache
│   └── data_cache.py                  # DataManager integration
│
├── dash_app.py                        # Main Dash app
├── dash_layouts.py                    # Shared layouts (header, sidebar)
├── dash_layouts_gis.py                # GIS-specific layout
├── dash_layouts_stats.py
├── dash_layouts_labor.py
└── main.py                            # Streamlit entry
```

### Naming Conventions

**Component IDs** (use pattern matching):

```python
# Format: {type}-{view}-{chart-name}
# Examples:
"viz-gis-ramp-heatmap"                       # Chart component
"store-gis-spatial-filters"                  # Data store
"btn-gis-draw-polygon"                       # Button
"toggle-gis-3d-buildings"                    # Toggle switch
"input-gis-search"                           # Input field

# Pattern matching:
{"type": "viz-chart", "index": "ramp-heatmap"}      # Flexible
{"type": "filter-select", "index": "season"}
```

**Callback Functions:**

```python
# Format: {action}_{component}_{subject}
# Examples:
update_ramp_heatmap()          # Update a single chart
update_all_gis_charts()         # Update multiple charts
generate_feature_importance()   # Create chart figure
sync_filters_to_redis()         # State management
debounce_search_query()         # Debouncing
```

**Service Functions:**

```python
# Format: {operation}_{entity}_{detail}
# Examples:
get_spatial_clusters()          # Query spatial data
compute_sla_matrix()            # Expensive computation
fetch_contractor_performance()  # Data retrieval
cache_statistical_moments()     # Caching operation
```

---

## Multi-User Concurrency

### Session Isolation Guarantees

**Scenario:** Two analysts using same dashboard simultaneously.

```
Analyst A (session_id: abc123)          Analyst B (session_id: def456)
│                                       │
├─ redis:session:abc123                 ├─ redis:session:def456
│  ├─ borough: "MANHATTAN"              │  ├─ borough: "BROOKLYN"
│  └─ date_start: "2026-01-01"          │  └─ date_start: "2026-02-01"
│                                       │
├─ dcc.Store (browser)                  ├─ dcc.Store (browser)
│  └─ Tab selection: "Insights"         │  └─ Tab selection: "Visual"
│                                       │
└─ DuckDB (shared, read-only)           └─ DuckDB (shared, read-only)
   └─ No conflicts: reads only             └─ No conflicts: reads only
```

**Why no conflicts?**

1. **Redis sessions isolated:** Different session_ids = different data
2. **DuckDB read-only:** No writes, so no race conditions
3. **Browser stores isolated:** Different session IDs = different dcc.Store data
4. **Analysis history append-only:** New records never overwrite

### Handling Concurrent Updates

```python
@app.callback(
    Output("store-filters", "data", allow_duplicate=True),
    Input("borough-filter", "value"),
    State("store-filters", "data"),              # Current state
    prevent_initial_call=True
)
def update_filters_atomic(selected_borough, current_filters):
    """
    Atomic update: Read current state, modify, write back.
    Dash prevents callback re-entrancy (no nested invocations).
    """
    if current_filters is None:
        current_filters = {}
    
    updated = current_filters.copy()
    updated["borough"] = selected_borough
    
    # Redis update is atomic (single HSET command)
    redis_store.update_session(dash.ctx.session.session_id, updated)
    
    return updated
```

### Load Testing (100 Concurrent Users)

```python
# tests/test_concurrent_load.py
from locust import HttpUser, task, between

class DashboardUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def filter_borough(self):
        self.client.get("/geo?borough=BROOKLYN")
    
    @task(2)
    def toggle_3d(self):
        self.client.get("/geo?toggle=3d_buildings")
    
    @task(1)
    def export_data(self):
        self.client.get("/api/export/csv?dataset=violations")

# Run: locust -f tests/test_concurrent_load.py -u 100 -r 10 --run-time 5m
# Expected: <500ms P95 latency, >95% success rate
```

---

## Troubleshooting Guide

### Issue 1: Callback Timeout (>10 seconds)

**Symptom:** "Callback not updating" + browser logs show pending request.

**Root Cause:** Callback function is expensive (expensive computation, slow network).

**Fix:**

```python
# Before (slow)
@app.callback(Output("viz-chart", "figure"), Input("filter", "value"))
def slow_callback(filter_val):
    df = dm.fetch_dataset("violations")  # 2 seconds
    df = expensive_aggregation(df)       # 5 seconds
    return create_figure(df)             # Total: 7 seconds

# After (optimized)
@app.callback(Output("viz-chart", "figure"), Input("filter", "value"))
@timer_callback
@memoize_with_ttl(seconds=600)  # Cache for 10 min
def fast_callback(filter_val):
    df = dm.fetch_dataset("violations")  # 2s (cached after first run)
    # Pre-computed aggregation (from nightly job)
    cached_agg = redis_store.client.get(f"agg:{filter_val}")
    if cached_agg:
        df_agg = pickle.loads(cached_agg)  # 50ms
    else:
        df_agg = expensive_aggregation(df)  # 5s (fallback)
    return create_figure(df_agg)  # Total: 50-100ms (cached)
```

### Issue 2: Redis Connection Exhaustion

**Symptom:** Callbacks fail with "Connection pool exhausted" error.

**Root Cause:** Too many concurrent connections to Redis.

**Fix:**

```python
# app/middleware/redis_session.py
class RedisSessionStore:
    def __init__(self):
        self.client = redis.Redis(
            connection_pool=redis.ConnectionPool(
                max_connections=20,      # Limit concurrent connections
                retry_on_timeout=True,
            )
        )
```

### Issue 3: Session Data Inconsistency

**Symptom:** User's filter selection doesn't persist across page refresh.

**Root Cause:** dcc.Store (browser) lost due to browser cache clearing, Redis session expired, or wrong TTL.

**Fix:**

```python
# Explicitly set storage_type
dcc.Store(id="store-filters", storage_type="local")  # Survives refresh + restart

# Or extend Redis TTL on every access
@app.callback(...)
def update_filters(new_val, old_filters):
    redis_store.update_session(session_id, old_filters)
    redis_store.client.expire(f"session:{session_id}", 3600)  # Reset TTL
    return new_filters
```

### Issue 4: Memory Bloat (50 Charts = 2GB RAM)

**Symptom:** App crashes with "Out of Memory" after loading dashboard.

**Root Cause:** All 50 charts rendered + data cached in memory.

**Fix:**

```python
# Implement lazy loading (only render visible charts)
@app.callback(
    Output("chart-container", "children"),
    Input("scroll-position", "value"),
)
def lazy_load_visible_charts(scroll_pos):
    """Only render 5-10 charts in viewport."""
    # (see Pattern 2 above)
    pass

# Or limit chart data size
@app.callback(Output("viz-chart", "figure"), Input("dataset-select", "value"))
def create_chart_with_sampling(dataset):
    df = dm.fetch_dataset(dataset, limit=10000)  # Sample instead of full fetch
    return create_figure(df)
```

### Issue 5: Cross-Site Request Forgery (CSRF)

**Symptom:** Callbacks fail with 403 Forbidden when Streamlit calls Dash API.

**Root Cause:** Missing CSRF token in cross-origin requests.

**Fix:**

```python
# app/dash_app.py
from fastapi.middleware.csrf import CSRFMiddleware

server.add_middleware(
    CSRFMiddleware,
    secret_key="your-secret-key",
    cookie_secure=True,
    cookie_httponly=True,
)

# In Streamlit, send CSRF token
import requests

csrf_token = requests.get("http://localhost:8012/api/csrf").json()["token"]
requests.post(
    "http://localhost:8012/api/session/sync",
    json={"borough": "BROOKLYN"},
    headers={"X-CSRF-Token": csrf_token}
)
```

---

## Performance Metrics Dashboard

Track these metrics in production:

```python
# app/middleware/timing.py
import time
from prometheus_client import Counter, Histogram

callback_duration = Histogram(
    "dash_callback_duration_seconds",
    "Callback execution time",
    ["callback_name"]
)

callback_errors = Counter(
    "dash_callback_errors_total",
    "Callback execution errors",
    ["callback_name"]
)

@app.callback(...)
def tracked_callback(input_val):
    with callback_duration.labels(callback_name="update_ramp_heatmap").time():
        try:
            # ... callback code
            pass
        except Exception as e:
            callback_errors.labels(callback_name="update_ramp_heatmap").inc()
            raise
```

**Prometheus Queries:**
```
# P95 latency
histogram_quantile(0.95, dash_callback_duration_seconds)

# Error rate
rate(dash_callback_errors_total[5m])

# Cache hit ratio
redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)
```

---

## Summary: Callback Design Principles

1. **Keep callbacks pure:** No side effects beyond dcc.Store updates
2. **Cache expensive ops:** Use @memoize_with_ttl for >500ms computations
3. **Isolate state:** Each callback manages its own Input/Output/State
4. **Test independently:** Unit test callbacks in isolation
5. **Monitor latency:** @timer_callback on every callback
6. **Distribute load:** Pre-compute nightly, fetch cached results during day
7. **Graceful degradation:** Always have fallback (compute on-demand if cache miss)


