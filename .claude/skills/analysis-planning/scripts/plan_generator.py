#!/usr/bin/env python3
"""
plan_generator.py — Generate a prefilled analysis plan for a named NYC DOT dataset.

Usage:
    python plan_generator.py --dataset ramp_progress --question "Ramp completion by borough Q1 2026"
    python plan_generator.py --dataset violations --question "Violation trend MN last 6 months"
    python plan_generator.py --list-datasets

Outputs a markdown analysis plan stub to stdout (redirect to a file to save).
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta

DATASET_REGISTRY: dict[str, dict] = {
    "inspection": {
        "fourfour": "dntt-gqwq",
        "rows": "~398K",
        "sla": "HIGH",
        "key_column": "objectid",
        "date_column": "created_date",
        "borough_column": "borough",
        "notes": "Updates daily",
    },
    "violations": {
        "fourfour": "6kbp-uz6m",
        "rows": "~312K",
        "sla": "HIGH",
        "key_column": "objectid",
        "date_column": "created_date",
        "borough_column": "borough",
        "notes": "Updates daily",
    },
    "ramp_progress": {
        "fourfour": "e7gc-ub6z",
        "rows": "~187K",
        "sla": "HIGH",
        "key_column": "objectid",
        "date_column": "date_opened",
        "borough_column": "borough",
        "notes": "Updates daily",
    },
    "dismissals": {
        "fourfour": "p4u2-3jgx",
        "rows": "~85K",
        "sla": "HIGH",
        "key_column": "objectid",
        "date_column": "created_date",
        "borough_column": "borough",
        "notes": "Updates daily",
    },
    "ramp_complaints": {
        "fourfour": "jagj-gttd",
        "rows": "~6K",
        "sla": "HIGH",
        "key_column": "objectid",
        "date_column": "created_date",
        "borough_column": "borough",
        "notes": "Updates daily",
    },
    "street_permits": {
        "fourfour": "tqtj-sjs8",
        "rows": "~3.6M",
        "sla": "MEDIUM",
        "key_column": "objectid",
        "date_column": "issueddate",
        "borough_column": "communityboard",
        "notes": "Large dataset — always use $where filter",
    },
    "tree_damage": {
        "fourfour": "j6v2-6uxq",
        "rows": "~17K",
        "sla": "MEDIUM",
        "key_column": "objectid",
        "date_column": "created_date",
        "borough_column": "borough",
        "notes": "",
    },
}

KNOWN_ISSUES: dict[str, str] = {
    "ramp_locations": "STALE since 2021 — use ramp_progress instead",
    "weekly_construction": "STALE since 2017 — use street_construction_inspections",
    "capital_blocks": "EMPTY (0 rows) — use capital_intersections",
    "permit_stipulations": "API 403 ERROR — unavailable",
}

SLA_DAYS = {"HIGH": 14, "MEDIUM": 30, "LOW": 60}


def list_datasets() -> None:
    print("Available datasets:\n")
    for key, meta in DATASET_REGISTRY.items():
        print(f"  {key:<30} {meta['fourfour']}  {meta['rows']:>8}  SLA={meta['sla']}")
    print("\nKnown-issue datasets (do not use without reading CLAUDE.md):")
    for key, issue in KNOWN_ISSUES.items():
        print(f"  {key:<30} {issue}")


def generate_plan(dataset_key: str, question: str) -> str:
    if dataset_key in KNOWN_ISSUES:
        print(
            f"WARNING: {dataset_key} has a known issue: {KNOWN_ISSUES[dataset_key]}",
            file=sys.stderr,
        )

    meta = DATASET_REGISTRY.get(dataset_key)
    if meta is None:
        print(
            f"ERROR: dataset '{dataset_key}' not in registry. Use --list-datasets.", file=sys.stderr
        )
        sys.exit(1)

    today = date.today()
    deadline = today + timedelta(days=5)
    sla_days = SLA_DAYS[meta["sla"]]

    lines = [
        "# Analysis Plan",
        "",
        f"**Project:** {question}",
        "**Analyst:** <!-- name -->",
        "**Requested by:** <!-- stakeholder name and team -->",
        f"**Date created:** {today}",
        f"**Deadline:** {deadline}",
        "**Status:** DRAFT",
        "",
        "---",
        "",
        "## Business question",
        "",
        f"{question}",
        "",
        "---",
        "",
        "## Sub-questions and sequencing",
        "",
        "| # | Sub-question | Dataset key | Fourfour | Est. effort | Depends on |",
        "|---|---|---|---|---|---|",
        f"| SQ1 | Dataset health check — is {dataset_key} fresh (SLA={meta['sla']}, {sla_days}d)? | {dataset_key} | {meta['fourfour']} | 5 min | — |",
        f"| SQ2 | Fetch and profile a sample (10K rows, filtered) | {dataset_key} | {meta['fourfour']} | 20 min | SQ1 |",
        f"| SQ3 | Borough-level metric calculation with Wilson 95% CI | {dataset_key} | {meta['fourfour']} | 30 min | SQ2 |",
        f"| SQ4 | Compare to prior period baseline | {dataset_key} | {meta['fourfour']} | 20 min | SQ3 |",
        "| SQ5 | Write-up and borough table | — | — | 45 min | SQ4 |",
        "",
        "---",
        "",
        "## Data dependencies",
        "",
        "| Dataset key | Fourfour | Rows | SLA | Availability | Notes |",
        "|---|---|---|---|---|---|",
        f"| {dataset_key} | {meta['fourfour']} | {meta['rows']} | {meta['sla']} ({sla_days}d) | Confirmed | {meta['notes']} |",
        "",
        "---",
        "",
        "## Effort summary",
        "",
        "| Phase | Steps | Est. effort |",
        "|---|---|---|",
        "| Phase 1 — Data acquisition | SQ1, SQ2 | 25 min |",
        "| Phase 2 — Analysis | SQ3, SQ4 | 50 min |",
        "| Phase 3 — Write-up and delivery | SQ5 | 45 min |",
        "| **Raw total** | | **120 min** |",
        "| **+30% buffer** | | **156 min (~2.5 hrs)** |",
        f"| **Fits deadline ({deadline})?** | | YES |",
        "",
        "---",
        "",
        "## Risks and mitigations",
        "",
        "| Risk | Likelihood | Impact | Mitigation |",
        "|---|---|---|---|",
        f"| {dataset_key} stale beyond {sla_days}d SLA | Low | High | Run dataset health check (SQ1) first |",
        "| SOCRATA_APP_TOKEN unset for full-corpus fetch | Medium | High | Confirm token; use 10K sample if unset |",
        "| Borough codes inconsistent | High | Medium | Normalize with upper(borough) in SOQL |",
        f"| Null rate in {meta['date_column']} invalidates time filter | Low | Medium | Check null rate in SQ2 profile |",
        "",
        "---",
        "",
        "## Definition of done",
        "",
        "- Output format: markdown table + .xlsx",
        "- Delivery channel: <!-- Slack #dot-analytics or email -->",
        "- Accepted when: stakeholder confirms borough rates are plausible; n= and data date shown for every number",
    ]

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a prefilled analysis plan for an NYC DOT dataset."
    )
    parser.add_argument(
        "--dataset", help="Dataset key (e.g. ramp_progress, violations, inspection)"
    )
    parser.add_argument("--question", help="Business question the analysis will answer")
    parser.add_argument(
        "--list-datasets", action="store_true", help="List available dataset keys and exit"
    )
    args = parser.parse_args()

    if args.list_datasets:
        list_datasets()
        return

    if not args.dataset or not args.question:
        parser.error("--dataset and --question are both required (or use --list-datasets)")

    print(generate_plan(args.dataset, args.question))


if __name__ == "__main__":
    main()
