# KPI & Dives Integrity Audit

**Date:** 2026-06-22
**Scope:** KPI definitions, KPI registry, serving SQL, Dives specification
**Method:** Cross-checked every KPI/Dive against the real ingested data (16 datasets, 3,075,082 rows in MotherDuck `nyc_dot_analytics`)

---

## Executive Summary

The KPI and Dives layer was **almost entirely non-functional and synthetic** before this audit. Headline claims in memory/docs ("51 KPIs materialized", "255 KPI records", "309+ KPIs", "12 dives") described artifacts that either contained hardcoded fake values or had no executable logic.

| Layer | Claimed | Real before | Real after fix |
|---|---|---|---|
| Serving KPIs | 255 records | 0 computed (255 hardcoded `threshold×0.95`) | **13 computed from live data** |
| KPI definitions | 51 KPIs | 51 names, **0 with formula/dataset** | unchanged (spec only) |
| KPI registry | ~667 (IDs to KPI-667) | 30 stubs, placeholder SQL | unchanged (spec only) |
| Dives | 12 dives | 12 specs, **0 executable** | 12 specs, 1/12 referenced views now exist |

---

## 1. Integrity Findings

### 1.1 Serving KPIs (`04_serving_kpis.sql`) — CRITICAL, FIXED
- **Before:** 255 rows built from `VALUES` literals. Every value was its threshold × 0.95 (the file's own comment: *"95% of threshold by default for demonstration"*). **Nothing was computed from data.** This directly violated the no-synthetic-data mandate.
- **After:** Replaced with 13 KPIs computed from staging tables, plus borough breakdowns. Verified values:
  - Total Inspections: **399,566**
  - Inspections No-Violation: **27.5%**
  - 311-Driven Inspections: **14.2%**
  - Total Violations: **120,217**
  - Violation Resolution Rate: **54.4%**
  - Open Violations: **54,827**
  - Total Defect SqFt: **39,056,658**
  - Dismissal (repair) Pass Rate: **75.8%**
  - Total Repair Completions: **45,303**
  - Total Construction Cost: **$25,369,312**
  - SqFt Sidewalk Repaired: **947,183**
  - Total Ramps Tracked: **187,546**
  - Total Ramp Complaints: **5,835**

### 1.2 KPI Definitions (`pipeline/config/kpi_definitions.json`) — NOT COMPUTABLE
- 51 KPIs, each only `{kpi_id, name, category, description, unit, threshold, sla_level}`.
- **No dataset, no column, no formula.** There is no way to compute any of them as specified.
- Names imply data that isn't ingested (e.g., "Permit Issuance Rate", "Intersection Congestion Index", "Environmental Compliance", "Inspector Utilization", "Vendor Performance") — no corresponding dataset exists in the verified 16.

### 1.3 KPI Registry (`config/kpi_registry_full.json`) — STUBS
- 30 entries with sparse IDs (KPI-089 … KPI-667), implying a claimed ~667-KPI catalog that does not exist.
- **Positive:** dataset linkage is correct (e.g., `violations` → `6kbp-uz6m`).
- **Negative:** `sql_pattern` is a placeholder (`"SELECT * FROM violations"`) — not a real KPI computation.

### 1.4 Dives (`pipeline/config/dives_specification.json`) — NOT EXECUTABLE
- 12 dives across 4 categories (exploratory, operational, analytical, strategic).
- Rich metadata (`source_datasets`, `kpis_referenced`, `charts`, `owner`, `quality_gates`) but **no SQL/query** — nothing to run.
- Reference 12 analytics views; **only 1 now exists** (`sim_core.inspection_summary`). 11 are missing: `violation_timeline`, `resolution_funnel`, `complaint_triage`, `ramp_completion_status`, `permit_lifecycle`, etc.

---

## 2. Scope Findings (what is genuinely computable today)

**Computable now** from the 16 verified datasets:
- Inspection volume & outcomes (no-violation %, 311-driven %)
- Violation volume, resolution rate, open count, defect area, distress-type breakdown
- Repair completion (dismissals) pass rate, by borough
- Ramp program counts, by borough
- Capital construction cost & repaired area

**Borough dimension:** available for `ramp_progress` and `dismissals` (clean `borough` column). **Not** directly available for `inspection`/`violations` (no borough field — `violations.cb` is community board; a BBL/geocode join is required).

---

## 3. Comprehensiveness Gaps (vs SIM mission)

| Gap | Why it matters | Needs |
|---|---|---|
| No borough split for inspections/violations | core equity/operational reporting | geocode/BBL join to a borough lookup |
| No time-series / trend KPIs | SCI trends, SLA over time | use `inspectiondate`, `vissuedate`, `vdismissdate` |
| No SLA / turnaround KPIs | 311→inspection→repair lifecycle | join across inspection/dismissals/correspondences by date |
| No equity / demographic KPIs | mission requires equity lens | census/ACS dataset (not in the 16) |
| No 311 complaint volume | demand signal | `complaints_311` not ingested (separate large dataset) |
| Dives non-executable | self-serve analytics | add SQL to each dive + build the 11 missing views |
| SCI / MRI indices not computed | headline condition metrics | define formula from violation distress + area |

---

## 4. Recommendations (priority order)

1. **Treat `kpi_definitions.json` (51) and `kpi_registry_full.json` (667) as aspirational backlogs, not delivered KPIs.** Update memory/docs to stop claiming they are materialized.
2. **Grow `serving.kpi_summary`** from 13 toward the genuinely computable set (add time-series + SCI/MRI + SLA once join keys are established).
3. **Add a borough lookup** (BBL→borough) to unlock borough-level inspection/violation KPIs.
4. **Make Dives executable** — attach SQL to each of the 12 dives and build the 11 missing analytics views, or prune dives that can't be backed by real data.
5. **Decide on 311 + census ingestion** to close the equity/demand gaps.

---

## 5. What this audit changed

- `04_serving_kpis.sql`: synthetic → **13 real computed KPIs** + borough breakdowns
- `03_analytics_schemas.sql`: invented columns → **8 real domain views**
- `05_verification_gates.sql`: broken (never ran) → **4 enforced gates, all PASS**
- All 4 downstream pipeline stages now execute and pass against live MotherDuck data.

**Bottom line:** the pipeline now produces a small but **honest and fully real** KPI layer. The large KPI/Dive counts previously claimed were not real; they remain as specs/backlog and are documented as such.
