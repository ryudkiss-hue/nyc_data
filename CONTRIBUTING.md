# Contributing

## Development Setup

1. Clone and install:

```bash
git clone https://github.com/ryudkiss-hue/nyc_data
pip install -e ".[mission]"
pip install -r requirements-dev.txt
```

2. Run tests:

```bash
python -m pytest tests/ -q --tb=short
```

3. Lint:

```bash
ruff check src/socrata_toolkit tests app
black src/socrata_toolkit tests app
```

## Data Policy (CRITICAL)

**Do NOT use synthetic, dummy, or simulated data** in application code.
All data must come from:

- Live Socrata API (NYC Open Data)
- User-uploaded files

Test fixtures are exempt — use realistic-structure DataFrames in test files.

## PR Guidelines

- Branch from `main`, name as `feat/`, `fix/`, `test/`, `docs/`
- Draft PRs are OK
- All CI checks must pass before merge
- Include test coverage for new functionality

## Adding a New Visualization

1. Create chart function in `src/socrata_toolkit/viz/`
2. Call `st.plotly_chart()` in the appropriate view file under `app/views/`
3. Guard optional deps with `HAS_X` flags
4. Add entry to the 30-chart dashboard HTML in `docs/`
