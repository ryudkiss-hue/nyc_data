# Plan 002: MotherDuck token no longer interpolated into SQL SET statement

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 4343044..HEAD -- src/socrata_toolkit/core/duckdb_store.py`
> If the file changed since this plan was written, compare the "Current state"
> excerpt against the live code before proceeding; on a mismatch, treat it as
> a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (can run in parallel with 001)
- **Category**: security
- **Planned at**: commit `4343044`, 2026-06-12

## Why this matters

`src/socrata_toolkit/core/duckdb_store.py` line 171 passes the MotherDuck token
into a DuckDB `SET` statement via Python f-string interpolation:
`SET motherduck_token='{self.motherduck_token}'`. This means the token value
appears verbatim in the SQL string, which DuckDB may include in query logs,
error messages, or `EXPLAIN` output. Anyone with access to the DuckDB log file
(a common shared path like `data/local_db/`) or an exception stack trace can
harvest the token. DuckDB 0.10+ reads `MOTHERDUCK_TOKEN` from the environment
automatically, making the `SET` statement unnecessary.

## Current state

**File**: `src/socrata_toolkit/core/duckdb_store.py`

The relevant block (lines 165–177) currently reads:

```python
# duckdb_store.py:165-177
if self.motherduck_token and not connection_path.startswith("md:"):
    # We connect to local but will enable MD extension
    self._conn = duckdb.connect(connection_path, read_only=is_read_only)
    try:
        self._conn.execute(f"SET motherduck_token='{self.motherduck_token}';")  # ← line 171
        self._conn.execute("INSTALL motherduck;")
        self._conn.execute("LOAD motherduck;")
    except Exception as exc:
        logger.warning("Could not initialize MotherDuck extension: %s", exc)
else:
    self._conn = duckdb.connect(connection_path, read_only=is_read_only)
```

The class reads `self.motherduck_token` from its constructor; trace it to find
where it is set (look for `__init__` in this file — it likely reads
`os.environ.get("MOTHERDUCK_TOKEN")`).

**Repo convention for environment variables**: All env vars are read via
`os.environ.get("KEY")` or `python-dotenv`. See `src/socrata_toolkit/core/config.py`
for the canonical pattern used elsewhere in the project.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Lint | `ruff check src/socrata_toolkit/core/duckdb_store.py` | `All checks passed!` |
| Run related tests | `pytest tests/test_duckdb_store_coverage.py tests/test_duckdb_pipeline.py -q` | all pass |
| Grep for SET pattern | `grep -n "SET motherduck_token" src/socrata_toolkit/core/duckdb_store.py` | no output after fix |

## Scope

**In scope**:
- `src/socrata_toolkit/core/duckdb_store.py` — remove the `SET` statement, set env var before connect

**Out of scope**:
- Any other file — the token is only consumed in this one location
- `tests/` — existing tests should continue to pass without modification
- `pyproject.toml`, `.env.example` (`.env.example` update for `MOTHERDUCK_TOKEN` is handled by Plan 001)

## Git workflow

- Branch: `fix/002-motherduck-token-env`
- Commit: `fix: pass MotherDuck token via environment variable instead of SQL SET`

## Steps

### Step 1: Locate the constructor and understand token sourcing

In `src/socrata_toolkit/core/duckdb_store.py`, find the class `__init__` method
and identify:
1. Where `self.motherduck_token` is assigned (it should read from
   `os.environ.get("MOTHERDUCK_TOKEN")` or similar).
2. Whether `self.motherduck_token` is used anywhere else in the file besides
   line 171.

**Verify**: `grep -n "motherduck_token" src/socrata_toolkit/core/duckdb_store.py`
→ list all usages. Confirm line 171 is the only `SET` usage.

### Step 2: Replace SET statement with environment-variable-based connection

Replace the block at lines 165–177 with this pattern:

```python
if self.motherduck_token and not connection_path.startswith("md:"):
    # DuckDB 0.10+ reads MOTHERDUCK_TOKEN from the environment automatically.
    # Set it before connecting so the extension picks it up without embedding
    # the token value in a SQL string (which can appear in logs/traces).
    import os
    os.environ.setdefault("MOTHERDUCK_TOKEN", self.motherduck_token)
    self._conn = duckdb.connect(connection_path, read_only=is_read_only)
    try:
        self._conn.execute("INSTALL motherduck;")
        self._conn.execute("LOAD motherduck;")
    except Exception as exc:
        logger.warning("Could not initialize MotherDuck extension: %s", exc)
else:
    self._conn = duckdb.connect(connection_path, read_only=is_read_only)
```

`os.environ.setdefault` is used (not `os.environ[...] = ...`) so that an
already-set environment variable is not overwritten by the in-memory value.

**Verify**: `grep -n "SET motherduck_token" src/socrata_toolkit/core/duckdb_store.py`
→ no output (the SET statement is gone).

### Step 3: Run lint and tests

```bash
ruff check src/socrata_toolkit/core/duckdb_store.py
pytest tests/test_duckdb_store_coverage.py tests/test_duckdb_pipeline.py -q
```

Both must pass before committing.

### Step 4: Commit

```bash
git add src/socrata_toolkit/core/duckdb_store.py
git commit -m "fix: pass MotherDuck token via environment variable instead of SQL SET"
```

## Test plan

No new tests are required — the change is a one-liner replacement in a private
method. The existing `tests/test_duckdb_store_coverage.py` and
`tests/test_duckdb_pipeline.py` cover DuckDB connection initialization; they
must continue to pass.

If `MOTHERDUCK_TOKEN` is not set in the test environment (expected), the `if`
branch is never entered and tests remain unaffected.

## Done criteria

- [ ] `grep -n "SET motherduck_token" src/socrata_toolkit/core/duckdb_store.py` → no output
- [ ] `ruff check src/socrata_toolkit/core/duckdb_store.py` → `All checks passed!`
- [ ] `pytest tests/test_duckdb_store_coverage.py tests/test_duckdb_pipeline.py -q` → all pass
- [ ] No files outside the in-scope list are modified (`git diff --name-only`)
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report if:

- Line 171 in the live file does not match the excerpt above (drift — the code
  may have already been partially fixed or refactored).
- `self.motherduck_token` is used in additional `SET` or `EXECUTE` calls beyond
  line 171 — each must be evaluated separately.
- The DuckDB version in use is `< 0.10` (check `import duckdb; print(duckdb.__version__)`)
  and does not support environment-variable token injection — report before
  proceeding.

## Maintenance notes

- If `self.motherduck_token` is ever changed to accept a value from a
  non-environment source (e.g., a config file or database), the `setdefault`
  call must be reviewed — it only sets the env var if not already present,
  so a config-file token would be silently ignored if `MOTHERDUCK_TOKEN` is
  already in the environment.
- DuckDB's MotherDuck extension API changes with each major release; if
  `INSTALL motherduck` starts failing, check the DuckDB changelog for new
  connection patterns.
