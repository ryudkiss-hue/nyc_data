# NYC DOT SIM Division — Domain Context

## Project Mission

Build and operate a unified data platform (Dash Mission Control) for NYC Department of Transportation's Sidewalk Inspection & Management (SIM) Division. Analyze 48+ datasets from NYC Open Data to track sidewalk condition, accessibility, equity, and operational efficiency.

## Core Domain Concepts

### Entities

**Sidewalk Segment** — A discrete section of sidewalk (typically 5,000 sq ft or less) uniquely identified by geometry and location. The primary analytical unit.

**Sidewalk Condition Assessment** — A detailed inspection recording condition across multiple distress types (cracks, trips, heave, tree damage). Stored in `violations` dataset.

**Accessibility Feature** — Infrastructure element enabling pedestrian access: curb ramps, truncated dome warnings, level surfaces. Tracked in `ramp_progress` dataset.

**Curb Ramp** — ADA-compliant structure connecting curb to sidewalk at slope ≤1:12. Target: 100% coverage.

### Metrics

**Sidewalk Condition Index (SCI)** — 0–100 score aggregating distress severity. Targets:
- 80–100: Excellent (no maintenance)
- 60–79: Good (preventative only)
- 40–59: Fair (corrective maintenance soon)
- 20–39: Poor (significant damage)
- 0–19: Failed (replacement needed)

**Maintenance & Repair Index (MRI)** — Percentage of segments requiring maintenance (SCI < 60).

**Service Level Agreement (SLA)** — Performance targets:
- Inspection turnaround: ≤14 days from 311 complaint
- Repair completion: ≤56 days from inspection
- SLA compliance: >95%
- Rework rate: <5%

**Equity Metrics** — Sidewalk Reach Quotient (SRQ), investment equity index, accessibility barrier density by neighborhood.

## Data Architecture

### Layers

**Raw Layer** — Socrata API ingest, one table per dataset, no transformation. ~48 datasets.

**Staging Layer** — Deduplicated, type-cast, validation-checked. Mirrors raw layer structure.

**Analytics Layer** — Materialized KPIs, dimension tables, reporting views. 309+ KPIs across 8 categories.

**Serving Layer** — Dashboard queries, report generators, data exports. (Future: materialized views for performance)

### Core Architectural Components

**Fuzzy Matching Routing Engine** — Central module (`QuestionKPIResolver`) that resolves natural language analyst queries to specific KPIs and datasets using composite scoring models.

**Pipeline Exporter Adapter** — Unified interface (`BaseExporter`) isolating the data ingestion runner from target database platforms (Postgres, Mongo, DuckDB, Excel).

**Spatial Analysis Engine** — Geographic processing module (`SpatialAnalysisEngine`) that manages coordinate transformations (projections) and geometric overlays to identify infrastructure conflicts.

### Critical Datasets (Tier-S)

| Dataset | Role | Criticality | Rows (2026) |
|---------|------|-------------|------------|
| `violations` | Condition assessments | **CRITICAL** | ~398K |
| `ramp_progress` | Ramp inventory + completion | **CRITICAL** | ~187K |
| `complaints_311` | Demand signal, SLA tracking | **CRITICAL** | ~21M |
| `street_centerline` | Geographic framework | **CRITICAL** | ~75K |
| `census_blocks_2020` | Equity analysis context | **HIGH** | ~50K |
| `dismissals` | Repair completion records | **HIGH** | ~85K |
| `ramp_complaints` | Ramp-specific demand | **HIGH** | ~6K |
| `in_house_resurfacing` | Cost/outcome data | **HIGH** | ~602K |

## Research Questions

60+ research questions organized in 8 categories. See `sim_division_research_operational_questions.md` for full list.

**Core Question Examples:**
- A1: What is the current SCI across all boroughs?
- B3: Are low-income neighborhoods systematically underfunded?
- D1: What budget is needed to maintain current condition?
- E1: How many ramps are still needed to meet transition plan?
- F1: Why do some inspections take 30+ days?

## Analyst Roles & Workflows

### SIM Project Analyst (JID-35715/42159)
11 official duties spanning:
- Data monitoring (SCI trends, SLA compliance, quality)
- Budget planning (cost forecasts, equity allocation)
- Equity analysis (access disparities, investment gaps)
- Operational reporting (completion rates, rework analysis)
- Program management (ramp completion tracking)

### Workflow Patterns

**Question-Driven Analysis:** Analyst asks research question → activated skill → pre-populated with datasets → materializes KPI.

**Time-Sensitive:** Condition assessment lag (2–4 weeks) affects decision latency.

**High-Consequence:** Budget decisions affect repair volume; equity errors underserve communities.

## Technology Stack

**Data Pipeline:** Python + DuckDB + MotherDuck (native cloud warehouse)

**Dashboard:** Dash (Plotly) + FastAPI backend + Mantine UI

**CLI:** Python socrata_toolkit library

**Infrastructure:** NYC Open Data (Socrata) + DuckDB + MotherDuck Pro ($99/month)

## Constraints & Assumptions

- **Data Freshness:** Socrata API updates daily; raw ingestion lags 2–4 weeks
- **Pagination:** Datasets >2K rows require pagination; no row limits on ingestion (mandatory)
- **Geography:** All analysis at borough/community-board/segment granularity
- **Equity:** MUST include demographic context; exclude analysis without equity lens
- **No Synthetic Data:** All analysis uses live data; never fabricate statistics
- **Exit Codes:** Pipeline must return explicit codes (0=success, 1=gate failure, 2=critical error)

## Key Decisions (ADRs)

(None recorded yet — add as architectural decisions are made)

## Glossary

See `sim_infrastructure_glossary.md` for comprehensive definitions of:
- Condition metrics (PCI, SCI, distress types)
- Accessibility standards (ADA, curb ramps, truncated domes)
- Asset management (preventative vs. corrective, lifecycle, CIP)
- Equity concepts (fairness, SRQ, investment equity)
- Operational metrics (SLA, rework rate, cost per ramp)
- Analysis concepts (cohort, segmentation, deterioration curves)

