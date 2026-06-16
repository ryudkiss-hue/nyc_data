# Dash Migration: Quick Reference Guide

**For developers implementing callbacks, quick lookup of patterns & solutions.**

---

## Callback Patterns Cheat Sheet

### Pattern 1: Single Input → Single Output

```python
@app.callback(
    Output("chart-id", "figure"),
    Input("filter-id", "value")
)
def update_chart(filter_val):
    df = dm.fetch_dataset("data")
    return create_figure(df[df["filter"] == filter_val])
```

**Use when:** Simple one-to-one updates (most common)

---

### Pattern 2: Multiple Inputs → Single Output

```python
@app.callback(
    Output("chart-id", "figure"),
    Input("filter-1", "value"),
    Input("filter-2", "value"),
    Input("filter-3", "value"),
)
def update_chart(val1, val2, val3):
    df = dm.fetch_dataset("data")
    df = df[(df["col1"] == val1) & (df["col2"] == val2)]
    return create_figure(df)
```

**Use when:** Multiple filters affect same chart

---

### Pattern 3: Pattern Matching (50 Charts at Once)

```python
# Layout
dcc.Graph(id={"type": "viz", "index": "chart1"}),
dcc.Graph(id={"type": "viz", "index": "chart2"}),
# ... 48 more charts

# Callback
@app.callback(
    Output({"type": "viz", "index": dash.ALL}, "figure"),
    Input("global-filter", "value"),
    prevent_initial_call=False
)
def update_all_charts(filter_val):
    figures = []
    for i in range(50):
        df = dm.fetch_dataset(f"data_{i}")
        figures.append(create_figure(df[df["filter"] == filter_val]))
    return figures
```

**Use when:** Many similar components need same logic

---

### Pattern 4: State (Don't Trigger on Change)

```python
@app.callback(
    Output("output-id", "children"),
    Input("btn-submit", "n_clicks"),
    State("input-field", "value"),  # Doesn't trigger callback
    prevent_initial_call=True
)
def on_button_click(n_clicks, input_val):
    # Only runs when button clicked, not when input changes
    return f"You entered: {input_val}"
```

**Use when:** Need input value but don't want callback on every keystroke

---

### Pattern 5: Prevent Duplicate Updates (allow_duplicate)

```python
@app.callback(
    Output("store", "data"),
    Input("filter", "value"),
    prevent_initial_call=False  # Run on page load
)
def set_default_filters(val):
    return val

@app.callback(
    Output("store", "data", allow_duplicate=True),  # Allow another callback to update
    Input("button", "n_clicks"),
    prevent_initial_call=True
)
def on_button(n_clicks):
    return "button clicked"
```

**Use when:** Multiple callbacks update same Output

---

### Pattern 6: Data Store (Browser-Level State)

```python
# Layout
dcc.Store(id="store-data", storage_type="session"),

# Callback 1: Load data
@app.callback(
    Output("store-data", "data"),
    Input("url", "pathname"),
)
def load_data(pathname):
    df = dm.fetch_dataset("data")
    return df.to_json()

# Callback 2: Use cached data
@app.callback(
    Output("chart", "figure"),
    Input("store-data", "data"),
)
def use_cached_data(json_data):
    df = pd.read_json(json_data)
    return create_figure(df)
```

**Use when:** Need to share data between callbacks without re-fetching

---

## Optimization Patterns

### Memoization (Cache Expensive Computation)

```python
from functools import lru_cache

@lru_cache(maxsize=32)
def expensive_aggregation(dataset_key, borough):
    """Cache up to 32 different combinations."""
    df = dm.fetch_dataset(dataset_key)
    return df[df["borough"] == borough].groupby("category").sum()

@app.callback(
    Output("chart", "figure"),
    Input("borough-filter", "value"),
)
def update_chart(borough):
    agg = expensive_aggregation("violations", borough)
    return create_figure(agg)
```

**Saves:** 2-5 seconds per identical filter combo

---

### Lazy Loading (Don't Render Offscreen)

```python
@app.callback(
    Output("chart-container", "children"),
    Input("scroll-position", "value"),
)
def render_visible_charts(scroll_pos):
    """Only render 5-10 visible charts."""
    first_visible = int(scroll_pos / CHART_HEIGHT)
    last_visible = first_visible + CHARTS_PER_SCREEN
    
    visible_ids = all_chart_ids[first_visible:last_visible]
    
    return [
        dcc.Graph(id={"type": "viz", "index": cid})
        for cid in visible_ids
    ]
```

**Saves:** 10+ seconds on initial load (50 charts)

---

### Debouncing (Slow Down Callbacks)

```python
dcc.Interval(id="debounce", interval=500, disabled=True)

@app.callback(
    Output("chart", "figure"),
    Input("debounce", "n_intervals"),
    State("search-input", "value"),
)
def debounced_search(n_intervals, search_val):
    """Called max every 500ms even if input changes every 10ms."""
    return create_figure(search_val)
```

**Saves:** Prevents callback storm (100+ callbacks/sec → 2 callbacks/sec)

---

## Session State Management

### Store User Filter in Redis

```python
from app.middleware.redis_session import redis_store
import dash

@app.callback(
    Output("store-filters", "data"),
    Input("borough-filter", "value"),
)
def update_filters(borough):
    """Save to Redis so it persists across page refreshes."""
    session_id = dash.ctx.session.session_id
    redis_store.update_session(session_id, {"borough": borough})
    return {"borough": borough}
```

**Result:** User's filters survive browser refresh, browser crash, etc.

---

### Load Session State on Page Load

```python
@app.callback(
    Output("borough-filter", "value"),
    Input("url", "pathname"),
    prevent_initial_call=False
)
def load_saved_filters(pathname):
    """Restore user's last selection from Redis."""
    session_id = dash.ctx.session.session_id
    session = redis_store.get_session(session_id)
    return session.get("borough", "ALL")
```

**Result:** Page loads with user's last-selected filters automatically

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Callback not updating` | Callback disabled (`disabled=True`) | Remove `disabled` attribute |
| `Callback runs endlessly` | Circular dependency (A→B, B→A) | Add `prevent_initial_call=True` or `allow_duplicate=True` |
| `Component not found` | ID mismatch (typo in component ID) | Check spelling in layout vs callback |
| `Memory leaks` | Storing large DataFrames in dcc.Store | Store JSON, recompute on demand |
| `Slow charts on load` | All 50 charts render at once | Use lazy loading (render only visible) |
| `Session lost on refresh` | Using `storage_type="session"` | Change to `storage_type="local"` |
| `Multi-user conflicts` | Shared state (not isolated by session) | Use Redis with session_id keys |

---

## Testing Checklist

```python
# tests/test_my_callback.py

def test_callback_renders(sample_data):
    """Does callback produce a valid figure?"""
    result = my_callback(sample_data)
    assert isinstance(result, go.Figure)

def test_callback_filters_data(sample_data):
    """Does callback apply filters correctly?"""
    result = my_callback_filtered(sample_data, filter_val="test")
    assert len(result.data) > 0

def test_callback_error_handling(empty_data):
    """Does callback handle edge cases?"""
    result = my_callback(empty_data)
    assert isinstance(result, go.Figure)  # Should return figure, not crash

def test_callback_latency():
    """Does callback complete in <500ms?"""
    start = time.time()
    result = my_callback(expensive_data)
    elapsed = time.time() - start
    assert elapsed < 0.5, f"Took {elapsed:.2f}s"
```

---

## Performance Monitoring

### Add Timing Instrumentation

```python
# app/callbacks/base.py
import functools
import time
import logging

logger = logging.getLogger(__name__)

def timer_callback(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        
        if elapsed > 0.5:
            logger.warning(f"SLOW: {func.__name__} took {elapsed:.2f}s")
        else:
            logger.info(f"OK: {func.__name__} took {elapsed:.2f}s")
        
        return result
    return wrapper

# Use it
@app.callback(...)
@timer_callback
def my_callback(val):
    ...
```

**Output logs:**
```
OK: update_chart took 0.23s
SLOW: expensive_computation took 2.15s  ← Needs optimization
OK: sync_filters took 0.04s
```

---

## Deployment Checklist

- [ ] All callbacks have `@timer_callback` decorator
- [ ] All expensive callbacks have `@memoize_with_ttl` or pre-computed data
- [ ] Unit tests: `pytest tests/ -v` (100% pass)
- [ ] Performance tests: `pytest tests/test_perf.py -v` (all <500ms)
- [ ] Code review: 1 colleague approval
- [ ] Redis running: `redis-cli ping` → PONG
- [ ] DuckDB database ready: `ls data/local_db/*.duckdb`
- [ ] Error handling tested (empty data, API downtime)
- [ ] Logging configured (check logs for errors)
- [ ] A/B test 10% users
- [ ] Monitor errors for 24h
- [ ] Expand to 50% users if no errors
- [ ] Full rollout once confidence high

---

## Key Files to Know

| File | Purpose | When to Edit |
|------|---------|--------------|
| `app/dash_app.py` | Main Dash app setup, callback registration | Adding new callback modules |
| `app/callbacks/gis_spatial.py` | GIS dashboard callbacks | Updating GIS charts |
| `app/services/gis_service.py` | Business logic (clustering, routes) | Adding new spatial algorithms |
| `app/middleware/redis_session.py` | Session storage | Changing session TTL or fields |
| `app/cache/callback_cache.py` | Callback memoization | Changing cache strategies |
| `tests/test_gis_callbacks.py` | Unit tests | Adding new chart types |
| `tests/test_gis_performance.py` | Performance tests | Measuring latency baselines |
| `.env` | Environment variables | Setting Redis/DuckDB paths |

---

## Quick Commands

```bash
# Start Dash (development)
cd /path/to/repo
python app/dash_app.py

# Start Streamlit (for comparison)
streamlit run app/main.py

# Run unit tests
pytest tests/test_gis_callbacks.py -v

# Run performance tests
pytest tests/test_gis_performance.py -v -s

# Check Redis connection
redis-cli ping

# Monitor callback latency
tail -f app.log | grep "Slow:"

# Check memory usage
redis-cli INFO memory

# Clear Redis cache (warning: production-only with backup)
redis-cli FLUSHDB

# Profile callback
python -m cProfile -s cumulative app/dash_app.py

# Load test with Locust
locust -f tests/test_load.py -u 100 -r 10
```

---

## Architecture Decision Records

**Why Dash instead of Streamlit?**
- Streamlit: Full script rerun (5-15s) on every interaction
- Dash: Callback-based updates (<500ms)
- Result: 30x faster interactions

**Why Redis for session state?**
- Streamlit and Dash are separate apps
- Redis bridges them (shared session store)
- Result: Users' filters persist across both apps

**Why @memoize_with_ttl instead of Streamlit @st.cache?**
- Streamlit caching tied to script execution
- Dash caching independent of page load
- Result: Cache survives across users, outlives session

**Why lazy load 50 charts?**
- Rendering 50 charts at once = 20+ seconds
- Lazy loading: render only visible (2-3 charts) = 2 seconds
- Result: 10x faster initial load

---

## Links & Resources

- **Dash Docs:** https://dash.plotly.com/
- **Callback Reference:** https://dash.plotly.com/basic-callbacks
- **Performance Guide:** https://dash.plotly.com/performance
- **Mantine Components:** https://mantine.dev/
- **Redis Documentation:** https://redis.io/docs/
- **Plotly Figures:** https://plotly.com/python/

---

## Getting Help

1. **Callback not working?**
   - Check logs: `grep "ERROR\|WARNING" app.log`
   - Check browser console: F12 → Console tab
   - Check Redis: `redis-cli KEYS "session:*"`

2. **Performance slow?**
   - Run performance test: `pytest tests/test_gis_performance.py -v -s`
   - Check logs for "SLOW:" warnings
   - Profile: `python -m cProfile -s cumulative app/dash_app.py`

3. **State not persisting?**
   - Check Redis TTL: `redis-cli TTL session:{session_id}`
   - Check storage_type: should be "local" for persistence
   - Check browser storage: F12 → Storage → Local Storage

4. **Multi-user conflicts?**
   - Verify session isolation: check session_ids are unique
   - Verify DuckDB read-only mode
   - Review callback State management

---

**Last Updated:** 2026-06-10  
**Next Review:** After Phase 1 completion

