"""
build_narrative.py — CLI tool to scaffold a data narrative document for NYC DOT SIM analysis.

Generates a fill-in-the-blank narrative structure based on the chosen framework and audience,
pre-populated with DOT-specific placeholders.

Usage:
    python build_narrative.py --framework scr --audience dot-leadership \
        --finding "Brooklyn ramp completion dropped 12pp in Q2" \
        --decision "Reallocate 15 additional inspectors to Brooklyn" \
        --output brooklyn_narrative.md

    python build_narrative.py --framework wswnw --audience city-council \
        --finding "ADA ramp completion is 67% citywide, below the 75% target" \
        --decision "Approve additional capital funding for ramp program" \
        --output council_brief.md
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

FRAMEWORKS = {
    "scr": "Situation–Complication–Resolution",
    "wswnw": "What–So What–Now What",
    "bab": "Before–After–Bridge",
}

AUDIENCE_CONTEXT = {
    "dot-leadership": {
        "role": "DOT Commissioner / Deputy Commissioner",
        "cares_about": "program targets, budget efficiency, political risk",
        "already_knows": "SIM program structure, borough operations",
        "tone": "direct, action-oriented, quantified",
        "format": "1-page memo or 3-slide deck",
    },
    "operations-manager": {
        "role": "Borough Operations Manager",
        "cares_about": "inspection velocity, crew utilisation, backlog reduction",
        "already_knows": "day-to-day field operations, inspection types",
        "tone": "operational, specific to their borough",
        "format": "weekly briefing email or dashboard callout",
    },
    "city-council": {
        "role": "City Council Member / Staff",
        "cares_about": "constituent impact, ADA compliance, budget accountability",
        "already_knows": "district geography; not DOT operations detail",
        "tone": "plain language, constituent-focused",
        "format": "one-page briefing or committee testimony",
    },
    "field-inspector": {
        "role": "SIM Field Inspector",
        "cares_about": "today's assignments, clear priorities, safety",
        "already_knows": "inspection procedures, borough geography",
        "tone": "direct, minimal jargon, action-first",
        "format": "mobile-friendly daily briefing",
    },
    "public": {
        "role": "NYC Resident",
        "cares_about": "neighborhood safety, ADA access, government accountability",
        "already_knows": "nothing about DOT operations",
        "tone": "plain language, concrete examples, avoid acronyms",
        "format": "press release or public dashboard callout",
    },
}

BOROUGH_NAMES = {
    "MN": "Manhattan",
    "BX": "Bronx",
    "BK": "Brooklyn",
    "QN": "Queens",
    "SI": "Staten Island",
}


def scr_template(finding: str, decision: str, audience_key: str) -> str:
    ctx = AUDIENCE_CONTEXT.get(audience_key, {})
    return f"""## Narrative Framework: Situation–Complication–Resolution

**Best for:** Problem/solution stories, escalation briefs, budget requests
**Audience:** {ctx.get("role", audience_key)}
**Format:** {ctx.get("format", "(fill in)")}

---

### SITUATION
*(Establish shared context — what your audience already knows and accepts as true)*

[1–2 sentences maximum. State the status quo. Example:]

> NYC DOT's Sidewalk Inspection & Management (SIM) program conducts [N] inspections
> annually across all five boroughs, with a citywide ramp completion target of [TARGET]%.

---

### COMPLICATION
*(Introduce the problem, tension, or surprising finding — this is the "but then...")*

[1–3 sentences. Lead with the central finding. Quantify. Example:]

> **[FINDING: {finding}]**
>
> This represents [change direction: a decline of / an increase of] [X]% compared to [reference period].
> At the current trajectory, the borough will miss its [YEAR] target by [MAGNITUDE] — affecting an
> estimated [N] pedestrians who rely on accessible routes daily.

**Supporting evidence (include in appendix or footnote, not body):**
- Data source: [dataset key, e.g. ramp_progress (e7gc-ub6z)]
- Data as of: [DATE]
- Sample: n=[N]; confidence interval: [XX–XX]% (95% Wilson Score)

---

### RESOLUTION
*(The clear path forward — what should happen, who should do it, by when)*

[2–4 sentences. State the recommendation answer-first. Example:]

> **Recommended action:** {decision}
>
> Specifically: [concrete steps — what, who, by when]
> - Step 1: [Action] — Owner: [NAME/ROLE] — By: [DATE]
> - Step 2: [Action] — Owner: [NAME/ROLE] — By: [DATE]
>
> Expected outcome: [quantified result, e.g. "Restoring Brooklyn to its 75% completion rate
> by Q4 2026 requires 15 additional inspector-weeks before September."]

---

### OPENING (capture attention in < 10 seconds)

Choose one:
- **Striking number:** "[N] Brooklyn sidewalk ramps are inaccessible to wheelchair users right now."
- **Counterintuitive finding:** "Despite a record inspection budget, Brooklyn's completion rate is at a 3-year low."
- **Direct question:** "How many additional inspectors does it take to close Brooklyn's ramp gap by Q4?"

### CLOSING (concrete call to action)

> **Decision needed by [DATE]:** [Decision owner] must [specific action].
> Investment required: [resource / budget].
> If no action: [consequence in concrete terms].

---

*Audience note: {ctx.get("cares_about", "(fill in)")}. Tone: {ctx.get("tone", "(fill in)")}.*
"""


def wswnw_template(finding: str, decision: str, audience_key: str) -> str:
    ctx = AUDIENCE_CONTEXT.get(audience_key, {})
    return f"""## Narrative Framework: What–So What–Now What

**Best for:** Findings briefings, status updates, committee presentations
**Audience:** {ctx.get("role", audience_key)}
**Format:** {ctx.get("format", "(fill in)")}

---

### WHAT
*(State the factual finding — no interpretation yet)*

> **Finding:** {finding}
>
> [Supporting context:]
> - Metric: [METRIC NAME], measured as [DEFINITION]
> - Period: [DATE RANGE]
> - Comparison: [vs. prior period / vs. target / vs. peer borough]
> - Data source: [dataset key + fourfour]
> - Confidence: n=[N]; [95% CI if applicable]

---

### SO WHAT
*(Why does this finding matter to this audience?)*

**Operational impact:**
> [What does this mean for the program, field teams, or residents?]
> Example: "At this completion rate, [BOROUGH] will serve [N] fewer accessible-route users than planned,
> increasing 311 complaint volume by an estimated [N]% and ADA grievance risk."

**Financial or resource impact:**
> [Quantify where possible.]
> Example: "Clearing the current backlog requires [N] inspector-weeks, costing approximately $[AMOUNT]
> at current overtime rates."

**Trend risk:**
> [Is this worsening? What happens if nothing changes?]
> Example: "If the current trajectory holds, the borough will miss its year-end target by [X] pp —
> the third consecutive quarter of decline."

---

### NOW WHAT
*(The recommended next action — specific, owned, time-bound)*

| Priority | Action | Owner | Deadline | Expected outcome |
|---------|--------|-------|---------|-----------------|
| 1 | [ACTION] | [ROLE] | [DATE] | [OUTCOME] |
| 2 | [ACTION] | [ROLE] | [DATE] | [OUTCOME] |
| 3 | [ACTION] | [ROLE] | [DATE] | [OUTCOME] |

> **Decision needed:** {decision}
> **Decision owner:** [NAME / ROLE]
> **Deadline:** [DATE]

---

*Audience note: {ctx.get("cares_about", "(fill in)")}. Tone: {ctx.get("tone", "(fill in)")}.*
"""


def bab_template(finding: str, decision: str, audience_key: str) -> str:
    ctx = AUDIENCE_CONTEXT.get(audience_key, {})
    return f"""## Narrative Framework: Before–After–Bridge

**Best for:** Change stories, program updates, impact reports, "here's what we did" narratives
**Audience:** {ctx.get("role", audience_key)}
**Format:** {ctx.get("format", "(fill in)")}

---

### BEFORE
*(Establish the baseline — the problem or state that existed)*

> [Describe the situation before the change, intervention, or finding period.]
> Example: "In Q1 2026, [BOROUGH] ramp completion stood at [X]%, with a backlog of [N] outstanding
> inspections and a data freshness SLA breach rate of [X]%."

**Baseline metrics:**
| Metric | Value | Period |
|--------|-------|--------|
| [METRIC 1] | [VALUE] | [BEFORE PERIOD] |
| [METRIC 2] | [VALUE] | [BEFORE PERIOD] |

---

### AFTER
*(Describe the current state — the outcome, finding, or change)*

> **[FINDING: {finding}]**
>
> [Describe what changed and by how much.]
> Example: "Following [INTERVENTION/PERIOD], completion rate moved to [Y]%, representing a
> [X]-percentage-point [increase / decrease]."

**Current metrics:**
| Metric | Value | Period | Change |
|--------|-------|--------|--------|
| [METRIC 1] | [VALUE] | [AFTER PERIOD] | [+/- X] |
| [METRIC 2] | [VALUE] | [AFTER PERIOD] | [+/- X] |

---

### BRIDGE
*(Connect before → after → explain why, and what comes next)*

**Why did this change happen?**
> [Root cause or contributing factors — use data, not opinion.]
> Example: "The decline correlates with a [N]% reduction in inspector-days due to [CAUSE], combined
> with a [N]% increase in new ramp orders in [BOROUGH]."

**What comes next?**
> **Recommended action:** {decision}
> - [Step 1]: [ACTION] by [DATE] — Owner: [ROLE]
> - [Step 2]: [ACTION] by [DATE] — Owner: [ROLE]
>
> **Target state by [DATE]:** [METRIC] returns to [TARGET VALUE].

---

*Audience note: {ctx.get("cares_about", "(fill in)")}. Tone: {ctx.get("tone", "(fill in)")}.*
"""


TEMPLATES = {
    "scr": scr_template,
    "wswnw": wswnw_template,
    "bab": bab_template,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scaffold a data narrative for NYC DOT SIM analysis."
    )
    parser.add_argument(
        "--framework",
        required=True,
        choices=list(FRAMEWORKS.keys()),
        help="Narrative framework: scr (Situation-Complication-Resolution), "
        "wswnw (What-So What-Now What), bab (Before-After-Bridge)",
    )
    parser.add_argument(
        "--audience",
        required=True,
        choices=list(AUDIENCE_CONTEXT.keys()),
        help="Target audience: " + ", ".join(AUDIENCE_CONTEXT.keys()),
    )
    parser.add_argument(
        "--finding",
        required=True,
        help="The central finding to build the narrative around (quoted string)",
    )
    parser.add_argument(
        "--decision",
        required=True,
        help="The decision or action the narrative should drive (quoted string)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path (.md). Defaults to stdout.",
    )

    args = parser.parse_args()

    header = (
        f"# Data Narrative: {args.finding[:60]}...\n\n"
        f"**Framework:** {FRAMEWORKS[args.framework]}\n"
        f"**Audience:** {AUDIENCE_CONTEXT[args.audience]['role']}\n"
        f"**Created:** {datetime.now().strftime('%Y-%m-%d')}\n\n---\n\n"
    )

    body = TEMPLATES[args.framework](args.finding, args.decision, args.audience)
    output = header + body

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Narrative scaffold written to: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
