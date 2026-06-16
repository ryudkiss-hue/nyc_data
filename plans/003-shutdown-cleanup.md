# Plan 003: Resource Leak Fix — Shutdown Cleanup

**Finding:** Connection shutdown leak  
**File:** `app/cloud_run.py` line 225–228  
**Severity:** CRITICAL  
**Effort:** Small (10 min)  
**Risk:** Low (simple import + one-line call)

## Problem

`shutdown_event()` never calls `close_connection()`. Global `_manager.conn` stays open when pod terminates:
- DuckDB file handles remain open → locked by stale process
- MotherDuck connections left in `TIME_WAIT` → waste socket resources
- Next pod startup may fail if DuckDB is still locked
- Memory not released properly

## Solution

Import and call `close_connection()` in the shutdown handler.

## Implementation Steps

### Step 1: Update shutdown_event() in app/cloud_run.py

Find the import section at the top of the file (lines 38–42) and verify `close_connection` is imported:

```python
from socrata_toolkit.platform import (
    get_connection,
    get_platform_name,
    is_motherduck,
    close_connection,  # ADD THIS LINE
)
```

### Step 2: Update shutdown_event() function

Replace lines 225–228 with:

```python
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down NYC Sidewalk Toolkit")
    try:
        close_connection()
        logger.info("✓ Database connection closed")
    except Exception as e:
        logger.warning(f"Error closing connection: {e}")
```

## Verification

### Manual test

```bash
# Start app
python -m uvicorn app.cloud_run:app --port 8080 &
APP_PID=$!

sleep 2

# Verify it's running
curl http://localhost:8080/api/health | jq .

# Send SIGTERM to gracefully shut down
kill $APP_PID

# Check logs for shutdown message
sleep 1
ps aux | grep uvicorn | grep -v grep || echo "✓ Process terminated cleanly"
```

### Check for log message

```bash
# Start with logging visible
python -m uvicorn app.cloud_run:app --log-level debug 2>&1 | tee app.log &

sleep 2

# Shut down
kill %1

# Verify shutdown message in logs
sleep 1
grep -E "(Shutting down|Database connection closed|Error closing)" app.log
# Expected: "Shutting down NYC Sidewalk Toolkit"
#           "✓ Database connection closed"
```

## Done Criteria

- [ ] `close_connection` imported in `from socrata_toolkit.platform import ...`
- [ ] `shutdown_event()` calls `close_connection()` with try/except
- [ ] Log message confirms connection closure
- [ ] Imports are clean: `python -c "from app.cloud_run import app; print('OK')"`

## Maintenance Notes

- If connection manager is upgraded to support connection pooling, update shutdown to close all connections
- Test startup/shutdown cycles under load (Cloud Run container restarts)
- Consider adding metrics for connection lifecycle (open/close events)

## Escape Hatches

- If `close_connection()` raises exceptions on a clean connection, wrap with try/except and log warning instead of propagating
