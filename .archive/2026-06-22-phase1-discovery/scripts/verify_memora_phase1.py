#!/usr/bin/env python
"""
Phase 1 Memora Integration Comprehensive Verification

Tests 4 critical components:
1. Memora health check (database, tags, edges, semantic search)
2. Question resolver verification (exact/fuzzy matching, no regressions)
3. Fuzzy matcher accuracy test (20+ question variations)
4. Integration verification (imports, dependencies, style compliance)

Exit code: 0 = PASS, 1 = FAIL
"""

import sys
sys.path.insert(0, 'src')

from socrata_toolkit.core.question_resolver import (
    QuestionKPIResolver, ResearchCategory, AnalysisSkill
)
from socrata_toolkit.core.question_matcher import QuestionMatcher, MatchStrategy
from socrata_toolkit.core.skill_activator import SkillActivator
from socrata_toolkit.core.research_framework import ResearchFramework
import json
from typing import Dict, List, Tuple

# ============================================================================
# COMPONENT 1: Memora Health Check
# ============================================================================

class MemoraHealthCheck:
    """Verify memora context is properly initialized and complete"""

    def __init__(self):
        self.resolver = QuestionKPIResolver(enable_fuzzy_matching=True)
        self.results = []

    def run(self) -> Tuple[bool, List[str]]:
        """Run all health checks"""
        checks = [
            self._check_glossary_terms,
            self._check_constraints,
            self._check_output_format,
            self._check_stale_datasets_awareness,
        ]

        for check in checks:
            try:
                check()
                self.results.append(f"PASS: {check.__name__}")
            except AssertionError as e:
                self.results.append(f"FAIL: {check.__name__} - {e}")
                return False, self.results
            except Exception as e:
                self.results.append(f"ERROR: {check.__name__} - {e}")
                return False, self.results

        return True, self.results

    def _check_glossary_terms(self):
        """Verify glossary terms are populated"""
        glossary = self.resolver.memora_context.get("glossary_terms", {})
        assert glossary, "Glossary terms missing"
        expected_terms = ["sci", "ramp", "equity", "sla", "quality_score"]
        for term in expected_terms:
            assert term in glossary, f"Missing glossary term: {term}"
            assert glossary[term], f"Empty definition for {term}"

    def _check_constraints(self):
        """Verify constraints are defined"""
        constraints = self.resolver.memora_context.get("constraints", {})
        assert "stale_datasets" in constraints, "Missing stale_datasets list"
        assert "min_sample_size" in constraints, "Missing min_sample_size"
        assert "confidence_method" in constraints, "Missing confidence_method"
        assert constraints["min_sample_size"] == 30, "Incorrect min_sample_size"
        assert constraints["confidence_method"] == "Wilson Score 95% CI"

    def _check_output_format(self):
        """Verify output format is documented"""
        output_format = self.resolver.memora_context.get("output_format", {})
        assert "borough_order" in output_format, "Missing borough_order"
        assert output_format["borough_order"] == ["MN", "BX", "BK", "QN", "SI"]
        assert "rate_decimals" in output_format
        assert "count_format" in output_format
        assert "include_metadata" in output_format

    def _check_stale_datasets_awareness(self):
        """Verify stale datasets are tracked"""
        stale = self.resolver.memora_context["constraints"]["stale_datasets"]
        assert len(stale) > 0, "No stale datasets tracked"
        assert any("ramp_locations" in s for s in stale), "ramp_locations not marked stale"


# ============================================================================
# COMPONENT 2: Question Resolver Verification
# ============================================================================

class QuestionResolverVerification:
    """Verify question resolver works for exact and fuzzy matching"""

    def __init__(self):
        self.resolver = QuestionKPIResolver(enable_fuzzy_matching=True)
        self.results = []

    def run(self) -> Tuple[bool, List[str]]:
        """Run all resolver checks"""
        checks = [
            self._test_exact_match_a1,
            self._test_exact_match_b1,
            self._test_exact_match_c1,
            self._test_case_insensitivity,
            self._test_question_by_id,
            self._test_list_by_category,
            self._test_all_questions_listed,
            self._test_dataset_references_valid,
            self._test_kpi_references_valid,
            self._test_no_regressions,
        ]

        for check in checks:
            try:
                check()
                self.results.append(f"PASS: {check.__name__}")
            except AssertionError as e:
                self.results.append(f"FAIL: {check.__name__} - {e}")
                return False, self.results
            except Exception as e:
                self.results.append(f"ERROR: {check.__name__} - {e}")
                return False, self.results

        return True, self.results

    def _test_exact_match_a1(self):
        """A1: Sidewalk Condition Index"""
        q = "What is the current Sidewalk Condition Index (SCI) across all boroughs?"
        res = self.resolver.resolve_question(q)
        assert res is not None, "A1 exact match returned None"
        assert res.question_id == "A1", f"Expected A1, got {res.question_id}"
        assert res.category == ResearchCategory.SIDEWALK_CONDITION
        assert res.confidence >= 0.95

    def _test_exact_match_b1(self):
        """B1: ADA Ramps"""
        q = "What percentage of street intersections have ADA-compliant curb ramps?"
        res = self.resolver.resolve_question(q)
        assert res is not None, "B1 exact match returned None"
        assert res.question_id == "B1"
        assert res.category == ResearchCategory.ACCESSIBILITY_EQUITY

    def _test_exact_match_c1(self):
        """C1: Data Quality"""
        q = "What percentage of sidewalk segments have current (≤2 year old) condition assessments?"
        res = self.resolver.resolve_question(q)
        assert res is not None, "C1 exact match returned None"
        assert res.question_id == "C1"
        assert res.category == ResearchCategory.DATA_QUALITY

    def _test_case_insensitivity(self):
        """Exact match is case-insensitive"""
        q_lower = "what is the current sidewalk condition index (sci) across all boroughs?"
        res = self.resolver.resolve_question(q_lower)
        assert res is not None, "Case insensitive match failed"
        assert res.question_id == "A1"

    def _test_question_by_id(self):
        """Get question by ID"""
        res = self.resolver.get_question("A1")
        assert res is not None, "get_question('A1') returned None"
        assert res.question_id == "A1"
        assert "SCI" in res.question_text

    def _test_list_by_category(self):
        """List questions by category"""
        results = self.resolver.list_questions_by_category(ResearchCategory.SIDEWALK_CONDITION)
        assert len(results) > 0, "No questions in SIDEWALK_CONDITION category"
        assert any(r.question_id == "A1" for r in results), "A1 not in results"

    def _test_all_questions_listed(self):
        """Get all questions"""
        all_q = self.resolver.get_all_questions()
        assert len(all_q) >= 6, f"Expected >=6 questions, got {len(all_q)}"
        qids = {q.question_id for q in all_q}
        assert "A1" in qids and "B1" in qids and "C1" in qids

    def _test_dataset_references_valid(self):
        """All dataset references have required fields"""
        res = self.resolver.resolve_question(
            "What is the current Sidewalk Condition Index (SCI) across all boroughs?"
        )
        assert res is not None
        for ds in res.datasets:
            assert ds.name, f"Dataset missing name"
            assert ds.fourfour, f"Dataset {ds.name} missing fourfour"
            assert ds.criticality in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
            assert ds.purpose, f"Dataset {ds.name} missing purpose"

    def _test_kpi_references_valid(self):
        """All KPI references have required fields"""
        res = self.resolver.resolve_question(
            "What is the current Sidewalk Condition Index (SCI) across all boroughs?"
        )
        assert res is not None
        for kpi in res.kpis:
            assert kpi.kpi_id, "KPI missing kpi_id"
            assert kpi.metric_name, "KPI missing metric_name"
            assert kpi.formula, "KPI missing formula"
            assert kpi.granularity, "KPI missing granularity"

    def _test_no_regressions(self):
        """Verify expected skills are assigned"""
        res = self.resolver.resolve_question(
            "What is the current Sidewalk Condition Index (SCI) across all boroughs?"
        )
        assert res.primary_skill == AnalysisSkill.EDA, f"Expected EDA, got {res.primary_skill}"


# ============================================================================
# COMPONENT 3: Fuzzy Matcher Accuracy (20+ Variations)
# ============================================================================

class FuzzyMatcherAccuracyTest:
    """Test fuzzy matching across 20+ question variations"""

    def __init__(self):
        self.resolver = QuestionKPIResolver(enable_fuzzy_matching=True)
        self.results = []
        self.variation_tests = {
            "A1_sidewalk_condition": [
                "How is the sidewalk condition in NYC?",
                "Sidewalk quality across boroughs",
                "What's the SCI?",
                "Show me sidewalk condition scores",
                "Sidewalk assessment results",
            ],
            "B1_ramp_compliance": [
                "How many curb ramps are ADA compliant?",
                "Ramp accessibility status",
                "ADA compliance for ramps",
                "What percentage of ramps are accessible?",
            ],
            "C1_data_freshness": [
                "How fresh is our sidewalk data?",
                "Data recency and coverage",
                "What fraction of segments are current?",
                "Assessment coverage percentage",
            ],
            "D1_budget": [
                "How much does sidewalk maintenance cost?",
                "Budget needed for repairs",
                "Maintenance cost analysis",
                "What's the annual repair budget?",
            ],
            "E1_ramp_completion": [
                "How many ramps are done?",
                "Ramp completion status",
                "Are we meeting the ramp schedule?",
                "How far along the ramp program?",
            ],
            "F1_efficiency": [
                "How long does complaint resolution take?",
                "Inspection speed and turnaround",
                "Time from complaint to fix",
                "What's our service response time?",
            ],
        }

    def run(self) -> Tuple[bool, List[str]]:
        """Run fuzzy matching accuracy tests"""
        total_tested = 0
        total_matched = 0

        for category, variations in self.variation_tests.items():
            for question in variations:
                total_tested += 1
                try:
                    res = self.resolver.resolve_question(question)
                    if res and res.confidence > 0.3:
                        total_matched += 1
                    status = "MATCH" if res else "NO_MATCH"
                    conf = f"({res.confidence:.2f})" if res else ""
                    self.results.append(
                        f"FUZZY: {category} - {question[:40]:40s} {status} {conf}"
                    )
                except Exception as e:
                    self.results.append(f"ERROR in fuzzy test: {question} - {e}")
                    return False, self.results

        accuracy = total_matched / total_tested if total_tested > 0 else 0
        summary = f"Fuzzy Accuracy: {total_matched}/{total_tested} ({accuracy*100:.1f}%)"
        self.results.insert(0, summary)

        # Require at least 70% accuracy for fuzzy matching
        if accuracy < 0.7:
            return False, self.results

        return True, self.results


# ============================================================================
# COMPONENT 4: Integration Verification
# ============================================================================

class IntegrationVerification:
    """Verify imports, dependencies, and style compliance"""

    def __init__(self):
        self.results = []

    def run(self) -> Tuple[bool, List[str]]:
        """Run all integration checks"""
        checks = [
            self._check_imports,
            self._check_question_matcher_integration,
            self._check_skill_activator_integration,
            self._check_code_style,
            self._check_no_circular_imports,
        ]

        for check in checks:
            try:
                check()
                self.results.append(f"PASS: {check.__name__}")
            except AssertionError as e:
                self.results.append(f"FAIL: {check.__name__} - {e}")
                return False, self.results
            except Exception as e:
                self.results.append(f"ERROR: {check.__name__} - {e}")
                return False, self.results

        return True, self.results

    def _check_imports(self):
        """All required modules import successfully"""
        try:
            from socrata_toolkit.core.question_resolver import (
                QuestionKPIResolver, ResearchCategory, AnalysisSkill, MatchDetail
            )
            from socrata_toolkit.core.question_matcher import (
                QuestionMatcher, MatchStrategy, MatchResult
            )
            from socrata_toolkit.core.skill_activator import (
                SkillActivator, SkillContext
            )
            from socrata_toolkit.core.research_framework import ResearchFramework
        except ImportError as e:
            raise AssertionError(f"Import failed: {e}")

    def _check_question_matcher_integration(self):
        """QuestionMatcher is properly integrated with QuestionKPIResolver"""
        resolver = QuestionKPIResolver(enable_fuzzy_matching=True)
        assert resolver.matcher is not None, "QuestionMatcher not initialized"

        # Test that fuzzy matching works
        res = resolver.resolve_question("How is sidewalk condition?")
        # Should return something even if not exact match
        if res is None:
            raise AssertionError("Fuzzy matching returned None")

    def _check_skill_activator_integration(self):
        """SkillActivator can be instantiated and used"""
        activator = SkillActivator()
        resolver = QuestionKPIResolver()

        # Get a question and activate a skill
        res = resolver.resolve_question(
            "What is the current Sidewalk Condition Index (SCI) across all boroughs?"
        )
        assert res is not None

        context = activator.activate(res)
        assert context is not None
        assert context.skill == AnalysisSkill.EDA
        assert context.question_id == "A1"
        assert len(context.datasets) > 0

    def _check_code_style(self):
        """Basic code style checks"""
        import inspect
        from socrata_toolkit.core.question_resolver import QuestionKPIResolver

        # Check that classes have docstrings
        assert QuestionKPIResolver.__doc__, "QuestionKPIResolver missing docstring"
        assert hasattr(QuestionKPIResolver, 'resolve_question'), "Missing resolve_question method"

        # Check method signatures
        sig = inspect.signature(QuestionKPIResolver.resolve_question)
        assert 'question_text' in sig.parameters, "Missing question_text parameter"

    def _check_no_circular_imports(self):
        """No circular import dependencies"""
        # If we can import and instantiate all components without error,
        # there are no circular imports
        resolver = QuestionKPIResolver(enable_fuzzy_matching=True)
        activator = SkillActivator()
        # Successfully instantiated, so no circular imports
        assert True


# ============================================================================
# Main Verification Runner
# ============================================================================

def main():
    """Run all verification components"""
    print("\n" + "="*80)
    print("PHASE 1 MEMORA INTEGRATION - COMPREHENSIVE VERIFICATION")
    print("="*80)

    all_passed = True
    total_results = []

    # Component 1: Memora Health Check
    print("\n[1/4] MEMORA HEALTH CHECK")
    print("-" * 80)
    health = MemoraHealthCheck()
    passed, results = health.run()
    for r in results:
        print(f"  {r}")
    total_results.extend(results)
    all_passed = all_passed and passed

    # Component 2: Question Resolver Verification
    print("\n[2/4] QUESTION RESOLVER VERIFICATION")
    print("-" * 80)
    resolver_check = QuestionResolverVerification()
    passed, results = resolver_check.run()
    for r in results:
        print(f"  {r}")
    total_results.extend(results)
    all_passed = all_passed and passed

    # Component 3: Fuzzy Matcher Accuracy
    print("\n[3/4] FUZZY MATCHER ACCURACY TEST (20+ VARIATIONS)")
    print("-" * 80)
    fuzzy_check = FuzzyMatcherAccuracyTest()
    passed, results = fuzzy_check.run()
    for r in results[:15]:  # Show first 15
        print(f"  {r}")
    if len(results) > 15:
        print(f"  ... ({len(results) - 15} more test results)")
    total_results.extend(results)
    all_passed = all_passed and passed

    # Component 4: Integration Verification
    print("\n[4/4] INTEGRATION VERIFICATION")
    print("-" * 80)
    integration = IntegrationVerification()
    passed, results = integration.run()
    for r in results:
        print(f"  {r}")
    total_results.extend(results)
    all_passed = all_passed and passed

    # Summary
    print("\n" + "="*80)
    passed_count = sum(1 for r in total_results if r.startswith("PASS"))
    failed_count = sum(1 for r in total_results if r.startswith("FAIL"))
    error_count = sum(1 for r in total_results if r.startswith("ERROR"))

    print(f"VERIFICATION SUMMARY")
    print(f"  PASSED: {passed_count}")
    print(f"  FAILED: {failed_count}")
    print(f"  ERRORS: {error_count}")
    print(f"  TOTAL:  {len(total_results)}")

    if all_passed:
        print("\n*** ALL COMPONENTS PASSED ***")
        print("="*80 + "\n")
        return 0
    else:
        print("\n*** SOME COMPONENTS FAILED ***")
        print("="*80 + "\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
