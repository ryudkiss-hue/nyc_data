# GitHub Actions CI

## Active workflow

**[`.github/workflows/nyc-toolkit-ci.yml`](../.github/workflows/nyc-toolkit-ci.yml)** runs on every push/PR to `main`:

| Job | What it does |
|-----|----------------|
| Tests (3.10 / 3.11 / 3.12) | `pip install -e ".[xlsx,postgres]"`, ruff, full `pytest tests/` |
| Readiness report | `socrata readiness` (automated quality axes) |
| Docker (analyst) | Build `Dockerfile.analyst` (no push) |

You should see **5 checks** (3 Python versions + readiness + Docker), not 19.

## Legacy workflows (manual only)

These still exist but **do not run on push** (use **Actions → Run workflow** if needed):

- `ci.yml` — old monorepo lint + frontend + bandit
- `test.yml` — outdated import list + 70% coverage gate
- `tests.yml` — type-export test only
- `python-app.yml` — superseded by `nyc-toolkit-ci.yml`
- `pre-commit.yml` — run `pre-commit run --all-files` locally instead
- `deploy.yml` — Docker/docs deploy (`workflow_dispatch` or version tags `v*`)

## Local parity

```powershell
pip install -e ".[xlsx,postgres]"
pip install -r requirements-dev.txt
pip install dash dash-bootstrap-components plotly
ruff check socrata_toolkit tests dash_app
python -m pytest tests/ -q
python -m socrata_toolkit.core.cli readiness
```
