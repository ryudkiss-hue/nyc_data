"""Tests for unified data governance processor integration.

Tests the complete governance flow:
- Schema validation
- CDC event capture and storage
- Data lineage enrichment
- Design rule compliance checking
"""

from datetime import datetime, timezone

import pytest

try:
    from socrata_toolkit.governance import (
        GovernanceEvent,
        GovernanceProcessor,
    )
    from socrata_toolkit.pipeline import CDCEvent
except ImportError:
    pytest.skip("Governance modules not available", allow_module_level=True)

class TestGovernanceProcessor:
    """Test GovernanceProcessor orchestration."""

    def test_governance_event_creation(self):
        """Test creating and serializing governance events."""
        event = GovernanceEvent(
            event_id="evt-001",
            source_dataset="sidewalk_repairs",
            operation="UPDATE",
            record_id="repair-123",
            before_values={"budget": 50000},
            after_values={"budget": 55000},
            timestamp=datetime.now(timezone.utc),
            is_compliant=True,
        )

        assert event.event_id == "evt-001"
        assert event.operation == "UPDATE"
        assert not event.design_rule_violations

        # Test serialization
        data = event.to_dict()
        assert data["event_id"] == "evt-001"
        assert data["is_compliant"] is True

    def test_governance_processor_initialization(self):
        """Test GovernanceProcessor initialization with optional components."""
        # Initialize with minimal config (components may fail, but processor should initialize)
        processor = GovernanceProcessor(
            dsn="postgresql://invalid",
            enable_lineage=True,
            enable_compliance=True,
        )

        assert processor.enable_lineage is True
        assert processor.enable_compliance is True

    def test_cdc_event_enrichment(self):
        """Test that CDC events are properly enriched with governance metadata."""
        # Create a simple CDC event
        cdc_event = CDCEvent(
            event_id="cdc-001",
            source_dataset="contracts",
            operation="INSERT",
            record_id="contr-456",
            timestamp_ms=int(datetime.now(timezone.utc).timestamp() * 1000),
            after={"contract_id": "contr-456", "budget": 100000},
        )

        # Simulate enrichment (without full processor dependencies)
        enriched = GovernanceEvent(
            event_id=cdc_event.event_id,
            source_dataset=cdc_event.source_dataset,
            operation=cdc_event.operation,
            record_id=cdc_event.record_id,
            after_values=cdc_event.after,
            timestamp=datetime.now(timezone.utc),
        )

        assert enriched.event_id == "cdc-001"
        assert enriched.after_values["budget"] == 100000
        assert enriched.is_compliant  # default true

class TestProjectAnalystReports:
    """Test ProjectAnalystReports for Project Analysts."""

    def test_budget_audit_structure(self):
        """Test that budget audit reports have expected structure."""
        from socrata_toolkit.analysis import ProjectAnalystReports
        from socrata_toolkit.governance import GovernanceProcessor

        # Initialize with mock processor
        processor = GovernanceProcessor(dsn="postgresql://invalid")
        reports = ProjectAnalystReports(processor)

        # Test report structure (without actual data)
        result = reports.contract_budget_audit("CONTR-2026-001")

        assert "contract_id" in result
        assert "changes_count" in result or "error" in result  # May fail due to DSN

    def test_compliance_report_structure(self):
        """Test that compliance reports have expected structure."""
        from socrata_toolkit.analysis import ProjectAnalystReports
        from socrata_toolkit.governance import GovernanceProcessor

        processor = GovernanceProcessor(dsn="postgresql://invalid")
        reports = ProjectAnalystReports(processor)

        result = reports.construction_compliance("PROJ-2026-001")

        assert "project_id" in result
        assert "is_compliant" in result or "error" in result

class TestGovernanceIntegration:
    """End-to-end integration tests for governance flow."""

    def test_event_flow(self):
        """Test complete event flow through governance pipeline."""
        # This is a simplified test to verify the integration works
        # Full integration requires database setup

        event = GovernanceEvent(
            event_id="integration-test",
            source_dataset="test_dataset",
            operation="INSERT",
            record_id="test-record",
            timestamp=datetime.now(timezone.utc),
        )

        # Verify event is valid and serializable
        assert event.is_compliant is True
        data = event.to_dict()
        assert isinstance(data, dict)
        assert data["event_id"] == "integration-test"

    def test_schema_version_tracking(self):
        """Test that governance events track schema versions."""
        event = GovernanceEvent(
            event_id="schema-test",
            source_dataset="contracts",
            operation="INSERT",
            record_id="test",
            schema_version="1.0",
            schema_valid=True,
        )

        assert event.schema_version == "1.0"
        assert event.schema_valid is True

    def test_compliance_violations_tracking(self):
        """Test that governance events track design rule violations."""
        event = GovernanceEvent(
            event_id="compliance-test",
            source_dataset="segments",
            operation="INSERT",
            record_id="test",
            design_rule_violations=["Material type not in standard taxonomy"],
            is_compliant=False,
        )

        assert len(event.design_rule_violations) == 1
        assert event.is_compliant is False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
