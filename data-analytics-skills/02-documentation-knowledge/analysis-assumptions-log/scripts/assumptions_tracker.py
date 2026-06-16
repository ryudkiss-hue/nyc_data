"""Assumptions tracker for NYC DOT SIM analysis workflows.

Logs analytical assumptions, data decisions, and business logic choices to a
structured JSON file. Flags high-impact assumptions for validation before
finalising conclusions.

Usage:
    python assumptions_tracker.py init --analysis "Ramp Completion Q2 2026" \\
        --author "ryudkiss@gmail.com" --datasets inspection violations

    python assumptions_tracker.py add --file analysis.json \\
        --type data --description "Null borough values treated as UNKNOWN" \\
        --impact high --confidence medium

    python assumptions_tracker.py report --file analysis.json

    python assumptions_tracker.py flag-critical --file analysis.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

ImpactLevel = Literal["high", "medium", "low"]
ConfidenceLevel = Literal["high", "medium", "low"]
AssumptionType = Literal["data", "business_logic", "statistical", "scope"]

DATASET_DESCRIPTIONS = {
    "inspection": "Sidewalk inspection records (dntt-gqwq, ~398K rows, updates daily)",
    "violations": "Open sidewalk violations (6kbp-uz6m, ~312K rows, updates daily)",
    "ramp_progress": "Curb ramp completion tracking (e7gc-ub6z, ~187K rows, updates daily)",
    "dismissals": "Dismissed violation records (p4u2-3jgx, ~85K rows, updates daily)",
    "street_permits": "Street construction permits (tqtj-sjs8, ~3.6M rows)",
    "ramp_complaints": "Ramp-related 311 complaints (jagj-gttd, ~6K rows, updates daily)",
    "tree_damage": "Tree root sidewalk damage (j6v2-6uxq, ~17K rows)",
}

BOROUGH_CODES = ["MN", "BX", "BK", "QN", "SI"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path) -> dict:
    if not path.exists():
        print(f"Error: {path} does not exist. Run 'init' first.", file=sys.stderr)
        sys.exit(1)
    with path.open() as f:
        return json.load(f)


def _save(path: Path, data: dict) -> None:
    with path.open("w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved: {path}")


def cmd_init(args: argparse.Namespace) -> None:
    path = Path(args.file)
    if path.exists() and not args.overwrite:
        print(f"Error: {path} already exists. Use --overwrite to replace.", file=sys.stderr)
        sys.exit(1)

    data_sources = []
    for key in args.datasets or []:
        data_sources.append(
            {
                "key": key,
                "description": DATASET_DESCRIPTIONS.get(key, ""),
                "population_filter": None,
                "time_period": None,
                "null_handling": None,
                "confidence": None,
            }
        )

    doc = {
        "schema_version": "1.0",
        "analysis_name": args.analysis,
        "author": args.author,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "borough_scope": args.boroughs or BOROUGH_CODES,
        "data_sources": data_sources,
        "assumptions": [],
        "critical_flags": [],
        "sign_off": None,
    }
    _save(path, doc)
    print(f"Initialised assumptions log for: {args.analysis}")


def cmd_add(args: argparse.Namespace) -> None:
    path = Path(args.file)
    doc = _load(path)

    assumption = {
        "id": f"A{len(doc['assumptions']) + 1:03d}",
        "type": args.type,
        "description": args.description,
        "rationale": args.rationale or "",
        "alternatives_considered": args.alternatives or [],
        "impact_if_wrong": args.impact,
        "confidence": args.confidence,
        "validation_status": "pending",
        "added_at": _now_iso(),
        "dataset_key": args.dataset or None,
        "column": args.column or None,
    }

    doc["assumptions"].append(assumption)
    doc["updated_at"] = _now_iso()

    if args.impact == "high":
        doc["critical_flags"].append(assumption["id"])
        print(f"WARNING: High-impact assumption {assumption['id']} flagged for validation.")

    _save(path, doc)
    print(f"Added assumption {assumption['id']}: {args.description[:60]}")


def cmd_report(args: argparse.Namespace) -> None:
    path = Path(args.file)
    doc = _load(path)

    print(f"\n{'=' * 60}")
    print(f"ASSUMPTIONS LOG: {doc['analysis_name']}")
    print(f"Author: {doc['author']}  |  Created: {doc['created_at'][:10]}")
    print(f"Borough scope: {', '.join(doc['borough_scope'])}")
    print(f"{'=' * 60}\n")

    by_type: dict[str, list] = {}
    for a in doc["assumptions"]:
        by_type.setdefault(a["type"], []).append(a)

    for atype, items in by_type.items():
        print(f"[{atype.upper().replace('_', ' ')}]")
        for a in items:
            flag = " *** CRITICAL ***" if a["id"] in doc["critical_flags"] else ""
            print(f"  {a['id']}{flag}")
            print(f"    {a['description']}")
            print(
                f"    Impact: {a['impact_if_wrong']}  |  Confidence: {a['confidence']}  "
                f"|  Status: {a['validation_status']}"
            )
            if a.get("dataset_key"):
                print(
                    f"    Dataset: {a['dataset_key']}"
                    + (f", column: {a['column']}" if a.get("column") else "")
                )
            print()

    critical = [a for a in doc["assumptions"] if a["id"] in doc["critical_flags"]]
    if critical:
        print(f"CRITICAL ASSUMPTIONS REQUIRING VALIDATION ({len(critical)}):")
        for a in critical:
            print(f"  - {a['id']}: {a['description'][:80]}")
    else:
        print("No critical assumptions flagged.")


def cmd_flag_critical(args: argparse.Namespace) -> None:
    path = Path(args.file)
    doc = _load(path)

    critical = [a for a in doc["assumptions"] if a["impact_if_wrong"] == "high"]
    pending = [a for a in critical if a["validation_status"] == "pending"]

    print(f"\nCritical assumptions ({len(critical)} total, {len(pending)} pending validation):")
    for a in critical:
        status_marker = "PENDING" if a["validation_status"] == "pending" else "OK"
        print(f"  [{status_marker}] {a['id']}: {a['description'][:70]}")

    if pending:
        print(
            f"\nACTION REQUIRED: Validate {len(pending)} high-impact assumption(s) "
            "before finalising conclusions."
        )
        sys.exit(1)
    else:
        print("\nAll critical assumptions validated.")


def cmd_validate(args: argparse.Namespace) -> None:
    path = Path(args.file)
    doc = _load(path)

    target = next((a for a in doc["assumptions"] if a["id"] == args.assumption_id), None)
    if target is None:
        print(f"Error: assumption {args.assumption_id} not found.", file=sys.stderr)
        sys.exit(1)

    target["validation_status"] = "validated"
    target["validated_at"] = _now_iso()
    target["validation_notes"] = args.notes or ""
    doc["updated_at"] = _now_iso()
    _save(path, doc)
    print(f"Marked {args.assumption_id} as validated.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NYC DOT SIM analysis assumptions tracker")
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = sub.add_parser("init", help="Initialise a new assumptions log")
    p_init.add_argument("--analysis", required=True, help="Analysis name")
    p_init.add_argument("--author", required=True, help="Author email")
    p_init.add_argument(
        "--datasets", nargs="+", choices=list(DATASET_DESCRIPTIONS), help="Dataset keys being used"
    )
    p_init.add_argument(
        "--boroughs", nargs="+", choices=BOROUGH_CODES, help="Borough scope (default: all)"
    )
    p_init.add_argument(
        "--file",
        default="assumptions_log.json",
        help="Output file path (default: assumptions_log.json)",
    )
    p_init.add_argument("--overwrite", action="store_true")

    # add
    p_add = sub.add_parser("add", help="Log an assumption")
    p_add.add_argument("--file", default="assumptions_log.json")
    p_add.add_argument(
        "--type", required=True, choices=["data", "business_logic", "statistical", "scope"]
    )
    p_add.add_argument("--description", required=True)
    p_add.add_argument("--impact", required=True, choices=["high", "medium", "low"])
    p_add.add_argument("--confidence", required=True, choices=["high", "medium", "low"])
    p_add.add_argument("--rationale", help="Why this assumption was made")
    p_add.add_argument("--alternatives", nargs="+", help="Alternatives considered")
    p_add.add_argument("--dataset", help="Dataset key this assumption applies to")
    p_add.add_argument("--column", help="Specific column this assumption applies to")

    # report
    p_rep = sub.add_parser("report", help="Print structured assumption report")
    p_rep.add_argument("--file", default="assumptions_log.json")

    # flag-critical
    p_flag = sub.add_parser("flag-critical", help="List and exit non-zero if unvalidated criticals")
    p_flag.add_argument("--file", default="assumptions_log.json")

    # validate
    p_val = sub.add_parser("validate", help="Mark an assumption as validated")
    p_val.add_argument("--file", default="assumptions_log.json")
    p_val.add_argument("--assumption-id", required=True, help="e.g. A001")
    p_val.add_argument("--notes", help="Validation evidence notes")

    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    {
        "init": cmd_init,
        "add": cmd_add,
        "report": cmd_report,
        "flag-critical": cmd_flag_critical,
        "validate": cmd_validate,
    }[args.command](args)
