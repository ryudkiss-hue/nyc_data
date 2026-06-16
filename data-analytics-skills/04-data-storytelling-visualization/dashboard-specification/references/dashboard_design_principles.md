# Dashboard Design Principles
## NYC DOT Sidewalk Inspection & Management Platform

---

## Layout and Information Hierarchy

### The Hero → Trends → Breakdowns → Details Pattern

Every DOT dashboard follows this top-to-bottom hierarchy:

1. **Hero (top of page):** 3–5 primary KPIs as large numbers or gauges. The reader must be able to answer the central question without scrolling. Examples: citywide ramp completion %, active violations count, data quality score.

2. **Trends (second section):** One or two time-series charts showing the last 90–365 days. Annotate policy events, data gaps, and SLA thresholds as vertical reference lines.

3. **Breakdowns (third section):** Borough-level comparison. Always show all five boroughs (MN, BX, BK, QN, SI) together — never filter to a single borough by default, as relative performance is the story.

4. **Details (bottom):** Paginated or searchable table. Export to CSV/Excel. This section is optional on executive-facing views.

### F-Pattern Scanning

Place the most critical KPI in the top-left position. Viewers scan F-shaped: left edge, then left-to-right across the top, then down the left edge again. Put alerts and at-risk indicators in the left column.

### Scrolling Budget

Field inspector dashboards: all critical information above the fold (no scroll required).
Operations dashboards: one scroll at most.
Leadership dashboards: fits on a single screen at 1080p.

---

## Metric Hierarchy Rules

- **Max 3–5 primary KPIs.** More than 5 top-level numbers means the dashboard lacks a clear purpose.
- **Max 10–12 total metrics.** Beyond this, split into separate dashboards by audience or workflow.
- **Every metric needs a source and refresh rate.** If you can't state both, the metric isn't ready for the dashboard.
- **Derived metrics must show their numerator and denominator.** Completion rate means nothing without showing completed / total.

---

## Interactivity Guidelines

### Add a filter only if it enables a listed decision

| Filter | Adds value when | Skip when |
|--------|----------------|-----------|
| Borough | Operations are borough-scoped | Leadership needs citywide view only |
| Date range | Trend analysis is a primary use case | Dashboard only shows current state |
| SLA tier | Users manage datasets across tiers | Dashboard covers one tier only |
| Inspection type | Field teams specialise by type | Single inspection type in scope |
| Status (open/closed) | Workflow management is a use case | Read-only reporting dashboard |

### Drill-down depth

Limit to two levels: summary → borough → block. Three levels requires navigation redesign (tabs or sidebar). Never nest drill-downs more than two levels without a breadcrumb.

### Defaults matter more than options

Always set sensible defaults:
- Borough: All (citywide view)
- Date range: Last 90 days
- SLA tier: All

The default view should answer the primary question without any user interaction.

---

## Color Usage

### Semantic palette (non-negotiable for operational dashboards)

| Color | Meaning | Use for |
|-------|---------|---------|
| Green (#2ca02c) | On track / healthy | Completion rate > target, SLA compliant |
| Amber (#ff7f0e) | At risk / warning | Completion rate 10–20% below target, approaching SLA |
| Red (#d62728) | Critical / breached | Completion rate >20% below target, SLA breached |
| Blue (#1f77b4) | Neutral / informational | Primary trend lines, default bars |
| Grey (#7f7f7f) | Context / secondary | Comparison periods, benchmarks |

### Accessibility

- All color pairs must pass WCAG AA contrast ratio (4.5:1 for text, 3:1 for UI elements).
- Never use red/green as the only differentiator — add icons (checkmark / warning triangle) for colorblind viewers.
- Test every chart in greyscale before publishing.

---

## Chart Titles and Annotations

### Title rule: state the finding, not the variable

| Wrong (variable name) | Right (finding) |
|----------------------|----------------|
| "Ramp completion by borough" | "Staten Island ramp completion lags citywide average by 18 pp" |
| "Violation count over time" | "Brooklyn violations increased 23% since February" |
| "Data quality score" | "Inspection data quality dropped below 70 in April" |

### Mandatory annotations

- **SLA threshold line** on all freshness/timeliness charts (dashed grey, labelled)
- **Target/goal line** on completion rate charts (dashed green, labelled with target value)
- **Data as-of date** in chart footer (e.g. "Data as of 2026-06-05")
- **Sample size (n=)** on any chart using Wilson Score CIs

---

## Plotly/Dash Implementation Notes

The production platform uses Plotly/Dash (`src/socrata_toolkit/dashboards/`). Key conventions:

- Use `get_unit_label()` from `src/socrata_toolkit/viz/units.py` for all axis labels.
- Reference `DATA_DICTIONARY.md` for authoritative unit specifications per column.
- Borough colors: use a consistent 5-color categorical palette across all borough charts.
- All callbacks must include `prevent_initial_call=True` where appropriate to avoid redundant API calls on load.
- DuckDB L2 cache (`DUCKDB_PATH`) should be queried first; fall back to live Socrata API only on cache miss.
