"""
Example: Dismissal Pattern Analysis Workflow

Demonstrates how to use the dismissal_analysis_workflow and dismissal_classifier
to analyze inspector dismissal patterns and flag suspicious cases.
"""

import json
import logging

from socrata_toolkit.analysis.dismissal_analysis_workflow import (
    run_dismissal_workflow,
)
from socrata_toolkit.analysis.dismissal_classifier import (
    DismissalReasonClassifier,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def example_single_classification():
    """Example: Classify individual dismissal reasons."""
    print("\n" + "="*80)
    print("EXAMPLE 1: Classify Individual Dismissal Reasons")
    print("="*80 + "\n")

    classifier = DismissalReasonClassifier()

    test_cases = [
        {
            "dismissal_id": "D001",
            "reason": "Complies with NYC Administrative Code § 19-502. Licensed contractor completed work.",
            "defect_type": "TRIP_HAZARD",
            "inspector_id": "INS001",
            "inspector_rate": 0.12,
        },
        {
            "dismissal_id": "D002",
            "reason": "Data entry error - wrong category",
            "defect_type": "STRUCTURAL_DAMAGE",
            "inspector_id": "INS002",
            "inspector_rate": 0.08,
        },
        {
            "dismissal_id": "D003",
            "reason": "Reinspection shows defect no longer present. Previously repaired.",
            "defect_type": "WATER_INTRUSION",
            "inspector_id": "INS003",
            "inspector_rate": 0.18,
        },
        {
            "dismissal_id": "D004",
            "reason": "Personal favor from contractor",
            "defect_type": "TRIP_HAZARD",
            "inspector_id": "INS004",
            "inspector_rate": 0.45,
        },
        {
            "dismissal_id": "D005",
            "reason": "na",
            "defect_type": "POOR_MAINTENANCE",
            "inspector_id": "INS001",
            "inspector_rate": 0.12,
        },
    ]

    for case in test_cases:
        result = classifier.classify(
            dismissal_id=case["dismissal_id"],
            dismissal_reason_text=case["reason"],
            defect_type=case["defect_type"],
            inspector_id=case["inspector_id"],
            inspector_dismissal_rate=case["inspector_rate"],
            inspector_cohort_rate=0.15,
        )

        print(f"\nDismissal ID: {case['dismissal_id']}")
        print(f"Reason: {case['reason'][:60]}...")
        print(f"Classification: {result.category.value} (confidence={result.confidence.value})")
        print(f"Suspicion Score: {result.suspicion_score:.1f}/100")
        print(f"Inspector Consistency: {result.inspector_consistency.value}")
        print(f"Requires Review: {result.requires_review}")
        if result.flagged_reason:
            print(f"Flag: {result.flagged_reason}")

def example_full_workflow():
    """Example: Run full dismissal analysis workflow on live data."""
    print("\n" + "="*80)
    print("EXAMPLE 2: Full Dismissal Analysis Workflow (Live Data)")
    print("="*80 + "\n")

    print("Running workflow on dismissals dataset...")
    print("(This will fetch live data from NYC Open Data portal)\n")

    try:
        report = run_dismissal_workflow(
            dismissals_fourfour="p4u2-3jgx",  # NYC SIM dismissals
            violations_fourfour="6kbp-uz6m",  # NYC SIM violations
            max_rows=500,
            borough_filter=None,  # Analyze all boroughs
        )

        print("\nWORKFLOW COMPLETE\n")
        print("="*80)
        print("SUMMARY")
        print("="*80)

        summary = report["summary"]
        print(f"Total dismissals analyzed: {summary['total_dismissals']}")
        print(f"Execution time: {summary['execution_time']:.1f}s")
        print("\nCategory breakdown:")
        for category, count in summary["classifications"].items():
            pct = 100 * count / summary["total_dismissals"] if summary["total_dismissals"] > 0 else 0
            print(f"  - {category}: {count} ({pct:.1f}%)")

        print(f"\nFlagged dismissals: {summary['flagged_count']}")
        print(f"Inspectors analyzed: {summary['inspectors_analyzed']}")

        print("\n" + "="*80)
        print("INSPECTOR OUTLIERS (High dismissal rates)")
        print("="*80)

        inspector_summary = report["inspector_summary"]
        flagged_inspectors = [
            (insp_id, stats)
            for insp_id, stats in inspector_summary.items()
            if stats.get("flagged_for_review", False)
        ]

        for insp_id, stats in sorted(flagged_inspectors, key=lambda x: x[1]["suspicious_rate"], reverse=True):
            print(f"\nInspector: {insp_id}")
            print(f"  Total dismissals: {stats['total_dismissals']}")
            print(f"  Dismissal rate: {stats['dismissal_rate']*100:.1f}%")
            print(f"  Suspicious dismissals: {stats['suspicious_dismissals']}")
            print(f"  Suspicious rate: {stats['suspicious_rate']*100:.1f}%")

        print("\n" + "="*80)
        print("TOP FLAGGED CASES (Highest suspicion)")
        print("="*80)

        flagged = report["flagged_dismissals"][:5]
        for case in flagged:
            print(f"\nDismissal ID: {case['dismissal_id']}")
            print(f"Inspector: {case['inspector_id']}")
            print(f"Reason: {case['dismissal_reason']}")
            print(f"Category: {case['category']}")
            print(f"Suspicion score: {case['suspicion_score']:.1f}/100")
            print(f"Requires review: {case['requires_review']}")

        print("\n" + "="*80)
        print("CLAUDE ASSESSMENT")
        print("="*80)
        print("\n" + report["claude_assessment"])

        print("\n" + "="*80)
        print("Full report saved to: dismissal_analysis_report.json")
        print("="*80)

        # Save full report
        with open("dismissal_analysis_report.json", "w") as f:
            json.dump(report, f, indent=2, default=str)

    except Exception as e:
        logger.error(f"Workflow failed: {e}", exc_info=True)

def example_pattern_analysis():
    """Example: Pattern analysis by defect type."""
    print("\n" + "="*80)
    print("EXAMPLE 3: Defect Type Pattern Analysis")
    print("="*80 + "\n")

    try:
        report = run_dismissal_workflow(max_rows=300)

        patterns = report["defect_patterns"]

        print("Dismissal patterns by defect type:\n")
        for defect_type, pattern in sorted(
            patterns.items(), key=lambda x: x[1]["suspicious_dismissals"], reverse=True
        ):
            print(f"\nDefect Type: {defect_type}")
            print(f"  Total dismissals: {pattern['total_dismissals']}")
            print(f"  Suspicious dismissals: {pattern['suspicious_dismissals']}")
            print(f"  Avg suspicion score: {pattern['avg_suspicion_score']:.1f}/100")
            if pattern["total_dismissals"] > 0:
                sus_rate = 100 * pattern["suspicious_dismissals"] / pattern["total_dismissals"]
                print(f"  Suspicious rate: {sus_rate:.1f}%")

    except Exception as e:
        logger.error(f"Pattern analysis failed: {e}", exc_info=True)

if __name__ == "__main__":
    # Run examples
    example_single_classification()
    # Uncomment below to run full workflow (requires API access):
    # example_full_workflow()
    # example_pattern_analysis()
