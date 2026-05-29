# Agency runbook — Manhattan Mission Control

Operational guide for NYC DOT SIM analysts and release owners targeting **95+ readiness**.

## Daily operations

| Step | Action | Command / UI |
|------|--------|----------------|
| 1 | Verify health | `socrata doctor` · **Settings & Quality → System health** |
| 2 | Open workspace | `python main.py` or `mission` |
| 3 | Review workflow | **Analyst Workflows** → QA / Spatial / Contract / Productivity |
| 4 | Export findings | CSV download buttons on each workflow |
| 5 | Weekly pack | **Publish & Pack → Run Analyst Pack** or `scripts/nightly_analyst_sync.ps1` |
| 6 | Publish | **Publish & Pack** → dry-run → live publish |

## Authentication

| Mode | When | Setup |
|------|------|--------|
| **Live** | Production | `SOCRATA_APP_TOKEN` in `.env` |
| **Key pair** | SODA3 rate limits | `SOCRATA_KEY_ID` + `SOCRATA_KEY_SECRET` |
| **Demo** | Training / CI | No token, or `MISSION_DEMO=1` |

## Quality gates

```powershell
socrata readiness                    # target ≥ 95 overall
python -m pytest tests/ -m "not legacy" -q
python main.py                       # smoke UI
```

In-app: **Settings & Quality → Readiness** and **Completeness** tabs.

## Deployment options

| Channel | Artifact |
|---------|----------|
| Analyst PC | `pip install -e ".[mission]"` + `python main.py` |
| Scheduled pack | `scripts/nightly_analyst_sync.ps1` |
| Container | `Dockerfile.mission` on port 8501 |
| Windows installer | `scripts/build_installer.ps1` |

## Sign-off

Complete [COMPLETENESS.md](COMPLETENESS.md) in the app checklist and record analyst + tech lead signatures.

## Support

- Ingestion issues → `outputs/logs/ingest.jsonl`
- CLI reference → [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md)
- Publishing → [PUBLISHING.md](PUBLISHING.md)
