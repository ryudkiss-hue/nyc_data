"""
CLI interface to the LangGraph triage workflow.

Provides simple commands to run the complete triage workflow from the command line.

Usage:
    python -m socrata_toolkit.analysis.triage_cli violations dntt-gqwq --limit 1000
    python -m socrata_toolkit.analysis.triage_cli complaints_311 erm2-nwe9 --borough MN --severity-min 75
    python -m socrata_toolkit.analysis.triage_cli tree_damage j6v2-6uxq --full-report
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

from socrata_toolkit.analysis.langgraph_triage import run_triage, workflow_visualization

logger = logging.getLogger(__name__)

DATASET_REGISTRY = {
    # Inspection data
    "violations": {
        "fourfour": "6kbp-uz6m",
        "description": "SIM violations dataset",
    },
    "inspection": {
        "fourfour": "dntt-gqwq",
        "description": "SIM inspection records",
    },
    "dismissals": {
        "fourfour": "p4u2-3jgx",
        "description": "Dismissal records",
    },

    # Complaints
    "complaints_311": {
        "fourfour": "erm2-nwe9",
        "description": "311 complaints (21.3M rows)",
    },
    "ramp_complaints": {
        "fourfour": "jagj-gttd",
        "description": "Ramp-related complaints",
    },

    # Other
    "tree_damage": {
        "fourfour": "j6v2-6uxq",
        "description": "Tree damage reports",
    },
}

def format_report(result: dict, verbose: bool = False) -> str:
    """Format workflow results for display."""
    lines = []

    lines.append("\n" + "=" * 70)
    lines.append("NYC DOT VIOLATION TRIAGE REPORT")
    lines.append("=" * 70)

    lines.append(f"\nDataset: {result['dataset']}")
    lines.append(f"Records Analyzed: {result['total_records']:,}")
    lines.append(f"High-Severity Items: {result['high_severity_count']}")
    lines.append(f"Action Taken: {result['action_taken'].upper()}")

    lines.append("\n" + "-" * 70)
    lines.append("INITIAL ASSESSMENT (Claude)")
    lines.append("-" * 70)
    lines.append(result["initial_assessment"])

    if result["spatial_analysis"]:
        lines.append("\n" + "-" * 70)
        lines.append("SPATIAL ANALYSIS")
        lines.append("-" * 70)
        lines.append(json.dumps(result["spatial_analysis"], indent=2))

    if result["borough_analysis"]:
        lines.append("\n" + "-" * 70)
        lines.append("BOROUGH BREAKDOWN")
        lines.append("-" * 70)
        for borough, count in result["borough_analysis"].items():
            lines.append(f"  {borough}: {count} records")

    lines.append("\n" + "-" * 70)
    lines.append("FINAL RECOMMENDATION")
    lines.append("-" * 70)
    lines.append(result["final_recommendation"])

    if verbose:
        lines.append("\n" + "-" * 70)
        lines.append("AUDIT LOG")
        lines.append("-" * 70)
        for entry in result["audit_log"]:
            lines.append(f"  {entry['step']}: {entry['status']} @ {entry['timestamp']}")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)

def save_report(result: dict, output_path: str) -> None:
    """Save detailed report to file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        f.write("# NYC DOT Triage Report\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        f.write(f"## Dataset\n{result['dataset']}\n\n")
        f.write("## Summary\n")
        f.write(f"- Total Records: {result['total_records']:,}\n")
        f.write(f"- High-Severity: {result['high_severity_count']}\n")
        f.write(f"- Action: {result['action_taken']}\n\n")
        f.write(f"## Assessment\n{result['initial_assessment']}\n\n")
        f.write(f"## Recommendation\n{result['final_recommendation']}\n\n")
        f.write(f"## Raw Data\n```json\n{json.dumps(result['report_data'], indent=2)}\n```\n")

    print(f"✓ Report saved to {path}")

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run NYC DOT violation triage workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Triage violations dataset
  python -m socrata_toolkit.analysis.triage_cli violations

  # Triage complaints in Manhattan only
  python -m socrata_toolkit.analysis.triage_cli complaints_311 --borough MN

  # Triage tree damage, high severity threshold
  python -m socrata_toolkit.analysis.triage_cli tree_damage --severity-min 80

  # Save detailed report
  python -m socrata_toolkit.analysis.triage_cli violations --output-report triage_report.md

  # Show available datasets
  python -m socrata_toolkit.analysis.triage_cli --list-datasets

  # Show workflow diagram
  python -m socrata_toolkit.analysis.triage_cli --show-workflow
        """
    )

    parser.add_argument(
        "dataset",
        nargs="?",
        help="Dataset key (e.g., violations, complaints_311, tree_damage)"
    )

    parser.add_argument(
        "--list-datasets",
        action="store_true",
        help="Show available datasets"
    )

    parser.add_argument(
        "--show-workflow",
        action="store_true",
        help="Show workflow diagram"
    )

    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=1000,
        help="Maximum records to fetch (default: 1000)"
    )

    parser.add_argument(
        "-b", "--borough",
        help="Filter by borough (MN, BX, BK, QN, SI)"
    )

    parser.add_argument(
        "-s", "--severity-min",
        type=float,
        default=70.0,
        help="Minimum severity threshold (0-100, default: 70)"
    )

    parser.add_argument(
        "-o", "--output-report",
        help="Save detailed report to file"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed audit log"
    )

    args = parser.parse_args()

    # Show datasets
    if args.list_datasets:
        print("\nAvailable Datasets:")
        print("-" * 60)
        for key, info in DATASET_REGISTRY.items():
            print(f"  {key:20s} → {info['description']}")
        print()
        return

    # Show workflow
    if args.show_workflow:
        print(workflow_visualization())
        return

    # Validate dataset
    if not args.dataset:
        parser.print_help()
        return

    if args.dataset not in DATASET_REGISTRY:
        print(f"Unknown dataset: {args.dataset}")
        print("Use --list-datasets to see available options")
        return

    dataset_info = DATASET_REGISTRY[args.dataset]

    # Run triage
    print(f"\n[TRIAGE] Starting workflow for '{args.dataset}'...")
    print(f"  Max records: {args.limit}")
    if args.borough:
        print(f"  Borough filter: {args.borough}")
    print(f"  Severity threshold: {args.severity_min}")
    print()

    result = run_triage(
        dataset_key=args.dataset,
        fourfour=dataset_info["fourfour"],
        max_rows=args.limit,
        borough_filter=args.borough,
        severity_threshold=args.severity_min,
    )

    # Display report
    print(format_report(result, verbose=args.verbose))

    # Save if requested
    if args.output_report:
        save_report(result, args.output_report)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    main()
