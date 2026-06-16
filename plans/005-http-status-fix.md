# Plan 005: HTTP Status Code Fix

**Finding:** health() endpoint returns incorrect HTTP status code  
**File:** `app/cloud_run.py` line 81–91  
**Severity:** HIGH  
**Effort:** Small (10 min)  
**Risk:** Low (isolated endpoint, clear fix)

## Problem

health() endpoint returns inconsistent HTTP status codes:
- Success case (line 81–85): Returns dict, FastAPI converts to HTTP 200 ✓
- Error case (line 88–91): Returns `(dict, 503)` tuple
  - FastAPI doesn't recognize tuple syntax
  - Serializes tuple as JSON array: `[{"status": "unhealthy"}, 503]`
  - Returns HTTP 200 instead of 503
- Load balancers expect HTTP 503 → treats broken pod as healthy

## Solution

Use `JSONResponse(status_code=503, content={...})` for error case to explicitly set HTTP status.

## Implementation Steps

### Step 1: Update health() endpoint in app/cloud_run.py

Replace lines 71–91 with:

```python
@app.get("/api/health")
async def health():
    """Health check endpoint."""
    try:
        conn = get_connection()
        platform = get_platform_name()

        # Test connection with a simple query
        result = conn.execute("SELECT 1 AS test").fetchall()

        return {
            "status": "healthy",
            "platform": platform,
            "connection": "OK",
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
            }
        )
```

## Verification

### Manual test

```bash
# Start app
python -m uvicorn app.cloud_run:app --port 8080 &

sleep 2

# Test healthy response
echo "=== Testing healthy response ==="
curl -v http://localhost:8080/api/health 2>&1 | grep -E "^< HTTP|status|platform"
# Expected: HTTP/1.1 200 OK
#           "status": "healthy"

# Test unhealthy response (simulate by stopping the database if possible, or just verify code path)
echo "=== Testing unhealthy response format ==="
python -c "
import json
import sys
sys.path.insert(0, '/home/user/nyc_data/src')
sys.path.insert(0, '/home/user/nyc_data')

from fastapi.responses import JSONResponse

# Verify JSONResponse produces correct status code
resp = JSONResponse(
    status_code=503,
    content={'status': 'unhealthy', 'error': 'test'}
)
print(f'Status code: {resp.status_code}')
assert resp.status_code == 503
print('✓ JSONResponse correctly sets HTTP 503')
"

# Clean up
killall uvicorn 2>/dev/null
```

### Unit test (add to tests/test_cloud_run.py if it exists)

```python
from fastapi.testclient import TestClient
from app.cloud_run import app

client = TestClient(app)

def test_health_endpoint_success():
    """Test health endpoint when connection succeeds."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "platform" in data
    assert data["connection"] == "OK"

def test_health_endpoint_error_code():
    """Test that unhealthy response returns HTTP 503."""
    # This test requires mocking get_connection to raise an error
    # Mock example (requires unittest.mock):
    from unittest.mock import patch
    
    with patch("app.cloud_run.get_connection") as mock_conn:
        mock_conn.side_effect = Exception("Connection failed")
        
        response = client.get("/api/health")
        assert response.status_code == 503  # ← THIS IS THE KEY CHECK
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "error" in data
```

## Done Criteria

- [ ] `health()` endpoint success case returns dict (HTTP 200 by default)
- [ ] `health()` endpoint error case returns `JSONResponse(status_code=503, content={...})`
- [ ] Manual curl test shows HTTP 503 status code for unhealthy response
- [ ] Imports are clean: `python -c "from app.cloud_run import app; print('OK')"`
- [ ] Docker build succeeds: `docker build -f Dockerfile.cloudbuild -t test:latest .`

## Maintenance Notes

- Verify that monitoring/alerting systems correctly handle HTTP 503 from healthcheck
- Consider adding response time metrics (CloudRun tracks this automatically)
- Future: Add detailed health info (database latency, memory usage) to response body

## Escape Hatches

- If JSONResponse import is missing, verify `from fastapi.responses import JSONResponse` is in imports
