# Plan 003: Dash analytics callbacks memoize data fetches to eliminate per-interaction full refetches

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 4343044..HEAD -- app/callbacks/analytics_integration.py app/services/analytics_service.py app/callbacks/decorators.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts before proceeding.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: perf
- **Planned at**: commit `4343044`, 2026-06-12

## Why this matters

Every time a user changes any Dash filter (borough picker, date range, column
selector), the callbacks in `app/callbacks/analytics_integration.py` call
`get_dataset(filters)` and `get_spatial_data(filters)` unconditionally. These
functions hit DuckDB or the Socrata API and return full DataFrames — for a
100K-row dataset this can take 1–3 seconds per interaction, blocking the entire
Dash UI. The `@memoize_with_ttl` decorator already exists in
`app/callbacks/decorators.py` and is already imported in
`analytics_integration.py` but is only applied to a small number of
visualization functions — not to the data-fetch services themselves. Applying
it to `get_dataset` and `get_spatial_data` means repeated identical filter
combinations return from memory instantly.

## Current state

**`app/callbacks/decorators.py` — the memoization decorator (lines 17–51)**:

```python
_CACHE_STORE = {}

def memoize_with_ttl(seconds: int = 600):
    """Cache decorator with TTL in seconds."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            cache_key = f"{func.__name__}_{args}_{kwargs}"
            if cache_key in _CACHE_STORE:
                value, expiry = _CACHE_STORE[cache_key]
                if datetime.now() < expiry:
                    return value
            result = func(*args, **kwargs)
            _CACHE_STORE[cache_key] = (result, datetime.now() + timedelta(seconds=seconds))
            return result
        return wrapper
    return decorator
```

The cache key is `f"{func.__name__}_{args}_{kwargs}"`. For this to work
correctly, the `filters` dict argument passed to `get_dataset` and
`get_spatial_data` must be hashable-representable as a string (a plain dict
with string/int/None values serializes correctly with `str()`).

**`app/services/analytics_service.py` — data fetch functions (lines 1–30+)**:

The file defines `get_dataset(filters)`, `get_spatial_data(filters)`,
`get_timeseries_data(filters)`, and `get_kpi_metrics(filters)`. None of them
have a `@memoize_with_ttl` decorator applied.

**`app/callbacks/analytics_integration.py` — callbacks that call them (lines 1–70)**:

`memoize_with_ttl` is imported at line 20 (`from app.callbacks.decorators import memoize_with_ttl, timer_callback`) but only applied to visualization helpers, not to service functions.

The data fetch pattern in each callback is:
```python
df = get_dataset(filters)          # line ~62 in update_distribution_classification
df = get_spatial_data(filters)     # line ~120 in update_anomaly_detection
```

**Repo convention for decorators**: The `@timer_callback` decorator is applied
to individual callback functions. The `@memoize_with_ttl` pattern is the same
style — see existing usages in `app/callbacks/analytics_integration.py` for
reference.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Lint | `ruff check app/services/analytics_service.py app/callbacks/analytics_integration.py` | `All checks passed!` |
| Run callback tests | `pytest tests/test_cache_service.py tests/test_analytics_integration.py -q` | all pass |
| Verify decorator import | `grep "memoize_with_ttl" app/services/analytics_service.py` | line showing import |

## Scope

**In scope**:
- `app/services/analytics_service.py` — add `@memoize_with_ttl` to `get_dataset`, `get_spatial_data`, `get_timeseries_data`, `get_kpi_metrics`

**Out of scope**:
- `app/callbacks/analytics_integration.py` — no changes needed; the decorator lives on the service, not the caller
- `app/callbacks/decorators.py` — do not modify the decorator implementation
- Any source file in `src/socrata_toolkit/`

## Git workflow

- Branch: `perf/003-memoize-analytics-fetches`
- Commit: `perf: memoize analytics service data fetches with TTL cache`

## Steps

### Step 1: Read the full analytics_service.py to understand all fetch functions

Open `app/services/analytics_service.py` and find every function that:
1. Accepts a `filters` argument
2. Performs a DuckDB query or external API call
3. Returns a DataFrame or dict

List those function names before proceeding — they are your targets.

**Verify**: You should find at minimum: `get_dataset`, `get_spatial_data`,
`get_timeseries_data`, `get_kpi_metrics`. If you find more, apply the decorator
to all of them.

### Step 2: Add the import and apply @memoize_with_ttl

At the top of `app/services/analytics_service.py`, add the import:

```python
from app.callbacks.decorators import memoize_with_ttl
```

Then decorate each data-fetch function identified in Step 1. Use a 5-minute TTL
(300 seconds) — this matches the `CacheManager` TTL already in the same file:

```python
@memoize_with_ttl(seconds=300)
def get_dataset(filters: dict) -> pd.DataFrame:
    ...

@memoize_with_ttl(seconds=300)
def get_spatial_data(filters: dict) -> gpd.GeoDataFrame:
    ...
```

Apply to `get_timeseries_data` and `get_kpi_metrics` as well.

**Verify**: `grep -c "@memoize_with_ttl" app/services/analytics_service.py`
→ should equal the number of functions you decorated (at least 4).

### Step 3: Confirm filters dict is safely serializable as a cache key

The decorator uses `f"{func.__name__}_{args}_{kwargs}"` as the cache key. The
`filters` argument is a plain dict from `dcc.Store` (JSON-serializable values
only: strings, ints, None, lists of those). This is safe.

**Verify**: Add a temporary smoke test locally (do not commit):
```python
# In a Python REPL with PYTHONPATH=src:.
from app.callbacks.decorators import memoize_with_ttl

call_count = [0]

@memoize_with_ttl(seconds=30)
def test_fn(filters):
    call_count[0] += 1
    return {"result": 42}

filters = {"borough": "MN", "date_range": ["2026-01-01", "2026-06-01"]}
test_fn(filters)
test_fn(filters)
assert call_count[0] == 1, "Cache did not hit on second call"
print("Cache hit verified")
```

### Step 4: Run lint and tests

```bash
ruff check app/services/analytics_service.py
pytest tests/test_cache_service.py tests/test_analytics_integration.py -q
```

Both must pass.

### Step 5: Commit

```bash
git add app/services/analytics_service.py
git commit -m "perf: memoize analytics service data fetches with TTL cache"
```

## Test plan

No new test file is required, but add one assertion to an existing test:

In `tests/test_cache_service.py` (or `tests/test_analytics_integration.py`),
add a test that:
1. Calls `get_dataset(same_filters)` twice with identical filters.
2. Asserts that the underlying DuckDB/API call is only made once (use
   `unittest.mock.patch` on the inner query function).

Model the test after the existing pattern in `tests/test_cache_service.py`
(which already uses `fakeredis` for cache mocking — adapt for `_CACHE_STORE`).

**Verify**: `pytest tests/test_cache_service.py -q` → all pass including the
new cache-hit test.

## Done criteria

- [ ] `grep -c "@memoize_with_ttl" app/services/analytics_service.py` ≥ 4
- [ ] `ruff check app/services/analytics_service.py app/callbacks/analytics_integration.py` → `All checks passed!`
- [ ] `pytest tests/test_cache_service.py tests/test_analytics_integration.py -q` → all pass
- [ ] No files outside the in-scope list are modified
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report if:

- `app/services/analytics_service.py` does not define `get_dataset` or `get_spatial_data`
  (the file may have been renamed or refactored since this plan was written).
- A `filters` argument turns out to contain an unhashable type (e.g., a nested
  list of dicts) — `str()` will still work as a key, but test the cache-hit
  assertion (Step 3) before committing.
- The `memoize_with_ttl` import creates a circular import error (the service
  module importing from callbacks is unusual — if this happens, move
  `memoize_with_ttl` to a shared `app/utils/cache.py` module instead).

## Maintenance notes

- The `_CACHE_STORE` dict in `decorators.py` grows unboundedly in a long-running
  Dash process. The TTL-based eviction only runs on read, not on write. For
  production deployments, consider capping `_CACHE_STORE` size or switching to
  `diskcache` (already in optional deps: `pyproject.toml` line 71 lists
  `diskcache`).
- If filter shapes change (new filter keys added to `dcc.Store`), the cache key
  will naturally miss and re-fetch — no action needed.
- The 300-second TTL matches the `CacheManager` TTL elsewhere in the file.
  If freshness requirements change, update both consistently.
