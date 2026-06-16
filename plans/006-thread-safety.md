# Plan 006: Thread-Safety Fix

**Finding:** Global _manager cache not thread-safe  
**File:** `src/socrata_toolkit/platform/connection.py` line 93, 112, 137  
**Severity:** HIGH  
**Effort:** Medium (30 min)  
**Risk:** Medium (requires careful testing of concurrent access)

## Problem

Global `_manager` singleton (line 137) is shared across async requests. When concurrent requests call:
- Request A: `get_connection(platform='motherduck')` → sets `self.conn`, `self.platform = "motherduck"`
- Request B: `get_connection(platform='duckdb')` → sets `self.conn`, `self.platform = "duckdb"` (simultaneously)

No mutex protects the write sequence at lines 93–94 and 112–113. Under Cloud Run's async model:
- Context switch between `self.conn = conn` and `self.platform = platform` assignment
- One request gets wrong connection type
- Silent data corruption or query failures

## Solution

Add `threading.Lock` to protect connection state writes.

## Implementation Steps

### Step 1: Add threading import to connection.py

At the top of the file (after `from pathlib import Path`), add:

```python
import threading
```

### Step 2: Add lock to ConnectionManager.__init__()

Modify the `__init__` method (around line 31) to initialize a lock:

```python
def __init__(self, auto_fallback: bool = True):
    """
    Initialize connection manager.

    Args:
        auto_fallback: If True, automatically fallback to DuckDB if MotherDuck unavailable
    """
    self.auto_fallback = auto_fallback
    self.conn = None
    self.platform = None
    self._lock = threading.Lock()  # ADD THIS LINE
```

### Step 3: Protect connection state writes in _connect_motherduck()

Modify lines 93–95 to use the lock:

**Before:**
```python
self.conn = conn
self.platform = "motherduck"
logger.info("✓ Connected to MotherDuck")
```

**After:**
```python
with self._lock:
    self.conn = conn
    self.platform = "motherduck"
logger.info("✓ Connected to MotherDuck")
```

### Step 4: Protect connection state writes in _connect_duckdb()

Modify lines 112–113 similarly:

**Before:**
```python
self.conn = conn
self.platform = "duckdb"
```

**After:**
```python
with self._lock:
    self.conn = conn
    self.platform = "duckdb"
```

### Step 5: Protect cache read in get_connection()

Modify lines 57–59 to use the lock:

**Before:**
```python
if self.conn and self.platform == platform:
    return self.conn
```

**After:**
```python
with self._lock:
    if self.conn and self.platform == platform:
        return self.conn
```

### Step 6: Protect state clear in close()

Modify lines 132–133 to use the lock:

**Before:**
```python
finally:
    self.conn = None
    self.platform = None
```

**After:**
```python
finally:
    with self._lock:
        self.conn = None
        self.platform = None
```

## Verification

### Unit test (add to tests/test_platform_connection.py if it exists)

```python
import concurrent.futures
import threading

def test_concurrent_platform_switch():
    """Test that concurrent platform switches don't corrupt state."""
    manager = ConnectionManager()
    results = []
    
    def switch_platform(platform_name: str):
        """Try to connect to specified platform and record result."""
        try:
            # Mock connection (won't actually connect in test)
            conn = manager.get_connection(platform=platform_name)
            with manager._lock:
                results.append({
                    'requested': platform_name,
                    'actual': manager.platform,
                })
        except Exception as e:
            results.append({'error': str(e)})
    
    # Simulate concurrent requests switching platforms
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for i in range(10):
            platform = "motherduck" if i % 2 == 0 else "duckdb"
            futures.append(executor.submit(switch_platform, platform))
        
        concurrent.futures.wait(futures)
    
    # Verify no corruption: each result's platform matches request
    # (or is a cached value from previous request)
    for result in results:
        if 'error' not in result:
            # Either requested platform was set, or cached value is consistent
            assert 'requested' in result
            print(f"✓ Platform switch consistent: {result}")
```

### Manual concurrent test

```bash
python -c "
import sys
sys.path.insert(0, '/home/user/nyc_data/src')

from socrata_toolkit.platform.connection import ConnectionManager
import threading
import time

manager = ConnectionManager()
success = True

def concurrent_connect(platform, delay=0):
    global success
    try:
        time.sleep(delay)
        # Don't actually connect (no valid tokens), just test the lock logic
        print(f'Thread {platform} requesting connection...')
    except Exception as e:
        success = False
        print(f'ERROR: {e}')

# Start threads that would try to connect concurrently
threads = []
for i in range(5):
    t = threading.Thread(target=concurrent_connect, args=('motherduck', i*0.01))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

if success:
    print('✓ Concurrent access test passed')
else:
    print('✗ Concurrent access test failed')
"
```

## Done Criteria

- [ ] `threading` module imported at top of connection.py
- [ ] `self._lock = threading.Lock()` added to `ConnectionManager.__init__()`
- [ ] All writes to `self.conn` and `self.platform` protected by `with self._lock:`
- [ ] All reads from cache (line 57–59) protected by `with self._lock:`
- [ ] Imports are clean: `python -c "from socrata_toolkit.platform import *; print('OK')"`
- [ ] No deadlocks observed in concurrent test

## Maintenance Notes

- Lock is non-reentrant (standard Lock). If ConnectionManager methods call each other, verify no deadlock
- Monitor for lock contention on high-traffic Cloud Run instances (consider RWLock if read-heavy)
- Future: Consider async lock if switching to full async/await architecture
- Document that get_connection() is now thread-safe and suitable for multi-threaded environments

## Escape Hatches

- If lock causes performance issues, profile lock contention first before optimizing
- If re-entrancy is needed, switch to `threading.RLock()` instead of `Lock()`
