#!/usr/bin/env python3
"""
context_bundler.py — Merge schema docs, metric definitions, and business rules into
a single structured context file optimized for AI-assisted analysis sessions.

Usage:
    python context_bundler.py --dataset ramp_progress --goal "Borough completion rate Q1 2026"
    python context_bundler.py --dataset violations --goal "MoM violation trend MN" --layers 1,2,3,5
    python context_bundler.py --dataset inspection --goal "Quality scorecard" --budget 1500

Outputs a scored context package to stdout (redirect to file to save and reuse).
"""

from __future__ import annotations

import argparse
import sys

# Pre-written context snippets per dataset (Layer 2)
SCHEMA_SNIPPETS: dict[str, str] = {
    "ramp_progress": """\
Dataset: ramp_progress
Fourfour: e7gc-ub6z | Rows: ~187K | SLA: HIGH (14 days) | Updates: daily
Key columns:
  objectid       INTEGER  Primary key
  borough        TEXT     Borough code; normalize with upper(trim(borough)) → MN/BX/BK/QN/SI
  status         TEXT     Lifecycle status; 'CLOSED' = completed
  date_opened    DATE     Date the ramp work order was opened (ISO 8601)
  date_closed    DATE     Date the ramp work order was closed; NULL if still open
  inspection_id  TEXT     Links to inspection dataset (dntt-gqwq)
Known issues: none (use this instead of ramp_locations which is stale since 2021)""",
    "violations": """\
Dataset: violations
Fourfour: 6kbp-uz6m | Rows: ~312K | SLA: HIGH (14 days) | Updates: daily
Key columns:
  objectid        INTEGER  Primary key
  borough         TEXT     Normalize: upper(trim(borough)) → MN/BX/BK/QN/SI
  created_date    DATETIME Violation creation date; use for time-window filters (ISO 8601)
  violation_type  TEXT     Category of violation (e.g. SIDEWALK, RAMP, TREE_DAMAGE)
  status          TEXT     OPEN / CLOSED / DISMISSED
  inspection_id   TEXT     Links to inspection dataset (dntt-gqwq)
Known issues: none""",
    "inspection": """\
Dataset: inspection
Fourfour: dntt-gqwq | Rows: ~398K | SLA: HIGH (14 days) | Updates: daily
Key columns:
  objectid        INTEGER  Primary key
  borough         TEXT     Normalize: upper(trim(borough)) → MN/BX/BK/QN/SI
  created_date    DATETIME Inspection record creation date
  inspection_date DATE     Date the physical inspection occurred
  status          TEXT     OPEN / CLOSED
  inspector_id    TEXT     Assigned inspector identifier
Known issues: created_date ≠ inspection_date; clarify with stakeholder which to use""",
    "ramp_complaints": """\
Dataset: ramp_complaints
Fourfour: jagj-gttd | Rows: ~6K | SLA: HIGH (14 days) | Updates: daily
Key columns:
  objectid      INTEGER  Primary key
  borough       TEXT     Normalize: upper(trim(borough)) → MN/BX/BK/QN/SI
  created_date  DATETIME Complaint received date
  status        TEXT     OPEN / CLOSED
  complaint_type TEXT    Category of accessibility complaint
Known issues: small dataset; SI may have n<30 in monthly cuts""",
    "dismissals": """\
Dataset: dismissals
Fourfour: p4u2-3jgx | Rows: ~85K | SLA: HIGH (14 days) | Updates: daily
Key columns:
  objectid       INTEGER  Primary key
  borough        TEXT     Normalize: upper(trim(borough)) → MN/BX/BK/QN/SI
  created_date   DATETIME Dismissal date
  violation_id   TEXT     Links to violations dataset (6kbp-uz6m)
  reason         TEXT     Dismissal reason code
Known issues: none""",
}

# Metric definitions (Layer 3)
METRIC_SNIPPETS: dict[str, str] = {
    "completion_rate": """\
Metric: completion_rate
Formula: COUNT(status='CLOSED') / COUNT(*) per borough
CI method: Wilson Score 95% (always — n may be small for SI)
Date field: date_opened (use for time-window filter); date_closed for duration
SLA context: ramp_progress SLA = HIGH (14 days freshness)
Flag if: n < 30 for any borough (report as "insufficient sample" rather than suppress)""",
    "violation_trend": """\
Metric: violation_trend (month-over-month change)
Formula: (count_month_n - count_month_n_minus_1) / count_month_n_minus_1 * 100
Date field: created_date (not inspection_date)
Grouping: DATE_TRUNC('month', created_date), borough
Output: absolute count + MoM change %; flag months with unusual spikes for investigation""",
    "quality_score": """\
Metric: quality_score (composite 0–100)
Components: completeness 0.35 / validity 0.25 / consistency 0.25 / freshness 0.15
API: compute_quality_score(df, key_columns=['objectid'], date_column='created_date', freshness_days_threshold=<SLA_days>)
Output: score.overall, score.completeness, score.validity, score.consistency, score.freshness""",
}

# Analytical constraints (Layer 4)
CONSTRAINTS_SNIPPET = """\
Analytical constraints:
- DO NOT USE: ramp_locations (ufzp-rrqu) — stale since 2021
- DO NOT USE: weekly_construction (r528-jcks) — stale since 2017
- DO NOT USE: capital_blocks (jvk9-k4re) — empty dataset
- DO NOT USE: permit_stipulations (gsgx-6efw) — API 403 error
- Row limit: confirm SOCRATA_APP_TOKEN is set for fetches > 2K rows
- Always use $where and $select projections; never pull full corpus without a filter"""

# Output format (Layer 5)
OUTPUT_SNIPPET = """\
Output format:
- Borough table columns: [borough, n, <metric>, ci_lower, ci_upper] (Wilson 95% CI for rates)
- Rates: 1 decimal place percentage (e.g. 73.4%)
- Counts: integer with comma separator (e.g. 12,847)
- Always include: n= and data freshness date (last_modified) for every quantitative claim
- Borough order: MN, BX, BK, QN, SI"""

LAYER_NAMES = {
    1: "Business context",
    2: "Data schema",
    3: "Metric definitions",
    4: "Constraints",
    5: "Output format",
}


def estimate_tokens(text: str) -> int:
    # ~4 characters per token (rough estimate for English prose + code)
    return len(text) // 4


def score_package(package: str, dataset: str, goal: str, layers: list[int]) -> int:
    score = 0
    # Dimension 1: goal clarity
    if all(w in goal.lower() for w in ["borough", "q"]) or len(goal.split()) >= 5:
        score += 20
    elif len(goal.split()) >= 3:
        score += 15
    else:
        score += 5
    # Dimension 2: schema
    if dataset in SCHEMA_SNIPPETS and 2 in layers:
        score += 25
    elif dataset in SCHEMA_SNIPPETS:
        score += 10
    # Dimension 3: metric
    if 3 in layers:
        score += 20
    # Dimension 4: constraints
    if 4 in layers:
        score += 15
    # Dimension 5: token efficiency (always included if layer 5 present)
    if 5 in layers:
        score += 15
    return score


def build_package(dataset: str, goal: str, layers: list[int], metric: str | None) -> str:
    parts: list[str] = []

    if 1 in layers:
        parts.append(
            f"## Layer 1 — Business context\n\nGoal: {goal}\nDataset: {dataset}\nBoroughs: MN, BX, BK, QN, SI\n"
        )

    if 2 in layers:
        snippet = SCHEMA_SNIPPETS.get(dataset)
        if snippet:
            parts.append(f"## Layer 2 — Data schema\n\n{snippet}\n")
        else:
            parts.append(
                f"## Layer 2 — Data schema\n\nDataset: {dataset} (schema not in bundler registry — add manually)\n"
            )

    if 3 in layers:
        snippet = METRIC_SNIPPETS.get(metric or "")
        if snippet:
            parts.append(f"## Layer 3 — Metric definitions\n\n{snippet}\n")
        else:
            available = ", ".join(METRIC_SNIPPETS.keys())
            parts.append(
                f"## Layer 3 — Metric definitions\n\n<!-- No metric specified. Available: {available} -->\n"
            )

    if 4 in layers:
        parts.append(f"## Layer 4 — Analytical constraints\n\n{CONSTRAINTS_SNIPPET}\n")

    if 5 in layers:
        parts.append(f"## Layer 5 — Output format\n\n{OUTPUT_SNIPPET}\n")

    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a scored context package for an AI analysis session."
    )
    parser.add_argument(
        "--dataset", required=True, help="Dataset key (e.g. ramp_progress, violations, inspection)"
    )
    parser.add_argument("--goal", required=True, help="Analytical goal in plain language")
    parser.add_argument(
        "--layers",
        default="1,2,3,4,5",
        help="Comma-separated layer numbers to include (default: all)",
    )
    parser.add_argument(
        "--metric",
        default=None,
        help="Metric key for Layer 3 (completion_rate, violation_trend, quality_score)",
    )
    parser.add_argument(
        "--budget", type=int, default=2000, help="Token budget ceiling (default: 2000)"
    )
    parser.add_argument(
        "--list-datasets", action="store_true", help="List datasets with pre-built schema snippets"
    )
    parser.add_argument(
        "--list-metrics", action="store_true", help="List available metric snippets"
    )
    args = parser.parse_args()

    if args.list_datasets:
        print("Datasets with pre-built schema snippets:")
        for k in SCHEMA_SNIPPETS:
            print(f"  {k}")
        return

    if args.list_metrics:
        print("Available metric snippets:")
        for k in METRIC_SNIPPETS:
            print(f"  {k}")
        return

    layers = [int(l.strip()) for l in args.layers.split(",")]
    package = build_package(args.dataset, args.goal, layers, args.metric)
    tokens = estimate_tokens(package)
    score = score_package(package, args.dataset, args.goal, layers)

    header = (
        f"# Context Package\n\n"
        f"**Dataset:** {args.dataset} | **Goal:** {args.goal}\n"
        f"**Layers:** {args.layers} | **Est. tokens:** ~{tokens} / {args.budget} budget\n"
        f"**Quality score:** {score}/100\n\n"
        f"---\n\n"
    )

    if tokens > args.budget:
        print(
            f"WARNING: estimated tokens ({tokens}) exceeds budget ({args.budget}). Trim Layer 2 or 4.",
            file=sys.stderr,
        )

    if score < 50:
        print(
            f"WARNING: quality score {score}/100 is below threshold. Review context_quality_rubric.md.",
            file=sys.stderr,
        )

    print(header + package)


if __name__ == "__main__":
    main()
