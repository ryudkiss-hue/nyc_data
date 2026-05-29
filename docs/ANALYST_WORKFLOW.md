# Analyst Autopilot Workflow

Maps NYC DOT Project Analyst duties to toolkit commands and output files.

## Quick path

```bash
python launcher.py setup all
socrata analyst init-config
# Edit config/analyst_profile.yaml — point sources at your Excel/Postgres/Socrata paths
socrata analyst run --profile config/analyst_profile.yaml
```

Weekly outputs land in `outputs/analyst_pack/{YYYY-MM-DD}/`.

## Job duty → command → output

| Job duty | Workflow step | Output file |
|----------|---------------|-------------|
| Repair-location analysis | `prioritize` | `construction_list.xlsx` |
| Week-over-week list changes | `construction_diff` | `construction_list_diff.md` |
| Construction lists + GIS conflicts | `conflicts` | `conflicts_summary.md`, `conflicts_review.xlsx` |
| Contract progress / budget / productivity | `contract_report` | `contract_status.md`, `contract_analytics.json` |
| Program metrics tracking | `program_kpi` | `program_kpi.json` |
| Executive handoff | `executive_summary` | `executive_summary.html`, `executive_summary.md` |
| Contract-planning inquiries | `inquiry_templates` | `inquiry_drafts/*.md` (from `config/inquiry_templates/`) |
| Manager handoff | `manifest.json` | Sources, row counts, warnings, partial failures, toolkit version |
| Role duties & KPIs (optional `role:` in profile) | role profile YAML | `role_kpi_dashboard.json`, `role_task_status.md` |

## SW Project Analyst role (jid-42159)

Business title **SW - PROJECT ANALYST** (Staff Analyst, job level 02). Serves the **Sidewalk Program Management and Budget Unit** — in-house pedestrian ramp crews, IFA justifications, high-priority/GIS work, and ramp make-safe / curb metal programs.

| Posting duty | Profile step | Command / output |
|--------------|--------------|------------------|
| IFA justifications & reports | `executive_summary`, `contract_report` | `executive_summary.html`, `contract_status.md` |
| Project conflict analysis | `prioritize`, `conflicts` | `conflicts_summary.md`, `conflicts_review.xlsx` |
| Analytical studies & reviews | `program_kpi`, `construction_diff` | `program_kpi.json`, `construction_list_diff.md` |
| Review progress; recommend to supervisor | `executive_summary`, `program_kpi` | `role_task_status.md`, `executive_summary.md` |
| High-priority construction inquiries | `inquiry_templates`, `prioritize` | `inquiry_drafts/high_priority_construction.md` |
| Ramp make-safe / curb metal programs | `prioritize`, `conflicts` | `construction_list.xlsx` (ADA / severity queue) |

Enable in `config/analyst_profile.yaml`:

```yaml
role: sw_project_analyst
```

Role definition: `config/role_profiles/sw_project_analyst.yaml`. Compare with **Project Analyst - SW** (`role: project_analyst_sw`, jid-35715).

## Project Analyst - SW (jid-35715)

Capital contract planning, construction lists, contract progress/budget/productivity, and program metrics. Profile: `config/role_profiles/project_analyst_sw.yaml`, templates `contract_delay.md`, `budget_variance.md`.

```yaml
role: project_analyst_sw
```

## GUI (primary)

```bash
python main.py
# or: PYTHONPATH=src:. python -m streamlit run app/mission_control.py
```

Workflow in the UI: configure `config/analyst_profile.yaml` → **Home → Load All Datasets** → navigate the 8 tabs for Agency Workflows / Data Quality / Spatial Analytics / Governance / AI Copilot.

Legacy Dash (archived): `python legacy_archive/dash_app/app.py` → http://127.0.0.1:8050

**Explore page (what-if only):** Use **Explore** in the sidebar to adjust priority weights, filters, and preview charts from the latest pack. This does **not** replace `socrata analyst run` — pack output remains canonical until you update the profile YAML and re-run. See [USER_MANUAL.md](USER_MANUAL.md#interactive-exploration).

Set `offline: true` in the profile to skip Socrata sources. Set `NYC_DOT_DEBUG=1` only if you need legacy devtools/quantum pages.

## Commands

| Command | Purpose |
|---------|---------|
| `socrata analyst init-config` | Copy example YAML to `config/analyst_profile.yaml` |
| `socrata analyst run --profile PATH` | Run full pack |
| `socrata analyst run --dry-run` | Validate sources only |
| `python launcher.py doctor` | Check profile, DuckDB, optional `PG_DSN` |
| `docker compose --profile analyst up analyst-runner` | Scheduled local runner |

## Source types

- **excel** — glob or file path (`openpyxl` extra)
- **socrata** — NYC Open Data dataset (`domain`, `fourfour`)
- **postgres** — table via `PG_DSN`
- **geo** — GeoJSON / geopackage (`geo` extra)

## Docker scheduling

Set `ANALYST_PROFILE` and `ANALYST_CRON` (default Monday 06:00). The `analyst-runner` service runs `scripts/analyst_scheduler.py`.
