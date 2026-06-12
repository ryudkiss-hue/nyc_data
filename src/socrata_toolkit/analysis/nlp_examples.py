"""
Examples: Hardcoded NLP classification + analysis.

Shows how to classify and analyze text data without LLM calls.
"""

import pandas as pd

from socrata_toolkit.analysis.nlp_analysis import DatasetAnalyzerWithNLP
from socrata_toolkit.core.client import SocrataClient, SocrataConfig


def example_classify_violations():
    """Fetch violations data and classify by type/severity."""
    client = SocrataClient(SocrataConfig())
    analyzer = DatasetAnalyzerWithNLP()

    # Fetch violations sample
    df = client.fetch_dataframe(
        "data.cityofnewyork.us", "6kbp-uz6m", max_rows=1000
    )

    # Classify and get summary
    result = analyzer.analyze_dataset(df, "violations")

    enriched_df = result["dataframe"]
    summary = result["summary"]

    print(f"\nViolation Classification Summary ({result['total_records']} records)")
    print(summary)

    # Extract high-severity violations
    high_severity = analyzer.get_high_severity_records(
        enriched_df, "violations", severity_threshold=75
    )
    print(f"\nHigh-Severity Violations: {len(high_severity)}")
    print(high_severity[["description", "violation_type", "violation_severity"]].head())

    # Borough breakdown
    borough_stats = analyzer.borough_breakdown(enriched_df, "violations")
    print("\nViolations by Borough:")
    for borough, stats in borough_stats.items():
        print(f"\n{borough}:")
        print(stats)

def example_classify_311_complaints():
    """Fetch 311 complaints and classify by urgency."""
    client = SocrataClient(SocrataConfig())
    analyzer = DatasetAnalyzerWithNLP()

    # Fetch complaints sample
    df = client.fetch_dataframe(
        "data.cityofnewyork.us", "erm2-nwe9", max_rows=500
    )

    # Classify
    result = analyzer.analyze_dataset(df, "complaints_311")

    print(f"\n311 Complaint Classification ({result['total_records']} records)")
    print(result["summary"])

    # Find urgent complaints
    urgent = analyzer.get_high_severity_records(
        result["dataframe"], "complaints_311", severity_threshold=80
    )
    print(f"\nUrgent Complaints: {len(urgent)}")
    print(urgent[["description", "complaint_category", "complaint_urgency"]].head())

def example_classify_tree_damage():
    """Fetch tree damage data and classify by damage type."""
    client = SocrataClient(SocrataConfig())
    analyzer = DatasetAnalyzerWithNLP()

    # Fetch tree damage
    df = client.fetch_dataframe(
        "data.cityofnewyork.us", "j6v2-6uxq", max_rows=300
    )

    result = analyzer.analyze_dataset(df, "tree_damage")

    print(f"\nTree Damage Classification ({result['total_records']} records)")
    print(result["summary"])

    # Hazardous trees
    hazardous = analyzer.get_high_severity_records(
        result["dataframe"], "tree_damage", severity_threshold=70
    )
    print(f"\nHazardous Trees: {len(hazardous)}")

def example_construction_inspections():
    """Fetch construction inspections and classify findings."""
    client = SocrataClient(SocrataConfig())
    analyzer = DatasetAnalyzerWithNLP()

    # Fetch construction inspections
    df = client.fetch_dataframe(
        "data.cityofnewyork.us", "ydkf-mpxb", max_rows=500
    )

    result = analyzer.analyze_dataset(
        df, "street_construction_inspections", text_column="finding_description"
    )

    print(f"\nConstruction Inspection Findings ({result['total_records']} records)")
    print(result["summary"])

    # Safety concerns
    safety_issues = analyzer.get_high_severity_records(
        result["dataframe"],
        "street_construction_inspections",
        severity_threshold=75
    )
    print(f"\nSafety Concerns: {len(safety_issues)}")

def example_multi_dataset_analysis():
    """
    Hardcoded workflow: Fetch multiple datasets, classify all,
    then pass high-level summaries to Claude for interpretation.
    """
    client = SocrataClient(SocrataConfig())
    analyzer = DatasetAnalyzerWithNLP()

    datasets_to_analyze = [
        ("violations", "6kbp-uz6m", 500),
        ("complaints_311", "erm2-nwe9", 500),
        ("tree_damage", "j6v2-6uxq", 200),
    ]

    all_summaries = {}

    for dataset_key, fourfour, limit in datasets_to_analyze:
        print(f"\n[Hardcoded] Classifying {dataset_key}...")

        # Fetch
        df = client.fetch_dataframe("data.cityofnewyork.us", fourfour, max_rows=limit)

        # Classify (deterministic, no LLM)
        result = analyzer.analyze_dataset(df, dataset_key)

        all_summaries[dataset_key] = {
            "total": result["total_records"],
            "summary": result["summary"].to_dict() if result["summary"] is not None else None,
            "high_severity_count": len(
                analyzer.get_high_severity_records(result["dataframe"], dataset_key, threshold=70)
            ),
        }

        print(f"✓ {result['total_records']} records classified")

    # NOW Claude only interprets structured facts, not raw text
    print("\n" + "=" * 60)
    print("HARDCODED ANALYSIS COMPLETE")
    print("=" * 60)
    print("\nStructured facts for Claude to interpret:")
    for dataset_key, summary_data in all_summaries.items():
        print(f"\n{dataset_key}:")
        print(f"  - Total records: {summary_data['total']}")
        print(f"  - High-severity items: {summary_data['high_severity_count']}")
        if summary_data["summary"]:
            print(f"  - Top categories: {list(summary_data['summary'].keys())[:3]}")

    # Claude now gets this summary instead of raw text
    # Token usage: ~500 tokens vs ~5000 if Claude parsed raw text
    print("\n[Hardcoded NLP saves ~2500 tokens per analysis]")

    return all_summaries

def example_borough_focused_analysis():
    """Analyze violations by borough to find problem areas."""
    client = SocrataClient(SocrataConfig())
    analyzer = DatasetAnalyzerWithNLP()

    # Fetch violations
    df = client.fetch_dataframe(
        "data.cityofnewyork.us", "6kbp-uz6m", max_rows=2000
    )

    result = analyzer.analyze_dataset(df, "violations")
    enriched_df = result["dataframe"]

    # Borough breakdown
    borough_stats = analyzer.borough_breakdown(enriched_df, "violations")

    print("\nViolation Patterns by Borough")
    print("=" * 60)

    for borough in sorted(borough_stats.keys()):
        stats_df = borough_stats[borough]
        total_violations = stats_df[("violation_severity", "count")].sum()
        avg_severity = stats_df[("violation_severity", "mean")].mean()

        print(f"\n{borough}: {int(total_violations)} violations, avg severity {avg_severity:.1f}")

        # Top issue type
        top_issue = stats_df[("violation_severity", "count")].idxmax()
        top_count = stats_df.loc[top_issue, ("violation_severity", "count")]
        print(f"  → Most common: {top_issue} ({int(top_count)} cases)")

    # Hardcoded facts ready for Claude interpretation:
    # Claude: "These are the violation patterns by borough. What should DOT prioritize?"
    # (instead of Claude parsing raw descriptions itself)

if __name__ == "__main__":
    print("NYC DOT NLP Classification Examples")
    print("=" * 60)

    # Uncomment to run examples:
    # example_classify_violations()
    # example_classify_311_complaints()
    # example_classify_tree_damage()
    # example_construction_inspections()
    # example_multi_dataset_analysis()
    # example_borough_focused_analysis()

    print("\nTo use these examples:")
    print("  1. Set SOCRATA_APP_TOKEN environment variable")
    print("  2. Uncomment an example in __main__")
    print("  3. Run: python -m socrata_toolkit.analysis.nlp_examples")
