# NYC DOT Sidewalk Toolkit — Completeness checklist

One-page readiness check for analysts and release owners. Mark each item before handing off to production users.

## Core product

| Item | Status | How to verify |
|------|--------|----------------|
| Install wizard writes `.env` + profile YAML | ☐ | `python -m socrata_toolkit.install_wizard` |
| Analyst Pack run (full) | ☐ | `socrata analyst run --profile config/analyst_profile.yaml` |
| Analyst Pack run (offline) | ☐ | `socrata analyst run --profile config/analyst_profile.yaml --offline` |
| Multi-profile state isolated | ☐ | `socrata profile list` · packs under `outputs/.state/profiles/<name>/` |
| Publish after pack (`steps.publish: true`) | ☐ | Profile has `publish_profile:` · run completes without publish warning |
| Manual publish | ☐ | `socrata analyst publish --profile config/publish_profile.yaml --pack outputs/analyst_pack/YYYY-MM-DD --dry-run` |
| Review decisions persist | ☐ | `socrata review list --pack-date YYYY-MM-DD` |
| Data dictionary in pack | ☐ | `data_dictionary.json` in latest pack folder |

## CLI & packaging

| Item | Status | How to verify |
|------|--------|----------------|
| `socrata doctor` | ☐ | `socrata doctor` (add `--check-db` if Postgres used) |
| EXE wizard / analyst / dash | ☐ | `dist\nyc-dot-toolkit.exe wizard` (after `python scripts/build_exe.py`) |
| Windows installer script valid | ☐ | `pytest tests/test_installer_files.py -q` |
| Docker analyst profile | ☐ | `docker compose --profile analyst config` · `docker compose --profile analyst up -d analyst-runner` |

## Dash UX (analyst nav)

| Item | Status | How to verify |
|------|--------|----------------|
| All nav pages load (`page_shell`) | ☐ | `pytest tests/test_dash_pages_import.py -q` |
| Theme / font / offline in Settings | ☐ | Settings → save → reload app |
| Skip link + aria-live regions | ☐ | Tab from top of page · run pack (status updates) |
| Demo pack when no data | ☐ | Home empty state → Load demo pack |
| Deep links `?page=&pack=` | ☐ | Open `/explore?page=explore&pack=demo_pack` |
| Long tasks non-blocking | ☐ | Home Run Pack · Review list (background_jobs) |
| No console errors on smoke | ☐ | `python dash_app/app.py` · click each nav item · DevTools console |

## Documentation

| Item | Status | How to verify |
|------|--------|----------------|
| README links to primary guides | ☐ | [README.md](../README.md) |
| Docs index cross-links | ☐ | [index.md](index.md) |
| Analyst workflow duty map | ☐ | [ANALYST_WORKFLOW.md](ANALYST_WORKFLOW.md) |
| Publishing guide | ☐ | [PUBLISHING.md](PUBLISHING.md) |
| Windows installer | ☐ | [WINDOWS_INSTALLER.md](WINDOWS_INSTALLER.md) |
| Docker local | ☐ | [DOCKER_LOCAL.md](DOCKER_LOCAL.md) |
| Dash UX audit | ☐ | [DASH_UX_AUDIT.md](DASH_UX_AUDIT.md) |

## Code health

| Item | Status | How to verify |
|------|--------|----------------|
| Full test suite green | ☐ | `python -m pytest tests/ -q` |
| `outputs/` and `.env` gitignored | ☐ | See repo `.gitignore` |
| 311 pipeline imports (no missing `nlp`) | ☐ | `python -c "from socrata_toolkit.pipeline.complaints import ingest_311_complaints"` |

## Sign-off

- **Analyst lead:** _____________________ Date: _______
- **Tech lead:** _____________________ Date: _______

When all rows are checked, the toolkit is ready for analyst PCs and scheduled automation.
