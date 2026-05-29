# NYC DOT Sidewalk Toolkit — Completeness checklist

Mark each item before agency sign-off. Track progress in **Mission Control → Settings & Quality → Completeness**.

## Core product

| Item | Status | How to verify |
|------|--------|----------------|
| Install wizard writes `.env` + profile YAML | ☐ | `socrata setup` |
| Mission Control opens | ☐ | `python main.py` |
| Analyst Pack run (full) | ☐ | **Publish & Pack → Run Analyst Pack** or `socrata analyst run` |
| Analyst Pack run (offline) | ☐ | Offline checkbox on Publish page |
| Publish dry-run | ☐ | **Publish & Pack** with dry-run enabled |
| Publish live (share/email/BI) | ☐ | `config/publish_profile.yaml` configured |
| Review decisions persist | ☐ | `socrata review list --pack-date YYYY-MM-DD` |
| Data dictionary in pack | ☐ | `data_dictionary.json` in latest pack folder |

## Mission Control (Streamlit)

| Item | Status | How to verify |
|------|--------|----------------|
| All four workflows load data | ☐ | QA, Spatial, Contract, Productivity side nav |
| Demo mode for training | ☐ | Open without token or `MISSION_DEMO=1` |
| Readiness ≥ 95% | ☐ | Settings → Readiness |
| Ingestion log populated | ☐ | Settings → Ingestion log after live fetch |
| CSV exports per workflow | ☐ | Download buttons on QA / Spatial / Contract |
| Onboarding shown for new users | ☐ | Home → first-time setup |

## CLI & packaging

| Item | Status | How to verify |
|------|--------|----------------|
| `socrata doctor` | ☐ | `socrata doctor --checklist` |
| `socrata readiness` ≥ 95 | ☐ | `socrata readiness` |
| Nightly sync script | ☐ | `scripts/nightly_analyst_sync.ps1` |
| Docker mission image | ☐ | `docker build -f Dockerfile.mission .` |
| Core pytest green | ☐ | `pytest tests/ -m "not legacy" -q` |

## Documentation

| Item | Status | How to verify |
|------|--------|----------------|
| [AGENCY_RUNBOOK.md](AGENCY_RUNBOOK.md) | ☐ | Present |
| [SIMPLE_START.md](SIMPLE_START.md) | ☐ | Present |
| [MISSION_CONTROL.md](MISSION_CONTROL.md) | ☐ | Present |

## Sign-off

- **Analyst lead:** _____________________ Date: _______
- **Tech lead:** _____________________ Date: _______
