"""
generate_exec_summary.py — CLI tool to scaffold a 1-page executive summary for NYC DOT
Sidewalk Inspection & Management analysis.

Accepts raw findings as bullet points or a text file and produces a structured,
decision-ready summary following the pyramid principle.

Usage:
    python generate_exec_summary.py \
        --title "Q2 2026 Ramp Completion Review" \
        --audience dot-leadership \
        --decision "Approve inspector reallocation to Brooklyn and Queens" \
        --findings findings.txt \
        --output exec_summary_q2.md

    # With inline findings:
    python generate_exec_summary.py \
        --title "May Violation Trend Alert" \
        --audience operations-manager \
        --decision "Adjust May inspection schedule to prioritise open violations" \
        --finding "Brooklyn violations up 23% vs April" \
        --finding "Queens SLA breach rate reached 18%" \
        --finding "Citywide quality score dropped from 78 to 71" \
        --output may_violation_alert.md
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

AUDIENCE_PROFILES = {
    "dot-leadership": {
        "label": "DOT Commissioner / Deputy Commissioner",
        "reading_time": "3 minutes",
        "priorities": "program targets, budget efficiency, political and ADA risk",
        "jargon_level": "minimal — avoid internal dataset names; use program language",
    },
    "operations-manager": {
        "label": "Borough Operations Manager",
        "reading_time": "5 minutes",
        "priorities": "inspection velocity, crew utilisation, backlog clearance",
        "jargon_level": "moderate — can reference borough codes and inspection types",
    },
    "city-council": {
        "label": "City Council Member or Committee Staff",
        "reading_time": "3 minutes",
        "priorities": "district outcomes, ADA commitments, budget accountability",
        "jargon_level": "none — plain language, constituent framing",
    },
    "dot-data-team": {
        "label": "DOT Data Engineering / Analytics Team",
        "reading_time": "5 minutes",
        "priorities": "data quality, SLA compliance, schema health, pipeline reliability",
        "jargon_level": "high — can reference dataset fourfours, DuckDB, SLA tiers",
    },
}

DECISION_BLOCK_DEFAULTS = {
    "dot-leadership": {
        "approval_needed": "Commissioner or Deputy Commissioner sign-off",
        "urgency": "Decision needed before next budget cycle / before field reallocation window",
    },
    "operations-manager": {
        "approval_needed": "Borough Manager sign-off",
        "urgency": "Decision needed before next weekly scheduling cycle",
    },
    "city-council": {
        "approval_needed": "Committee vote or budget amendment",
        "urgency": "Decision needed before [HEARING DATE]",
    },
    "dot-data-team": {
        "approval_needed": "Team lead or architecture review",
        "urgency": "Decision needed before next nightly scheduler run / before next data refresh",
    },
}


def load_findings(args: argparse.Namespace) -> list[str]:
    findings = list(args.finding) if args.finding else []
    if args.findings:
        path = Path(args.findings)
        if not path.exists():
            print(f"Error: findings file not found: {args.findings}", file=sys.stderr)
            sys.exit(1)
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip().lstrip("-•*").strip()
            if line:
                findings.append(line)
    return findings


def format_findings_table(findings: list[str]) -> str:
    if not findings:
        return "| 1 | [Fill in finding] | [Impact] | [High / Med / Low] |\n"

    rows = []
    for i, f in enumerate(findings[:5], 1):
        rows.append(f"| {i} | {f} | (fill in: quantified impact) | (fill in: High / Med / Low) |")
    return "\n".join(rows) + "\n"


def format_recommendations(n: int = 3) -> str:
    lines = []
    for i in range(1, n + 1):
        lines.append(
            f"| {i} | (fill in: what to do) | (fill in: owner role) | (fill in: date) | (fill in: expected outcome) |"
        )
    return "\n".join(lines) + "\n"


def generate_summary(args: argparse.Namespace, findings: list[str]) -> str:
    profile = AUDIENCE_PROFILES.get(args.audience, AUDIENCE_PROFILES["dot-leadership"])
    decision_defaults = DECISION_BLOCK_DEFAULTS.get(args.audience, {})
    today = datetime.now().strftime("%Y-%m-%d")

    finding_preview = findings[0] if findings else "[key finding not yet specified]"
    findings_table = format_findings_table(findings)
    recommendations = format_recommendations(3)

    return f"""# Executive Summary: {args.title}

**Date:** {today}
**Prepared for:** {profile["label"]}
**Prepared by:** (fill in)
**Reading time:** {profile["reading_time"]}
**Data as of:** (fill in)

---

## Bottom Line

> **{finding_preview}**
>
> [One additional sentence expanding the key implication.
> Example: "This is the largest single-quarter decline in three years and requires immediate action
> to avoid missing the fiscal-year completion target."]
>
> **Recommended action:** {args.decision}

---

## Key Findings

*Up to 5 findings that change or reinforce the decision. Exclude supporting detail.*

| # | Finding | Quantified impact | Confidence |
|---|---------|------------------|-----------|
{findings_table}
**Borough breakdown:**

| Borough | Key metric | Status |
|---------|-----------|--------|
| MN (Manhattan) | (fill in) | On track / At risk / Critical |
| BX (Bronx) | (fill in) | On track / At risk / Critical |
| BK (Brooklyn) | (fill in) | On track / At risk / Critical |
| QN (Queens) | (fill in) | On track / At risk / Critical |
| SI (Staten Island) | (fill in) | On track / At risk / Critical |

*Data source: (fill in dataset key + fourfour). n=(fill in). Rates use 95% Wilson Score CI.*

---

## Recommendations

| # | What to do | Who | By when | Expected outcome |
|---|-----------|-----|---------|----------------|
{recommendations}
---

## Decision Block

| Element | Detail |
|---------|--------|
| **Decision required** | {args.decision} |
| **Decision owner** | {decision_defaults.get("approval_needed", "(fill in)")} |
| **Deadline** | {decision_defaults.get("urgency", "(fill in)")} |
| **Investment required** | (fill in: resource, budget, or approval needed) |
| **Expected return** | (fill in: quantified outcome if action is taken) |
| **Risk if no action** | (fill in: consequence in concrete terms, e.g. "Borough will miss Q3 target by 15 pp") |

---

## What Was Excluded

*(Brief note on what is NOT in this summary — important for executives who will ask)*

- Full data quality detail and SLA metrics — see separate data health report
- Block-level breakdown — available on request or in the operations dashboard
- Prior-period trend detail beyond the key comparison — see appendix in full analysis

---

*Audience calibration note: {profile["priorities"]}. Jargon guidance: {profile["jargon_level"]}.*
*Full analysis and supporting data available at: (fill in path or link)*
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a 1-page executive summary scaffold for NYC DOT analysis."
    )
    parser.add_argument("--title", required=True, help="Summary title")
    parser.add_argument(
        "--audience",
        required=True,
        choices=list(AUDIENCE_PROFILES.keys()),
        help="Target audience: " + ", ".join(AUDIENCE_PROFILES.keys()),
    )
    parser.add_argument(
        "--decision",
        required=True,
        help="The decision the executive needs to make (quoted string)",
    )
    parser.add_argument(
        "--finding",
        action="append",
        default=[],
        help="A finding bullet point (repeat flag for multiple findings, up to 5)",
    )
    parser.add_argument(
        "--findings",
        default=None,
        help="Path to a text file with one finding per line",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path (.md). Defaults to stdout.",
    )

    args = parser.parse_args()
    findings = load_findings(args)

    if not findings:
        print(
            "Warning: no findings provided. Use --finding or --findings to pre-populate.",
            file=sys.stderr,
        )

    if len(findings) > 5:
        print(
            f"Warning: {len(findings)} findings provided; only the first 5 will be included "
            "(executive summaries cap at 5 insights).",
            file=sys.stderr,
        )

    summary = generate_summary(args, findings[:5])

    if args.output:
        Path(args.output).write_text(summary, encoding="utf-8")
        print(f"Executive summary written to: {args.output}", file=sys.stderr)
    else:
        print(summary)


if __name__ == "__main__":
    main()
