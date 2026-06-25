#!/usr/bin/env python3
"""
Demo: Enhanced QuestionMetricResolver with Fuzzy Matching + Memora Context Enrichment

This script demonstrates:
1. Exact question matching
2. Fuzzy matching with diverse question variations
3. BM25 weighting (80%) + FastText (15%) + Jaccard (5%)
4. Memora context enrichment (glossary, constraints, output format)
5. Confidence scoring and strategy attribution

Run:
    python scripts/demo_fuzzy_matching_resolver.py
"""

import sys
from pathlib import Path
import io

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from socrata_toolkit.core.question_resolver import QuestionMetricResolver


def demo_exact_matching():
    """Demonstrate exact question matching"""
    print("\n" + "=" * 80)
    print("DEMO 1: Exact Question Matching")
    print("=" * 80)

    resolver = QuestionMetricResolver(enable_fuzzy_matching=True)

    exact_questions = [
        "What is the current Sidewalk Condition Index (SCI) across all boroughs?",
        "What percentage of street intersections have ADA-compliant curb ramps?",
        "What is the year-by-year budget required to maintain current condition levels?",
    ]

    for question in exact_questions:
        resolution = resolver.resolve_question(question)
        if resolution:
            print(f"\n✓ MATCHED: {question[:70]}...")
            print(f"  Question ID: {resolution.question_id}")
            print(f"  Category: {resolution.category.value}")
            print(f"  Confidence: {resolution.confidence:.3f}")
            print(f"  Datasets: {', '.join(d.name for d in resolution.datasets)}")
            print(f"  Primary Skill: {resolution.primary_skill.value}")


def demo_fuzzy_matching():
    """Demonstrate fuzzy matching with diverse variations"""
    print("\n" + "=" * 80)
    print("DEMO 2: Fuzzy Matching with Diverse Question Variations")
    print("=" * 80)

    resolver = QuestionMetricResolver(enable_fuzzy_matching=True)

    fuzzy_questions = [
        # A1 variations (Sidewalk Condition)
        "How is sidewalk condition distributed across NYC?",
        "What's the current SCI per borough?",
        "Show me condition scores by neighborhood",

        # E1 variations (Ramp Program)
        "How many ramps are completed vs. scheduled?",
        "What's the ramp completion status?",
        "Are we on track with ADA compliance?",

        # F1 variations (Operational Efficiency)
        "How long does it take from complaint to fix?",
        "What's the inspection turnaround time?",
        "Show me complaint resolution SLA metrics",

        # C1 variations (Data Quality)
        "How fresh is our condition data?",
        "What percentage of segments have recent assessments?",
        "Data freshness and staleness report",
    ]

    for question in fuzzy_questions:
        resolution = resolver.resolve_question(question)
        if resolution:
            print(f"\n✓ MATCHED: {question}")
            print(f"  Question ID: {resolution.question_id}")
            print(f"  Confidence: {resolution.confidence:.3f}")
            print(f"  Category: {resolution.category.value}")
            print(f"  Strategy: {resolution.notes[:100] if resolution.notes else 'Simple match'}")


def demo_bm25_weighting():
    """Demonstrate BM25 scoring breakdown"""
    print("\n" + "=" * 80)
    print("DEMO 3: BM25 Weighting (80%) + FastText (15%) + Jaccard (5%)")
    print("=" * 80)

    resolver = QuestionMetricResolver(enable_fuzzy_matching=True)

    test_question = "What is the current Sidewalk Condition Index (SCI) across all boroughs?"
    match_detail = resolver._fuzzy_match_with_bm25(test_question)

    if match_detail:
        print(f"\nQuery: {test_question}")
        print(f"Matched: {match_detail.matched_text}")
        print(f"\nScoring Breakdown:")
        print(f"  BM25 Score:      {match_detail.bm25_score:.4f} × 0.80 = {match_detail.bm25_score * 0.80:.4f}")
        print(f"  FastText Score:  {match_detail.fasttext_score:.4f} × 0.15 = {match_detail.fasttext_score * 0.15:.4f}")
        print(f"  Jaccard Score:   {match_detail.jaccard_score:.4f} × 0.05 = {match_detail.jaccard_score * 0.05:.4f}")
        print(f"  ───────────────────────────────────────────")
        print(f"  Composite Score: {match_detail.confidence:.4f}")
        print(f"  Strategy: {match_detail.strategy}")


def demo_memora_enrichment():
    """Demonstrate memora context enrichment"""
    print("\n" + "=" * 80)
    print("DEMO 4: Memora Context Enrichment")
    print("=" * 80)

    resolver = QuestionMetricResolver(enable_fuzzy_matching=True)

    print("\nGlossary Terms:")
    for term, definition in resolver.memora_context.get("glossary_terms", {}).items():
        print(f"  • {term}: {definition}")

    print("\nAnalytical Constraints:")
    constraints = resolver.memora_context.get("constraints", {})
    print(f"  • Stale datasets to avoid: {', '.join(constraints['stale_datasets'][:2])}")
    print(f"  • Minimum sample size: {constraints['min_sample_size']}")
    print(f"  • Confidence method: {constraints['confidence_method']}")

    print("\nOutput Format Standards:")
    output_format = resolver.memora_context.get("output_format", {})
    print(f"  • Borough order: {', '.join(output_format['borough_order'])}")
    print(f"  • Rate decimals: {output_format['rate_decimals']}")
    print(f"  • Count format: {output_format['count_format']}")


def demo_confidence_comparison():
    """Compare exact vs. fuzzy match confidence"""
    print("\n" + "=" * 80)
    print("DEMO 5: Confidence Scoring — Exact vs. Fuzzy Matches")
    print("=" * 80)

    resolver = QuestionMetricResolver(enable_fuzzy_matching=True)

    test_pairs = [
        (
            "What is the current Sidewalk Condition Index (SCI) across all boroughs?",
            "How is sidewalk condition distributed across NYC?",
        ),
        (
            "What percentage of street intersections have ADA-compliant curb ramps?",
            "How many ADA ramps do we need per intersection?",
        ),
        (
            "What is the average inspection turnaround time from 311 complaint to completion?",
            "How long does inspection take from complaint to fix?",
        ),
    ]

    for exact_q, fuzzy_q in test_pairs:
        exact_res = resolver.resolve_question(exact_q)
        fuzzy_res = resolver.resolve_question(fuzzy_q)

        if exact_res and fuzzy_res:
            print(f"\nExact:  {exact_q[:60]}...")
            print(f"        Confidence: {exact_res.confidence:.3f} (Q{exact_res.question_id})")
            print(f"\nFuzzy:  {fuzzy_q[:60]}...")
            print(f"        Confidence: {fuzzy_res.confidence:.3f} (Q{fuzzy_res.question_id})")
            print(f"        Difference: {abs(exact_res.confidence - fuzzy_res.confidence):.3f}")


def demo_dataset_mapping():
    """Show dataset mapping for a resolved question"""
    print("\n" + "=" * 80)
    print("DEMO 6: Dataset Mapping for Resolved Question")
    print("=" * 80)

    resolver = QuestionMetricResolver(enable_fuzzy_matching=True)

    question = "What is the current Sidewalk Condition Index (SCI) across all boroughs?"
    resolution = resolver.resolve_question(question)

    if resolution:
        print(f"\nQuestion: {question}")
        print(f"Resolved to Q{resolution.question_id}")
        print(f"\nCritical Datasets (required for this analysis):")

        for dataset in resolution.critical_datasets:
            print(f"\n  • {dataset.name} ({dataset.fourfour})")
            print(f"    Purpose: {dataset.purpose}")
            print(f"    Criticality: {dataset.criticality}")
            if dataset.key_columns:
                print(f"    Key columns: {', '.join(dataset.key_columns[:3])}...")

        print(f"\nMetrics to Calculate:")
        for metric in resolution.metrics:
            print(f"  • {metric.metric_id}: {metric.metric_name}")
            print(f"    Formula: {metric.formula}")
            if metric.target_value:
                print(f"    Target: {metric.target_value}")

        print(f"\nAnalysis Skills:")
        print(f"  Primary: {resolution.primary_skill.value}")
        if resolution.secondary_skills:
            print(f"  Secondary: {', '.join(s.value for s in resolution.secondary_skills)}")


def demo_all_questions_by_category():
    """List all registered questions by category"""
    print("\n" + "=" * 80)
    print("DEMO 7: All Registered Questions by Category")
    print("=" * 80)

    resolver = QuestionMetricResolver(enable_fuzzy_matching=True)

    all_questions = resolver.get_all_questions()
    by_category = {}

    for res in all_questions:
        cat = res.category.value
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(res)

    for category in sorted(by_category.keys()):
        print(f"\n{category.upper()}:")
        for res in by_category[category]:
            print(f"  Q{res.question_id}: {res.question_text[:70]}...")


def main():
    """Run all demos"""
    print("\n" + "=" * 80)
    print("Enhanced QuestionMetricResolver with Fuzzy Matching + Memora Enrichment")
    print("=" * 80)

    demo_exact_matching()
    demo_fuzzy_matching()
    demo_bm25_weighting()
    demo_memora_enrichment()
    demo_confidence_comparison()
    demo_dataset_mapping()
    demo_all_questions_by_category()

    print("\n" + "=" * 80)
    print("Demo Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
