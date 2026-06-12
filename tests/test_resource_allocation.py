"""Tests for Resource Allocation Optimization Workflow.

Tests cover:
- Classifier area priority and action recommendation
- Workflow orchestration (fetch -> classify -> optimize -> plan)
- Integration with Socrata and Claude APIs
"""

import pandas as pd
import pytest

from socrata_toolkit.analysis.allocation_classifier import (
    AllocationAction,
    AreaPriority,
    ImpactLevel,
    ResourceAllocationClassifier,
)
from socrata_toolkit.analysis.resource_allocation_workflow import (
    ReallocationPlan,
    ResourceAllocationWorkflow,
)

class TestResourceAllocationClassifier:
    """Test suite for ResourceAllocationClassifier."""

    def test_classify_critical_area(self):
        """Test classification of CRITICAL priority area."""
        clf = ResourceAllocationClassifier()
        result = clf.classify_area(
            area_id="critical_001",
            area_name="Critical Zone",
            violation_count=100,
            response_time_days=15.0,  # Exceeds 14-day threshold
            inspector_count=1,
            violations_with_response=60,
        )

        assert result.priority == AreaPriority.CRITICAL
        assert result.action == AllocationAction.DISPATCH
        assert result.impact == ImpactLevel.HIGH
        assert result.violations_per_inspector == 100.0
        assert result.coverage_gap_pct > 0.0
        assert result.confidence_score > 0.0

    def test_classify_high_area(self):
        """Test classification of HIGH priority area."""
        clf = ResourceAllocationClassifier()
        result = clf.classify_area(
            area_id="high_001",
            area_name="High Priority Zone",
            violation_count=70,
            response_time_days=10.5,
            inspector_count=2,
            violations_with_response=50,
        )

        assert result.priority == AreaPriority.HIGH
        assert result.action == AllocationAction.CONSOLIDATE
        assert result.violations_per_inspector == 35.0

    def test_classify_medium_area(self):
        """Test classification of MEDIUM priority area."""
        clf = ResourceAllocationClassifier()
        result = clf.classify_area(
            area_id="med_001",
            area_name="Medium Priority Zone",
            violation_count=70,
            response_time_days=7.5,
            inspector_count=3,
            violations_with_response=65,
        )

        assert result.priority == AreaPriority.MEDIUM
        assert result.action == AllocationAction.OPTIMIZE

    def test_classify_low_area(self):
        """Test classification of LOW priority area."""
        clf = ResourceAllocationClassifier()
        result = clf.classify_area(
            area_id="low_001",
            area_name="Low Priority Zone",
            violation_count=30,
            response_time_days=5.0,
            inspector_count=3,
            violations_with_response=28,
        )

        assert result.priority == AreaPriority.LOW
        assert result.action == AllocationAction.MONITOR
        assert result.impact == ImpactLevel.LOW

    def test_classify_dataframe(self):
        """Test batch classification using DataFrame."""
        clf = ResourceAllocationClassifier()

        df = pd.DataFrame({
            "area_id": ["a1", "a2", "a3"],
            "area_name": ["Area 1", "Area 2", "Area 3"],
            "violation_count": [100, 70, 20],
            "response_time_days": [15.0, 10.5, 5.0],
            "inspector_count": [1, 2, 3],
            "violations_with_response": [60, 50, 18],
        })

        results = clf.classify_dataframe(
            df=df,
            area_col="area_id",
            area_name_col="area_name",
            violations_col="violation_count",
            response_time_col="response_time_days",
            inspector_col="inspector_count",
            response_violations_col="violations_with_response",
        )

        assert len(results) == 3
        assert results[0].priority == AreaPriority.CRITICAL
        assert results[1].priority == AreaPriority.HIGH
        assert results[2].priority == AreaPriority.LOW

    def test_summarize_allocations(self):
        """Test summary generation from classifications."""
        clf = ResourceAllocationClassifier()

        results = [
            clf.classify_area("a1", "Area 1", 100, 15.0, 1, 60),
            clf.classify_area("a2", "Area 2", 70, 10.5, 2, 50),
            clf.classify_area("a3", "Area 3", 20, 5.0, 3, 18),
        ]

        summary = clf.summarize_allocations(results)

        assert summary["total_areas"] == 3
        assert summary["total_violations"] == 190
        assert summary["total_inspectors"] == 6
        assert "priority_counts" in summary
        assert "action_counts" in summary
        assert summary["critical_areas"] == 1
        assert summary["high_areas"] == 1
        assert summary["low_areas"] == 1

    def test_confidence_score(self):
        """Test confidence score computation."""
        clf = ResourceAllocationClassifier()

        # High confidence: large sample, complete data
        high_conf = clf.classify_area("h1", "H1", 100, 10.0, 2, 80)
        assert high_conf.confidence_score > 0.7

        # Low confidence: small sample
        low_conf = clf.classify_area("l1", "L1", 1, 10.0, 2, 0)
        assert low_conf.confidence_score < 0.6

    def test_configurable_thresholds(self):
        """Test classifier with custom thresholds."""
        clf = ResourceAllocationClassifier(
            critical_violations_per_inspector=30.0,
            critical_response_days=10.0,
        )

        result = clf.classify_area(
            area_id="custom",
            area_name="Custom Threshold Area",
            violation_count=60,
            response_time_days=11.0,
            inspector_count=2,
            violations_with_response=40,
        )

        assert result.priority == AreaPriority.CRITICAL

    def test_zero_inspector_handling(self):
        """Test handling of zero inspectors (avoid division by zero)."""
        clf = ResourceAllocationClassifier()

        result = clf.classify_area(
            area_id="zero_insp",
            area_name="Zero Inspector Area",
            violation_count=50,
            response_time_days=10.0,
            inspector_count=0,  # Edge case
            violations_with_response=0,
        )

        assert result.violations_per_inspector == 50.0  # 50 / 1

class TestResourceAllocationWorkflow:
    """Test suite for ResourceAllocationWorkflow (integration tests)."""

    def test_workflow_initialization(self):
        """Test workflow can be instantiated."""
        workflow = ResourceAllocationWorkflow()
        assert workflow.socrata_client is not None
        assert workflow.classifier is not None

    def test_compute_metrics_by_block_empty(self):
        """Test metrics computation with empty dataframe."""
        workflow = ResourceAllocationWorkflow()

        empty_violations = pd.DataFrame(columns=["block", "created_date"])
        empty_inspections = pd.DataFrame()

        metrics = workflow._compute_metrics_by_block(empty_violations, empty_inspections)
        assert metrics.empty

    def test_compute_metrics_with_block_data(self):
        """Test metrics computation with sample block data."""
        workflow = ResourceAllocationWorkflow()

        violations_df = pd.DataFrame({
            "block": [1, 1, 2, 2, 3],
            "created_date": ["2024-01-01"] * 5,
        })
        inspections_df = pd.DataFrame()

        metrics = workflow._compute_metrics_by_block(violations_df, inspections_df)

        assert not metrics.empty
        assert len(metrics) == 3  # 3 unique blocks
        assert "violation_count" in metrics.columns
        assert "inspector_count" in metrics.columns

    def test_classify_areas(self):
        """Test area classification from metrics."""
        workflow = ResourceAllocationWorkflow()

        metrics_df = pd.DataFrame({
            "area_id": ["a1", "a2"],
            "area_name": ["Area 1", "Area 2"],
            "violation_count": [100, 30],
            "response_time_days": [15.0, 5.0],
            "inspector_count": [1, 2],
            "violations_with_response": [60, 28],
        })

        classifications = workflow.classify_areas(metrics_df)

        assert len(classifications) == 2
        assert classifications[0].priority == AreaPriority.CRITICAL
        assert classifications[1].priority == AreaPriority.LOW

    def test_optimize_routing(self):
        """Test routing optimization for consolidation."""
        workflow = ResourceAllocationWorkflow()
        clf = ResourceAllocationClassifier()

        # Create classification with consolidation action
        areas = [
            clf.classify_area("a1", "Area 1", 50, 10.0, 2, 40),
            clf.classify_area("a2", "Area 2", 30, 5.0, 1, 28),
        ]

        groups = workflow.optimize_routing(areas)

        assert isinstance(groups, list)
        if groups:
            assert "group_id" in groups[0]
            assert "areas" in groups[0]

    def test_reallocation_plan_structure(self):
        """Test ReallocationPlan dataclass structure."""
        plan = ReallocationPlan(
            summary="Test plan",
            critical_areas=[{"area_id": "c1"}],
            high_priority_areas=[],
            consolidation_groups=[],
            estimated_efficiency_gain=25.0,
            estimated_response_time_improvement=15.0,
            cost_benefit_analysis="Test analysis",
            implementation_steps=["Step 1"],
            risk_assessment="Test risks",
            allocation_json={"test": "data"},
        )

        assert plan.summary == "Test plan"
        assert len(plan.critical_areas) == 1
        assert plan.estimated_efficiency_gain == 25.0
        assert plan.estimated_response_time_improvement == 15.0

class TestIntegration:
    """Integration tests (may require API keys)."""

    def test_workflow_with_mock_data(self):
        """Test full workflow with mock data."""
        workflow = ResourceAllocationWorkflow()

        violations_df = pd.DataFrame({
            "block": [1] * 50 + [2] * 30,
            "created_date": ["2024-01-01"] * 80,
            "latitude": [40.7] * 80,
            "longitude": [-74.0] * 80,
        })
        inspections_df = pd.DataFrame()

        plan = workflow.generate_reallocation_plan(
            violations_df=violations_df,
            inspections_df=inspections_df,
        )

        assert isinstance(plan, ReallocationPlan)
        assert plan.summary is not None
        assert len(plan.implementation_steps) > 0
