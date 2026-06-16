# Metric Definitions — NYC DOT SIM Operations

Canonical definitions for all program-level metrics. Use these when there is disagreement about how a metric is calculated.

---

## Throughput Metrics

### Inspection Completion Rate
```
completion_rate = completed_inspections / total_assigned_inspections
```
- Numerator: `status = 'COMPLETED'` in `inspection` (dntt-gqwq)
- Denominator: All records in scope period (excludes cancelled/withdrawn)
- Period: Monthly, trailing 3M rolling, YTD
- **Benchmarks:** Good ≥ 75% | Average 60–74% | Poor < 60%

### Inspection Throughput (Volume)
```
throughput = COUNT(objectid) WHERE status = 'COMPLETED' AND inspection_date BETWEEN [start] AND [end]
```
- Report as: absolute count, MoM % change, rolling 3M average
- Segment by: borough, unit_id, defect_type, material_type

### Month-over-Month Growth
```
mom_growth = (current_month - prior_month) / prior_month
```

---

## Resolution Metrics

### Violation Resolution Rate (30-day)
```
resolution_rate_30d = violations_closed_within_30d / violations_opened
```
- Source: `violations` (6kbp-uz6m)
- Window: 30 calendar days from `created_date`
- **Benchmarks:** Good ≥ 70% | Average 55–69% | Poor < 55%

### Dismissal Rate
```
dismissal_rate = dismissed_inspections / total_inspections
```
- Source: `dismissals` (p4u2-3jgx)
- High dismissal rate (>30%) may indicate data quality or workflow issues
- **Benchmarks:** Good < 20% | Average 20–30% | Poor > 30%

---

## SLA Metrics

### SLA Tiers (NYC DOT Default)
| Tier | Threshold | Dataset Category |
|---|---|---|
| HIGH | 14 days | `inspection`, `violations` |
| MEDIUM | 30 days | `ramp_complaints`, `ramp_progress` |
| LOW | 60 days | `correspondences`, overlay datasets |

### SLA Compliance Rate
```
compliance_rate = records_closed_within_SLA_days / total_closed_records
```

### SLA Breach Rate
```
breach_rate = records_exceeding_SLA_days / total_records
```
- **Benchmarks (HIGH tier):** Good < 15% | Average 15–25% | Poor > 25%

### Days to Close (P50, P90)
- P50 (median): typical experience
- P90: tail experience — useful for catching chronic backlog cases
- Formula: `completion_date - created_date` in calendar days

---

## Unit Economics

### Cost per Inspection (CPI)
```
CPI = total_program_cost / completed_inspections
```
- Use fiscal year cost for annual CPI
- Segment by borough to identify efficiency gaps

### Inspections per Inspector per Month
```
productivity = COUNT(objectid) GROUP BY unit_id, month
```
- Useful for capacity planning and workload balancing

---

## Ramp Program Metrics

### Borough Ramp Completion Rate
```
completion_rate = completed_ramps / total_ramps_in_scope
```
- Source: `ramp_progress` (e7gc-ub6z)
- Include 95% Wilson Score CI when n < 1000 per borough
- **Benchmarks:** Good ≥ 70% | Average 50–69% | Poor < 50%

### Ramp Complaint Rate
```
complaint_rate = ramp_complaints / total_ramps
```
- Source: `ramp_complaints` (jagj-gttd)
- High complaint rate (>5%) suggests quality or access issues

---

## Quick Ratio (Program Health)

Adapted from SaaS: measures whether program is net improving or declining.
```
quick_ratio = (new_completions + reactivated) / (new_violations + escalations)
```
- Quick ratio > 1.0 = program reducing backlog (growing)
- Quick ratio < 1.0 = backlog growing (declining)
- **Target:** ≥ 1.25

---

## Benchmark Comparison Table

| Metric | Good | Average | Poor | NYC DOT Target |
|---|---|---|---|---|
| Completion rate | ≥ 75% | 60–74% | < 60% | 78% |
| Resolution rate (30d) | ≥ 70% | 55–69% | < 55% | 72% |
| SLA compliance (HIGH) | ≥ 85% | 75–84% | < 75% | 87% |
| Breach rate (HIGH) | < 15% | 15–25% | > 25% | < 13% |
| Dismissal rate | < 20% | 20–30% | > 30% | < 22% |
| Ramp completion | ≥ 70% | 50–69% | < 50% | 73% |
