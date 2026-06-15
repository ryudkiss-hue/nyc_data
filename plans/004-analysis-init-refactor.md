# Plan 004: analysis/__init__.py exports are governed, explicit, and no longer cause test collection failures

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 4343044..HEAD -- src/socrata_toolkit/analysis/__init__.py src/socrata_toolkit/analysis.py`
> If either file changed, compare the "Current state" excerpts before proceeding.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: tech-debt
- **Planned at**: commit `4343044`, 2026-06-12

## Why this matters

During a single CI-fixing session (commits `70ad660` → `4343044`), four
consecutive pushes were needed to resolve test collection failures — each
exposing another missing export from `src/socrata_toolkit/analysis/__init__.py`.
The root cause is that the file uses three conflicting import mechanisms (eager
top-level imports, `try/except ImportError` with silent `None` assignment, and
`_legacy_import()` at the bottom that silently skips missing symbols). When a
test imports `from socrata_toolkit.analysis import Expectation`, there is no
single place to look to know if that export exists.

Additionally, `src/socrata_toolkit/analysis.py` (1,669 lines) is a parallel
re-export hub that shadows the `analysis/` package, creating confusion about
which is canonical.

This plan consolidates all re-exports into one explicit, auditable block in
`analysis/__init__.py`, eliminates the `_legacy_import` fallback for symbols
that exist unconditionally, and documents what is intentionally optional.

## Current state

**Two parallel re-export hubs exist:**
- `src/socrata_toolkit/analysis.py` — 1,669-line monolith, the *original* re-export hub
- `src/socrata_toolkit/analysis/__init__.py` — the *package* init, ~300 lines, three import mechanisms

When Python resolves `import socrata_toolkit.analysis`, it uses the **package**
(`analysis/__init__.py`) — the standalone `analysis.py` is a sibling module, not
the same thing. Tests import from the package. The monolith `analysis.py` is
currently unused by tests (Python prefers the package), but its existence
confuses contributors.

**Three import mechanisms in `analysis/__init__.py`:**

1. **Eager top-level** (lines 8–135): direct imports, some wrapped in
   `try/except ImportError` that assign `None` on failure (silently hides broken deps).

2. **`__all__` list** (line 136–239): declares public API but is not enforced —
   symbols in `__all__` that aren't actually imported cause `AttributeError` at
   runtime, not at import time.

3. **`_legacy_import()` fallback** (lines 252–300+): runtime `importlib` loader
   that silently skips symbols if the source module can't be found. Used for 20+
   symbols including `Anomaly`, `Expectation`, `QualityRule`, `ValidationResult`,
   etc.

**The problem with `_legacy_import`**: if `socrata_toolkit.quality.expectations`
exists (it does — confirmed at `src/socrata_toolkit/quality/expectations.py`),
then `Expectation` should be a hard import, not a silent fallback. Silent fallbacks
hide typos and renamed modules.

**Repo convention for imports**: Hard imports at the top of the file, wrapped in
`try/except ImportError` only for genuinely optional heavy dependencies (e.g.,
`pymc`, `geopandas`). See `src/socrata_toolkit/analysis/__init__.py` lines 8–15
for the existing pattern for optional imports (`BayesianInferenceResult = None`).

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Lint | `ruff check src/socrata_toolkit/analysis/__init__.py` | `All checks passed!` |
| Syntax check | `python3 -c "import ast; ast.parse(open('src/socrata_toolkit/analysis/__init__.py').read()); print('OK')"` | `OK` |
| Import smoke test | `PYTHONPATH=src python3 -c "import socrata_toolkit.analysis; print('OK')"` | `OK` (may warn about missing optional deps, that's fine) |
| Full test run | `pytest tests/ -q --tb=short --ignore=tests/test_interactive_explore.py --ignore=tests/test_studio.py --ignore=tests/test_i18n.py --ignore=tests/test_visualization.py --ignore=tests/test_docker_environment.py --ignore=tests/test_improvements.py -x` | no collection errors |

## Scope

**In scope**:
- `src/socrata_toolkit/analysis/__init__.py` — the only file to modify
- `src/socrata_toolkit/analysis.py` — rename to `analysis_legacy.py` (Step 5, optional but recommended)

**Out of scope**:
- Any file in `src/socrata_toolkit/quality/` — do not modify source modules
- Any file in `tests/` — do not modify test files
- `src/socrata_toolkit/analysis/` subdirectory modules (metrics.py, profiling.py, etc.)

## Git workflow

- Branch: `refactor/004-analysis-init-exports`
- Commit after each step so the codebase is never broken mid-plan
- Commit style: `refactor: <description>`

## Steps

### Step 1: Audit which _legacy_import symbols actually exist

For each symbol loaded by `_legacy_import` at the bottom of `__init__.py`,
verify the source module exists:

```bash
python3 -c "
import sys; sys.path.insert(0, 'src')
checks = [
    ('socrata_toolkit.quality.anomalies', 'Anomaly'),
    ('socrata_toolkit.quality.expectations', 'Expectation'),
    ('socrata_toolkit.quality.expectations', 'ExpectationSuite'),
    ('socrata_toolkit.quality.expectations', 'ExpectationType'),
    ('socrata_toolkit.quality.expectations', 'SeverityLevel'),
    ('socrata_toolkit.quality.profiler', 'ProfileGenerator'),
    ('socrata_toolkit.quality.reports', 'QualityReportGenerator'),
    ('socrata_toolkit.quality.rules', 'QualityRule'),
    ('socrata_toolkit.quality.rules', 'RuleMode'),
    ('socrata_toolkit.quality.rules', 'RuleSeverity'),
    ('socrata_toolkit.quality.rules', 'RuleViolations'),
    ('socrata_toolkit.quality.integration', 'QualityValidator'),
    ('socrata_toolkit.quality.sla', 'MetricType'),
    ('socrata_toolkit.quality.sla', 'SLADefinition'),
    ('socrata_toolkit.quality.validator', 'ValidationResult'),
    ('socrata_toolkit.quality.validator', 'ValidationResultsAggregator'),
]
import importlib
for mod, name in checks:
    try:
        m = importlib.import_module(mod)
        status = 'OK' if hasattr(m, name) else 'MISSING attr'
    except Exception as e:
        status = f'IMPORT ERROR: {e}'
    print(f'{mod}.{name}: {status}')
"
```

**Expected**: all lines print `OK`. Any line printing `IMPORT ERROR` or
`MISSING attr` is a STOP condition — report it before proceeding.

### Step 2: Replace _legacy_import calls with explicit hard imports

At the bottom of `src/socrata_toolkit/analysis/__init__.py`, replace all
`_legacy_import(...)` calls for symbols confirmed in Step 1 with explicit
imports. Group them by source module:

```python
# --- Quality module re-exports (explicit, not lazy) ---
from ..quality.anomalies import Anomaly
from ..quality.expectations import (
    Expectation,
    ExpectationSuite,
    ExpectationType,
    SeverityLevel,
    create_311_complaints_suite,
    create_sidewalk_inspections_suite,
)
from ..quality.profiler import ProfileGenerator
from ..quality.reports import QualityReportGenerator
from ..quality.rules import (
    QualityRule,
    RuleMode,
    RuleSeverity,
    RuleViolations,
    create_311_complaints_rules,
    create_sidewalk_rules,
)
from ..quality.integration import QualityValidator
from ..quality.sla import MetricType, SLADefinition, create_standard_slas
from ..quality.validator import ValidationResult, ValidationResultsAggregator
```

Keep the remaining `_legacy_import` calls **only** for symbols whose source
module is genuinely optional or may not exist (e.g., `..engineering.cost_estimator`,
`..relevance`, `..reports.analyst`). Add a comment explaining why each remaining
`_legacy_import` is intentionally fallible:

```python
# Optional modules — may not be installed in minimal environments
_legacy_import("..engineering.cost_estimator", "estimate_costs")
_legacy_import("..relevance", "build_weighted_rank_sql", "websearch_to_tsquery_sql")
```

Remove the `_legacy_import` function definition itself if no calls remain
(it's a dead helper). If calls remain, keep it.

**Verify after this step**: `python3 -c "import ast; ast.parse(open('src/socrata_toolkit/analysis/__init__.py').read()); print('OK')"` → `OK`

**Commit**: `refactor: replace _legacy_import fallbacks with explicit quality module imports`

### Step 3: Fix silent None assignments for required symbols

Scan `analysis/__init__.py` for `try/except ImportError` blocks that assign
`= None` to symbols. For each one, decide:

- **Truly optional** (e.g., `BayesianInferenceResult` — requires `pymc`):
  keep `= None` but add a type comment: `# type: ignore[assignment,misc]`
- **Should always be present** (e.g., any symbol from `analysis/metrics.py`,
  `analysis/profiling.py`): convert to a hard import with no try/except.

To identify which are truly optional, check if the source module imports a
heavy dependency at its top level:

```bash
head -5 src/socrata_toolkit/analysis/bayesian.py     # will show: import pymc
head -5 src/socrata_toolkit/analysis/metrics.py      # no heavy optional dep
```

**Verify**: `ruff check src/socrata_toolkit/analysis/__init__.py` → `All checks passed!`

**Commit**: `refactor: convert required optional-None imports to hard imports`

### Step 4: Add DriftReport to __all__

The `__all__` list (lines 136–239) does not include `DriftReport` (which was
added in a recent fix commit). Add it:

```python
__all__ = [
    ...
    "DriftReport",
    ...
]
```

Also add all symbols added via the new explicit imports in Step 2 that are not
already in `__all__`:
`Expectation`, `ExpectationSuite`, `ExpectationType`, `SeverityLevel`,
`ProfileGenerator`, `QualityReportGenerator`, `QualityRule`, `RuleMode`,
`RuleSeverity`, `RuleViolations`, `QualityValidator`, `SLADefinition`,
`ValidationResult`, `ValidationResultsAggregator`, `create_311_complaints_rules`,
`create_311_complaints_suite`, `create_sidewalk_inspections_suite`,
`create_sidewalk_rules`, `create_standard_slas`.

**Verify**: `python3 -c "import socrata_toolkit.analysis as a; print(sorted(a.__all__))"` (with `PYTHONPATH=src`) → prints a sorted list with no duplicates.

**Commit**: `refactor: sync __all__ with explicit imports in analysis/__init__.py`

### Step 5: (Recommended) Rename analysis.py to clarify it is a legacy shim

`src/socrata_toolkit/analysis.py` (1,669 lines) is never imported by tests
(the `analysis/` package takes precedence). Renaming it removes the confusion:

```bash
git mv src/socrata_toolkit/analysis.py src/socrata_toolkit/analysis_legacy.py
```

Then verify no code imports `from socrata_toolkit.analysis_legacy import ...` —
it should be zero:

```bash
grep -rn "from socrata_toolkit.analysis_legacy" src/ tests/ app/
```

→ should return nothing (the rename is safe because nothing imported `analysis.py` directly;
Python was already resolving to the package).

**Verify**: `pytest tests/ -q --tb=short --ignore=tests/test_interactive_explore.py --ignore=tests/test_studio.py --ignore=tests/test_i18n.py --ignore=tests/test_visualization.py --ignore=tests/test_docker_environment.py --ignore=tests/test_improvements.py 2>&1 | head -5`
→ no collection errors (the same 3820+ tests that were passing before still pass).

**Commit**: `refactor: rename analysis.py → analysis_legacy.py to avoid shadowing the package`

## Test plan

No new tests to write. The verification is that the test suite previously
passing (3,820 tests) continues to pass with zero collection errors after this
refactor.

Run the full suite:
```bash
pytest tests/ -q --tb=short \
  --ignore=tests/test_interactive_explore.py \
  --ignore=tests/test_studio.py \
  --ignore=tests/test_i18n.py \
  --ignore=tests/test_visualization.py \
  --ignore=tests/test_docker_environment.py \
  --ignore=tests/test_improvements.py
```

Expected: 0 collection errors, same pass/fail counts as before this plan.

## Done criteria

- [ ] `grep -c "_legacy_import" src/socrata_toolkit/analysis/__init__.py` ≤ 3 (only truly optional symbols remain)
- [ ] `python3 -c "import ast; ast.parse(open('src/socrata_toolkit/analysis/__init__.py').read()); print('OK')"` → `OK`
- [ ] `ruff check src/socrata_toolkit/analysis/__init__.py` → `All checks passed!`
- [ ] Pytest collection: `pytest tests/ --collect-only -q 2>&1 | grep "ERROR\|error"` → no output
- [ ] `src/socrata_toolkit/analysis.py` renamed to `analysis_legacy.py` (or documented as intentional if left)
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report if:

- Step 1 audit shows any symbol returning `IMPORT ERROR` — the source module may
  have been moved or deleted; do not convert those to hard imports.
- Any step's pytest run introduces new collection errors not present before.
- `analysis.py` is found to be directly imported somewhere:
  `grep -rn "from socrata_toolkit.analysis import\|import socrata_toolkit.analysis" src/ app/`
  — if the monolith is in use, do not rename it without tracing all callers.

## Maintenance notes

- Going forward: all new symbols in `src/socrata_toolkit/quality/` that need
  to be accessible as `socrata_toolkit.analysis.X` must be added as **explicit
  hard imports** in `__init__.py` at the time they are created — not via
  `_legacy_import`. The `_legacy_import` pattern is reserved for genuinely
  optional modules (those that import optional heavy deps like pymc, langchain).
- The `__all__` list must be kept in sync with the explicit imports. A CI check
  (`ruff` rule `F401` with `ignore = ["F401"]` disabled for `__init__.py`) can
  enforce that all imported names appear in `__all__`.
- `analysis_legacy.py` should be deleted (not just renamed) once all code that
  was re-exporting through it has been verified to use the package instead.
  Track this in a follow-up task.
