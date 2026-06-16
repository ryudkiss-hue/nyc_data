# Plan 004: Healthcheck Endpoint Fix

**Finding:** Broken healthcheck endpoint  
**File:** `Dockerfile.cloudbuild` line 45  
**Severity:** CRITICAL  
**Effort:** Small (5 min)  
**Risk:** Low (one-line change)

## Problem

HEALTHCHECK pings `/` endpoint instead of `/api/health`:
- `/` endpoint always returns HTTP 200 with JSON message (never fails)
- `/api/health` endpoint returns HTTP 503 when database is unavailable
- Zombie containers with dead connections never auto-restart
- Load balancer treats unhealthy pods as healthy

## Solution

Change healthcheck from `/` to `/api/health` endpoint.

## Implementation Steps

### Step 1: Update Dockerfile.cloudbuild

Replace line 45–46:

**Before:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/ || exit 1
```

**After:**
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1
```

## Verification

### Test Docker build

```bash
# Build the image
docker build -f Dockerfile.cloudbuild -t nyc-toolkit:test .

# Run container with healthcheck
docker run --name test-health -d -p 8080:8080 nyc-toolkit:test

# Wait for container to start
sleep 5

# Check health status
docker inspect test-health | jq '.State.Health'
# Expected: {"Status": "healthy", "FailingStreak": 0, "SuccessStreak": 3, ...}

# Verify the healthcheck command is correct
docker inspect test-health | jq '.Config.Healthcheck.Test'
# Expected: ["CMD-SHELL", "curl -f http://localhost:8080/api/health || exit 1"]

# Clean up
docker kill test-health
docker rm test-health
```

### Manual test (before Docker)

```bash
# Start app
python -m uvicorn app.cloud_run:app --port 8080 &

sleep 2

# Test the healthcheck endpoint directly
curl -v http://localhost:8080/api/health
# Expected: HTTP 200, {"status": "healthy", "platform": "...", "connection": "OK"}

# Verify root endpoint for comparison
curl http://localhost:8080/
# Expected: HTTP 200, {"message": "NYC Sidewalk Toolkit", "visit": "/dash/"}

# Kill app
killall uvicorn
```

## Done Criteria

- [ ] Line 45–46 in Dockerfile.cloudbuild changed from `/` to `/api/health`
- [ ] Docker build succeeds: `docker build -f Dockerfile.cloudbuild -t test:latest .`
- [ ] Container healthcheck responds with HTTP 200 and `"status": "healthy"`
- [ ] Docker inspect shows correct healthcheck command

## Maintenance Notes

- Healthcheck interval (30s) and timeout (10s) are appropriate for Cloud Run
- If `/api/health` endpoint is modified in the future, ensure it still serves as a valid health signal
- Monitor Cloud Run metrics for pod restart frequency (should only restart on actual failures)

## Escape Hatches

- If `/api/health` returns 503 too frequently due to transient errors, consider adding a retry mechanism in the health endpoint before returning 503
