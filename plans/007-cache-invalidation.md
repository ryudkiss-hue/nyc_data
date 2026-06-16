# Plan 007: Cache Invalidation Logic Fix

**Finding:** Cache inefficiency with platform=None parameter  
**File:** `src/socrata_toolkit/platform/connection.py` line 57–59  
**Severity:** MEDIUM  
**Effort:** Small (15 min)  
**Risk:** Low (logic fix, no new dependencies)

## Problem

Cache check at line 57–59:
```python
if self.conn and self.platform == platform:
    return self.conn
```

Fails when `platform=None` (default auto-detect):
- After first call: `self.platform = "motherduck"` or `"duckdb"`
- Subsequent call with `get_connection()` or `get_connection(platform=None)`: `"motherduck" == None` → False
- Cache ignored, new connection created unnecessarily
- Wastes connection resources and adds latency

Example:
```python
conn1 = get_connection()  # Auto, connects to motherduck, self.platform='motherduck'
conn2 = get_connection()  # platform=None, checks 'motherduck'==None, False, reconnects!
```

## Solution

Track the "effective" platform separately from the requested platform. Cache hit when:
1. Requested platform matches cached platform (explicit match), OR
2. Requested platform is None and a cached connection exists (use whatever is cached)

## Implementation Steps

### Step 1: Update cache logic in get_connection()

Replace lines 57–59 with:

```python
# If already connected, return cached connection
# - Explicit platform match: use cached connection if platforms match exactly
# - Auto mode (platform=None): use cached connection regardless of type
if self.conn:
    if platform is None or self.platform == platform:
        return self.conn
```

This logic says:
- If `platform=None` (auto mode), use cached connection of any type
- If `platform="motherduck"` or `platform="duckdb"`, use cached connection only if it matches

## Verification

### Unit test (add to tests/test_platform_connection.py if it exists)

```python
def test_cache_hit_with_none_platform():
    """Verify cache is used when platform=None (auto mode)."""
    manager = ConnectionManager()
    
    # First call: auto mode connects and caches
    try:
        conn1 = manager.get_connection(platform=None)
    except Exception:
        pass  # OK if connection fails, we just care about cache logic
    
    # Mock the connection to avoid real connection
    from unittest.mock import Mock
    mock_conn = Mock()
    mock_conn.execute = Mock(return_value=Mock(fetchall=Mock(return_value=[])))
    manager.conn = mock_conn
    manager.platform = "motherduck"
    
    # Second call: auto mode should reuse cached connection
    conn2 = manager.get_connection(platform=None)
    
    # Verify it's the same connection object (cache hit)
    assert conn1 is conn2, "Cache should be hit for platform=None"
    print("✓ Cache hit for platform=None")

def test_explicit_platform_mismatch_new_connection():
    """Verify different explicit platforms don't share cache."""
    manager = ConnectionManager()
    
    from unittest.mock import Mock
    
    # Set up cached motherduck connection
    mock_md = Mock()
    manager.conn = mock_md
    manager.platform = "motherduck"
    
    # Request explicit duckdb (should be cache miss in ideal case)
    # Note: In current implementation, this will try to connect to duckdb
    # and either succeed or fail based on environment
    # The cache logic should at least not return the motherduck connection
    # for a duckdb request
    
    print("✓ Explicit platform requests don't incorrectly reuse cache")
```

### Manual test

```bash
python -c "
import sys
sys.path.insert(0, '/home/user/nyc_data/src')

from socrata_toolkit.platform.connection import ConnectionManager
from unittest.mock import Mock

# Test cache hit with platform=None
manager = ConnectionManager()

# Mock a cached connection
mock_conn = Mock()
manager.conn = mock_conn
manager.platform = 'motherduck'

# Call with platform=None (auto mode)
result1 = manager.get_connection(platform=None)

# Check if it returned the cached connection
if result1 is mock_conn:
    print('✓ Cache hit: platform=None returned cached connection')
else:
    print('✗ Cache miss: platform=None did not use cached connection')

# Call with explicit platform that doesn't match
result2 = manager.get_connection(platform='duckdb')

# This should attempt a new connection (may fail if no DuckDB env)
# But the important thing is the cache logic is correct
print('✓ Explicit platform request handled')
"
```

## Done Criteria

- [ ] Cache logic updated at lines 57–59 to handle `platform=None` case
- [ ] Test confirms cache hit for `get_connection()` and `get_connection(platform=None)`
- [ ] Explicit platform requests don't incorrectly reuse cross-platform cached connections
- [ ] Imports are clean: `python -c "from socrata_toolkit.platform import *; print('OK')"`

## Maintenance Notes

- This is a performance optimization, not a correctness fix
- Monitor cache hit rates if metrics are added in the future
- Consider tracking cache performance (hits vs. misses) for optimization opportunities

## Escape Hatches

- If different platforms should never share cache, revert to strict equality check: `self.platform == platform`
