#!/usr/bin/env python
"""Example usage of the Geographic Hotspot Analysis Workflow.

This script demonstrates:
1. Basic hotspot analysis for a single borough
2. Full-corpus analysis across all NYC
3. Direct classifier usage
4. Output inspection and reporting

Run:
    python examples_hotspot_workflow.py
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from socrata_toolkit.analysis.hotspot_classifier import (
    DensityLevel,
    HotspotClassificationEngine,
    HotspotMetrics,
    HotspotType,
    Trend,
)
from socrata_toolkit.analysis.hotspot_workflow import GeographicHotspotWorkflow


def example_1_single_borough_analysis():
    """Example 1: Analyze hotspots in Manhattan only."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Single Borough Analysis (Manhattan)")
    print("=" * 70)

    workflow = GeographicHotspotWorkflow(
        violations_fourfour="dntt-gqwq",
        complaints_fourfour="erm2-nwe9",
        inspections_fourfour="p7ve-f997",  # Example; may not exist
    )

    print("\nRunning hotspot analysis for Manhattan...")
    result = workflow.run(borough_filter="MN", sample_size=3000)

    # Print summary
    print("\nSummary:")
    print(f"  Total hotspots detected: {result['summary']['total_hotspots']}")
    print(f"  High-severity hotspots: {result['summary']['high_severity_count']}")
    print(f"  Borough: {result['summary']['borough_filter']}")

    # Print top 3 priorities
    print("\nTop 3 Priority Hotspots:")
    for i, hotspot in enumerate(result['hotspots'][:3], 1):
        print(f"\n  {i}. {hotspot['hotspot_id']}")
        print(f"     Type: {hotspot['hotspot_type']}")
        print(f"     Severity Score: {hotspot['severity_score']:.1f}/100")
        print(f"     Density: {hotspot['density_level']} ({hotspot['density_per_sqkm']:.1f} events/sq km)")
        print(f"     Trend: {hotspot['trend']}")
        print(f"     Resource Allocation: {hotspot['resource_allocation']}")
        print(f"     Estimated Backlog: {hotspot['estimated_backlog_days']} days")
        print(f"     Recommendation: {hotspot['recommendation'][:120]}...")

    # Print Claude guidance
    if result['claude_guidance']:
        print("\nClaude's Resource Allocation Guidance:")
        print(f"  {result['claude_guidance'][:200]}...")

    # Print execution log
    print("\nExecution Log:")
    for log_entry in result['execution_log']:
        print(f"  {log_entry}")

    # Print errors if any
    if result['final_report']['errors']:
        print("\nErrors Encountered:")
        for error in result['final_report']['errors']:
            print(f"  {error}")

    # Save map
    if result['map_html']:
        output_file = "hotspot_map_manhattan.html"
        with open(output_file, "w") as f:
            f.write(result['map_html'])
        print(f"\nMap saved to {output_file}")

    # Save report
    output_file = "hotspot_report_manhattan.json"
    with open(output_file, "w") as f:
        json.dump(result['final_report'], f, indent=2)
    print(f"Report saved to {output_file}")

    return result

def example_2_direct_classifier_usage():
    """Example 2: Use classifier directly on hypothetical cluster data."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Direct Classifier Usage (No Workflow)")
    print("=" * 70)

    # Define some test hotspot metrics
    test_cases = [
        HotspotMetrics(
            hotspot_id="HS_URGENT_001",
            latitude=40.7505,
            longitude=-73.9972,
            density_per_sqkm=120.0,
            event_count=200,
            recent_event_count=80,
            event_types=["violation", "complaint"],
            trend_direction=Trend.GROWING,
            trend_pct_change=0.35,
            estimated_personnel=2,
            resource_efficiency=0.30,
        ),
        HotspotMetrics(
            hotspot_id="HS_STABLE_002",
            latitude=40.7614,
            longitude=-73.9776,
            density_per_sqkm=45.0,
            event_count=80,
            recent_event_count=8,
            event_types=["violation"],
            trend_direction=Trend.STABLE,
            trend_pct_change=0.02,
            estimated_personnel=3,
            resource_efficiency=0.65,
        ),
        HotspotMetrics(
            hotspot_id="HS_DECLINING_003",
            latitude=40.7489,
            longitude=-73.9680,
            density_per_sqkm=12.0,
            event_count=30,
            recent_event_count=2,
            event_types=["complaint"],
            trend_direction=Trend.SHRINKING,
            trend_pct_change=-0.30,
            estimated_personnel=2,
            resource_efficiency=0.80,
        ),
    ]

    engine = HotspotClassificationEngine()
    classifiers = []

    print(f"\nClassifying {len(test_cases)} test hotspots:")
    for metrics in test_cases:
        classifier = engine.classify(metrics, total_hotspots=len(test_cases))
        classifiers.append(classifier)

    # Rank by severity
    ranked = engine.rank_hotspots(classifiers)

    for classifier in ranked:
        print(f"\n{classifier.hotspot_id}:")
        print(f"  Type: {classifier.hotspot_type.value}")
        print(f"  Density Level: {classifier.density_level.value}")
        print(f"  Severity Score: {classifier.severity_score:.1f}/100")
        print(f"  Trend: {classifier.trend.value}")
        print(f"  Resource Allocation: {classifier.resource_allocation.value}")
        print(f"  Priority Rank: {classifier.priority_rank}/{len(ranked)}")
        print(f"  Reasoning: {classifier.classification_reasoning}")
        print(f"  Recommendation: {classifier.recommendation[:150]}...")
        print(f"  Estimated Backlog: {classifier.estimated_backlog_days} days")

    # Export to JSON
    output_file = "hotspot_classifications.json"
    with open(output_file, "w") as f:
        json.dump([c.to_dict() for c in ranked], f, indent=2)
    print(f"\nClassifications saved to {output_file}")

def example_3_batch_analysis():
    """Example 3: Run analysis on multiple boroughs sequentially."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Batch Analysis Across Boroughs")
    print("=" * 70)

    workflow = GeographicHotspotWorkflow(
        violations_fourfour="dntt-gqwq",
        complaints_fourfour="erm2-nwe9",
        inspections_fourfour="p7ve-f997",
    )

    boroughs = ["MN", "BX", "BK", "QN", "SI"]
    all_results = {}

    for borough in boroughs:
        print(f"\nAnalyzing {borough}...")
        result = workflow.run(borough_filter=borough, sample_size=2000)
        all_results[borough] = result

        print(f"  Hotspots: {result['summary']['total_hotspots']}")
        print(f"  High-severity: {result['summary']['high_severity_count']}")

        if result['hotspots']:
            top_hotspot = result['hotspots'][0]
            print(f"  Top priority: {top_hotspot['hotspot_id']} "
                  f"(severity: {top_hotspot['severity_score']:.0f})")

    # Summary across all boroughs
    print("\n" + "-" * 70)
    print("Aggregate Summary:")
    print("-" * 70)

    total_hotspots = sum(r['summary']['total_hotspots'] for r in all_results.values())
    total_high_severity = sum(r['summary']['high_severity_count'] for r in all_results.values())

    print(f"Total hotspots across all boroughs: {total_hotspots}")
    print(f"Total high-severity: {total_high_severity}")

    # Borough breakdown
    print("\nBy Borough:")
    for borough in boroughs:
        result = all_results[borough]
        print(f"  {borough}: {result['summary']['total_hotspots']} hotspots, "
              f"{result['summary']['high_severity_count']} high-severity")

    # Save aggregate report
    output_file = "hotspot_report_all_boroughs.json"
    summary = {
        "total_hotspots": total_hotspots,
        "total_high_severity": total_high_severity,
        "by_borough": {
            borough: {
                "total_hotspots": all_results[borough]['summary']['total_hotspots'],
                "high_severity": all_results[borough]['summary']['high_severity_count'],
            }
            for borough in boroughs
        }
    }
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nAggregate report saved to {output_file}")

def main():
    """Run all examples."""
    print("\n")
    print("=" * 70)
    print("  Geographic Hotspot Analysis Workflow - Examples".center(70))
    print("=" * 70)

    try:
        # Example 1: Single borough
        # Uncomment if you have live Socrata access and valid token
        # example_1_single_borough_analysis()

        # Example 2: Direct classifier usage (no external API calls required)
        example_2_direct_classifier_usage()

        # Example 3: Batch analysis
        # Uncomment if you have live Socrata access and valid token
        # example_3_batch_analysis()

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n" + "=" * 70)
    print("All examples completed successfully!")
    print("=" * 70)
    return 0

if __name__ == "__main__":
    sys.exit(main())
