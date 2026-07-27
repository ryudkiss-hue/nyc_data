# Analyst Runbook — NYC DOT SIM Mission Control (Solo Workstation)

One page: how to run the tool day-to-day as a Sidewalk Program Project Analyst.

## Start the dashboard

Double-click **`start_mission_control.bat`** in the repo root (or run `python app/dash_app.py`).
It opens http://localhost:8011. Stop with Ctrl+C in the console window.

## Data freshness (automatic)

Two user-level Windows scheduled tasks are installed by `scripts/install_scheduled_tasks.ps1`
(rerun-safe; remove with `schtasks /Delete /TN "<name>" /F`):

| Task | Schedule | What it does |
|---|---|---|
| `NYC-DOT-Nightly-Refresh` | daily 02:00 | Checkpointed pipeline refresh of all 112 in-scope datasets, then rotates a DuckDB backup into `backups/` (keeps 3). Log: `pipeline/logs/nightly_refresh.log` |
| `NYC-DOT-Weekly-Drift-Audit` | Mon 08:00 | Live audit of every configured dataset (accessibility, freshness, row/schema drift, role scope). Log: `pipeline/logs/drift_audit.log`, report: `pipeline/logs/registry_drift_report.json` |

Manual refresh anytime: `python pipeline/run_local.py` (resumes from checkpoints).

## Answering the six standard request types

| Request | Where |
|---|---|
| Where are sidewalk repairs needed? | Dashboard home + `/stats` (inspection/violation charts); `socrata health inspection` for freshness first |
| Construction lists | `socrata_toolkit.analyst.construction_list_generator` (Python API); GIS dashboard `/geo` |
| Conflicts (GIS + contract scope) | `/geo` conflict overlays; `spatial_intersects_join()` + `analyst.conflicts_queue.build_conflicts_review()`. ⚠ Use the **spatial join**, not `inspection.capitalconflicts` — that column is only 7.5% populated full-corpus, so filtering on it would miss ~92% of real conflicts. |
| Contract progress / budget dollars | **`capital_projects_dashboard` (fb86-vt7u)** is the authoritative budget-vs-spend source — 590 DOT projects, $36.3B budgeted / $7.6B spent, current to 2026-05. ⚠ Take the **latest `reporting_period` only** (each project repeats per period; summing raw inflates ~9×). Permit **fee** revenue: `street_construction_permit_fees` ↔ `street_construction_permits` on `permitnumber`. ❌ Do **not** use `built` cost columns — verified 3.5–3.9% populated and 0% for 2024–25. |
| Productivity studies | Inspector throughput chart (`/labor`); CUSUM & control charts under Advanced Analytics |
| Program metrics tracking | KPI cards on home; `socrata ramp-analysis` for borough ramp completion with 95% CIs |

Interagency coordination: `raw.street_construction_permit_related_agency` (DEP/DDC/etc. cross-permits, 2025+).
Permit **stipulations** (gsgx-6efw, 45.6M rows) are intentionally NOT ingested nightly —
query them live with a `$where` filter (the GIS dashboard's stipulations panel does this).

## Reports / deliverables

- **Combined PDF of every chart** (no native deps): `python scripts/export_all_charts_pdf.py` → `exports/`
- Excel / PPTX: export buttons in `/reports`
- WeasyPrint-styled PDFs additionally require the Windows GTK3 runtime; without it the
  app shows a clear message and the ReportLab exporter above is the fallback

## Quick health checks

```bash
socrata health violations          # any dataset key or 4x4 id; SLA-aware
socrata quality-score inspection --key-column inspectionid --date-column created_date
python scripts/audit_registry_drift.py   # full 112-dataset live audit on demand
```

## Which datasets carry the analysis (full-corpus verified 2026-07-26)

Population measured with SoQL aggregates over the **entire** dataset, not a sample.

| Duty | Use this | Populated | Don't use |
|---|---|---|---|
| Budget dollars / contract progress | `capital_projects_dashboard` (fb86-vt7u), latest `reporting_period` only | 100% budget + spend, 590 DOT projects, current to 2026-05 | `built` cost columns — 3.5–3.9%, **0% for 2024–25** |
| Permit fee revenue | `street_construction_permit_fees` (9fnm-j6if) | 100% on `permitfeeamountcharged`, 1.09M rows 2025+ | — |
| Repair locations / outcomes | `inspection` (dntt-gqwq) | outcome flags 100%, `inspectiondate` 88.6% | `capitalconflicts` (7.5%) |
| Enforcement | `violations` (6kbp-uz6m) | `vissuedate`/`sq_feet`/`cb` 100%; `trip_haz` 67%, `certi_date` 64% | — |
| Ramp completion | `ramp_progress` (e7gc-ub6z) | `construc_2` + `borough` 100%, 187K corners | `ramp_locations` (stale 2021) |
| Re-inspection turnaround | `reinspection` (gx72-kirf) | `actualreinspectdate` 91% | — |
| Paving productivity | `street_resurfacing_inhouse` (ffaf-8mrv) | `location_actual_lane_miles` 51% — qualify conclusions | — |

**Always state `n=` and the populated share** when reporting a dollar or rate figure.

## Known data caveats (verified 2026-07-26)

- `capital_blocks` (jvk9-k4re): 0 rows upstream (NYC publication gap) — use `capital_intersections` (97nd-ff3i)
- `ramp_locations` / `weekly_construction`: stale since 2021 / 2017 — use `ramp_progress` / `street_construction_inspections`
- Full current list: CLAUDE.md “Known Dataset Issues” + the weekly drift report

## Recovery

- DB corrupted or deleted → restore newest `backups/nyc_dot_analytics.*.duckdb`, or re-run `python pipeline/run_local.py` (rebuilds from Socrata; ~1–2h)
- Rebuild the environment → `uv venv && uv pip install -r requirements-lock.txt && uv pip install -e ".[mission]"`
- Cloud deploy (not used in solo mode) → GitHub Actions “Deploy to Cloud Run”, manual trigger only
