# NYC DOT Sidewalk Toolkit — User Manual

## Local deployment: EXE vs Docker vs Python

Choose one path after initial configuration.

### Step 0 — Install wizard (all paths)

```bash
pip install -e ".[postgres,xlsx]"
python -m socrata_toolkit.install_wizard
```

This writes:

- `.env` — `SOCRATA_APP_TOKEN`, `PG_DSN`, data/output paths, DuckDB path
- `TOOLKIT_PROFILE` — active profile name (for multi-profile installs)
- `config/profiles/<name>/analyst_profile.yaml` — from `config/analyst_profile.example.yaml`

Aliases: `socrata setup`, `socrata wizard`, `python launcher.py setup wizard`.

---

### Path A — Python (recommended for development)

```bash
socrata analyst run --profile config/analyst_profile.yaml
python launcher.py doctor
```

---

### Path B — Windows standalone `.exe`

Build on Windows (requires PyInstaller; large binary ~80–200 MB):

```bash
pip install -e .
python scripts/build_exe.py
```

Run:

```text
dist\nyc-dot-toolkit.exe wizard
dist\nyc-dot-toolkit.exe analyst run --profile config\analyst_profile.yaml
```

See [EXECUTABLE_PACKAGE.md](EXECUTABLE_PACKAGE.md) for Task Scheduler examples.

---

### Path C — Docker (recommended for scheduled production)

```bash
python launcher.py setup docker
docker compose --profile analyst run --rm setup
docker compose --profile analyst up -d analyst-runner
```

See [DOCKER_LOCAL.md](DOCKER_LOCAL.md) for compose profiles and volumes.

---

## Mission Control (primary UI)

```bash
# Recommended shortcut
python main.py

# Full form
PYTHONPATH=src:. python -m streamlit run app/mission_control.py
```

Open http://localhost:8501. Mission Control is the unified 8-tab Streamlit app for all agency workflows.

### 8-tab layout

| Tab | What it does |
|-----|-------------|
| **Home** | Dataset status cards, Load All Datasets button, audit trail |
| **Agency Workflows** | QA/spatial/contract/productivity views |
| **Data Quality** | Per-dataset health scores, null/duplicate profiling, SLA freshness (green <7d, amber <30d, red >30d), anomaly detection, CSV export |
| **Spatial Analytics** | Borough bar charts, Plotly Scattermapbox, Folium bubble map, conflict detection |
| **Governance** | Plotly lineage DAG, dataset registry, ingest audit log, SLA compliance |
| **AI Copilot** | Gemini/OpenAI/Ollama multi-backend chat; context-hydrated; quick-action chips |
| **Settings & Quality** | Readiness score, completeness checklist, system health |

Demo mode (no Socrata token needed): `MISSION_DEMO=1 python main.py`

Legacy Analyst Pack UI (archived Dash): `python legacy_archive/dash_app/app.py` → http://localhost:8050

### Theme, offline mode, and preferences

| Control | Where | Effect |
|---------|-------|--------|
| **Theme** (dark / light) | Settings → Appearance | Sets `data-theme` on the app root; Plotly uses dark or white template |
| **Font scale** (normal / large) | Settings | `data-font-scale=large` increases base typography |
| **Offline mode** | Settings or Home run card | Skips Socrata on pack run (`socrata analyst run --offline`); banner when enabled |
| **Export / import JSON** | Settings | Backs up `ui_prefs.json` and `explore_prefs.json` under `outputs/.state/` |

Preferences persist per toolkit profile (`TOOLKIT_PROFILE`, default `default`).

<!-- Screenshot placeholder: docs/images/analyst-home.png -->

Golden column headers for Excel sources: `config/templates/*_headers.txt`.

## Analyst pack outputs

Each run writes `outputs/analyst_pack/{YYYY-MM-DD}/`:

| File | Purpose |
|------|---------|
| `construction_list.xlsx` | Prioritized repair locations |
| `construction_list_diff.md` | Week-over-week changes vs previous pack |
| `conflicts_summary.md` / `conflicts_review.xlsx` | Permit conflicts and review queue |
| `contract_status.md` / `contract_analytics.json` | Progress, budget CPI, productivity |
| `program_kpi.json` | Red/yellow/green program metrics |
| `executive_summary.html` | One-pager for managers |
| `inquiry_drafts/*.md` | Template-based inquiry letters |
| `manifest.json` | Sources, row counts, warnings, partial failures, version |
| `data_dictionary.md` / `data_dictionary.json` | Column stats per source (trust / QA) |
| `decisions_export.xlsx` / `decisions_summary.md` | Review decisions exported into the pack (optional) |
| `role_kpi_dashboard.json` | Role-specific KPIs when `role:` is set in profile |
| `role_task_status.md` | Job-duty checklist vs pack artifacts |

Profile flags: `offline: true` skips Socrata; `budget_codes: config/budget_codes.yaml` adds validation warnings.

## Publish (after a run)

After a pack is generated, you can publish it to your organization’s destinations (share drive, BI staging folder, Teams webhook, email, optional PPTX).

- Setup: copy `config/publish_profile.example.yaml` to `config/publish_profile.yaml`
- Docs: [PUBLISHING.md](PUBLISHING.md)

CLI:

```bash
socrata analyst publish --profile config/publish_profile.yaml --pack outputs/analyst_pack/YYYY-MM-DD --dry-run
socrata analyst publish --profile config/publish_profile.yaml --pack outputs/analyst_pack/YYYY-MM-DD
```

Automation: enable publish after pack generation by adding:

```yaml
steps:
  publish: true
  publish_profile: config/publish_profile.yaml
```

## Review workflow (conflicts + approvals)

Decisions are stored locally in a DuckDB file under your per-profile state directory:

- `outputs/.state/profiles/<name>/decisions.duckdb`

CLI:

```bash
socrata review list --pack-date YYYY-MM-DD
socrata review set --pack-date YYYY-MM-DD --kind conflict --key-type location_id --key L123 --status resolved --assigned-to "you" --notes "checked permits"
socrata review set --pack-date YYYY-MM-DD --kind approval --key-type location_id --key L123 --status hold --reason "needs photo" --notes "missing context"
socrata review export --pack outputs/analyst_pack/YYYY-MM-DD
```

Dash includes a **Review** page that calls the same commands behind the scenes.

### SW Project Analyst role (jid-42159)

Set `role: sw_project_analyst` in `config/analyst_profile.yaml` to align weekly outputs with the **SW - PROJECT ANALYST** posting (Management & Budget Unit): IFA justifications, conflict analysis, high-priority inquiries, and ramp make-safe queues. See [ANALYST_WORKFLOW.md](ANALYST_WORKFLOW.md) for duty → command mapping.

Dual-role teams: profiles exist for **Project Analyst - SW** (`project_analyst_sw`, jid-35715) and **SW Project Analyst** (`sw_project_analyst`, jid-42159). The Dash **Metrics** and **Settings** pages list both; each pack run uses one `role:` at a time.

## Health check

```bash
python launcher.py doctor
socrata doctor --check-db
```

Verifies Python deps, `.env`, analyst profile, DuckDB writability, optional Postgres.

## Completeness checklist (analysts)

Before your first production week, walk through the one-page readiness list:

- [docs/COMPLETENESS.md](COMPLETENESS.md) — sign-off table for install, Analyst Pack, publish, Dash UX, tests, and docs

Quick self-check:

1. Wizard completed (`.env` + `config/analyst_profile.yaml` or profile under `config/profiles/<name>/`).
2. `socrata analyst run` produces `outputs/analyst_pack/YYYY-MM-DD/` with construction list, contracts, KPIs, and inquiries.
3. Dash opens all sidebar pages without errors; Settings theme/offline persist after reload.
4. Optional: `socrata analyst publish --dry-run` and `socrata review list --pack-date YYYY-MM-DD`.

## Further reading

- [COMPLETENESS.md](COMPLETENESS.md) — “Is it ready?” release checklist
- [EXECUTABLE_PACKAGE.md](EXECUTABLE_PACKAGE.md) — PyInstaller build and packaging
- [DOCKER_LOCAL.md](DOCKER_LOCAL.md) — Compose analyst profile
- [GETTING_STARTED.md](GETTING_STARTED.md) — Full platform setup
- [DASH_UX_AUDIT.md](DASH_UX_AUDIT.md) — Accessibility and performance checklist
