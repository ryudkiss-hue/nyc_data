# Plan 001: Query Complexity Limits

**Finding:** OOM Vulnerability in POST /api/query  
**File:** `app/cloud_run.py` line 142  
**Severity:** CRITICAL  
**Effort:** Medium (30–45 min)  
**Risk:** Low (no new dependencies, isolated endpoint)

## Problem

The `POST /api/query` endpoint accepts arbitrary SQL with no limits:
- No max row limit → user can `SELECT * FROM complaints_311` (21.3M rows)
- Full result materializes in memory before `.head(100)` truncation
- Cloud Run default 2 GB memory → OOM kill
- No timeout → long-running queries hang pod

## Solution

Add three guards to the `execute_query()` endpoint:
1. **max_rows=1000** — Limit result set to 1000 rows max
2. **timeout=30s** — Kill queries running >30 seconds
3. **query validation** — Reject `SELECT *` on large tables

## Implementation Steps

### Step 1: Add constants and imports to app/cloud_run.py

At the top of the file (after existing imports), add:

```python
import asyncio
from time import time
```

After the root endpoint definition (around line 68), add:

```python
# Query execution limits
MAX_ROWS = 1000
QUERY_TIMEOUT_SECONDS = 30
LARGE_TABLE_THRESHOLD = 100_000  # Tables with >100K rows
LARGE_TABLES = {"complaints_311", "inspection", "violations", "street_permits", "street_construction_inspections"}
```

### Step 2: Create a query validator helper

Add this new function before the `execute_query()` endpoint (around line 140):

```python
def validate_query(sql: str) -> dict:
    """
    Validate SQL query for safety.
    
    Returns dict with 'valid' bool and 'error' message if invalid.
    """
    sql_upper = sql.strip().upper()
    
    # Reject SELECT * on known large tables
    if "SELECT *" in sql_upper:
        for table in LARGE_TABLES:
            if table.upper() in sql_upper:
                return {
                    "valid": False,
                    "error": f"SELECT * not allowed on large table '{table}'. Use SELECT column1, column2 instead."
                }
    
    return {"valid": True}
```

### Step 3: Fix the execute_query() endpoint

Replace lines 142–161 with:

```python
@app.post("/api/query")
async def execute_query(query_obj: dict):
    """Execute SQL query with safety limits."""
    try:
        sql = query_obj.get("query")
        platform = query_obj.get("platform")
        
        if not sql:
            raise ValueError("Query parameter required")
        
        # Validate query safety
        validation = validate_query(sql)
        if not validation["valid"]:
            raise ValueError(validation["error"])
        
        # Execute with timeout
        conn = get_connection(platform=platform)
        
        # Run query with timeout using asyncio
        try:
            def execute():
                return conn.execute(sql).df()
            
            loop = asyncio.get_event_loop()
            df = await asyncio.wait_for(
                loop.run_in_executor(None, execute),
                timeout=QUERY_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            raise ValueError(
                f"Query exceeded timeout of {QUERY_TIMEOUT_SECONDS} seconds. "
                "Add LIMIT clause to reduce rows."
            )
        
        # Limit output rows
        if len(df) > MAX_ROWS:
            logger.warning(f"Query returned {len(df)} rows, limiting to {MAX_ROWS}")
            df = df.head(MAX_ROWS)
        
        return {
            "rows": len(df),
            "platform": get_platform_name(),
            "data": df.to_dict(orient="records"),
            "note": f"Results limited to {MAX_ROWS} rows. Add ORDER BY + LIMIT to control output."
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Query execution error: {e}")
        raise HTTPException(status_code=500, detail="Query execution failed")
```

## Verification

### Unit test (optional, add to tests/test_cloud_run.py if it exists)

```python
def test_query_limits():
    """Verify query limits are enforced."""
    # Test 1: SELECT * rejected on large table
    response = client.post("/api/query", json={
        "query": "SELECT * FROM complaints_311"
    })
    assert response.status_code == 400
    assert "SELECT * not allowed" in response.json()["detail"]
    
    # Test 2: Valid query with limit succeeds
    response = client.post("/api/query", json={
        "query": "SELECT * FROM complaints_311 LIMIT 100"
    })
    assert response.status_code == 200
```

### Manual test

```bash
# Start the app
python -m uvicorn app.cloud_run:app --port 8080 &

# Test 1: Query with SELECT * (should fail)
curl -X POST http://localhost:8080/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM complaints_311"}' | jq .
# Expected: {"detail": "SELECT * not allowed on large table 'complaints_311'..."}

# Test 2: Query with LIMIT (should succeed)
curl -X POST http://localhost:8080/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM complaints_311 LIMIT 100"}' | jq '.rows'
# Expected: 100 (or actual row count if table has fewer)

# Test 3: Timeout test (run a slow query)
curl -X POST http://localhost:8080/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM complaints_311 LIMIT 10000000"}' | jq .
# Expected: {"detail": "Query exceeded timeout..."}
```

## Done Criteria

- [ ] `validate_query()` function added and returns correct validation errors
- [ ] `execute_query()` endpoint rejects `SELECT *` on large tables with 400 status
- [ ] `execute_query()` endpoint enforces 30-second timeout with clear error message
- [ ] `execute_query()` endpoint limits output to 1000 rows max
- [ ] Docker build succeeds: `docker build -f Dockerfile.cloudbuild -t test:latest .`
- [ ] Imports are clean: `python -c "from app.cloud_run import app; print('OK')"`

## Maintenance Notes

- If new large tables are added to Socrata, update `LARGE_TABLES` set
- Timeout value (30s) can be tuned based on Cloud Run observability
- Consider adding prometheus metrics for query execution time and row counts
- Future: Add query complexity scoring (count of joins, subqueries) instead of just SELECT * check

## Escape Hatches

- If `asyncio.wait_for()` causes issues with synchronous DuckDB, revert to simple `.execute().df()` without timeout and document the limitation
- If timeout handling breaks Dash callbacks, isolate timeout to API endpoint only (not internal get_connection calls)
