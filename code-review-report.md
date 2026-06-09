# Review Report: Current Uncommitted Changes

## Summary
The changes introduce significant performance optimizations and architectural upgrades (Dash 4.2 + FastAPI), but contain several "Industrial" violations regarding portability, documentation, and concurrency safety.

## Verification Checks
- [x] **Plan Compliance**: Yes - Implements optimizations and Dash 4.2 migration.
- [ ] **Style Compliance**: Fail - Missing docstrings and hardcoded local paths.
- [ ] **New Tests**: No
- [x] **Test Coverage**: Partial - Existing unit tests cover logic, but integration tests for new port/backend are missing.
- [x] **Test Results**: Passed - 130 tests passed (subset of 147).

## Findings

### High: Hardcoded Machine-Specific Paths
- **File**: `app/dash_app.py` (Lines 20-21)
- **Context**: Mingw64 paths are hardcoded to `C:\msys64\...`. This breaks the "Industrial" mandate for reproducibility. 
- **Suggestion**: Use an environment variable or configuration file to specify the Mingw64 bin path.
```python
# Use a more portable approach
MINGW_BIN = os.getenv("MINGW_BIN_PATH", r"C:\msys64\mingw64\bin")
os.environ["PATH"] = f"{MINGW_BIN};" + os.environ.get("PATH", "")
```

### Medium: Port Discrepancy
- **File**: `app/dash_app.py` (Line 572)
- **Context**: Port changed to `8025`, but project root `GEMINI.md` specifies `8011`. This will confuse users following the manual instructions.
- **Suggestion**: Align with `GEMINI.md` (8011) or update the root documentation.
```python
    uvicorn.run(server, host="127.0.0.1", port=8011, log_level="debug")
```

### Medium: Potential Race Condition in Progress Tracking
- **File**: `app/data_manager.py` (Lines 66, 89, 94)
- **Context**: Removed locks around `self.progress["completed"] += 1`. While Python's GIL provides some protection, `+= 1` is not atomic. In a high-concurrency "Total Recall" streaming mode, this could lead to inaccurate progress reporting.
- **Suggestion**: Restore the lock for atomic updates.
```python
            with self._lock:
                self.progress["completed"] += 1
```

### Low: Missing Docstrings for New Cache Functions
- **File**: `app/analytics.py` (Lines 38-51)
- **Context**: `_get_cached_geo_cols` and `_get_cached_date_cols` lack docstrings, violating the Python style guide.
- **Suggestion**: Add docstrings explaining the purpose and parameters.
```python
@lru_cache(max_size=128)
def _get_cached_geo_cols(schema_hash: str, columns_tuple: tuple[str, ...]) -> list[str]:
    """Detect and cache geospatial column names based on common naming patterns."""
```

---
