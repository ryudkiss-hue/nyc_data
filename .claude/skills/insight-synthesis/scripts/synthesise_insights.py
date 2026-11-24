"""
synthesise_insights.py — CLI tool to score and prioritise analytical findings
for NYC DOT SIM analysis, producing a ranked insight brief.

Takes raw findings (as text file or inline flags) and guides the analyst through
impact / confidence / actionability scoring to produce the top 3–5 prioritised insights.

Usage:
    python synthesise_insights.py \
        --findings findings.txt \
        --context "Q2 2026 ramp completion review — decision: reallocate inspectors" \
        --audience dot-leadership \
        --output insight_brief.md

    # Interactive mode (no findings file — enter interactively):
    python synthesise_insights.py --interactive --audience operations-manager
"""

import argparse
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

IMPACT_GUIDE = {
    3: "HIGH — directly affects program target, budget, or ADA compliance at scale (>1K residents or >$100K)",
    2: "MED — affects operational efficiency or quality in one borough or workflow",
    1: "LOW — informational; useful context but not decision-changing on its own",
}

CONFIDENCE_GUIDE = {
    3: "HIGH — large sample (n>1000), validated data, 95% CI computed",
    2: "MED — moderate sample (100<n<1000) or single data source without CI",
    1: "LOW — small sample (n<100), proxy metric, or data quality concerns flagged",
}

ACTIONABILITY_GUIDE = {
    3: "HIGH — clear owner, clear action, can be executed this quarter",
    2: "MED — requires coordination or budget approval before action",
    1: "LOW — interesting but no clear near-term action; flag for future analysis",
}


@dataclass
class Finding:
    text: str
    impact: int = 0
    confidence: int = 0
    actionability: int = 0
    so_what: str = ""
    why: str = ""
    now_what: str = ""
    estimated_impact: str = ""
    gaps: list[str] = field(default_factory=list)

    @property
    def score(self) -> int:
        return self.impact + self.confidence + self.actionability

    @property
    def score_label(self) -> str:
        if self.score >= 8:
            return "Priority 1"
        elif self.score >= 6:
            return "Priority 2"
        elif self.score >= 4:
            return "Priority 3"
        else:
            return "Low priority"


def load_findings_from_file(path: str) -> list[str]:
    p = Path(path)
    if not p.exists():
        print(f"Error: findings file not found: {path}", file=sys.stderr)
        sys.exit(1)
    lines = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip().lstrip("-•*0123456789.").strip()
        if line:
            lines.append(line)
    return lines


def score_finding_interactive(finding_text: str, index: int) -> Finding:
    f = Finding(text=finding_text)
    print(f"\n--- Finding {index}: {finding_text[:80]}... ---")

    print("\nImpact score (1–3):")
    for k, v in IMPACT_GUIDE.items():
        print(f"  {k} = {v}")
    while True:
        try:
            f.impact = int(input("Impact [1/2/3]: ").strip())
            if f.impact in (1, 2, 3):
                break
        except (ValueError, KeyboardInterrupt):
            pass

    print("\nConfidence score (1–3):")
    for k, v in CONFIDENCE_GUIDE.items():
        print(f"  {k} = {v}")
    while True:
        try:
            f.confidence = int(input("Confidence [1/2/3]: ").strip())
            if f.confidence in (1, 2, 3):
                break
        except (ValueError, KeyboardInterrupt):
            pass

    print("\nActionability score (1–3):")
    for k, v in ACTIONABILITY_GUIDE.items():
        print(f"  {k} = {v}")
    while True:
        try:
            f.actionability = int(input("Actionability [1/2/3]: ").strip())
            if f.actionability in (1, 2, 3):
                break
        except (ValueError, KeyboardInterrupt):
            pass

    f.so_what = input("\nSo What (why does this matter to the business?): ").strip()
    f.why = input("Why (likely cause): ").strip()
    f.now_what = input("Now What (recommended action): ").strip()
    f.estimated_impact = input("Estimated impact (quantified if possible): ").strip()

    gap = input("Data gaps / caveats (press Enter to skip): ").strip()
    if gap:
        f.gaps.append(gap)

    return f


def score_finding_auto(finding_text: str) -> Finding:
    """Auto-assign mid-level scores with placeholder text for batch/non-interactive mode."""
    return Finding(
        text=finding_text,
        impact=2,
        confidence=2,
        actionability=2,
        so_what="(fill in: why does this matter to the business?)",
        why="(fill in: likely cause or contributing factor)",
        now_what="(fill in: recommended action — who, what, by when)",
        estimated_impact="(fill in: quantified business or operational impact)",
        gaps=["(fill in: data gaps or caveats)"],
    )


def format_insight_brief(
    findings: list[Finding],
    context: str,
    audience: str,
    today: str,
) -> str:
    ranked = sorted(findings, key=lambda f: f.score, reverse=True)
    top = ranked[:5]
    gaps = ranked[5:]

    sections = []
    for i, f in enumerate(top, 1):
        section = f"""### Insight {i} — {f.score_label} (Score: {f.score}/9)

**Finding:** {f.text}

**So What:** {f.so_what}

**Why:** {f.why}

**Recommended action (Now What):** {f.now_what}

**Estimated impact:** {f.estimated_impact}

**Scoring:**
| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Impact | {f.impact}/3 | {IMPACT_GUIDE[f.impact]} |
| Confidence | {f.confidence}/3 | {CONFIDENCE_GUIDE[f.confidence]} |
| Actionability | {f.actionability}/3 | {ACTIONABILITY_GUIDE[f.actionability]} |
| **Total** | **{f.score}/9** | |
"""
        if f.gaps:
            section += "\n**Gaps / caveats before acting:**\n"
            for g in f.gaps:
                section += f"- {g}\n"
        sections.append(section)

    gaps_section = ""
    if gaps:
        gaps_section = "\n---\n\n## Deprioritised Findings (score < threshold)\n\n"
        gaps_section += (
            "*These findings need further validation before they become actionable insights.*\n\n"
        )
        for f in gaps:
            gaps_section += (
                f"- **{f.text}** (Score: {f.score}/9) — {f.so_what or 'No interpretation yet'}\n"
            )

    sep = "---\n\n"
    sections_joined = sep.join(sections)
    return f"""# Insight Brief

**Context:** {context}
**Audience:** {audience}
**Created:** {today}
**Total findings reviewed:** {len(findings)}
**Insights prioritised:** {min(len(findings), 5)}

---

## Prioritised Insights

{sections_joined}
{gaps_section}
---

## Next Steps

| # | Action | Owner | By |
|---|--------|-------|----|
| 1 | Validate top insight with additional data or stakeholder | (fill in) | (fill in) |
| 2 | Present Insight 1 + Insight 2 in next operations briefing | (fill in) | (fill in) |
| 3 | Schedule follow-up analysis on deprioritised findings | (fill in) | (fill in) |
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score and prioritise analytical findings for NYC DOT SIM analysis."
    )
    parser.add_argument(
        "--findings",
        default=None,
        help="Path to text file with one finding per line",
    )
    parser.add_argument(
        "--context",
        default="(fill in: business context and decision being made)",
        help="Business context — what decisions are being made based on this analysis?",
    )
    parser.add_argument(
        "--audience",
        default="dot-leadership",
        help="Target audience for the insight brief",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Score each finding interactively (prompts for impact/confidence/actionability)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path (.md). Defaults to stdout.",
    )

    args = parser.parse_args()

    if not args.findings and not args.interactive:
        print(
            "Error: provide --findings <file> or use --interactive mode.",
            file=sys.stderr,
        )
        sys.exit(1)

    raw_findings = load_findings_from_file(args.findings) if args.findings else []

    if args.interactive:
        if not raw_findings:
            print("Interactive mode: enter findings one per line. Empty line to finish.")
            while True:
                line = input(f"Finding {len(raw_findings) + 1}: ").strip()
                if not line:
                    break
                raw_findings.append(line)

        findings = []
        for i, text in enumerate(raw_findings, 1):
            findings.append(score_finding_interactive(text, i))
    else:
        findings = [score_finding_auto(text) for text in raw_findings]

    if not findings:
        print("No findings to process. Exiting.", file=sys.stderr)
        sys.exit(0)

    today = datetime.now().strftime("%Y-%m-%d")
    brief = format_insight_brief(findings, args.context, args.audience, today)

    if args.output:
        Path(args.output).write_text(brief, encoding="utf-8")
        print(f"Insight brief written to: {args.output}", file=sys.stderr)
    else:
        print(brief)


if __name__ == "__main__":
    main()
