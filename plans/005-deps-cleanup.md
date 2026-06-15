# Plan 005: Unused optional dependencies removed and redis moved to optional

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 4343044..HEAD -- pyproject.toml requirements.txt requirements-dev.txt`
> If any in-scope file changed, compare the "Current state" excerpts before proceeding.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: migration
- **Planned at**: commit `4343044`, 2026-06-12

## Why this matters

`pyproject.toml` lists several dependencies that are never imported anywhere in
`src/` or `app/`:

- `mapie`, `dowhy`, `numba`, `opendp`, `agentql`, `playwright` are listed in
  `[tool.poetry.extras]` under the `mission` extra — meaning every
  `pip install -e ".[mission]"` (which CI does) pulls them. `playwright` alone
  downloads ~200 MB of browser binaries. None of these are imported in any
  `.py` file.

- `redis >= 5.0.0` is declared as a **core** (non-optional) dependency but is
  only imported in `app/services/cache_service.py` (the Dash cache layer). The
  `app/` layer is not part of the core library and is itself optional. Every
  `pip install nyc-dot-socrata-toolkit` pulls Redis into CLI-only environments.

Removing these reduces install time by minutes, cuts CI time, and makes the
dependency manifest honest about what the core toolkit actually requires.

## Current state

**`pyproject.toml` — relevant sections**:

```toml
# [tool.poetry.dependencies] — non-optional (lines 13–18):
redis = ">=5.0.0"         # line 16 — core dep, only used in app/services/cache_service.py
msgpack = ">=1.0.0"       # line 17 — keep (used in caching/serialization)
zstandard = ">=0.23.0"    # line 18 — keep (compression)

# Optional heavy deps (lines 57–63):
mapie = {version = ">=0.8", optional = true}       # line 57 — 0 imports in src/
dowhy = {version = ">=0.11", optional = true}      # line 58 — 0 imports in src/
sentence-transformers = ...                         # line 59 — keep (used in semantic search)
numba = {version = ">=0.57", optional = true}      # line 60 — 0 imports in src/
opendp = {version = ">=0.9", optional = true}      # line 61 — 0 imports in src/
agentql = {version = ">=1.19.0", optional = true}  # line 62 — 0 imports in src/ or app/
playwright = {version = ">=1.40", optional = true} # line 63 — 0 imports in src/ or app/

# mission extras (line 84) — currently includes:
# "mapie", "dowhy", ..., "numba", "opendp", "agentql", "playwright"
```

**`app/services/cache_service.py` line 1**: `import redis` — sole consumer of the
`redis` package. This file is only used by the Dash app layer.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Confirm redis not in src/ | `grep -rn "^import redis\|^from redis" src/` | no output |
| Confirm mapie/dowhy not in repo | `grep -rn "import mapie\|import dowhy\|import numba\|import opendp\|import agentql\|import playwright" src/ app/` | no output |
| Lint | `ruff check src/ tests/ app/` | `All checks passed!` |
| Install test | `pip install -e . --dry-run 2>&1 \| grep "redis"` | no redis listed (after change) |
| Tests | `pytest tests/test_config.py tests/test_client.py tests/test_cache_service.py -q` | all pass |

## Scope

**In scope**:
- `pyproject.toml` — move `redis` to optional, remove 6 unused deps from `mission` extra
- `requirements.txt` (if it exists and lists these packages) — update accordingly
- `requirements-dev.txt` — no change needed unless redis is there (check first)

**Out of scope**:
- `app/services/cache_service.py` — do not change the import; the package will
  still be available when `.[mission]` or `.[cache]` is installed
- Any `.py` source file
- `poetry.lock` / `uv.lock` — these regenerate automatically with `poetry lock`

## Git workflow

- Branch: `chore/005-deps-cleanup`
- Commit: `chore: remove unused optional deps and make redis optional`

## Steps

### Step 1: Confirm nothing actually imports the packages to be removed

Run the grep from the commands table to be certain:

```bash
grep -rn "import mapie\|import dowhy\|import numba\|import opendp\|import agentql\|import playwright" src/ app/ tests/
grep -rn "^import redis\|^from redis" src/
```

**Expected**: all return no output.

**If any return output**: that package is actually used — remove it from your
removal list and note it in the STOP conditions.

### Step 2: Move redis to optional in pyproject.toml

Change line 16 of `pyproject.toml` from:

```toml
redis = ">=5.0.0"
```

to:

```toml
redis = {version = ">=5.0.0", optional = true}
```

Add a new extras group `cache` (insert after the existing extras, before
`[tool.poetry.dev-dependencies]` or equivalent):

```toml
cache = ["redis"]
```

Also add `redis` to the `mission` extra (since the Dash app uses it):

In the `mission = [...]` list (line 84), add `"redis"` to the list.

**Verify**: `python3 -c "import tomllib; d = tomllib.load(open('pyproject.toml','rb')); print(d['tool']['poetry']['extras']['cache'])"` → `['redis']`

### Step 3: Remove the 6 unused optional deps from pyproject.toml

Remove these lines entirely from `[tool.poetry.dependencies]`:

```toml
mapie = {version = ">=0.8", optional = true}
dowhy = {version = ">=0.11", optional = true}
numba = {version = ">=0.57", optional = true}
opendp = {version = ">=0.9", optional = true}
agentql = {version = ">=1.19.0", optional = true}
playwright = {version = ">=1.40", optional = true}
```

In the `mission = [...]` extras list (line 84), remove
`"mapie"`, `"dowhy"`, `"numba"`, `"opendp"`, `"agentql"`, `"playwright"` from
the list. Keep all other entries.

**Verify**: `grep -c "mapie\|dowhy\|numba\|opendp\|agentql\|playwright" pyproject.toml`
→ should return 0.

### Step 4: Check requirements.txt for affected packages

```bash
grep -i "mapie\|dowhy\|numba\|opendp\|agentql\|playwright\|redis" requirements.txt 2>/dev/null
```

If any are present, remove them. If `requirements.txt` doesn't exist, skip.

### Step 5: Run lint and tests

```bash
ruff check src/ tests/ app/
pytest tests/test_config.py tests/test_client.py tests/test_cache_service.py -q
```

Both must pass.

### Step 6: Commit

```bash
git add pyproject.toml requirements.txt  # omit requirements.txt if no change
git commit -m "chore: remove unused optional deps and make redis optional"
```

## Test plan

No new tests required. The existing `tests/test_cache_service.py` exercises
`app/services/cache_service.py` (which imports `redis`); it must pass after
the change (confirming `redis` is still available when the `.[mission]` extra
is installed, which CI does).

**Verify**: `pytest tests/test_cache_service.py -q` → all pass.

## Done criteria

- [ ] `grep -c "mapie\|dowhy\|numba\|opendp\|agentql\|playwright" pyproject.toml` → 0
- [ ] `grep "^redis" pyproject.toml` → shows `redis = {version = ..., optional = true}`
- [ ] `grep "\"cache\"" pyproject.toml` → shows `cache = ["redis"]` extras entry
- [ ] `ruff check src/ tests/ app/` → `All checks passed!`
- [ ] `pytest tests/test_cache_service.py -q` → all pass
- [ ] No files outside the in-scope list are modified
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report if:

- Step 1 grep finds any of the packages actually imported — do not remove it
  until the usage is traced.
- `app/services/cache_service.py` imports `redis` via a conditional
  `try/except ImportError` (meaning it already handles redis being absent) —
  in that case moving redis to optional is lower risk but still correct.
- `pyproject.toml` has a `[tool.poetry.dependencies]` group that uses a
  different syntax than shown in the excerpts (e.g., TOML inline tables vs
  multi-line) — adapt the edit to match the existing style.

## Maintenance notes

- If `playwright` or `agentql` are ever needed (future web automation feature),
  re-add them to `pyproject.toml` as a named optional extra (e.g., `automation`)
  rather than bundling them into `mission` — this keeps the standard install lightweight.
- `numba` is a JIT compiler that can accelerate numerical code significantly;
  if spatial or analysis hotspots are profiled and numba is chosen for
  acceleration, add it back to a new `fast` extras group.
- After this change, users who previously did `pip install -e ".[mission]"` will
  automatically get `redis` because it's added to that extra. No user-facing
  breaking change.
