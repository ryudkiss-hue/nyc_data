"""
intake_form.py — Requirements intake for NYC DOT analysis requests.

Usage:
    python intake_form.py --output requirements.yaml
    python intake_form.py --non-interactive --output requirements.yaml
"""

import argparse
import sys
from datetime import date
from pathlib import Path


def prompt(question: str, default: str = "") -> str:
    display = f"{question} [{default}]: " if default else f"{question}: "
    answer = input(display).strip()
    return answer if answer else default


def run_interactive() -> dict:
    print("\n=== NYC DOT Analysis Requirements Intake ===\n")

    req = {}
    req["date"] = str(date.today())

    req["requestor_name"] = prompt("Requestor name")
    req["requestor_role"] = prompt("Requestor role", "Operations Manager")
    req["requestor_email"] = prompt("Requestor email")
    req["analyst"] = prompt("Analyst assigned")

    print("\n--- Analysis Scope ---")
    print(
        "Available datasets: inspection, violations, ramp_progress, dismissals, street_permits, complaints_311"
    )
    req["dataset"] = prompt("Primary dataset", "violations")
    req["secondary_datasets"] = prompt("Secondary datasets (comma-separated, or blank)", "")

    print("\nTime period:")
    req["date_from"] = prompt("From date (YYYY-MM-DD)", "2026-01-01")
    req["date_to"] = prompt("To date (YYYY-MM-DD)", str(date.today()))

    print("\nBorough scope:")
    print("  Options: ALL, MN, BX, BK, QN, SI (comma-separated for multiple)")
    req["borough_scope"] = prompt("Borough scope", "ALL")

    print("\n--- Question Type ---")
    print("  1. trend      — How has [metric] changed over time?")
    print("  2. comparison — How does [metric] compare across [dimension]?")
    print("  3. distribution — What is the spread / distribution of [metric]?")
    print("  4. prediction — What will [metric] be in [future period]?")
    print("  5. diagnosis  — Why did [metric] change?")
    req["question_type"] = prompt(
        "Question type (trend/comparison/distribution/prediction/diagnosis)", "comparison"
    )
    req["primary_question"] = prompt("In one sentence, what question should the analysis answer?")
    req["key_metric"] = prompt("Primary metric to measure", "violation_closure_rate")
    req["secondary_metrics"] = prompt("Secondary metrics (comma-separated)", "")

    print("\n--- Output Requirements ---")
    print("  Options: slide, report, dashboard, data_file, email")
    req["output_format"] = prompt("Output format", "report")
    req["output_deadline"] = prompt("Deadline (YYYY-MM-DD)", "")
    req["audience"] = prompt("Intended audience", "Operations Manager")
    req["technical_level"] = prompt("Technical level of audience (low/medium/high)", "medium")

    print("\n--- Known Constraints ---")
    req["exclude_conditions"] = prompt(
        "Any data to exclude? (e.g., 'dismissed cases', 'borough=SI')", ""
    )
    req["known_issues"] = prompt("Known data quality issues to flag?", "")
    req["prior_analysis"] = prompt("Link to prior related analysis (or blank)", "")

    print("\n--- Success Criteria ---")
    req["success_criteria"] = prompt(
        "How will you know the analysis answered the question?",
        "Stakeholder confirms finding is actionable",
    )

    return req


def run_non_interactive() -> dict:
    return {
        "date": str(date.today()),
        "requestor_name": "TBD",
        "requestor_role": "Operations Manager",
        "requestor_email": "",
        "analyst": "TBD",
        "dataset": "violations",
        "secondary_datasets": "",
        "date_from": "2026-01-01",
        "date_to": str(date.today()),
        "borough_scope": "ALL",
        "question_type": "comparison",
        "primary_question": "How does the violation closure rate compare across boroughs?",
        "key_metric": "violation_closure_rate",
        "secondary_metrics": "days_to_close, defect_type",
        "output_format": "report",
        "output_deadline": "",
        "audience": "Operations Manager",
        "technical_level": "medium",
        "exclude_conditions": "",
        "known_issues": "",
        "prior_analysis": "",
        "success_criteria": "Stakeholder confirms finding is actionable",
    }


def write_yaml(req: dict, output: str) -> None:
    lines = ["# NYC DOT Analysis Requirements\n"]
    for key, val in req.items():
        safe_val = str(val).replace('"', '\\"') if val else '""'
        if " " in str(val) or "," in str(val) or not val:
            lines.append(f'{key}: "{safe_val}"')
        else:
            lines.append(f"{key}: {val}")
    Path(output).write_text("\n".join(lines) + "\n")
    print(f"\n[DONE] Requirements written to {output}")
    print("\nNext step: share with analyst and confirm scope before starting work.")


def main():
    parser = argparse.ArgumentParser(description="NYC DOT analysis requirements intake.")
    parser.add_argument("--output", default="requirements.yaml", help="Output YAML file path")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Generate a template with placeholder values (no prompts)",
    )
    args = parser.parse_args()

    if args.non_interactive:
        req = run_non_interactive()
    else:
        try:
            req = run_interactive()
        except (KeyboardInterrupt, EOFError):
            print("\n[CANCELLED]")
            sys.exit(0)

    write_yaml(req, args.output)


if __name__ == "__main__":
    main()
