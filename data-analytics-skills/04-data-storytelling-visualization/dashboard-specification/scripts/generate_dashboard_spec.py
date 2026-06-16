"""
generate_dashboard_spec.py — CLI tool to scaffold a dashboard specification document
for NYC DOT Sidewalk Inspection & Management dashboards.

Usage:
    python generate_dashboard_spec.py --name "Ramp Completion" --audience "DOT Leadership" \
        --question "Which boroughs are falling behind on ramp completion?" \
        --datasets ramp_progress violations --output ramp_completion_spec.md
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

AUDIENCE_PROFILES = {
    "field-inspector": {
        "visit_frequency": "Daily",
        "primary_questions": [
            "Which blocks are due for inspection today?",
            "What violations were flagged in my zone this week?",
            "Are any inspections overdue?",
        ],
        "key_decisions": ["Prioritise inspection routes", "Escalate critical violations"],
        "technical_comfort": "Low — prefers maps and simple counts over charts",
    },
    "operations-manager": {
        "visit_frequency": "Weekly",
        "primary_questions": [
            "How is completion rate trending across boroughs?",
            "Are any SLAs at risk this month?",
            "Where are inspection backlogs building up?",
        ],
        "key_decisions": [
            "Reallocate field resources",
            "Trigger escalation to DOT leadership",
        ],
        "technical_comfort": "Medium — comfortable with bar/line charts and drill-downs",
    },
    "dot-leadership": {
        "visit_frequency": "Monthly",
        "primary_questions": [
            "What is the borough-level ramp completion rate?",
            "Are we on track for program targets?",
            "What is the quality score trend for inspection data?",
        ],
        "key_decisions": [
            "Budget allocation and reallocation",
            "Program escalation to Commissioner",
        ],
        "technical_comfort": "Low — needs KPIs and 1–2 charts with clear callouts",
    },
    "city-council": {
        "visit_frequency": "Quarterly",
        "primary_questions": [
            "How does my district compare to the citywide average?",
            "Are ADA ramp commitments being met?",
            "What is the violation resolution rate?",
        ],
        "key_decisions": ["Oversight hearings", "Budget amendments"],
        "technical_comfort": "Low — needs infographic-style summaries",
    },
}

DATASET_REGISTRY = {
    "inspection": {
        "fourfour": "dntt-gqwq",
        "refresh": "Daily",
        "rows": "~398K",
        "sla": "HIGH (14 days)",
    },
    "violations": {
        "fourfour": "6kbp-uz6m",
        "refresh": "Daily",
        "rows": "~312K",
        "sla": "HIGH (14 days)",
    },
    "ramp_progress": {
        "fourfour": "e7gc-ub6z",
        "refresh": "Daily",
        "rows": "~187K",
        "sla": "HIGH (14 days)",
    },
    "ramp_complaints": {
        "fourfour": "jagj-gttd",
        "refresh": "Daily",
        "rows": "~6K",
        "sla": "MED (30 days)",
    },
    "dismissals": {
        "fourfour": "p4u2-3jgx",
        "refresh": "Daily",
        "rows": "~85K",
        "sla": "HIGH (14 days)",
    },
}

BOROUGHS = ["MN (Manhattan)", "BX (Bronx)", "BK (Brooklyn)", "QN (Queens)", "SI (Staten Island)"]


def format_audience_block(audience_key: str) -> str:
    profile = AUDIENCE_PROFILES.get(audience_key)
    if not profile:
        return f"**{audience_key}** — (custom audience, profile not in registry)\n"

    lines = [
        f"**{audience_key.replace('-', ' ').title()}**",
        f"- Visit frequency: {profile['visit_frequency']}",
        "- Primary questions:",
    ]
    for q in profile["primary_questions"]:
        lines.append(f"  - {q}")
    lines.append("- Key decisions:")
    for d in profile["key_decisions"]:
        lines.append(f"  - {d}")
    lines.append(f"- Technical comfort: {profile['technical_comfort']}")
    return "\n".join(lines)


def format_dataset_block(dataset_keys: list[str]) -> str:
    lines = []
    for key in dataset_keys:
        info = DATASET_REGISTRY.get(key)
        if info:
            lines.append(f"**{key}** (`{info['fourfour']}`)")
            lines.append(f"  - Rows: {info['rows']}")
            lines.append(f"  - Refresh: {info['refresh']}")
            lines.append(f"  - SLA tier: {info['sla']}")
        else:
            lines.append(f"**{key}** — (not in registry, verify fourfour manually)")
        lines.append("")
    return "\n".join(lines)


def generate_spec(args: argparse.Namespace) -> str:
    audiences = args.audience if isinstance(args.audience, list) else [args.audience]
    datasets = args.datasets if args.datasets else []
    today = datetime.now().strftime("%Y-%m-%d")

    audience_section = "\n\n".join(format_audience_block(a) for a in audiences)
    dataset_section = format_dataset_block(datasets)

    return f"""# Dashboard Specification: {args.name}

**Version:** 1.0-draft
**Created:** {today}
**Author:** (fill in)
**Status:** Draft — pending stakeholder review

---

## 1. Purpose Statement

> This dashboard answers **"{args.question}"**
> for **{", ".join(audiences)}**
> who need to **{args.decision or "(fill in: the decision or action this dashboard enables)"}**.

---

## 2. User Profiles

{audience_section}

---

## 3. Metric Hierarchy

### Primary KPIs (max 3–5, shown top of page)

| Metric | Definition | Source | Refresh |
|--------|-----------|--------|---------|
| (fill in) | | | |
| (fill in) | | | |
| (fill in) | | | |

### Secondary Metrics (supporting context)

| Metric | Definition | Source |
|--------|-----------|--------|
| (fill in) | | |
| (fill in) | | |

### Detail Breakdowns

Borough filter: {", ".join(BOROUGHS)}

- (fill in breakdown 1, e.g. completion rate by borough)
- (fill in breakdown 2, e.g. violation rate by inspection type)
- (fill in breakdown 3, e.g. SLA compliance trend)

> **Scope check:** If total metrics exceed 12, split into separate dashboards by audience.

---

## 4. Information Architecture

```
[HERO SECTION]
  Primary KPI 1 | Primary KPI 2 | Primary KPI 3
  Trend sparkline (last 90 days)

[TREND SECTION]
  Time-series chart — (fill in metric) over last 12 months
  Borough toggle filter

[BREAKDOWN SECTION]
  Borough comparison bar chart
  Drill-down: click borough → block-level detail

[DETAIL TABLE]
  Paginated table of individual records
  Export to CSV/Excel
```

Layout principle: hero top-left → trends → breakdowns → details. Most actionable content must be visible without scrolling.

---

## 5. Interactivity

| Interaction | Purpose | Justified? |
|-------------|---------|-----------|
| Borough filter | Scope to user's operational area | Yes — field teams are borough-scoped |
| Date range picker | Compare periods | Yes — supports trend analysis |
| SLA threshold toggle | Show/hide at-risk datasets | Yes — direct operational decision |
| Drill-down on borough | Navigate to block-level | Yes — root cause investigation |
| (add/remove rows) | | |

> Remove any filter that doesn't directly support a listed key decision.

---

## 6. Data Requirements

{dataset_section}
**Refresh strategy:** Nightly APScheduler prefetch. Delta fetch via DuckDB L2 cache.
**Known issues:**
- `ramp_locations` stale since 2021 — use `ramp_progress` instead
- `capital_blocks` is empty (0 rows) — use `capital_intersections`
- `permit_stipulations` returns API 403 — do not use

---

## 7. Success Criteria

- [ ] Dashboard answers the purpose statement question in under 60 seconds for the target audience
- [ ] Primary KPIs visible without scrolling on a 1080p display
- [ ] All data sources refresh at or before their SLA threshold
- [ ] Chart titles state the finding, not the variable name
- [ ] Passes accessibility check: works in greyscale, all colors accessible (WCAG AA)
- [ ] Stakeholder sign-off: (name, date)

---

## 8. Out of Scope

(List items explicitly excluded to prevent scope creep)

- (fill in)
- (fill in)

---

## 9. Open Questions

| # | Question | Owner | Due |
|---|---------|-------|-----|
| 1 | (fill in) | | |
| 2 | (fill in) | | |
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scaffold a NYC DOT dashboard specification document."
    )
    parser.add_argument("--name", required=True, help="Dashboard name (e.g. 'Ramp Completion')")
    parser.add_argument(
        "--audience",
        required=True,
        nargs="+",
        choices=list(AUDIENCE_PROFILES.keys()) + ["public"],
        help="Target audience(s). Choose from: " + ", ".join(AUDIENCE_PROFILES.keys()),
    )
    parser.add_argument(
        "--question",
        required=True,
        help="Primary business question the dashboard answers (quoted string)",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=[],
        choices=list(DATASET_REGISTRY.keys()),
        help="Dataset keys from registry (e.g. ramp_progress violations)",
    )
    parser.add_argument(
        "--decision",
        default="",
        help="The decision or action this dashboard enables",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path (.md). Defaults to stdout.",
    )

    args = parser.parse_args()
    spec = generate_spec(args)

    if args.output:
        Path(args.output).write_text(spec, encoding="utf-8")
        print(f"Dashboard spec written to: {args.output}", file=sys.stderr)
    else:
        print(spec)


if __name__ == "__main__":
    main()
