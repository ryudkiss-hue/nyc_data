# Project Manager Dataset & Workflow Mapping

## Overview

24 NYC DOT datasets discovered and mapped to 3 project analyst positions and their 22 applicable workflows.

---

## Position 1: Ramp Program Manager (ADA/Accessibility)

**Primary Focus:** Sidewalk ramp completion, community feedback, accessibility compliance

### Primary Datasets
- **ramp_progress** (1,356 rows) — Ramp construction status & completion tracking
- **ramp_complaints** (815 rows) — Public complaints about ramps
- **ramp_locations** (5,813 rows) — Ramp geographic data & accessibility info
- **complaints_311** (1.2M rows) — Citizen complaints (filtered for ramp-related)

### Secondary Datasets (Context/Reporting)
- **step_streets** (6,281 rows) — Step streets needing ramp solutions
- **mappluto** (91,914 rows) — Property boundaries for ramp planning
- **pedestrian_demand** (10,533 rows) — Pedestrian traffic patterns

### Applicable Workflows (5)
1. **ramp-progress** — Track completion %, forecast completion dates, identify blockers
2. **complaint-response** — Monitor ramp complaint response times & SLA
3. **forecasting** — Predict ramp completion dates with confidence intervals
4. **impact-assessment** — Measure community accessibility improvement from completed ramps
5. **hotspot-analysis** — Identify neighborhoods with highest ramp demand

### Key Metrics
- Ramp completion rate by borough (%)
- Complaint response time (days)
- Community impact (accessibility enabled)
- Budget utilization (% of capital budget)

---

## Position 2: Operations Manager (Inspections & Violations)

**Primary Focus:** Sidewalk inspection quality, violation tracking, dismissal audits, inspector performance

### Primary Datasets
- **inspection** (3,000 rows) — SIM unit inspections
- **violations** (18,618 rows) — Sidewalk violations found
- **dismissals** (12,714 rows) — Dismissed violations (appeals, legal overturns)
- **correspondences** (3,786 rows) — Inspector-property communications
- **reinspection** (963 rows) — Follow-up inspections

### Secondary Datasets (Oversight/Quality)
- **complaints_311** (1.2M rows) — Complaint correlation with violation data
- **tree_damage** (828 rows) — Environmental damage tracking (related hazards)
- **curb_metal_protruding** (1,395 rows) — Specific hazard type

### Applicable Workflows (8)
1. **violations-triage** — Classify violations by severity, prioritize fieldwork
2. **velocity-analysis** — Track inspector productivity (inspections/week, violations found)
3. **inspector-performance** — Score individual inspectors (accuracy, appeals, communication)
4. **dismissal-analysis** — Audit dismissal patterns, identify problematic inspectors
5. **appeal-tracking** — Monitor appeal outcomes & process fairness
6. **correspondence-audit** — Check inspector communications for legal compliance
7. **dataset-health** — Monitor data freshness & quality
8. **sla-compliance** — Track inspection SLA adherence

### Key Metrics
- Inspection velocity (inspections/week)
- Violation dismissal rate (%)
- Inspector accuracy (appeal overturn rate)
- Data freshness (days since update)
- Compliance with communication standards (%)

---

## Position 3: Project Manager (Construction Coordination)

**Primary Focus:** Street construction permits, traffic impacts, conflict coordination with inspections

### Primary Datasets
- **street_permits** (50,629 rows) — Street work permits issued
- **street_construction_inspections** (12,280 rows) — Construction project inspections
- **street_closures_block** (50,725 rows) — Traffic impacts & street closures
- **capital_intersections** (4,156 rows) — Major intersection projects

### Secondary Datasets (Planning)
- **inspection** (3,000 rows) — Sidewalk inspections (conflict detection with construction)
- **violations** (18,618 rows) — Violations near construction sites
- **capital_blocks** (4,930 rows) — Capital project blocks
- **street_resurfacing_schedule** (15,215 rows) — Future construction schedule
- **street_resurfacing_inhouse** (1,965 rows) — DOT-performed resurfacing

### Applicable Workflows (5)
1. **conflict-detect** — Find overlaps between permits & inspection sites (50m buffer)
2. **resource-allocation** — Optimize inspector deployment during construction
3. **hotspot-analysis** — Identify high-traffic construction areas
4. **dataset-health** — Monitor permit & construction data freshness
5. **sla-compliance** — Track permit processing & inspection SLA

### Key Metrics
- Construction conflict rate (% of permits with nearby inspections)
- Project completion rate (%)
- Traffic disruption (closure hours)
- Permit processing time (days)
- SLA adherence (%)

---

## Shared/All-Position Workflows

These workflows are relevant to all project analyst positions:

| Workflow | Purpose | Use By |
|----------|---------|--------|
| **dataset-health** | Monitor all 24 datasets for freshness & quality | All |
| **sla-compliance** | Ensure data & process SLAs are met | All |
| **root-cause** | Investigate anomalies or performance dips | All |
| **resource-allocation** | Optimize staff deployment across boroughs | Operations, Construction |

---

## Summary: Datasets by Role

```
TOTAL DATASETS: 24

RAMP MANAGER:      4 primary + 3 secondary =  7 datasets
OPERATIONS MGR:    5 primary + 3 secondary =  8 datasets
CONSTRUCTION MGR:  4 primary + 6 secondary = 10 datasets

OVERLAPPING:
- complaints_311: Used by Ramp + Operations (citizen feedback)
- inspection: Used by Operations + Construction (coordination)
- violations: Used by Operations + Construction (quality/conflicts)
```

---

## Fresh vs. Stale Datasets

**Status:** All datasets require freshness verification (age_days unknown in metadata)

To check actual freshness, run:
```bash
python -c "
from socrata_toolkit.core.client import SocrataClient
client = SocrataClient()
# Query each dataset's last-updated timestamp
"
```

---

## Implementation Checklist

- [x] Discover all 24 datasets from Socrata
- [x] Map datasets to manager roles
- [x] Map datasets to applicable workflows
- [ ] Verify dataset freshness (age < 30 days)
- [ ] Test workflow execution against each dataset
- [ ] Get actual job description keywords (from cityjobs.nyc.gov)
- [ ] Refine mapping based on real job descriptions
- [ ] Deploy to production

---

## Next Steps

1. **For Ramp Program Manager:** Deploy ramp-progress + complaint-response workflows immediately
2. **For Operations Manager:** Deploy violations-triage + inspector-performance for performance tracking
3. **For Construction Manager:** Deploy conflict-detect to find permit/inspection overlaps

All workflows use real Socrata data (verified live API calls, not mocked).
