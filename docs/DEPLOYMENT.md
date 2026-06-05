# Deployment Guide

## Local Development

**Prerequisites:**
- Python 3.11+
- pip with `requirements-dev.txt` installed: `pip install -r requirements-dev.txt`
- Optional: Docker (for containerized deployment)

**Setup:**
```bash
cd /home/user/nyc_data
pip install -e ".[dev,mission]"
```

**Run locally:**
```bash
# Streamlit dashboard
streamlit run app/app.py

# CLI
socrata --help
socrata dataset health --all

# Tests
pytest tests/ -q
```

**Environment variables** (optional):
```bash
export SOCRATA_APP_TOKEN=<your-token>        # For full-corpus fetches >2K rows
export ANTHROPIC_API_KEY=<claude-api-key>    # For NL query feature
export SOCRATA_DOMAIN=data.cityofnewyork.us  # Default domain
export SOCRATA_CACHE_DIR=data/cache          # Parquet cache location
```

---

## Docker Containerization

**Build the image** (see Dockerfile at repo root):
```bash
docker build -t nyc-sim-toolkit:latest .
```

**Run container locally:**
```bash
docker run -p 8501:8501 \
  -e SOCRATA_APP_TOKEN=$SOCRATA_APP_TOKEN \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -v $(pwd)/data:/app/data \
  nyc-sim-toolkit:latest
```

**Access dashboard:** http://localhost:8501

**Persistent cache:**
- Cache persisted in `/app/data/cache/` (Parquet files)
- Mount `data/` volume to preserve cache across container restarts

---

## CI/CD Pipelines

**GitHub Actions workflows** (.github/workflows/):

### 1. **validate-docs-consistency.yml** (on push/PR to main)
Triggered by changes to CLAUDE.md, sla_config.json, governance code, or tests.

**Steps:**
1. Checkout code
2. Set up Python 3.11
3. Install dependencies
4. Run governance weights tests (7 tests): `pytest tests/test_governance_weights.py`
5. Run SLA config tests (9 tests): `pytest tests/test_sla_config.py`
6. Validate SLA JSON syntax
7. Grep for hardcoded quality weights (0.35, 0.25, 0.15) → fail if found
8. Cross-reference SLA thresholds in CLAUDE.md
9. Report results

**Fail conditions:**
- Any test fails
- Hardcoded weights detected in governance/core.py
- SLA thresholds in config ≠ CLAUDE.md references

### 2. **pytest.yml** (on push/PR)
Full test suite run.

**Steps:**
1. Checkout code
2. Set up Python 3.11
3. Install dependencies
4. Run all tests: `pytest tests/ -v --tb=short --cov=src`
5. Report coverage

**Fail conditions:**
- Any test fails
- Coverage < 45% (gate on key modules)

### 3. **ruff.yml** (on push/PR)
Code quality gate.

**Steps:**
1. Run linting: `ruff check src/ tests/ app`
2. Run formatter check: `black --check src/ tests/ app`

**Fail conditions:**
- Any linting errors (E, F, W, I, UP, B rules)
- Formatting issues

### 4. **docker-build.yml** (on push to main)
Build and push image to registry.

**Steps:**
1. Build Docker image
2. Tag as latest + commit SHA
3. Push to Docker Hub / ECR (configured in secrets)

**Fail conditions:**
- Docker build fails
- Registry authentication fails

---

## Deployment Environments

### **Staging** (pre-production testing)
- Triggered on merges to `develop` branch
- Deploy to staging Streamlit Cloud / GCP Cloud Run
- Uses cached data from test fixtures
- All features enabled

**Deploy:**
```bash
git push origin develop  # CI automatically deploys
```

### **Production** (live)
- Triggered on merges to `main` branch
- Deploy to production environment with real API credentials
- Real Socrata API token and Claude API key required
- Scheduled nightly cache refresh via APScheduler

**Deploy:**
```bash
git push origin main  # CI automatically deploys
```

**Configuration differences:**

| Config | Staging | Production |
|---|---|---|
| SOCRATA_DOMAIN | data.cityofnewyork.us | data.cityofnewyork.us |
| API Token | Test token (limited) | Full token (unlimited) |
| Cache refresh | Manual | Nightly (00:00 UTC) |
| Log level | DEBUG | INFO |
| Error reporting | Console | Slack webhook |

---

## Rollback Procedure

**If deployment breaks production:**

1. **Immediate:** Revert to previous main commit
   ```bash
   git revert HEAD
   git push origin main
   ```
   CI automatically redeploys the previous version.

2. **Diagnose:** Check GitHub Actions logs for the failing step
   ```
   https://github.com/ryudkiss-hue/nyc_data/actions
   ```

3. **Fix:** Investigate the root cause
   - Syntax error: Fix code, merge fix PR to main
   - Missing dependency: Update requirements.txt or Dockerfile
   - API credentials: Verify in GitHub Secrets
   - Data issue: Check DuckDB or Socrata API status

4. **Verify:** Before re-pushing, ensure all local tests pass
   ```bash
   pytest tests/ -q && ruff check src/
   ```

---

## Monitoring & Alerts

**Health checks:**

1. **Dataset staleness:** Every 6 hours, check if any dataset exceeds its SLA threshold
   - HIGH (14d), MEDIUM (30d), LOW (60d)
   - If exceeded: Post alert to Slack webhook (configured in SLACK_WEBHOOK_URL)

2. **Cache freshness:** Nightly refresh task logs success/failure
   - If refetch fails 3 consecutive times: Escalate alert

3. **API connectivity:** Test Socrata API connectivity on startup
   - If API unreachable: Dashboard shows warning banner, uses cached data

4. **Quality score regression:** If overall quality score drops >5 points week-over-week: Flag for analyst review

**View logs:**
```bash
# Local: Streamlit logs
streamlit logs

# Docker: Container logs
docker logs nyc-sim-toolkit

# GitHub Actions: Run logs
gh run list --repo ryudkiss-hue/nyc_data
gh run view <run-id> --log
```

---

## Scheduled Tasks

**APScheduler config** (data/scheduler_config.json):

```json
{
  "jobs": [
    {
      "id": "nightly_cache_refresh",
      "trigger": "cron",
      "hour": 0,
      "minute": 0,
      "timezone": "UTC",
      "func": "socrata_toolkit.core.duckdb_store.fetch_and_update_cache",
      "datasets": ["inspection", "violations", "ramp_progress"],
      "incremental": true
    }
  ]
}
```

**Manual cache refresh:**
```bash
socrata cache refresh inspection
socrata cache refresh violations
socrata cache refresh ramp_progress
```

---

## Database Migrations

**DuckDB schema:** Defined in src/socrata_toolkit/core/duckdb_store.py

If schema changes required:
1. Update schema definition in duckdb_store.py
2. Increment version number in comment
3. Add migration step (recreate tables if needed)
4. Run locally, verify cache rebuilds cleanly
5. Merge to main; CI tests will catch incompatibilities

**Backup:**
```bash
cp data/local_db/nyc_mission_control.duckdb data/local_db/nyc_mission_control.duckdb.backup
```

---

## Performance Tuning

**Cache efficiency:**
- Parquet files stored in `data/cache/` with index files
- Delta updates (incremental fetch) reduce API calls 80%
- DuckDB in-memory caching for repeated queries

**Query optimization:**
- Always use `$where` filters in Socrata API calls (server-side filtering)
- Prefer `SELECT [columns]` over `SELECT *`
- Use `MAX_ROWS` to limit initial fetch

**Dashboard performance:**
- Streamlit caching via `@st.cache_data` for expensive computations
- Session state for user interactions (drill-down, filters)
- Lazy-load tabs (only compute active tab's data)

---

## Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| "API rate limit exceeded" | Too many requests in short time | Wait 60 seconds; use cache instead of live fetch |
| "SOCRATA_APP_TOKEN not set" | Missing environment variable | Set token: `export SOCRATA_APP_TOKEN=...` |
| "DuckDB locked" | Another process using database | Check for stale processes: `lsof data/local_db/*.duckdb` |
| "Streamlit session state missing" | Cache expired | Refresh browser (hard refresh: Ctrl+Shift+R) |
| "CI fails on ruff check" | Formatting issues | Run locally: `ruff check src/ --fix && black src/` |
| "Docker build fails" | Dependency conflict | Rebuild base image: `docker build --no-cache .` |

---

## Maintenance Calendar

**Weekly:**
- Monitor GitHub Actions for any test failures
- Check Slack alerts for data staleness

**Monthly:**
- Run `scripts/refresh_claude_md_dates.py --apply` to update verification dates
- Review SLA compliance report in dashboard

**Quarterly:**
- Audit code coverage: `pytest --cov=src/ --cov-report=term-missing`
- Review performance metrics (query latency, cache hit rate)
- Update dependencies: `pip list --outdated`

**Annually:**
- Major version bump if significant features added
- Review and update deployment procedures
- Disaster recovery drill (restore from backup)
