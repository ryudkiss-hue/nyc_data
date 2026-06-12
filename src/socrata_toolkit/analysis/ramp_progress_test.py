"""
Test and demo file for Ramp Progress Tracking workflow.

Shows:
1. RampStatusClassifier usage
2. Classification summary statistics
3. Workflow execution (when dependencies available)

Run with: python -m socrata_toolkit.analysis.ramp_progress_test
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict

# NOTE: Only import the classifier; don't import workflow yet (spacy dependency)
from socrata_toolkit.analysis.ramp_status import (
    BlockerType,
    RampStatus,
    RampStatusClassifier,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_ramp_classifier():
    """Test RampStatusClassifier with sample descriptions."""
    print("\n" + "=" * 70)
    print("TEST 1: RampStatusClassifier on Sample Descriptions")
    print("=" * 70)

    try:
        classifier = RampStatusClassifier()
    except Exception as e:
        print(f"[SKIP] spaCy not available: {e}")
        print("       To enable: pip install -e '.[nlp]'")
        return

    # Sample ramp progress descriptions from NYC data
    sample_descriptions = [
        "Completed - Ramp installed and approved by DCP. Ready for public use.",
        "In progress - Fabrication 60% complete. Installation scheduled for Q2 2026.",
        "Blocked by permit - Waiting for DOB approval. Expected delay 2-3 weeks.",
        "Stalled due to weather. Work resumed once temperature normalizes.",
        "Not started - Design phase pending budget allocation. Queued for spring 2027.",
        "Under construction. Foundation work ongoing. 45% complete.",
        "Permit pending with DOE for utility coordination. Critical path item.",
        "Material shortage delaying installation. Supply chain issue expected to resolve.",
        "Contractor workforce constraints. Additional crew allocated to accelerate.",
        "Design and planning phase complete. Awaiting final permitting approval.",
    ]

    results = []
    for desc in sample_descriptions:
        try:
            result = classifier.classify(desc)
            results.append(result)
            print(f"\nDescription: {desc[:60]}...")
            print(f"  Status: {result.status.value}")
            print(f"  Work Stage: {result.work_stage_percent:.0f}%")
            print(f"  Blockers: {[b.value for b in result.blocker_types]}")
            print(f"  Confidence: {result.confidence_score:.0f}%")
        except Exception as e:
            logger.error(f"Classification failed: {e}")

    # Summary statistics
    print("\n" + "=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)
    summary = RampStatusClassifier.summary_table(results)
    print(json.dumps(summary, indent=2))

    return results, classifier


def test_workflow_imports():
    """Test that workflow can be imported (without running it)."""
    print("\n" + "=" * 70)
    print("TEST 2: Workflow Module Imports")
    print("=" * 70)

    try:
        from socrata_toolkit.analysis.ramp_progress_workflow import (
            BoroughRampStats,
            RampProgressState,
            create_ramp_workflow,
            run_ramp_workflow,
        )
        print("[PASS] All workflow classes imported successfully")
        print(f"  - BoroughRampStats: {BoroughRampStats.__name__}")
        print("  - RampProgressState: dict-based state")
        print(f"  - create_ramp_workflow: {create_ramp_workflow.__name__}")
        print(f"  - run_ramp_workflow: {run_ramp_workflow.__name__}")
        return True
    except Exception as e:
        print(f"[FAIL] Workflow import failed: {e}")
        return False


def test_classifier_batch():
    """Test batch classification and filtering."""
    print("\n" + "=" * 70)
    print("TEST 3: Batch Classification and Filtering")
    print("=" * 70)

    try:
        classifier = RampStatusClassifier()
    except Exception as e:
        print(f"[SKIP] spaCy not available: {e}")
        return

    descriptions = [
        "Completed - Ready for use",
        "In progress - 70% complete",
        "Blocked by permit",
        "Not started yet",
        "Stalled due to weather and budget constraints",
    ]

    results_dict = classifier.classify_batch(descriptions)
    print(f"Classified {len(results_dict)} descriptions\n")

    # Group by status
    by_status = {}
    for text, result in results_dict.items():
        status = result.status.value
        if status not in by_status:
            by_status[status] = []
        by_status[status].append({
            "text": text[:50],
            "work_stage": result.work_stage_percent,
            "blockers": [b.value for b in result.blocker_types],
        })

    for status, items in sorted(by_status.items()):
        print(f"\n{status}: ({len(items)} items)")
        for item in items:
            print(f"  - {item['text']}...")
            print(f"    Work stage: {item['work_stage']:.0f}%")
            if item['blockers']:
                print(f"    Blockers: {', '.join(item['blockers'])}")


def test_blocker_extraction():
    """Test blocker type extraction."""
    print("\n" + "=" * 70)
    print("TEST 4: Blocker Type Extraction")
    print("=" * 70)

    try:
        classifier = RampStatusClassifier()
    except Exception as e:
        print(f"[SKIP] spaCy not available: {e}")
        return

    blocker_texts = [
        "Waiting for DOB permit approval",
        "Weather delays - construction paused",
        "Budget allocation pending",
        "Material supply chain issues",
        "Contractor workforce constraints",
        "Utility coordination required with Con Ed",
        "Multiple issues: permit pending AND weather delay",
    ]

    for text in blocker_texts:
        result = classifier.classify(text)
        blockers = [b.value for b in result.blocker_types]
        print(f"\nText: {text}")
        print(f"  Blockers identified: {blockers if blockers else '(none)'}")


def test_confidence_scoring():
    """Test confidence scoring logic."""
    print("\n" + "=" * 70)
    print("TEST 5: Confidence Scoring")
    print("=" * 70)

    try:
        classifier = RampStatusClassifier()
    except Exception as e:
        print(f"[SKIP] spaCy not available: {e}")
        return

    test_cases = [
        ("Completed", 60),  # Should have high confidence
        ("In progress 50%", 65),  # Status + percentage = high conf
        ("Ramp work", 20),  # Vague = low conf
        (
            "Completed - installed and approved. "
            "Permit obtained from DOB. Weather delays resolved. "
            "Ready 2026-06-15.",
            90,
        ),  # Multiple signals = very high conf
    ]

    for text, expected_min_conf in test_cases:
        result = classifier.classify(text)
        status = "PASS" if result.confidence_score >= expected_min_conf else "WARN"
        print(f"\n[{status}] '{text[:40]}...'")
        print(f"  Confidence: {result.confidence_score:.0f}% (expected >= {expected_min_conf}%)")


def test_wilson_ci():
    """Test Wilson Score CI computation."""
    print("\n" + "=" * 70)
    print("TEST 6: Wilson Score Confidence Intervals")
    print("=" * 70)

    from socrata_toolkit.analysis.confidence_intervals import (
        wilson_score_confidence_interval,
    )

    test_cases = [
        (350, 400, "Manhattan large sample"),
        (10, 20, "Small borough sample"),
        (0, 50, "No completions"),
        (50, 50, "All completed"),
    ]

    for successes, total, label in test_cases:
        result = wilson_score_confidence_interval(successes, total, confidence_level=0.95)
        completion_pct = result["point_estimate"] * 100
        ci_lower = result["lower_bound"] * 100
        ci_upper = result["upper_bound"] * 100
        print(f"\n{label} ({successes}/{total}):")
        print(f"  Completion Rate: {completion_pct:.1f}%")
        print(f"  95% CI: [{ci_lower:.1f}%, {ci_upper:.1f}%]")
        print(f"  SE: {result['standard_error']:.4f}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("RAMP PROGRESS TRACKING: COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    # Run tests
    test_workflow_imports()
    test_ramp_classifier()
    test_classifier_batch()
    test_blocker_extraction()
    test_confidence_scoring()
    test_wilson_ci()

    print("\n" + "=" * 70)
    print("TEST SUITE COMPLETE")
    print("=" * 70)
    print(
        "\nTo run the full workflow with live data:\n"
        "  python -c 'from socrata_toolkit.analysis import run_ramp_workflow; "
        "result = run_ramp_workflow(max_rows=500); print(result[\"final_report\"])'"
    )
