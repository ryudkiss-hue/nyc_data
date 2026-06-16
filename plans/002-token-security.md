# Plan 002: Token Exposure Security

**Finding:** MOTHERDUCK_TOKEN exposed in exception tracebacks  
**File:** `src/socrata_toolkit/platform/connection.py` line 90  
**Severity:** CRITICAL  
**Effort:** Medium (30–45 min)  
**Risk:** Low (isolated to connection module, no API changes)

## Problem

Token is embedded in f-string connection URI:
```python
conn = duckdb.connect(f"md:?motherduck_token={token}")
```

If `conn.execute("SELECT 1")` (line 92) fails, Python traceback includes the full f-string with plaintext token. Exposed in:
- Logs (CloudRun, CloudLogging)
- Error reporting (Sentry, DataDog)
- Stack traces displayed to developers
- Debug output

## Solution

Use DuckDB's secure connection API that doesn't embed token in URI. Pass token via environment or secure context.

## Implementation Steps

### Step 1: Modify _connect_motherduck() in connection.py

Replace lines 78–98 with:

```python
def _connect_motherduck(self, duckdb):
    """Connect to MotherDuck cloud."""
    token = os.getenv("MOTHERDUCK_TOKEN")
    
    if not token:
        raise ValueError(
            "MOTHERDUCK_TOKEN not set. Get from: https://console.motherduck.com/\n"
            "Set: export MOTHERDUCK_TOKEN='your_token'\n"
            "Or use DuckDB fallback: get_connection(platform='duckdb')"
        )
    
    try:
        # Use environment variable instead of embedding in connection string
        # This prevents token exposure in tracebacks
        os.environ["MOTHERDUCK_TOKEN"] = token
        
        # Connect using md: scheme, which reads token from env
        conn = duckdb.connect("md:")
        
        # Test connection
        try:
            conn.execute("SELECT 1")
        except Exception as test_error:
            # Scrub token from error message before logging/raising
            error_msg = str(test_error)
            if token in error_msg:
                error_msg = error_msg.replace(token, "***REDACTED***")
            
            raise ConnectionError(f"Failed to test MotherDuck connection: {error_msg}")
        
        self.conn = conn
        self.platform = "motherduck"
        logger.info("✓ Connected to MotherDuck")
        return conn
        
    except ConnectionError:
        raise
    except Exception as e:
        # Scrub token from any exception message
        error_msg = str(e)
        if token in error_msg:
            error_msg = error_msg.replace(token, "***REDACTED***")
        
        raise ConnectionError(f"Failed to connect to MotherDuck: {error_msg}")
```

### Step 2: Add exception scrubber utility (optional but recommended)

Add this helper function near the top of connection.py (after imports):

```python
def _scrub_sensitive_from_error(error_message: str, patterns: list = None) -> str:
    """
    Remove sensitive values from error messages.
    
    Args:
        error_message: Error message that may contain sensitive data
        patterns: List of sensitive strings to scrub (default: MOTHERDUCK_TOKEN)
    
    Returns:
        Error message with sensitive data replaced with ***REDACTED***
    """
    if patterns is None:
        patterns = []
        # Always scrub MOTHERDUCK_TOKEN
        md_token = os.getenv("MOTHERDUCK_TOKEN")
        if md_token:
            patterns.append(md_token)
    
    result = error_message
    for pattern in patterns:
        if pattern:
            result = result.replace(pattern, "***REDACTED***")
    
    return result
```

Then update error handling to use it:

```python
except Exception as e:
    error_msg = _scrub_sensitive_from_error(str(e))
    raise ConnectionError(f"Failed to connect to MotherDuck: {error_msg}")
```

## Verification

### Unit test (add to tests/test_platform_connection.py if it exists)

```python
def test_token_not_exposed_in_exceptions():
    """Verify token is scrubbed from exceptions."""
    # Simulate a connection failure
    os.environ["MOTHERDUCK_TOKEN"] = "test_secret_token_12345"
    
    manager = ConnectionManager()
    
    try:
        # This will fail because token is invalid
        manager._connect_motherduck(duckdb)
    except ConnectionError as e:
        error_msg = str(e)
        # Verify token is NOT in error message
        assert "test_secret_token_12345" not in error_msg
        assert "***REDACTED***" in error_msg or "Failed to" in error_msg
        print(f"✓ Error message is clean: {error_msg}")
```

### Manual test

```bash
# Set invalid token
export MOTHERDUCK_TOKEN="fake_token_should_not_appear_in_logs"

# Try to connect and capture error
python -c "
from socrata_toolkit.platform import get_connection
try:
    get_connection(platform='motherduck')
except Exception as e:
    error = str(e)
    if 'fake_token_should_not_appear_in_logs' in error:
        print('FAIL: Token is exposed in error')
        exit(1)
    else:
        print('✓ PASS: Token scrubbed from error:', error)
"
```

### Log inspection

```bash
# Start app with debug logging
export MOTHERDUCK_TOKEN="invalid_token_xyz123"
python -m uvicorn app.cloud_run:app 2>&1 | head -20

# Verify startup logs don't contain token
grep -i "invalid_token_xyz123" logs/app.log || echo "✓ Token not in logs"
```

## Done Criteria

- [ ] `duckdb.connect()` call changed from f-string to `duckdb.connect("md:")` using env var
- [ ] Exception handling scrubs token with "***REDACTED***" before logging/raising
- [ ] No plaintext token appears in any logged error message
- [ ] Tests confirm token is removed from exceptions
- [ ] Docker build succeeds: `docker build -f Dockerfile.cloudbuild -t test:latest .`

## Maintenance Notes

- Document that MOTHERDUCK_TOKEN must be set in environment (Cloud Run secrets do this automatically)
- If new environment variables need scrubbing (API keys, etc.), update `_scrub_sensitive_from_error()` function
- Review logs regularly to check for unintended token exposure
- Consider using structured logging (JSON) with sensitive field masking for future auditing

## Escape Hatches

- If `duckdb.connect("md:")` doesn't work without explicit token in URI, check DuckDB version compatibility
- If token still appears in DuckDB's internal logging, add suppress logic at logger level before raising
