"""
Analysis Assumptions Tracker

Log, categorise, and manage analytical assumptions. Identifies critical
assumptions (low confidence + high impact) that need validation before delivery.

Usage:
    python assumptions_tracker.py --demo
    python assumptions_tracker.py --load assumptions.json --report
    python assumptions_tracker.py --load assumptions.json --validate 1 --result confirmed \
        --notes "Validated with product team"
"""

import argparse
import json
import sys
from datetime import date


CATEGORIES = ["data", "business_logic", "statistical", "technical"]
CONFIDENCE_LEVELS = ["high", "medium", "low"]
IMPACT_LEVELS = ["low", "medium", "high", "critical"]

# Risk score matrix: (confidence, impact) -> score
RISK_SCORES = {
    ("high", "critical"): 6, ("high", "high"): 5, ("high", "medium"): 3,
    ("medium", "critical"): 7, ("medium", "high"): 6, ("medium", "medium"): 4,
    ("low", "critical"): 9, ("low", "high"): 8, ("low", "medium"): 5,
}


def new_log(analysis_name: str, analyst: str) -> dict:
    return {
        "analysis_name": analysis_name,
        "analyst": analyst,
        "created": str(date.today()),
        "assumptions": [],
    }


def add_assumption(log: dict, category: str, assumption: str, rationale: str,
                   confidence: str, impact_if_wrong: str, validation_plan: str = "") -> int:
    """Add an assumption to the log and return its ID."""
    entry = {
        "id": len(log["assumptions"]) + 1,
        "category": category,
        "assumption": assumption,
        "rationale": rationale,
        "confidence": confidence,
        "impact_if_wrong": impact_if_wrong,
        "validation_plan": validation_plan,
        "validated": False,
        "validation_result": None,
        "validation_notes": None,
    }
    log["assumptions"].append(entry)
    return entry["id"]


def validate_assumption(log: dict, assumption_id: int, result: str, notes: str):
    for a in log["assumptions"]:
        if a["id"] == assumption_id:
            a["validated"] = True
            a["validation_result"] = result
            a["validation_notes"] = notes
            return
    raise ValueError(f"Assumption {assumption_id} not found")


def get_critical(log: dict) -> list[dict]:
    """Return unvalidated assumptions with low confidence and high/critical impact."""
    return [
        a for a in log["assumptions"]
        if not a["validated"]
        and a["confidence"] == "low"
        and a["impact_if_wrong"] in ("high", "critical")
    ]


def risk_score(assumption: dict) -> int:
    return RISK_SCORES.get((assumption["confidence"], assumption["impact_if_wrong"]), 3)


def report(log: dict) -> str:
    lines = [
        "=" * 60,
        f"ASSUMPTIONS LOG: {log['analysis_name']}",
        f"Analyst: {log['analyst']}  |  Created: {log['created']}",
        "=" * 60,
        f"Total assumptions: {len(log['assumptions'])}",
        f"Validated: {sum(1 for a in log['assumptions'] if a['validated'])}",
    ]
    critical = get_critical(log)
    if critical:
        lines.append(f"CRITICAL (unvalidated, low confidence, high impact): {len(critical)}")

    for cat in CATEGORIES:
        cat_items = [a for a in log["assumptions"] if a["category"] == cat]
        if not cat_items:
            continue
        lines.append(f"\n--- {cat.replace('_', ' ').upper()} ---")
        for a in cat_items:
            score = risk_score(a)
            validated_str = f"✓ {a['validation_result']}" if a["validated"] else "✗ not validated"
            lines.append(f"  #{a['id']} [{a['confidence'].upper()} conf / {a['impact_if_wrong'].upper()} impact | risk={score}]")
            lines.append(f"    {a['assumption']}")
            lines.append(f"    Rationale: {a['rationale']}")
            lines.append(f"    Validation: {validated_str}")

    if critical:
        lines += ["", "CRITICAL ASSUMPTIONS REQUIRING VALIDATION:"]
        for a in critical:
            lines.append(f"  #{a['id']}: {a['assumption']}")
            if a["validation_plan"]:
                lines.append(f"    Plan: {a['validation_plan']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Track analytical assumptions.")
    parser.add_argument("--load", help="JSON file to load")
    parser.add_argument("--report", action="store_true", help="Print assumption report")
    parser.add_argument("--validate", type=int, metavar="ID", help="Validate assumption by ID")
    parser.add_argument("--result", help="Validation result string")
    parser.add_argument("--notes", help="Validation notes")
    parser.add_argument("--demo", action="store_true", help="Run demo")
    args = parser.parse_args()

    if args.demo:
        _demo()
        return

    if not args.load:
        parser.error("Provide --load <file> or --demo")

    with open(args.load) as f:
        log = json.load(f)

    if args.validate:
        if not args.result:
            parser.error("--result required when --validate is set")
        validate_assumption(log, args.validate, args.result, args.notes or "")
        with open(args.load, "w") as f:
            json.dump(log, f, indent=2)
        print(f"Assumption #{args.validate} validated.")

    if args.report:
        print(report(log))

    critical = get_critical(log)
    sys.exit(1 if critical else 0)


def _demo():
    log = new_log("Customer Churn Model", "Analytics Team")
    add_assumption(log, "data",
                   "Last 90 days of data is representative of future customer behaviour",
                   "Captures recent product changes and seasonal variation",
                   "medium", "high",
                   "Test model on holdout period outside the 90-day window")
    add_assumption(log, "business_logic",
                   "A user is 'churned' if no activity for 30 days",
                   "Stakeholder requirement — aligns with billing cycle",
                   "high", "low")
    add_assumption(log, "statistical",
                   "Features are approximately independent (no multicollinearity)",
                   "Correlation matrix checked: max correlation 0.45",
                   "low", "high",
                   "Run VIF test; consider PCA if VIF > 5")
    add_assumption(log, "technical",
                   "Missing engagement data means inactivity, not a tracking gap",
                   "Spot-checked 100 users with product team — confirmed",
                   "high", "medium")

    print(report(log))
    print()
    print("Critical assumptions:", len(get_critical(log)))


if __name__ == "__main__":
    _demo()
