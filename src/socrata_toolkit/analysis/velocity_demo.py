"""
Demo: Inspection Velocity Analysis Workflow

Shows how to use the velocity_classifier and velocity_analysis_workflow
to analyze inspector performance and generate coaching recommendations.

Run with: python -m socrata_toolkit.analysis.velocity_demo
"""

import json
import pandas as pd
from datetime import datetime, timedelta

# Import velocity components
from .velocity_classifier import (
    VelocityClassifier,
    VelocityMetrics,
    PerformanceTier,
)
from .velocity_analysis_workflow import (
    VelocityAnalysisContext,
    VelocityState,
    run_velocity_analysis,
)


def demo_classifier():
    """Demo 1: VelocityClassifier with sample inspector metrics."""
    print("\n" + "=" * 70)
    print("DEMO 1: VelocityClassifier - Single Inspector Classification")
    print("=" * 70)

    classifier = VelocityClassifier()

    # Sample inspector profiles
    profiles = [
        {
            "name": "Alice Chen (High Performer)",
            "inspection_count": 24,
            "weeks": 4,
            "violations": 96,
            "dismissals": 2,
            "reopened": 1,
            "days_to_close": 22,
        },
        {
            "name": "Bob Rodriguez (Medium Performer)",
            "inspection_count": 12,
            "weeks": 4,
            "violations": 36,
            "dismissals": 3,
            "reopened": 2,
            "days_to_close": 45,
        },
        {
            "name": "Carol Wang (Low Performer)",
            "inspection_count": 4,
            "weeks": 4,
            "violations": 8,
            "dismissals": 2,
            "reopened": 1,
            "days_to_close": 75,
        },
    ]

    for profile in profiles:
        metrics = VelocityMetrics(
            inspector_id=f"INS_{profile['name'].split()[0].upper()}",
            inspector_name=profile["name"].split(" (")[0],
            period_start=pd.Timestamp("2026-05-01"),
            period_end=pd.Timestamp("2026-05-31"),
            inspection_count=profile["inspection_count"],
            inspections_per_week=profile["inspection_count"] / profile["weeks"],
            total_violations=profile["violations"],
            violations_per_inspection=profile["violations"] / max(profile["inspection_count"], 1),
            dismissal_count=profile["dismissals"],
            dismissal_rate=profile["dismissals"] / max(profile["inspection_count"], 1),
            reopened_count=profile["reopened"],
            reopened_rate=profile["reopened"] / max(profile["violations"], 1),
            accuracy_ratio=1.0 - (profile["reopened"] / max(profile["violations"], 1)),
            avg_days_to_close=profile["days_to_close"],
            median_days_to_close=profile["days_to_close"] * 0.95,
            velocity_std_dev=0.5,
            data_quality_flag="HIGH",
            sample_size=profile["inspection_count"],
        )

        classification = classifier.classify(metrics)

        print(f"\n{profile['name']}")
        print(f"  Period: {metrics.period_start.date()} to {metrics.period_end.date()}")
        print(f"  Tier: {classification.performance_tier.value}")
        print(f"  Composite Score: {classification.composite_score:.1f}/100")
        print(f"    - Velocity:    {classification.velocity_score:.1f}/100")
        print(f"    - Quality:     {classification.quality_score:.1f}/100")
        print(f"    - Accuracy:    {classification.accuracy_score:.1f}/100")
        print(f"    - Efficiency:  {classification.efficiency_score:.1f}/100")
        print(f"  Anomaly: {classification.anomaly.value}")
        if classification.metric_drivers:
            print(f"  Drivers: {', '.join([d.value for d in classification.metric_drivers])}")
        print(f"  Coaching: {classification.coaching_focus}")
        if classification.flagged_issues:
            print(f"  Flags: {', '.join(classification.flagged_issues)}")


def demo_workflow():
    """Demo 2: Full VelocityAnalysisWorkflow (LangGraph-based)."""
    print("\n" + "=" * 70)
    print("DEMO 2: Velocity Analysis Workflow (Full Pipeline)")
    print("=" * 70)

    start_date = pd.Timestamp("2026-05-01")
    end_date = pd.Timestamp("2026-05-31")

    print(f"\nConfiguration:")
    print(f"  Start: {start_date.date()}")
    print(f"  End: {end_date.date()}")
    print(f"  Borough: All")
    print(f"  Inspector IDs: All")

    print(f"\nWorkflow Steps:")
    print(f"  1. Fetch inspections, violations, dismissals from Socrata")
    print(f"  2. Group by inspector, compute metrics")
    print(f"  3. Classify with VelocityClassifier")
    print(f"  4. Query Claude for insights (~300 tokens)")
    print(f"  5. Generate coaching recommendations")
    print(f"  6. Build final report with execution log")

    print(f"\nNote: Full workflow requires Socrata API access and Claude API key.")
    print(f"      For testing, use demo_classifier() above.")


def demo_json_output():
    """Demo 3: JSON export for integration with dashboards."""
    print("\n" + "=" * 70)
    print("DEMO 3: JSON Export (Dashboard Integration)")
    print("=" * 70)

    classifier = VelocityClassifier()

    metrics = VelocityMetrics(
        inspector_id="INS_A001",
        inspector_name="Alice Chen",
        period_start=pd.Timestamp("2026-05-01"),
        period_end=pd.Timestamp("2026-05-31"),
        inspection_count=24,
        inspections_per_week=6.0,
        total_violations=96,
        violations_per_inspection=4.0,
        dismissal_count=2,
        dismissal_rate=0.083,
        reopened_count=1,
        reopened_rate=0.010,
        accuracy_ratio=0.99,
        avg_days_to_close=22.0,
        median_days_to_close=20.0,
        velocity_std_dev=0.5,
        data_quality_flag="HIGH",
        sample_size=24,
    )

    classification = classifier.classify(metrics)

    # Export to dict (JSON-serializable)
    output = classification.to_dict()

    print(f"\nJSON Export (for Streamlit/Dashboard):")
    print(json.dumps(output, indent=2, default=str))


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("INSPECTION VELOCITY ANALYSIS - DEMO")
    print("=" * 70)

    demo_classifier()
    demo_workflow()
    demo_json_output()

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\nAPI Usage:")
    print("  from socrata_toolkit.analysis.velocity_classifier import VelocityClassifier")
    print("  from socrata_toolkit.analysis.velocity_analysis_workflow import run_velocity_analysis")
    print("")
    print("  # Single classification:")
    print("  classifier = VelocityClassifier()")
    print("  result = classifier.classify(metrics)")
    print("")
    print("  # Full workflow:")
    print("  report = run_velocity_analysis(start_date, end_date, borough_filter='MANHATTAN')")
    print("")


if __name__ == "__main__":
    main()
