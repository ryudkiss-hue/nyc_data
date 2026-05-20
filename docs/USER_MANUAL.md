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
- `config/analyst_profile.yaml` — from `config/analyst_profile.example.yaml`

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

## Analyst GUI (primary)

```bash
python dash_app/app.py
```

Open http://localhost:8050. The sidebar guides the happy path: **Setup** → edit `config/analyst_profile.yaml` → **Run Analyst Pack** on Home → review pages.

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
| `role_kpi_dashboard.json` | Role-specific KPIs when `role:` is set in profile |
| `role_task_status.md` | Job-duty checklist vs pack artifacts |

Profile flags: `offline: true` skips Socrata; `budget_codes: config/budget_codes.yaml` adds validation warnings.

### SW Project Analyst role (jid-42159)

Set `role: sw_project_analyst` in `config/analyst_profile.yaml` to align weekly outputs with the **SW - PROJECT ANALYST** posting (Management & Budget Unit): IFA justifications, conflict analysis, high-priority inquiries, and ramp make-safe queues. See [ANALYST_WORKFLOW.md](ANALYST_WORKFLOW.md) for duty → command mapping.

Dual-role teams: profiles exist for **Project Analyst - SW** (`project_analyst_sw`, jid-35715) and **SW Project Analyst** (`sw_project_analyst`, jid-42159). The Dash **Metrics** and **Settings** pages list both; each pack run uses one `role:` at a time.

## Health check

```bash
python launcher.py doctor
socrata doctor --check-db
```

Verifies Python deps, `.env`, analyst profile, DuckDB writability, optional Postgres.

## Further reading

- [EXECUTABLE_PACKAGE.md](EXECUTABLE_PACKAGE.md) — PyInstaller build and packaging
- [DOCKER_LOCAL.md](DOCKER_LOCAL.md) — Compose analyst profile
- [GETTING_STARTED.md](GETTING_STARTED.md) — Full platform setup
