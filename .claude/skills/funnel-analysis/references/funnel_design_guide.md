# Funnel Design Guide — NYC DOT SIM

Reference for defining, measuring, and avoiding pitfalls in inspection workflow funnel analyses.

---

## Standard NYC DOT Inspection Funnel

```
[1] Inspection Record Created  (created_date populated)
        ↓  ~88% assignment rate
[2] Assigned to Inspector      (assigned_date populated)
        ↓  ~82% inspection rate
[3] Inspection Conducted       (inspection_date populated)
        ↓  ~58% violation rate
[4] Violation Issued           (violation_date populated)
        ↓  ~71% resolution rate
[5] Resolved / Completed       (completion_date populated)
```

**End-to-end conversion (expected):** ~30–35% of all created records result in a resolved violation within 90 days.

---

## Ramp Program Funnel

```
[1] Ramp Location Identified   (ramp_progress: created_date)
        ↓
[2] Complaint Filed (if any)   (ramp_complaints: created_date)
        ↓
[3] Work Scheduled             (scheduled_date populated)
        ↓
[4] Work Completed             (completion_date populated, status = 'COMPLETED')
```

---

## Completion Window Rules

| Funnel Type | Recommended Window | Rationale |
|---|---|---|
| Inspection → Resolution | 90 days | HIGH SLA = 14d, but full resolution takes longer |
| Ramp: Complaint → Completion | 180 days | Ramp construction timelines |
| Violation → Dismissal | 60 days | Dismissal typically occurs within 30–60d |
| 311 Complaint → Resolution | 30 days | DOT 311 SLA target |

**Rule:** A user/record must complete ALL steps within the window from their first step to count as converted. Do not use a global date cutoff — this creates survivor bias.

---

## Common Measurement Pitfalls

### 1. Using Global Date Filters Instead of Per-Record Windows
**Wrong:** Filter all steps to records where `inspection_date BETWEEN '2025-01-01' AND '2025-12-31'`
**Right:** Filter records with `created_date IN 2025`, then track all events within 90d from their `created_date`

### 2. Counting Multi-Step Events Twice
If a record has two violation dates, count it once at the violation step.
Use `MIN(violation_date)` or `FIRST(violation_date)` for funnel membership.

### 3. Including In-Progress Records at Late Stages
Records created recently may not yet have had time to reach later funnel steps.
Apply right-censoring: only include cohorts at least as old as the completion window.

### 4. Confusing "No Data" with "Did Not Convert"
A null `inspection_date` might mean: (a) not yet inspected, (b) inspection date not recorded, or (c) cancelled.
Always audit null rates per column before using as funnel step.

### 5. Ignoring Step Order
Funnel steps must occur in sequence. A record with `completion_date < created_date` has a data error.
Validate: `step_n_date >= step_(n-1)_date` for all records.

---

## Drop-Off Prioritisation Formula

```
priority_score = users_lost_at_step × avg_value_per_completion

# NYC DOT proxy values (estimated):
avg_value_per_resolved_violation ≈ $850 (remediation + enforcement cost savings)
avg_value_per_ramp_completion ≈ $4,200 (estimated accessibility improvement value)
```

Rank improvement opportunities by `priority_score`, not just absolute drop %.

---

## Segmentation Variables

| Variable | Column | Use Case |
|---|---|---|
| Borough | `borough` | Identify geographic bottlenecks |
| Defect type | `defect_type` | Structural vs. surface defects take different paths |
| Material type | `material_type` | Asphalt vs. concrete repair timelines differ |
| Inspector unit | `unit_id` | Workload distribution and efficiency gaps |
| Month created | `created_date` month | Seasonal capacity effects |

---

## Funnel Quality Checklist

Before presenting funnel results:
- [ ] Completion window defined and applied per-record (not globally)
- [ ] Step ordering validated (no date inversions)
- [ ] Null rate per column audited and documented
- [ ] Cancelled/withdrawn records excluded with count noted
- [ ] Right-censoring applied (recent cohorts excluded from late-step analysis)
- [ ] At least 100 records per segment for segment analysis
- [ ] Biggest drop-off step identified and investigated
