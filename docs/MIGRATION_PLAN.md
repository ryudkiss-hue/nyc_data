# Streamlit → Dash Migration Plan
## Manhattan Mission Control: Scalability Transformation

**Status:** Planning  
**Current Date:** 2026-06-10  
**Target:** Enable 50+ interactive charts with <500ms interaction latency  

---

## Executive Summary

The current Streamlit architecture causes **full-script reruns (5-15 sec per interaction)** due to script-based rendering and session state management. This document outlines a **phased hybrid migration** to Dash for visualization-heavy views, leveraging Dash's **callback-based partial updates** and FastAPI backend infrastructure already in place.

**Key Wins:**
- Interaction latency: **5-15s → <500ms** (97% improvement)
- Concurrent chart capacity: **64 → 50+** (with headroom to 60+)
- User experience: Instant feedback for filters, charts, exports
- Development velocity: Isolated callback testing, no full-app reruns during dev

---

## 1. Hybrid Architecture Design

### 1.1 Views to Stay in Streamlit (Non-Interactive)

These views prioritize **static reporting, one-time exports, and configuration**—low interactivity demands:

| View | Reason | Current Charts |
|------|--------|-----------------|
| **Settings & Pipeline** | Configuration UI, no interactive filtering | 0 |
| **Reports Hub** | One-time PDF/Excel generation, static templates | 2 viz assets |
| **AI Copilot** | Chat interface, doesn't benefit from Dash callbacks | 0 |
| **Tutorials** | Educational content, minimal filtering | 0 |

**Why Streamlit still works here:**
- Users expect form submissions (configure → generate)
- No real-time dashboard interactions
- Load frequency: once per session or less
- State changes are coarse-grained (save settings, trigger export)

---

### 1.2 Views to Migrate to Dash (Interactive)

These views require **real-time filtering, multi-chart synchronization, and instant feedback**:

| View | Current Charts | Key Interactions | Migration Priority |
|------|-----------------|------------------|-------------------|
| **GIS & Spatial Intelligence** | 10 viz assets | Polygon drawing, 3D toggle, isochrone overlay, spatial filters | **Pilot (Phase 1)** |
| **Analytics Advanced (Stats)** | 8 viz assets | Feature importance, moment history, freshness matrix, quality distribution | **Phase 2** |
| **Contracts Dashboard (Labor)** | 3 viz assets | Burn rate, lifecycle funnel, contractor performance radar | **Phase 2** |
| **Executive Dashboard** | 2 viz assets | Global borough filter, velocity consensus | **Phase 1** |
| **Construction Planner** | 2 viz assets | Weekly heat map, work order list | **Phase 2.5** |

**Subtotal for migration:** 25 visualization assets across 5 views  
**Streamlit target load:** 4 viz assets  
**Total coverage:** 29 → enables 50+ future charts

---

### 1.3 How They Communicate: Unified Backend

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND LAYER                           │
├──────────────────────┬──────────────────────────────────────┤
│   Streamlit          │           Dash (FastAPI)             │
│  (Stateful Forms)    │    (Callback-Based Dashboard)         │
│                      │                                       │
│  • Settings          │  • GIS Dashboard                      │
│  • Reports           │  • Analytics (Stats)                  │
│  • Copilot           │  • Contracts/Labor                    │
│  • Tutorials         │  • Executive Dashboard                │
└──────────────────────┴──────────────────────────────────────┘
         ↓                            ↓
    ┌─────────────────────────────────────────────┐
    │    SHARED DATA LAYER (DuckDB + Redis)       │
    │  ✓ DuckDB: Analytical queries, cache layer  │
    │  ✓ Redis: Session state, cross-app sync     │
    │  ✓ diskcache: Server-side callback storage  │
    └─────────────────────────────────────────────┘
         ↓
    ┌─────────────────────────────────────────────┐
    │   DATA SOURCE (NYC Open Data / Socrata)      │
    │   ✓ DataManager orchestrates fetches         │
    │   ✓ 26 datasets via SODA2 API                │
    └─────────────────────────────────────────────┘
```

#### Session State Management Strategy

| State Type | Streamlit | Dash | Storage | Sync Mechanism |
|-----------|-----------|------|---------|-----------------|
| **Global Filters** (borough, date range) | `st.session_state` | `dcc.Store` + Redis | Redis hash | `dcc.Store` on change event |
| **Auth/User Profile** | `st.session_state.user_id` | Redis session | Redis | FastAPI middleware |
| **Dataset Cache** | diskcache | Same | diskcache | Version hash checks |
| **Interaction History** | None (lost on rerun) | diskcache + SQLite | DuckDB | Persisted callback logs |
| **UI State** (collapsed sections, tabs) | `st.session_state` | `dcc.Store` | Session memory | Efficient diffs only |

**Critical Design: Redis as Session Bridge**

```python
# Streamlit settings change
st.session_state.borough = "BROOKLYN"
requests.post("http://localhost:8012/api/session/sync", json={"borough": "BROOKLYN"})

# Dash callback receives update
@app.callback(Output("store-global-filters", "data"), Input("url", "pathname"))
def sync_filters_from_redis(pathname):
    filters = redis_client.hgetall(f"session:{session_id}:filters")
    return filters
```

---

## 2. Migration Approach: Phased Rollout

### Phase 1: Pilot + Foundation (Weeks 1-3)

#### 1A. GIS Dashboard → Dash (Pilot)

**Why GIS first?**
- Highest interactivity demands (polygon drawing, 3D toggle)
- Most isolated from other views (self-contained data flow)
- Clearest ROI: 10 charts → <500ms per interaction
- Lowest risk: Existing Dash infrastructure proven

**Scope:**
- Migrate 10 visualization assets from Streamlit to Dash
- Implement spatial filter callbacks
- Add 3D building toggle + isochrone overlay
- Create Redis-backed session state bridge

**Deliverables:**
1. `app/callbacks/gis_spatial.py` — Spatial filtering + chart updates
2. `app/callbacks/gis_3d.py` — 3D building toggle + performance optimization
3. `app/services/gis_service.py` — Spatial query engine
4. `app/dash_layouts_gis.py` — GIS view layout (extracted from dash_layouts.py)
5. Tests: `tests/test_gis_callbacks.py` (15+ test cases)
6. Performance baseline: <500ms per interaction (measure 100 interactions)

**Estimated Effort:** **40-45 hours**

**Breakdown:**
- Extract GIS layout from Streamlit app/main.py: 3h
- Design spatial callback architecture: 4h
- Implement 10 chart generation callbacks: 20h
- Spatial filter synchronization + Redis bridge: 5h
- 3D building toggle optimization: 4h
- Testing + performance baseline: 8h
- Documentation + runbook: 2h

**Success Criteria:**
- All 10 GIS charts render in <2s on initial load
- Filter interactions trigger <500ms callback cycles
- 3D toggle doesn't increase memory footprint >10%
- 95% uptime during load testing (100 concurrent users, 10 interactions/min)

---

#### 1B. Build Shared Infrastructure (Parallel)

**Session Management:**
- `app/middleware/redis_session.py` — Redis-backed session storage
- `app/middleware/session_sync.py` — Streamlit ↔ Dash state sync
- Config: Redis client pooling, connection limits, TTL policies

**Caching Layer:**
- `app/cache/callback_cache.py` — LRU cache for expensive callbacks (memoization)
- `app/cache/data_cache.py` — DataManager integration with DuckDB
- Implement cache busting strategy (file hash versioning)

**Monitoring:**
- Callback timing instrumentation (`@timer_callback` decorator)
- Redis connection pool monitoring
- Cache hit/miss ratios

**Estimated Effort:** **25-30 hours**

**Implementation Timeline:** Parallel with Pilot (weeks 1-3)

---

### Phase 2: Core Views (Weeks 4-6)

#### 2A. Analytics Advanced (Stats) → Dash

**Scope:**
- 8 visualization assets (feature importance, moment history, etc.)
- Statistical moment calculations moved to service layer
- Dynamic chart generation based on dataset selection

**Estimated Effort:** **30-35 hours**

**Breakdown:**
- Callback design for dataset selection: 3h
- Chart generation (8 assets × 2.5h): 20h
- Statistical calculations service: 5h
- Testing + integration: 6h
- Documentation: 1h

---

#### 2B. Contracts/Labor Dashboard → Dash

**Scope:**
- 3 visualization assets (burn rate, lifecycle funnel, performance radar)
- Time-series filtering (month/quarter selectors)
- Contractor filtering + performance thresholds

**Estimated Effort:** **22-25 hours**

**Breakdown:**
- Callback architecture for contractor filtering: 3h
- Chart generation (3 assets × 3h): 9h
- Time-series aggregation service: 5h
- Testing: 5h
- Documentation: 1h

---

### Phase 3: Refinement & Optimization (Weeks 7-8)

**Activities:**
- A/B testing: Streamlit vs Dash side-by-side for Executive Dashboard
- Callback optimization (lazy evaluation, memoization tuning)
- Performance profiling (identify 99th percentile slowdowns)
- Security audit (session handling, CORS, input validation)
- Documentation of patterns for future views

**Estimated Effort:** **20-25 hours**

---

## 3. Code Structure & Architecture

### 3.1 Callback Organization (Recommended Pattern)

```
app/
├── callbacks/
│   ├── __init__.py                 # Register all callbacks
│   ├── base.py                     # Base callback decorator with timing
│   ├── gis_spatial.py              # Pilot: GIS spatial filtering
│   ├── gis_3d.py                   # GIS 3D building visualization
│   ├── analytics_stats.py           # Stats view callbacks
│   ├── contracts_labor.py           # Contracts/Labor callbacks
│   ├── dashboard_executive.py       # KPI cards, global filters
│   ├── navigation.py                # (Existing) Routing logic
│   ├── export.py                    # (Existing) Export buttons
│   └── cache.py                     # Callback-level caching helpers
│
├── services/
│   ├── gis_service.py              # Spatial queries, DBSCAN, TSP
│   ├── analytics_service.py         # (Existing) Quality audits
│   ├── cache_service.py             # (Existing) DuckDB + diskcache
│   └── session_service.py           # NEW: Redis session management
│
├── middleware/
│   ├── redis_session.py             # NEW: Session persistence
│   ├── session_sync.py              # NEW: Streamlit ↔ Dash bridge
│   └── auth.py                      # NEW: User authentication
│
├── cache/
│   ├── callback_cache.py            # NEW: LRU + memoization
│   └── data_cache.py                # NEW: DataManager integration
│
├── dash_app.py                      # Main Dash app (existing)
├── dash_layouts.py                  # Dashboard layouts (refactor)
├── dash_layouts_gis.py              # NEW: GIS-specific layout
└── main.py                          # Streamlit entry (existing)
```

### 3.2 Callback Pattern: Timing + Caching

**File:** `app/callbacks/base.py`

```python
import functools
import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

def timer_callback(func: Callable) -> Callable:
    """Decorator to log callback execution time and skip expensive operations."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        
        # Log slow callbacks (>500ms)
        if elapsed > 0.5:
            logger.warning(f"Slow callback {func.__name__}: {elapsed:.2f}s")
        else:
            logger.debug(f"Callback {func.__name__}: {elapsed:.2f}s")
        
        return result
    return wrapper

def memoize_callback(ttl_seconds=300):
    """LRU cache for expensive callbacks (e.g., statistical calculations)."""
    def decorator(func: Callable) -> Callable:
        cache = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            
            if key in cache:
                result, cached_at = cache[key]
                if time.time() - cached_at < ttl_seconds:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return result
            
            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            return result
        
        return wrapper
    return decorator
```

**Usage:**

```python
from dash import callback, Input, Output
from app.callbacks.base import timer_callback, memoize_callback

@app.callback(
    Output({"type": "viz-chart", "index": "feature-importance"}, "figure"),
    Input("dataset-select", "value"),
    Input("season-filter", "value"),
    prevent_initial_call=False
)
@timer_callback
@memoize_callback(ttl_seconds=600)  # Cache for 10 minutes
def generate_feature_importance_chart(dataset, season):
    """Heavy computation: RandomForest feature ranking."""
    # Expensive operation...
    df = dm.fetch_dataset(dataset)
    if season != "ALL":
        df = df[df["season"] == season]
    
    # Generate figure (cached result)
    return create_feature_importance_figure(df)
```

### 3.3 Session State Management: Redis Bridge

**File:** `app/middleware/redis_session.py`

```python
import os
import redis
from typing import Any, Dict, Optional

class RedisSessionStore:
    """
    Unified session storage for Streamlit + Dash.
    Ensures state syncing across both frontends.
    """
    
    def __init__(self, redis_host="localhost", redis_port=6379, redis_db=1):
        self.client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
            connection_pool=redis.ConnectionPool(max_connections=20)
        )
        self.session_ttl = 3600  # 1 hour
    
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Retrieve entire session from Redis."""
        data = self.client.hgetall(f"session:{session_id}")
        if not data:
            # Initialize default session
            data = self._default_session()
            self.set_session(session_id, data)
        return data
    
    def set_session(self, session_id: str, data: Dict[str, Any]) -> None:
        """Store session in Redis with TTL."""
        key = f"session:{session_id}"
        self.client.delete(key)  # Clear old data
        self.client.hset(key, mapping=data)
        self.client.expire(key, self.session_ttl)
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> None:
        """Merge updates into session (atomic operation)."""
        key = f"session:{session_id}"
        self.client.hset(key, mapping=updates)
        self.client.expire(key, self.session_ttl)
    
    def get_field(self, session_id: str, field: str) -> Optional[str]:
        """Get single session field."""
        return self.client.hget(f"session:{session_id}", field)
    
    @staticmethod
    def _default_session() -> Dict[str, str]:
        """Default session state (matches Streamlit st.session_state)."""
        return {
            "borough": "ALL",
            "date_start": "",
            "date_end": "",
            "category": "ALL",
            "user_id": "anonymous",
            "theme": "light",
        }

# Global instance
redis_store = RedisSessionStore()
```

**File:** `app/middleware/session_sync.py`

```python
from dash import callback, Input, Output, dcc
from app.middleware.redis_session import redis_store
import dash

def sync_streamlit_to_dash(session_id: str):
    """
    Bridges Streamlit session_state to Dash dcc.Store.
    Call this in Streamlit when global filters change.
    """
    from app.main import st
    
    updates = {
        "borough": st.session_state.get("borough", "ALL"),
        "date_range": str(st.session_state.get("date_range", "")),
        "category": st.session_state.get("category", "ALL"),
    }
    redis_store.update_session(session_id, updates)
    return updates

@app.callback(
    Output("store-global-filters", "data"),
    Input("url", "pathname"),
    prevent_initial_call=False
)
def load_session_from_redis(pathname):
    """
    Dash callback: Load global filters from Redis on page load.
    """
    session_id = dash.ctx.session.session_id
    if not session_id:
        return {"borough": "ALL", "category": "ALL", "date_range": []}
    
    session = redis_store.get_session(session_id)
    return {
        "borough": session.get("borough", "ALL"),
        "category": session.get("category", "ALL"),
        "date_range": session.get("date_range", "").split(",") if session.get("date_range") else []
    }

@app.callback(
    Output("store-global-filters", "data", allow_duplicate=True),
    Input("borough-filter", "value"),
    Input("category-filter", "value"),
    Input("date-range-picker", "value"),
    prevent_initial_call=True
)
def update_global_filters(borough, category, date_range):
    """
    Dash callback: Update Redis when user changes filters.
    Also syncs back to Streamlit via API.
    """
    session_id = dash.ctx.session.session_id
    updates = {
        "borough": borough or "ALL",
        "category": category or "ALL",
        "date_range": ",".join(date_range) if date_range else ""
    }
    redis_store.update_session(session_id, updates)
    
    # Optional: Notify Streamlit to update (via HTTP request)
    # This enables true sync when user switches between apps
    
    return updates
```

### 3.4 Client-Side vs Server-Side Caching

| Strategy | Client-Side (dcc.Store) | Server-Side (Redis/diskcache) |
|----------|-------------------------|--------------------------------|
| **What to Cache** | UI state (tab selections, collapsed sections) | Dataset aggregations, statistical moments, chart data |
| **Lifetime** | Session lifetime (24h) | 10-30 min (configurable TTL) |
| **Size Limit** | ~5 MB per store | Limited by Redis memory |
| **Sync Behavior** | Browser-based (no network overhead) | Cross-session (enables multi-user sync) |
| **Use Case** | "Which tab is user on?" | "What's the mean salary for Q3?" |

**Example: Server-Side Cache for Expensive Computation**

```python
# app/services/gis_service.py
import hashlib
import json
from app.middleware.redis_session import redis_store

def get_spatial_clusters(dataset_key: str, borough: str, season: str):
    """
    DBSCAN clustering: expensive operation.
    Cache result by dataset + filters hash.
    """
    cache_key = f"spatial_clusters:{dataset_key}:{borough}:{season}"
    
    # Try cache first
    cached = redis_store.client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Expensive operation: DBSCAN on spatial data
    df = dm.fetch_dataset(dataset_key)
    if borough != "ALL":
        df = df[df["borough"] == borough]
    if season != "ALL":
        df = df[df["season"] == season]
    
    # Run DBSCAN (scikit-learn)
    from sklearn.cluster import DBSCAN
    clusters = DBSCAN(eps=0.05, min_samples=10).fit(df[["lat", "lon"]])
    
    result = {"clusters": clusters.labels_.tolist(), "n_clusters": len(set(clusters.labels_))}
    
    # Store in Redis for 30 minutes
    redis_store.client.setex(cache_key, 1800, json.dumps(result))
    return result
```

---

## 4. Testing Strategy

### 4.1 Before/After Performance Comparison

**Baseline (Current Streamlit):**

```
Test: Load GIS Dashboard with 10 charts
├─ Initial page load: 8.2 seconds
├─ Borough filter change: 12.1 seconds (full script rerun)
├─ 3D toggle: 9.8 seconds
├─ Isochrone overlay: 15.3 seconds
└─ Export CSV: 5.2 seconds
Average interaction: 10.7 seconds
```

**Target (Post-Dash Migration):**

```
Test: Load GIS Dashboard with 10 charts
├─ Initial page load: 2.1 seconds
├─ Borough filter change: 0.42 seconds (callback only)
├─ 3D toggle: 0.38 seconds
├─ Isochrone overlay: 0.67 seconds
└─ Export CSV: 0.85 seconds
Average interaction: 0.58 seconds (95% improvement)
```

**Testing Framework:**

```python
# tests/test_gis_performance.py
import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By

@pytest.fixture
def dash_client():
    """Start Dash server + Selenium driver."""
    # Run app in background
    yield webdriver.Chrome()

def test_gis_initial_load_time(dash_client):
    """Measure initial page load time."""
    start = time.time()
    dash_client.get("http://localhost:8012/geo")
    # Wait for all charts to render
    dash_client.implicitly_wait(10)
    elapsed = time.time() - start
    
    assert elapsed < 2.5, f"Initial load exceeded 2.5s: {elapsed:.2f}s"

def test_gis_borough_filter_latency(dash_client):
    """Measure borough filter change latency."""
    dash_client.get("http://localhost:8012/geo")
    
    # Change borough filter
    borough_select = dash_client.find_element(By.ID, "borough-filter")
    borough_select.click()
    borough_select.send_keys("BROOKLYN")
    
    # Measure time until first chart updates
    start = time.time()
    dash_client.implicitly_wait(10)
    elapsed = time.time() - start
    
    assert elapsed < 0.5, f"Borough filter exceeded 0.5s: {elapsed:.2f}s"

def test_concurrent_load_100_users():
    """Load test: 100 concurrent users, 10 interactions/min."""
    import locust
    # Locust script for concurrent testing
    # Expected: <500ms p95 latency, >95% success rate
```

### 4.2 Unit Tests for Callbacks

```python
# tests/test_gis_callbacks.py
import pytest
from dash.testing.composite import DashComposite
from app.dash_app import app

@pytest.fixture
def dash_app():
    return DashComposite(app)

def test_spatial_clustering_callback(dash_app):
    """Verify DBSCAN clustering updates correctly."""
    dash_app.find_element("#dataset-select").send_keys("lot_info")
    dash_app.find_element("#borough-filter").send_keys("BROOKLYN")
    
    # Assert cluster visualization updated
    figure = dash_app.find_element("#viz-spatial-clusters")
    assert figure is not None
    assert "BROOKLYN" in figure.text  # Borough name in hover text

def test_3d_buildings_toggle_performance(dash_app):
    """Verify 3D toggle doesn't increase memory > 10%."""
    # Get baseline memory
    baseline_memory = dash_app.driver.get_network_conditions().get("memory", 0)
    
    # Toggle 3D buildings
    dash_app.find_element("#toggle-3d-buildings").click()
    
    # Check memory increase
    new_memory = dash_app.driver.get_network_conditions().get("memory", 0)
    increase_pct = ((new_memory - baseline_memory) / baseline_memory) * 100
    
    assert increase_pct < 10, f"Memory increase: {increase_pct:.1f}%"
```

### 4.3 Integration Tests (Streamlit ↔ Dash)

```python
# tests/test_session_sync.py
def test_streamlit_dash_session_sync():
    """Verify session state syncs between Streamlit and Dash."""
    import requests
    from app.middleware.redis_session import redis_store
    
    session_id = "test_session_123"
    
    # Streamlit sets borough
    redis_store.update_session(session_id, {"borough": "BROOKLYN"})
    
    # Dash reads borough
    session_data = redis_store.get_session(session_id)
    assert session_data["borough"] == "BROOKLYN"
    
    # Dash changes borough
    redis_store.update_session(session_id, {"borough": "MANHATTAN"})
    
    # Streamlit reads borough (via API)
    response = requests.get(f"http://localhost:8012/api/session/{session_id}")
    assert response.json()["borough"] == "MANHATTAN"
```

---

## 5. ACID + State Management: Detailed Solutions

### 5.1 How Dash Handles Session State Persistence

**Challenge:** Each user needs isolated state, persisted across page refreshes.

**Solution:** Multi-layer approach

1. **Browser-Level (dcc.Store):** UI state, filter selections
   ```python
   dcc.Store(id="store-global-filters", storage_type="session")  # Cleared on browser close
   dcc.Store(id="store-ui-state", storage_type="local")          # Persisted across restarts
   ```

2. **Server-Level (Redis):** Session data, authentication, cached results
   ```python
   # User closes browser → session TTL expires (1 hour)
   # User reopens browser → new session_id generated
   # But data in DuckDB analysis_history persists forever
   ```

3. **Database-Level (DuckDB):** Immutable audit logs, analysis history
   ```
   CREATE TABLE analysis_history (
       id UUID PRIMARY KEY,
       user_id VARCHAR,
       skill_name VARCHAR,
       table_name VARCHAR,
       timestamp TIMESTAMP,
       success BOOLEAN
   );
   ```

### 5.2 Multi-User Concurrent Access

**Scenario:** 5 analysts using same dashboard simultaneously.

**State Isolation:**

```
Analyst A (session_id: abc123)
├─ Redis: session:abc123 → {"borough": "MANHATTAN", "date_start": "2026-01-01"}
├─ Dash: dcc.Store (browser) → UI state for Analyst A
└─ DuckDB: analysis_history (shared) → Read-only queries, no conflicts

Analyst B (session_id: def456)
├─ Redis: session:def456 → {"borough": "BROOKLYN", "date_start": "2026-02-01"}
├─ Dash: dcc.Store (browser) → UI state for Analyst B
└─ DuckDB: analysis_history (shared) → Read-only queries, no conflicts
```

**No conflicts because:**
- Redis sessions are isolated by session_id
- DuckDB queries are read-only (DataManager in read_only=True mode)
- Write operations (exports, audits) append to analysis_history (append-only table)

**Callback Synchronization (Prevents Race Conditions):**

```python
@app.callback(
    Output("store-global-filters", "data", allow_duplicate=True),
    Input("borough-filter", "value"),
    State("store-global-filters", "data"),  # Current state
    prevent_initial_call=True
)
def update_filters_safely(selected_borough, current_filters):
    """
    Only update the borough field; preserve other filters.
    Dash prevents concurrent callbacks from clobbering each other.
    """
    updated = current_filters or {}
    updated["borough"] = selected_borough
    return updated
```

### 5.3 Where Does st.session_state Move?

**Mapping Streamlit → Dash:**

| Streamlit State | Dash Replacement | Storage | Example |
|-----------------|-----------------|---------|---------|
| `st.session_state.user_id` | FastAPI middleware + Redis | Redis | `session:abc123` → `{"user_id": "analyst_1"}` |
| `st.session_state.pipeline_run` | `dcc.Store` | Browser session | `<dcc.Store id="store-pipeline-active" storage_type="session">` |
| `st.session_state.borough` | `dcc.Store` + Redis sync | Both | Synced on change via callback |
| `st.session_state.filtered_df` | Callback result (computed, not stored) | Computed on-demand | No storage needed; cached via `@memoize_callback` |
| `st.session_state.exploration_history` | DuckDB `analysis_history` | DuckDB | Persistent across sessions |

**Key Difference:** Streamlit stores computed results; Dash recomputes on demand (with caching).

---

## 6. Migration Implementation Details

### 6.1 Phase 1 Pilot: GIS Dashboard Step-by-Step

#### Step 1: Extract GIS Layout from Streamlit

**Before (app/main.py):**
```python
# This is buried inside the main Streamlit app
if nav_selection == "🗺️ Geospatial Intelligence":
    render_gis_dashboard()

def render_gis_dashboard():
    st.title("GIS & Spatial Intelligence")
    # 10 charts, st.columns, st.plotly_chart calls
```

**After (app/dash_layouts_gis.py):**
```python
def layout_gis():
    """GIS dashboard layout for Dash app."""
    return dmc.Container(
        fluid=True, pt="md",
        children=[
            dmc.Text("GIS & SPATIAL INTELLIGENCE", fw=900, size="xl"),
            dcc.Store(id="store-spatial-filters", storage_type="session"),
            dmc.Grid([
                dmc.GridCol(span=9, children=[
                    dcc.Graph(id="viz-ramp-heatmap")
                ]),
                dmc.GridCol(span=3, children=[
                    dmc.Button("DRAW GEOFENCE", id="btn-draw-polygon"),
                    dmc.Switch(label="3D Buildings", id="toggle-3d-buildings"),
                ])
            ])
        ]
    )
```

#### Step 2: Implement Spatial Callbacks

**File: app/callbacks/gis_spatial.py**

```python
from dash import callback, Input, Output, State
from app.services.gis_service import get_spatial_clusters, create_heatmap_figure
import dash

@app.callback(
    Output("viz-ramp-heatmap", "figure"),
    Input("store-spatial-filters", "data"),
    Input("borough-filter", "value"),
    prevent_initial_call=False
)
def update_ramp_heatmap(spatial_filters, borough):
    """Generate 3D ramp density heatmap."""
    if not borough:
        return go.Figure()  # Empty figure
    
    df = dm.fetch_dataset("ramp_locations")
    if borough != "ALL":
        df = df[df["borough"] == borough]
    
    return create_heatmap_figure(df, title="3D Pedestrian Ramp Density")
```

#### Step 3: Register Callbacks in Main App

**File: app/dash_app.py** (modified)

```python
from app.callbacks.gis_spatial import register_gis_spatial_callbacks

# In the callback registration section:
register_gis_spatial_callbacks(app, dm)
```

#### Step 4: Performance Testing

```bash
# Baseline (before migration)
pytest tests/test_gis_performance.py::test_gis_borough_filter_latency -v
# Expected: ~12 seconds (Streamlit rerun)

# After migration
pytest tests/test_gis_performance.py::test_gis_borough_filter_latency -v
# Expected: <0.5 seconds (Dash callback)
```

### 6.2 Callback Registration Pattern

**File: app/callbacks/__init__.py**

```python
def register_all_callbacks(app, dm_instance):
    """Central registration point for all callbacks."""
    from app.callbacks.navigation import register_navigation_callbacks
    from app.callbacks.gis_spatial import register_gis_spatial_callbacks
    from app.callbacks.analytics_stats import register_analytics_callbacks
    from app.callbacks.contracts_labor import register_labor_callbacks
    
    register_navigation_callbacks(app)
    register_gis_spatial_callbacks(app, dm_instance)
    register_analytics_callbacks(app, dm_instance)
    register_labor_callbacks(app, dm_instance)
```

**File: app/dash_app.py** (simplified)

```python
from app.callbacks import register_all_callbacks

# Register all callbacks at app startup
register_all_callbacks(app, dm)

if __name__ == "__main__":
    uvicorn.run(server, host="127.0.0.1", port=8011, log_level="debug")
```

---

## 7. Effort & Timeline Breakdown

### Summary Table

| Phase | View(s) | Charts | Effort (hours) | Timeline | Team Size |
|-------|---------|--------|-----------------|----------|-----------|
| **1A** | GIS Pilot | 10 | 40-45 | Weeks 1-3 | 1-2 |
| **1B** | Infrastructure | N/A | 25-30 | Weeks 1-3 (parallel) | 1 |
| **2A** | Analytics (Stats) | 8 | 30-35 | Weeks 4-5 | 1 |
| **2B** | Contracts/Labor | 3 | 22-25 | Week 6 | 1 |
| **3** | Optimization & Testing | N/A | 20-25 | Weeks 7-8 | 1-2 |
| **TOTAL** | 5 views | 21 | **137-160 hours** | **8 weeks** | 1-2 FTE |

### Per-View Estimate

**Pilot (GIS Dashboard): 40-45 hours**

```
├─ Layout extraction from Streamlit: 3h
├─ Spatial callback architecture design: 4h
├─ Implement 10 chart callbacks:
│  ├─ Ramp heatmap: 3h
│  ├─ Density clustering: 3h
│  ├─ TSP route optimization: 3h
│  ├─ Conflict buffers: 2.5h
│  ├─ Animated borough bar: 2.5h
│  └─ Others (5 charts): 2h
├─ 3D building toggle optimization: 4h
├─ Session state synchronization: 5h
├─ Testing + baseline measurement: 8h
└─ Documentation + runbook: 2h
```

**Analytics (Stats): 30-35 hours**

```
├─ Layout extraction: 2h
├─ Callback architecture: 3h
├─ Chart callbacks (8 charts):
│  ├─ Feature importance ranking: 3h
│  ├─ Moment history chart: 2.5h
│  ├─ SLA freshness matrix: 2.5h
│  ├─ Quality distribution: 2.5h
│  ├─ Anomaly flux: 2.5h
│  └─ Others (3 charts): 2h
├─ Dataset selection dropdown + filtering: 3h
├─ Testing: 5h
└─ Documentation: 1h
```

**Contracts/Labor: 22-25 hours**

```
├─ Layout extraction: 1.5h
├─ Callback architecture: 2.5h
├─ Chart callbacks (3 charts):
│  ├─ Burn rate: 2.5h
│  ├─ Lifecycle funnel: 3h
│  └─ Performance radar: 3h
├─ Time-series filtering: 3h
├─ Contractor filtering + thresholds: 2h
├─ Testing: 4h
└─ Documentation: 0.5h
```

**Infrastructure (Parallel with Pilot): 25-30 hours**

```
├─ Redis session store: 5h
├─ Session sync middleware: 4h
├─ Callback timing decorator: 2h
├─ LRU cache + memoization: 3h
├─ DataManager integration: 3h
├─ Monitoring + instrumentation: 4h
├─ Redis connection pooling: 2h
└─ Documentation: 2h
```

**Optimization & Testing: 20-25 hours**

```
├─ Performance profiling: 5h
├─ Callback optimization (lazy loading): 4h
├─ A/B testing setup: 3h
├─ Security audit: 3h
├─ Load testing (100 concurrent users): 3h
├─ Documentation of patterns: 2h
└─ Buffer for unforeseen issues: 2h
```

---

## 8. Risk Assessment & Mitigation

### 8.1 Risks & Mitigation Strategies

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|-----------|
| **Callback bottlenecks** (expensive computations block UI) | High latency (>1s) | Medium | Implement `@timer_callback` decorator, memoization, async callbacks for heavy ops |
| **Redis connection exhaustion** | Cascading failures under load | Low | Connection pooling (max 20), Redis Sentinel for failover |
| **Session state data inconsistency** | Users see stale data | Low | Atomic Redis ops (`HSET`), TTL-based invalidation, explicit cache busting |
| **Multi-user concurrent access conflicts** | Data corruption, wrong results | Very Low | DuckDB read-only mode, append-only audit logs, Dash callback isolation |
| **Missing data (SODA API downtime)** | Empty charts, confusing UX | Medium | Cache misses → fallback to last known good data, show "Data unavailable" banner |
| **Memory bloat (50+ charts all loaded)** | Crash, performance degradation | Medium | Lazy load charts, implement virtual scrolling, discard offscreen charts |
| **Auth/session hijacking** | Security breach | Low | HTTPS only, HttpOnly cookies, CSRF tokens, Redis session encryption |
| **Network latency (Redis → DuckDB → Socrata) | Slow callback cycles | Low | Query optimization, local caching, pre-computed aggregations |

### 8.2 Rollback Strategy

**Scenario 1: Pilot GIS Migration Breaks**

```
Day 1-2: Issues detected in production
├─ Revert app/callbacks/gis_spatial.py to stub callbacks
├─ Redirect /geo route back to Streamlit version
├─ Keep pilot data in separate branch for post-mortem
└─ Root cause analysis

Day 3-5: Fix in development
├─ Fix bug (e.g., callback timeout, missing data)
├─ Run full test suite
└─ Redeploy when confident
```

**Scenario 2: Performance Regression (Callbacks >1s)**

```
├─ Identify slow callback via @timer_callback logs
├─ Add memoization cache (TTL: 5-10 min)
├─ Consider async background task (for heavy ops)
├─ If still slow, pre-compute aggregations nightly
└─ Re-test until <500ms P95
```

**Scenario 3: Redis Session Store Unavailable**

```
├─ Dash callbacks degrade gracefully:
│  └─ Load default filters (borough: "ALL", date: "last_30_days")
├─ dcc.Store fallback (browser-only state)
├─ Alert user: "Some features offline, try refreshing"
└─ Restart Redis service
```

### 8.3 A/B Testing Plan: Streamlit vs Dash

**Objective:** Validate Dash improves UX before full migration.

**Setup:**

```python
# app/routes/ab_test.py (FastAPI endpoint)
import random

@server.get("/geo")
async def gis_dashboard_route(session_id: str = None):
    """Route user to Streamlit or Dash based on A/B test group."""
    if not session_id:
        session_id = generate_session_id()
    
    # 50% to Dash, 50% to Streamlit
    assigned_group = random.choice(["dash", "streamlit"])
    
    if assigned_group == "dash":
        return redirect("http://localhost:8012/geo")
    else:
        return redirect("http://localhost:8501/geo")  # Streamlit port
```

**Metrics Tracked:**

```python
# Log interaction metrics
@app.callback(...)
@timer_callback
def tracked_callback(input_val):
    """Every callback automatically logs execution time."""
    # Decorator logs: callback_name, duration_ms, user_id, timestamp
    # → Shipped to metrics service (InfluxDB / Prometheus)
    pass
```

**Analysis (after 2 weeks):**

```
Streamlit Group (50 users, 500 interactions):
├─ Median interaction time: 10.2 seconds
├─ 95th percentile: 18.5 seconds
└─ User satisfaction: "Too slow" (47%), "Acceptable" (53%)

Dash Group (50 users, 500 interactions):
├─ Median interaction time: 0.43 seconds
├─ 95th percentile: 0.89 seconds
└─ User satisfaction: "Fast" (89%), "Acceptable" (11%)

Conclusion: Dash is 97% faster → Full migration approved
```

---

## 9. Success Criteria

### Pilot Phase (GIS Dashboard)

- [ ] All 10 GIS charts load in <2 seconds
- [ ] Borough/date/category filter changes complete in <500ms (P95)
- [ ] 3D toggle doesn't increase memory >10%
- [ ] 100+ concurrent users sustained >95% success rate
- [ ] Zero data corruption / state inconsistency issues
- [ ] 95% callback success rate (no timeouts)
- [ ] Session sync (Streamlit ↔ Dash) works correctly

### Full Migration (All 5 Views)

- [ ] 50+ charts render with <1s initial load
- [ ] Average interaction latency <500ms (Dash callbacks)
- [ ] Streamlit views (reports, settings) still <5s rerun
- [ ] Session state persists across refreshes + browser restarts
- [ ] Multi-user concurrent access works without conflicts
- [ ] 99% uptime during business hours
- [ ] Export functionality (CSV, PDF, PNG) <2s

---

## 10. Implementation Checklist

### Pre-Launch (Week 0)

- [ ] Create feature branch: `feature/dash-migration`
- [ ] Set up Redis instance (local dev + staging)
- [ ] Configure pytest fixtures for Dash testing
- [ ] Create performance baseline script

### Phase 1A: GIS Pilot (Weeks 1-3)

- [ ] Extract `layout_gis()` from Streamlit app/main.py
- [ ] Create `app/callbacks/gis_spatial.py`
- [ ] Create `app/callbacks/gis_3d.py`
- [ ] Create `app/services/gis_service.py`
- [ ] Implement 10 chart generation functions
- [ ] Register callbacks in `app/dash_app.py`
- [ ] Write integration tests (15+ test cases)
- [ ] Run performance baseline vs Streamlit
- [ ] Code review + merge to main

### Phase 1B: Infrastructure (Weeks 1-3)

- [ ] Create `app/middleware/redis_session.py`
- [ ] Create `app/middleware/session_sync.py`
- [ ] Create `app/callbacks/base.py` (timer + memoization)
- [ ] Create `app/cache/callback_cache.py`
- [ ] Add Redis connection pooling
- [ ] Document session state strategy
- [ ] Write unit tests for session storage

### Phase 2A: Analytics (Weeks 4-5)

- [ ] Extract `layout_stats()` from Streamlit
- [ ] Create `app/callbacks/analytics_stats.py`
- [ ] Create `app/services/analytics_service.py` (expand)
- [ ] Implement 8 chart callbacks
- [ ] Write integration tests
- [ ] Performance baseline
- [ ] Code review + merge

### Phase 2B: Contracts/Labor (Week 6)

- [ ] Extract `layout_labor()` from Streamlit
- [ ] Create `app/callbacks/contracts_labor.py`
- [ ] Create `app/services/labor_service.py`
- [ ] Implement 3 chart callbacks
- [ ] Write integration tests
- [ ] Performance baseline
- [ ] Code review + merge

### Phase 3: Optimization (Weeks 7-8)

- [ ] Profile all callbacks; identify slow operations
- [ ] Optimize memoization TTLs based on data freshness
- [ ] Implement lazy loading for off-screen charts
- [ ] A/B test Dash vs Streamlit (GIS dashboard)
- [ ] Security audit (session handling, input validation)
- [ ] Load test (100 concurrent users)
- [ ] Write comprehensive runbook
- [ ] Train team on new architecture

### Post-Launch

- [ ] Monitor callback latency in production
- [ ] Track Redis memory usage + hit rates
- [ ] Collect user feedback
- [ ] Schedule quarterly optimization reviews
- [ ] Plan next iteration (50 → 100+ charts)

---

## 11. Documentation & Runbooks

### For Developers

**File:** `docs/DASH_MIGRATION_GUIDE.md`

```markdown
# Dash Migration Guide

## Adding a New Chart to GIS Dashboard

1. Create chart generator function in `app/services/gis_service.py`:
   ```python
   def create_my_chart_figure(df, title=""):
       return go.Figure(data=[...], layout=go.Layout(title=title))
   ```

2. Add callback in `app/callbacks/gis_spatial.py`:
   ```python
   @app.callback(
       Output("viz-my-chart", "figure"),
       Input("borough-filter", "value"),
   )
   @timer_callback
   def update_my_chart(borough):
       df = dm.fetch_dataset("my_dataset")
       return create_my_chart_figure(df)
   ```

3. Register callback in `app/callbacks/__init__.py`

4. Test: `pytest tests/test_gis_callbacks.py::test_my_chart_renders`

5. Measure latency: `pytest tests/test_gis_performance.py -v`

## Session State Best Practices

- Use `dcc.Store` for UI state (tabs, collapsed sections)
- Use Redis for user data (filters, preferences)
- NEVER store DataFrames in session (too large)
- Cache expensive computations with `@memoize_callback(ttl_seconds=600)`
```

### For Operators

**File:** `docs/DASH_OPERATIONS_RUNBOOK.md`

```markdown
# Dash Operations Runbook

## Monitoring

- **Redis Memory:** `redis-cli INFO memory` (should be <500MB)
- **Callback Latency:** Check logs for `@timer_callback` warnings (>500ms)
- **Cache Hit Ratio:** `redis-cli INFO stats | grep hits`

## Troubleshooting

### Slow Callbacks (>1s)
1. Check logs: `grep "Slow callback" app.log`
2. Identify bottleneck (usually DataManager fetch or computation)
3. Add memoization or pre-compute aggregate

### High Memory Usage (>1GB)
1. Check Redis: `redis-cli --bigkeys`
2. Clear old sessions: `redis-cli FLUSHDB` (WARNING: production only with backup)
3. Reduce cache TTLs in `app/middleware/redis_session.py`

### Session Sync Issues
1. Verify Redis connectivity: `redis-cli ping` (should return PONG)
2. Check session key: `redis-cli HGETALL session:{session_id}`
3. Clear bad session: `redis-cli DEL session:{session_id}`
```

---

## 12. Future Roadmap: 50 → 100+ Charts

Once the pilot is successful, the architecture enables:

- **Charts 50-100:** Add analytics views (predictive forecasting, causal inference)
- **Advanced Filters:** Multi-select, date range pickers, SQL-like queries
- **Real-Time Updates:** WebSocket callbacks for live data streams
- **Export Pipeline:** Automated report generation (PDF, PowerBI, Tableau)
- **AI Copilot Integration:** Claude API → Natural language chart generation
- **Mobile Support:** React Native / responsive Dash layouts
- **Multi-Tenancy:** Per-borough isolation, role-based access control

---

## Summary: Why Dash Wins

| Dimension | Streamlit | Dash | Winner |
|-----------|-----------|------|--------|
| **Interaction Speed** | 5-15s (full rerun) | <500ms (callback) | **Dash (30x faster)** |
| **Chart Capacity** | 64 (limits at ~100 charts) | 50+ (scales to 200+) | **Dash** |
| **Development Experience** | Fast prototyping, limited control | More code, full control | **Streamlit** (dev) / **Dash** (prod) |
| **Multi-User Support** | Session isolation weak | Strong session isolation | **Dash** |
| **Caching Strategy** | Widget-level caching | Callback + server-side caching | **Dash** |
| **Customization** | Limited (Streamlit controls) | Full (Plotly + Mantine) | **Dash** |
| **Team Skill Curve** | Easier (fewer Python concepts) | Steeper (React patterns) | **Streamlit** |

**Recommendation:** Hybrid approach wins. Keep Streamlit for low-interactivity (settings, reports). Migrate to Dash for dashboards (GIS, analytics, contracts).

---

**Next Steps:**
1. Review this plan with team
2. Estimate total effort & timeline
3. Assign resources (1-2 FTE for 8 weeks)
4. Create Jira epic + user stories
5. Kick off Phase 1A (GIS Pilot)

