# GitHub Actions CI/CD Architecture

## Overview

The NYC DOT SIM Toolkit uses GitHub Actions to validate code quality, run tests across Python versions, and ensure the **Dash Mission Control** dashboard and analysis toolkit are production-ready.

**Primary CI/CD Workflow:** [`.github/workflows/nyc-toolkit-ci.yml`](../.github/workflows/nyc-toolkit-ci.yml)  
**Trigger:** Every push/PR to `main`  
**Expected Result:** **5 checks pass** (3 Python versions + readiness + Docker build)

---

## Active Workflow: `nyc-toolkit-ci.yml`

This workflow validates the entire toolkit stack: Dash UI, analysis modules, data quality, visualizations, and CLI.

### Check Breakdown

| Check | Purpose | What Gets Tested |
|-------|---------|------------------|
| **Tests (Python 3.10)** | Core functionality | `pytest tests/` with all analysis/quality/viz modules + Dash callbacks |
| **Tests (Python 3.11)** | Primary version | Full test suite (4100+ tests) including data quality, metrics, visualization builders |
| **Tests (Python 3.12)** | Future compatibility | Ensures code works on upcoming Python versions |
| **Readiness Report** | Quality gate | `socrata readiness` checks completeness, validity, consistency, timeliness |
| **Docker Build (mission)** | Deployment validation | Builds Dockerfile `mission` target (Dash/FastAPI at port 8011, no push to registry) |

### Installation & Linting

```yaml
# For all checks:
pip install -e ".[mission,xlsx,postgres]"  # All Dash + analysis dependencies
ruff check src/socrata_toolkit tests app/  # Lint: E,F,W,I,UP,B rules
```

**What Ruff Checks:**
- `src/socrata_toolkit/` — Analysis, quality, visualization, spatial modules
- `tests/` — Test suite (unit + integration tests)
- `app/` — Dash app code (dash_app.py, callbacks, components, layouts)

### Test Coverage

**4100+ tests** across three focus areas:

#### 1. **Data Analysis & Metrics** (65 modules)
- Bayesian inference, A/B testing, forecasting, clustering
- Domain workflows (complaint/dismissal/hotspot/velocity/ramp analysis)
- Sentiment analysis, NLP, semantic search
- Change point detection, anomaly detection
- SLA compliance tracking
- **Tests:** `tests/test_analysis*.py` (8+ test files)

#### 2. **Data Quality & Validation** (16 modules)
- Data profiling (null rates, duplicates, drift)
- Schema validation, domain rules, freshness tracking
- Quality scoring (completeness, validity, consistency, timeliness)
- Anomaly detection, data reconciliation
- Great Expectations integration
- **Tests:** `tests/test_quality*.py` (8 dedicated test files)

#### 3. **Visualization & Charts** (17 modules)
- Plotly interactive charts (histogram, bar, correlation, time-series, box plot)
- Statistical visualizations (CUSUM, Bayesian credible intervals, KMeans, survival curves)
- GIS & spatial mapping (Scattermapbox, DBSCAN, TSP optimization)
- Dashboard building, chart recommendation
- Accessibility features, Mantine theming
- **Tests:** `tests/test_*_visualization.py`, `tests/test_*_charts.py`

#### 4. **Dash Mission Control** (Primary UI)
- Dash app initialization (app/dash_app.py)
- Callback handlers (app/callbacks/*.py) — analytics, gis, export, navigation
- Component rendering (app/components/*.py) — filters, KPI cards, spatial maps
- FastAPI backend integration
- Mantine UI theming
- **Tests:** `tests/test_callback_registry.py`, `tests/test_gis_callbacks.py`, `tests/test_mission_control.py`

---

## Readiness Report Check

```bash
socrata readiness
```

**What it validates:**
- ✅ **Completeness** (35%) — All required modules present, imports resolve
- ✅ **Validity** (25%) — Config files parse, no circular imports, type hints valid
- ✅ **Consistency** (25%) — Callback IDs match layout component IDs, naming conventions follow standards
- ✅ **Timeliness** (15%) — Latest bug fixes integrated, dependencies up-to-date

**Failure Gates:**
- Any module import fails → test fails
- Ruff linting issues (E, F, W, I rules) → test fails
- Pytest failures → test fails
- Readiness score < threshold → test fails

---

## Docker Build Check

Builds the `mission` target from `Dockerfile`:

```dockerfile
FROM python:3.11-slim AS mission
# Installs: Dash, FastAPI, Plotly, Mantine components, analysis toolkit
# Entry: python app/dash_app.py → http://localhost:8011
```

**What it validates:**
- All dependencies install without conflict
- Dockerfile syntax is valid
- Base image (`python:3.11-slim`) is accessible
- No secrets leaked in build output

**Note:** Docker image is **not pushed** to any registry from CI. Manual deployment handles image push.

---

## Local Parity (Run Locally Before Pushing)

To match CI exactly, run:

```bash
# Install with mission extra (Dash + all dependencies)
pip install -e ".[mission,xlsx,postgres]"
pip install -r requirements-dev.txt

# Lint (must pass — same rules as CI)
ruff check src/socrata_toolkit tests app

# Run full test suite (4100+ tests)
python -m pytest tests/ -q --tb=short

# Generate readiness report (optional, local validation)
python -m socrata_toolkit.core.cli readiness

# Build Docker image (optional, same as CI)
docker build -t nyc-data:mission --target mission .
```

---

## Legacy Workflows (Manual Only)

These workflows still exist in `.github/workflows/` but **do NOT run automatically on push**. Use **Actions → Run workflow** if needed:

| Workflow | Purpose | Trigger |
|----------|---------|---------|
| `ci.yml` | Old monorepo lint + frontend + bandit | Manual dispatch |
| `test.yml` | Outdated import list + 70% coverage gate | Manual dispatch |
| `tests.yml` | Type-export test only | Manual dispatch |
| `python-app.yml` | Superseded by `nyc-toolkit-ci.yml` | Manual dispatch |
| `pre-commit.yml` | Use `pre-commit run --all-files` locally instead | Manual dispatch |
| `deploy.yml` | Docker/docs push; version tag deploy (v*) | Manual dispatch + tags |
| `validate-docs-consistency.yml` | Governance/SLA consistency checks | Manual dispatch |
| `dependabot-auto-merge.yml` | Auto-merge minor dependency updates | Dependabot events |

**Action:** These should be archived or removed in a future cleanup. They add noise to the Actions tab.

---

## Continuous Deployment (CD)

**Not automated.** Deployments are manual:

1. **Local/Dev:** Run `python app/dash_app.py` or `docker-compose up mission-control`
2. **Staging:** Push image to private ECR/registry, deploy via Terraform/CloudFormation
3. **Production:** Tag release (`v1.2.3`), trigger `deploy.yml` workflow, push to production registry

See [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) for full deployment instructions.

---

## Troubleshooting CI Failures

### `Tests failed on Python 3.11`

1. **Check ruff errors:**
   ```bash
   ruff check src/socrata_toolkit tests app
   ```
   Fix any E, F, W, I, UP, B errors locally.

2. **Check pytest failures:**
   ```bash
   python -m pytest tests/ -q --tb=short
   ```
   Run locally to reproduce. Check error message.

3. **Check imports:**
   ```bash
   python -c "from app.dash_app import app; from src.socrata_toolkit.analysis import *; print('OK')"
   ```

### `Readiness Report failed`

```bash
python -m socrata_toolkit.core.cli readiness
```

Check completeness, validity, consistency, timeliness scores. Fix any import issues or config errors.

### `Docker build failed`

```bash
docker build -t test:latest --target mission .
```

Check for missing dependencies or base image issues. Ensure `Dockerfile` syntax is valid.

---

## Related Documentation

- [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) — Cloud, Docker, Render.com deployment
- [`QUICKSTART.md`](../QUICKSTART.md) — Local development setup
- [`COMMAND_REFERENCE.md`](COMMAND_REFERENCE.md) — CLI toolkit commands
- [`ANALYSIS_MODULES.md`](ANALYSIS_MODULES.md) — Data analysis components (65 modules)
