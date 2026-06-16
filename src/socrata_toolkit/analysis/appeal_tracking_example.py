"""
Appeal & Reinspection Tracking Example Usage

Demonstrates how to use the appeal tracking workflow in production.
Requires spacy NLP module: pip install -e ".[nlp]"

Examples:
  1. Quick classifier test (synthetic data)
  2. Inspector performance analysis
  3. Full workflow execution with Claude assessment
  4. Systemic issue detection
"""

from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd

from socrata_toolkit.analysis.appeal_classifier import (
    AppealOutcomeClassifier,
    AppealResolution,
    InspectorAppealAnalyzer,
)
from socrata_toolkit.analysis.appeal_tracking_workflow import (
    create_appeal_tracking_workflow,
)

# ============================================================================
# EXAMPLE 1: Quick Classifier Test
# ============================================================================

def example_1_classifier_test():
    """Test the appeal classifier with synthetic examples."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Appeal Outcome Classifier")
    print("=" * 80)

    # Initialize classifier
    try:
        classifier = AppealOutcomeClassifier()
    except OSError:
        print("⚠️  spaCy model not installed. Install with: python -m spacy download en_core_web_sm")
        return

    # Test cases
    test_cases = [
        "Original violation upheld. Inspector correctly identified structural crack.",
        "Decision overturned. Repairs were made before reinspection. New evidence confirms compliance.",
        "Partially modified. Severity adjusted due to procedural error in documentation.",
        "Appeal dismissed. Inspector followed proper procedures and evidence is well documented.",
        "Case overturned due to insufficient evidence and lack of photographic documentation.",
    ]

    print("\nClassifying sample appeal decisions:\n")
    for text in test_cases:
        result = classifier.classify(text)
        print(f"Text: {text[:60]}...")
        print(f"  Resolution: {result.resolution.value} (confidence: {result.resolution_confidence:.0f}%)")
        print(f"  Reason: {result.reason.value} (confidence: {result.reason_confidence:.0f}%)")
        print(f"  Keywords: {', '.join(result.keywords_matched[:3])}")
        print()


# ============================================================================
# EXAMPLE 2: Inspector Performance Analysis
# ============================================================================

def example_2_inspector_analysis():
    """Analyze synthetic inspector appeal data."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Inspector Performance Analysis")
    print("=" * 80)

    try:
        from socrata_toolkit.analysis.appeal_classifier import AppealOutcomeClassifier
    except ImportError:
        print("⚠️  spaCy not installed")
        return

    # Create synthetic appeal data
    synthetic_data = [
        {
            "inspector_id": "INS001",
            "inspector_name": "John Smith",
            "decision_notes": "Original violation upheld. Crack properly documented.",
            "created_date": datetime.now() - timedelta(days=30),
        },
        {
            "inspector_id": "INS001",
            "inspector_name": "John Smith",
            "decision_notes": "Overturned. Insufficient evidence in original inspection.",
            "created_date": datetime.now() - timedelta(days=25),
        },
        {
            "inspector_id": "INS001",
            "inspector_name": "John Smith",
            "decision_notes": "Upheld. Proper documentation. Violation valid.",
            "created_date": datetime.now() - timedelta(days=20),
        },
        {
            "inspector_id": "INS002",
            "inspector_name": "Jane Doe",
            "decision_notes": "Decision overturned. Procedural error in severity assessment.",
            "created_date": datetime.now() - timedelta(days=15),
        },
        {
            "inspector_id": "INS002",
            "inspector_name": "Jane Doe",
            "decision_notes": "Overturned due to repairs made. New evidence.",
            "created_date": datetime.now() - timedelta(days=10),
        },
        {
            "inspector_id": "INS003",
            "inspector_name": "Bob Wilson",
            "decision_notes": "Upheld. Violation correctly identified and documented.",
            "created_date": datetime.now() - timedelta(days=5),
        },
    ]

    df = pd.DataFrame(synthetic_data)

    analyzer = InspectorAppealAnalyzer()
    stats = analyzer.compute_inspector_stats(
        df,
        inspector_id_col="inspector_id",
        inspector_name_col="inspector_name",
        outcome_col="decision_notes",
        date_col="created_date",
    )

    print("\nInspector Performance Summary:\n")
    for inspector_id, stat in stats.items():
        print(f"Inspector: {stat.inspector_name} (ID: {inspector_id})")
        print(f"  Total Appeals: {stat.total_appeals}")
        print(f"  Overturn Rate: {stat.overturn_rate:.1%}")
        print(f"  Upheld Rate: {stat.upheld_rate:.1%}")
        print(f"  Coaching Needed: {'Yes' if stat.coaching_needed else 'No'}")
        if stat.coaching_reason:
            print(f"  Reason: {stat.coaching_reason}")
        print()

    # Identify outliers
    outliers = analyzer.identify_outliers(stats, overturn_threshold=0.20)
    print(f"\nPerformance Outliers (threshold: 20%): {len(outliers)}\n")
    for outlier in outliers:
        print(f"  • {outlier.inspector_name} ({outlier.overturn_rate:.1%} overturn rate)")

    # Systemic issues
    systemic = analyzer.compute_systemic_issues(df)
    print("\nSystemic Issues:")
    print(f"  Overall Reversal Rate: {systemic['overall_reversal_rate']:.1%}")
    print("  Recommended Improvements:")
    for improvement in systemic.get("recommended_improvements", []):
        print(f"    • {improvement}")


# ============================================================================
# EXAMPLE 3: Full Workflow Execution
# ============================================================================

def example_3_full_workflow():
    """Run the complete appeal tracking workflow."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Full Appeal Tracking Workflow")
    print("=" * 80)

    try:
        workflow = create_appeal_tracking_workflow()
    except ImportError as e:
        print(f"⚠️  Import error: {e}")
        print("Install missing dependencies: pip install -e '.[nlp]'")
        return

    # Initialize state
    initial_state = {
        "context": None,
        "max_rows": 100,
        "include_coaching_plan": True,
        "reinspection_df": None,
        "dismissal_df": None,
        "combined_appeals_df": None,
        "total_appeals": 0,
        "appeal_classifications": [],
        "inspector_stats": {},
        "outliers": [],
        "systemic_issues": {},
        "claude_assessment": "",
        "coaching_recommendations": "",
        "next_action": "end",
        "final_report": {},
        "execution_log": [],
    }

    print("\nWorkflow Structure:")
    print("  1. Fetch reinspection + dismissal data")
    print("  2. Classify appeal outcomes (spaCy)")
    print("  3. Compute inspector statistics")
    print("  4. Identify performance outliers")
    print("  5. Claude performance assessment")
    print("  6. Generate coaching recommendations")
    print("  7. Generate final report")
    print("\n✓ Workflow created successfully")
    print("  Note: Full execution requires live Socrata API connection")
    print("  Use: result = workflow.invoke(initial_state)")


# ============================================================================
# EXAMPLE 4: CLI Integration
# ============================================================================

def example_4_cli_usage():
    """Show how to integrate with CLI."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: CLI Integration")
    print("=" * 80)

    print("""
Command line usage:

  # Run appeal tracking for all reinspections
  socrata appeal-tracking --output report.json

  # Run with specific borough
  socrata appeal-tracking --borough MN --output manhattan_report.json

  # Run with coaching plan
  socrata appeal-tracking --include-coaching --output full_report.json

  # Stream mode (live updates)
  socrata appeal-tracking --stream

Report output includes:
  - Inspector performance metrics
  - Outliers requiring coaching
  - Systemic process issues
  - Claude assessment (350 tokens)
  - Coaching recommendations
  - Actionable next steps
""")


# ============================================================================
# EXAMPLE 5: API Integration
# ============================================================================

def example_5_api_integration():
    """Show how to call programmatically."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Programmatic API Integration")
    print("=" * 80)

    example_code = """
from socrata_toolkit.analysis.appeal_tracking_workflow import create_appeal_tracking_workflow

# Create workflow
workflow = create_appeal_tracking_workflow()

# Run it
result = workflow.invoke({
    "context": None,
    "max_rows": 500,
    "include_coaching_plan": True,
    "execution_log": [],
})

# Access results
print(f"Total appeals analyzed: {result['total_appeals']}")
print(f"Inspectors needing coaching: {len(result['outliers'])}")
print(f"Claude assessment:\\n{result['claude_assessment']}")
print(f"Coaching plan:\\n{result['coaching_recommendations']}")

# Export to JSON
import json
with open("appeal_report.json", "w") as f:
    json.dump(result["final_report"], f, indent=2)
"""

    print(example_code)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("NYC DOT Appeal & Reinspection Tracking - Examples")
    print("=" * 80)

    # Run all examples
    try:
        example_1_classifier_test()
    except Exception as e:
        print(f"Example 1 skipped: {e}")

    try:
        example_2_inspector_analysis()
    except Exception as e:
        print(f"Example 2 skipped: {e}")

    example_3_full_workflow()
    example_4_cli_usage()
    example_5_api_integration()

    print("\n" + "=" * 80)
    print("For more details, see:")
    print("  - appeal_classifier.py (core classification logic)")
    print("  - appeal_tracking_workflow.py (LangGraph workflow)")
    print("=" * 80 + "\n")
