# Development Guide

## Coding Conventions

### Imports
```python
# Order: std lib, third-party, local
from __future__ import annotations
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from socrata_toolkit.core.client import SocrataClient
```

**Formatting**: `isort` + `black` handle this automatically.

### Type Hints
```python
def fetch_data(
    fourfour: str,
    max_rows: int = 10_000,
    cache: bool = True,
) -> pd.DataFrame:
    """Fetch dataset from Socrata."""
    pass
```

- Required on function signatures
- Optional on internal assignments
- Use `|` for unions (Python 3.10+)

### Naming
- **Functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `CONSTANT_CASE` (rarely needed; use functions instead)
- **Private**: `_leading_underscore`
- **Booleans**: `is_valid`, `has_null`, `can_fetch`

### Comments
```python
# Only explain WHY, not WHAT
# Self-documenting code is better than comments

# Workaround for Socrata API pagination bug #12345
if row_count > 50_000:
    result = paginated_fetch(fourfour, limit=50_000)
```

### Error Handling
```python
# At boundaries only (user input, external APIs)
try:
    df = client.fetch_dataframe(fourfour, max_rows)
except SocrataException as e:
    st.error(f"Failed to fetch {fourfour}: {e}")
    return pd.DataFrame()

# Not for internal code (let exceptions bubble up)
```

### Logging
```python
import logging

log = logging.getLogger(__name__)

log.info(f"Processing {len(df)} rows")
log.warning(f"Dataset {fourfour} is stale ({days_old}d old)")
log.error(f"Quality score computation failed: {e}")
```

## Project Structure

### `app/views/`
Each view is a function that renders a Streamlit page:
```python
def render_my_page() -> None:
    """Render page with title, controls, content."""
    st.title("My Page")
    st.caption("Description")
    
    # Sidebar controls
    row_limit = st.sidebar.slider("Row limit", 1000, 50000)
    
    # Main content
    if st.button("Fetch"):
        with st.spinner("Loading..."):
            df = client.fetch_dataframe("...", max_rows=row_limit)
        st.dataframe(df)
```

**Register in `app/app.py`**:
```python
if section == "my_page":
    render_my_page()
    return
```

### `src/socrata_toolkit/` (7 Pillars)
Each module is independently importable:
```python
# Good: Selective import
from socrata_toolkit.analysis import quality_report

# OK: Whole module
from socrata_toolkit import analysis

# Don't do: Internal imports
from socrata_toolkit.analysis.core import _internal_func
```

**Testing**:
```python
# Test pillar in isolation
import pytest
from socrata_toolkit.analysis import quality_report

def test_quality_report():
    df = pd.DataFrame({"col": [1, None, 3]})
    score = quality_report(df)
    assert 0 <= score.overall <= 100
```

### `tests/`
Pattern: `test_<module>.py` mirrors `src/socrata_toolkit/<module>.py`

```python
# tests/test_client.py
import pytest
from socrata_toolkit.core.client import SocrataClient

@pytest.fixture
def client():
    return SocrataClient(SocrataConfig())

def test_fetch_dataframe(client):
    df = client.fetch_dataframe("data.cityofnewyork.us", "dntt-gqwq", max_rows=10)
    assert len(df) <= 10
    assert "objectid" in df.columns
```

## Testing Strategy

### Unit Tests (test_*.py)
- Test single function/class
- Use fixtures for setup
- Mock external APIs
- Fast (<100ms)

```python
def test_quality_report_empty_df():
    df = pd.DataFrame()
    score = quality_report(df)
    assert score.overall == 0
```

### Integration Tests (test_*_integration.py, in CI)
- Test against real databases (PostgreSQL, MongoDB)
- Full workflow execution
- Slower but comprehensive

```python
def test_analyst_workflow_end_to_end(postgres_client):
    wf = AnalystWorkflow(name="test")
    wf.add_step("fetch", dataset="inspection")
    wf.add_step("export", path="/tmp/test.xlsx")
    result = wf.execute()
    assert result.success
```

### Coverage Tests (test_*_coverage.py)
- Target 45% gate for `src/socrata_toolkit/{analyst,core}`
- Verify key paths are exercised

```bash
pytest tests/ --cov --cov-report=term-missing
# Target: >=45% for analyst/, core/
```

### Before Commit
```bash
# Local
ruff check src/ app/ tests/
black --check src/ app/ tests/
pytest tests/ -q --tb=short

# Or use pre-commit hook (automatic on git push)
```

## Common Patterns

### Caching with Streamlit
```python
@st.cache_data(ttl=86400)  # 24 hours
def load_dataset(fourfour: str) -> pd.DataFrame:
    return client.fetch_dataframe("data.cityofnewyork.us", fourfour)

# On reruns, returns cached value (no API call)
df = load_dataset("dntt-gqwq")
```

### Session State Persistence
```python
# Store drill-down state
if "drill_level" not in st.session_state:
    st.session_state["drill_level"] = "city"

if st.button("Drill to borough"):
    st.session_state["drill_level"] = "borough"
    st.rerun()

st.write(f"Current level: {st.session_state['drill_level']}")
```

### Error Recovery
```python
try:
    df = client.fetch_dataframe(fourfour)
except Exception as e:
    st.error(f"Error: {e}")
    st.info("Using cached data from yesterday")
    df = load_cached_version(fourfour)  # Fallback
    
st.dataframe(df)
```

### Vectorized Operations (Pandas)
```python
# Good: Vectorized
df["score_category"] = pd.cut(df["score"], bins=[0, 30, 50, 100], labels=["critical", "low", "ok"])
df["age_days"] = (datetime.now() - df["created_date"]).dt.days

# Avoid: Loops
# for idx, row in df.iterrows():  ← SLOW
#     df.loc[idx, "score_category"] = categorize(row["score"])
```

## Performance Tips

### Data Loading
```python
# Good: Limit rows upfront
df = client.fetch_dataframe(fourfour, max_rows=10_000)

# Avoid: Fetch all then slice
# df = client.fetch_dataframe(fourfour)  # 398K rows
# df = df.head(10_000)
```

### Filtering
```python
# Good: Filter early
df[df["score"] > 50].groupby("borough").sum()

# Avoid: Process all then filter
# df.groupby("borough").sum().query("score > 50")
```

### Caching
```python
# Good: Cache expensive computations
@st.cache_data
def quality_report(fourfour: str) -> QualityScore:
    df = client.fetch_dataframe(fourfour)
    return compute_quality_score(df)

# Avoid: Recompute on every rerun
# Every st.rerun() triggers fresh fetch + computation
```

## Debugging

### Print Debugging
```python
import logging

log = logging.getLogger(__name__)
log.debug(f"df shape: {df.shape}, dtypes: {df.dtypes}")

# Enable in tests
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Streamlit Debug
```python
# Expand sidebar to see rerun counts, cache hits
st.set_page_config(initial_sidebar_state="expanded")

# Use st.write() to inspect values
st.write(f"Debug: {variable}")
st.write(df.info())
```

### Test Debugging
```bash
# Run single test with print output
pytest tests/test_client.py::test_fetch -v -s

# Run with pdb on failure
pytest tests/ --pdb --pdbcls=IPython.terminal.debugger:TerminalPdb
```

## Dependencies

### Adding a Package
1. Update `pyproject.toml` (or `requirements.txt`)
2. Add to correct group (extras if optional)
3. Update `tests/test_import_shims.py` if conditional
4. Test locally: `pip install -e ".[group]"`
5. Run `pytest tests/ -q` to verify

### Optional Dependencies
```python
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

# Use with flag
if HAS_ANTHROPIC:
    client = anthropic.Anthropic()
else:
    st.info("Install [llm] extra for Claude integration")
```

## Code Review Checklist

Before submitting PR:
- [ ] `ruff check` passes (linting)
- [ ] `black` formatted (style)
- [ ] `pytest` passing (tests)
- [ ] ≥45% coverage for modified code in `analyst/` or `core/`
- [ ] Imports sorted (`isort`)
- [ ] Type hints on function signatures
- [ ] Docstrings on public functions (1-line OK)
- [ ] No hardcoded magic numbers (use constants/config)
- [ ] Error handling at system boundaries only
- [ ] Commit message references session URL

---

**See `docs/API.md` for Python API reference and `CONTRIBUTING.md` for PR workflow.**
