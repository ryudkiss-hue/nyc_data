# Context Package

**Dataset:** <!-- dataset key, e.g. ramp_progress -->
**Goal:** <!-- analytical goal in one precise sentence -->
**Date packaged:** <!-- YYYY-MM-DD -->
**Token estimate:** <!-- run context_bundler.py to get this -->
**Quality score:** <!-- score/100 against context_quality_rubric.md -->

---

## Layer 1 — Business context

**Analytical goal:** <!-- Precise, data-answerable question: metric + population + time window -->
<!-- Example: "What is the borough-level ramp completion rate for Q1 2026 (2026-01-01 to 2026-03-31), with 95% Wilson CI?" -->

**Stakeholder:** <!-- name and team -->
**Decision this informs:** <!-- e.g. Q3 borough staffing allocation -->
**Boroughs in scope:** ALL / MN / BX / BK / QN / SI
**Time window:** <!-- YYYY-MM-DD to YYYY-MM-DD -->

---

## Layer 2 — Data schema

**Dataset:** <!-- name -->
**Fourfour:** <!-- e.g. e7gc-ub6z -->
**Row count:** <!-- approximate -->
**SLA:** <!-- HIGH (14d) / MEDIUM (30d) / LOW (60d) -->
**Last verified fresh:** <!-- YYYY-MM-DD -->

| Column | Type | Business definition | Null rate | Notes |
|---|---|---|---|---|
| objectid | INTEGER | Primary key | 0% | Use as dedup key |
| borough | TEXT | Borough code | <1% | Normalize: upper(trim(borough)) → MN/BX/BK/QN/SI |
| <!-- col --> | | | | |

**Borough encoding in this dataset:**
<!-- e.g. "Full names: MANHATTAN, BRONX, BROOKLYN, QUEENS, STATEN ISLAND" or "Codes: MN, BX, BK, QN, SI" -->

---

## Layer 3 — Metric definitions

**Metric:** <!-- name -->
**Formula:** <!-- numerator / denominator, with exact column references and filter conditions -->
**Date field to use:** <!-- e.g. "created_date (not inspection_date)" -->
**CI method:** Wilson Score 95% (always for proportions; n may be small for SI)
**SLA threshold:** <!-- if freshness is part of the metric -->

---

## Layer 4 — Analytical constraints

**Datasets explicitly excluded:**
- ramp_locations (ufzp-rrqu) — stale since 2021
- <!-- add any others not applicable to this analysis -->

**Access status:**
- SOCRATA_APP_TOKEN: SET / NOT SET
- Row limit for this analysis: <!-- e.g. 10K sample / full corpus -->

**Required output structure:** <!-- e.g. borough breakdown table, time-series by month -->

**Peer review required before delivery?** YES / NO

---

## Layer 5 — Output format

- Table columns: <!-- e.g. [borough, n, completion_rate%, ci_lower%, ci_upper%] -->
- Rate precision: 1 decimal (e.g. 73.4%)
- Count precision: integer with comma separator
- Every number must include: n= and data freshness date
- Borough row order: MN, BX, BK, QN, SI

---

## Prompt to open the session

Paste the following as the first message in the AI session:

```
You are helping me analyze NYC DOT SIM data. Use the context below to answer the question precisely.

[PASTE LAYERS 1–5 ABOVE HERE]

Question: <!-- restate the goal from Layer 1 as a direct question -->

Use only the datasets and columns defined above. Flag any assumption you make.
```
