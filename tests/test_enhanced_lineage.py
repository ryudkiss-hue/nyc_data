"""Tests for enhanced lineage tracking: datasets → marts → dashboards → reports → exports."""
import json
from datetime import datetime

import pytest

from socrata_toolkit.core.enhanced_lineage import (
    DashboardNode,
    DatasetNode,
    ExportNode,
    LineageDAG,
    LineageEvent,
    LineageTracker,
    MartNode,
    ReportNode,
)


class TestLineageEvent:
    """Test individual lineage events."""

    def test_create_fetch_event(self):
        """Test creating a dataset fetch event."""
        event = LineageEvent(
            event_type="fetch",
            source="inspection",
            target="raw.inspection",
            timestamp=datetime.now().isoformat(),
            row_count=398234,
            status="success",
        )

        assert event.event_type == "fetch"
        assert event.source == "inspection"
        assert event.target == "raw.inspection"
        assert event.status == "success"

    def test_create_stage_event(self):
        """Test creating a staging event."""
        event = LineageEvent(
            event_type="stage",
            source="raw.inspection",
            target="staging.inspection",
            timestamp=datetime.now().isoformat(),
            row_count=398234,
            status="success",
            metadata={"dedup_key": "objectid", "date_column": "created_date"},
        )

        assert event.event_type == "stage"
        assert event.metadata["dedup_key"] == "objectid"

    def test_create_materialize_event(self):
        """Test creating a mart materialization event."""
        event = LineageEvent(
            event_type="materialize",
            source="staging.inspection,staging.violations",
            target="analytics.sidewalk_repair_matrix",
            timestamp=datetime.now().isoformat(),
            row_count=450,
            status="success",
            metadata={"builder": "cross_tab", "duration_ms": 2340},
        )

        assert event.event_type == "materialize"
        assert event.metadata["builder"] == "cross_tab"

    def test_create_dashboard_event(self):
        """Test creating a dashboard generation event."""
        event = LineageEvent(
            event_type="dashboard",
            source="analytics.sidewalk_repair_matrix",
            target="dashboards/sidewalk_repair_matrix",
            timestamp=datetime.now().isoformat(),
            status="success",
            metadata={"charts": 4, "filters": 2},
        )

        assert event.event_type == "dashboard"
        assert event.metadata["charts"] == 4

    def test_create_export_event(self):
        """Test creating an export event."""
        event = LineageEvent(
            event_type="export",
            source="dashboards/sidewalk_repair_matrix",
            target="reports/sidewalk_repair_matrix.pdf",
            timestamp=datetime.now().isoformat(),
            status="success",
            metadata={"format": "pdf", "size_kb": 245},
        )

        assert event.event_type == "export"
        assert event.metadata["format"] == "pdf"

class TestLineageTracker:
    """Test lineage tracking and recording."""

    def test_record_event(self):
        """Test recording a single event."""
        tracker = LineageTracker()

        tracker.record_event(
            event_type="fetch",
            source="inspection",
            target="raw.inspection",
            row_count=398234,
        )

        events = tracker.get_events()
        assert len(events) == 1
        assert events[0].event_type == "fetch"

    def test_record_workflow_sequence(self):
        """Test recording a complete workflow sequence."""
        tracker = LineageTracker()

        # Fetch → Stage → Materialize → Dashboard → Export
        tracker.record_event("fetch", "inspection", "raw.inspection", row_count=398234)
        tracker.record_event("stage", "raw.inspection", "staging.inspection", row_count=398234)
        tracker.record_event(
            "materialize",
            "staging.inspection",
            "analytics.sidewalk_repair_matrix",
            row_count=450,
            metadata={"builder": "cross_tab"},
        )
        tracker.record_event(
            "dashboard", "analytics.sidewalk_repair_matrix", "dashboards/sidewalk_repair_matrix"
        )
        tracker.record_event(
            "export",
            "dashboards/sidewalk_repair_matrix",
            "reports/sidewalk_repair_matrix.pdf",
            metadata={"format": "pdf"},
        )

        events = tracker.get_events()
        assert len(events) == 5
        assert [e.event_type for e in events] == ["fetch", "stage", "materialize", "dashboard", "export"]

    def test_get_upstream_chain(self):
        """Test getting full upstream lineage chain."""
        tracker = LineageTracker()

        tracker.record_event("fetch", "inspection", "raw.inspection")
        tracker.record_event("stage", "raw.inspection", "staging.inspection")
        tracker.record_event("materialize", "staging.inspection", "analytics.sidewalk_repair_matrix")

        upstream = tracker.get_upstream_chain("analytics.sidewalk_repair_matrix")

        assert len(upstream) == 3
        assert upstream[0].source == "inspection"
        assert upstream[-1].target == "analytics.sidewalk_repair_matrix"

    def test_get_downstream_chain(self):
        """Test getting full downstream lineage chain."""
        tracker = LineageTracker()

        tracker.record_event("fetch", "inspection", "raw.inspection")
        tracker.record_event("stage", "raw.inspection", "staging.inspection")
        tracker.record_event("materialize", "staging.inspection", "analytics.sidewalk_repair_matrix")
        tracker.record_event("dashboard", "analytics.sidewalk_repair_matrix", "dashboards/sidewalk_repair_matrix")
        tracker.record_event("export", "dashboards/sidewalk_repair_matrix", "reports/sidewalk_repair_matrix.pdf")

        downstream = tracker.get_downstream_chain("raw.inspection")

        assert len(downstream) == 4
        assert downstream[0].target == "staging.inspection"
        assert downstream[-1].target == "reports/sidewalk_repair_matrix.pdf"

class TestLineageDAG:
    """Test DAG construction and visualization."""

    def test_build_dag_from_events(self):
        """Test building a DAG from events."""
        tracker = LineageTracker()

        tracker.record_event("fetch", "inspection", "raw.inspection")
        tracker.record_event("stage", "raw.inspection", "staging.inspection")
        tracker.record_event("materialize", "staging.inspection", "analytics.sidewalk_repair_matrix")

        dag = LineageDAG.from_tracker(tracker)

        # Nodes: inspection, raw.inspection, staging.inspection, analytics.sidewalk_repair_matrix
        assert len(dag.nodes) == 4
        assert len(dag.edges) == 3

    def test_dag_mermaid_export(self):
        """Test exporting DAG as Mermaid diagram."""
        tracker = LineageTracker()

        tracker.record_event("fetch", "inspection", "raw.inspection")
        tracker.record_event("stage", "raw.inspection", "staging.inspection")
        tracker.record_event("materialize", "staging.inspection", "analytics.sidewalk_repair_matrix")
        tracker.record_event("dashboard", "analytics.sidewalk_repair_matrix", "dashboards/sidewalk_repair_matrix")

        dag = LineageDAG.from_tracker(tracker)
        mermaid = dag.to_mermaid()

        assert "graph" in mermaid
        assert "inspection" in mermaid
        assert "sidewalk_repair_matrix" in mermaid

    def test_dag_json_export(self):
        """Test exporting DAG as JSON."""
        tracker = LineageTracker()

        tracker.record_event("fetch", "inspection", "raw.inspection")
        tracker.record_event("materialize", "raw.inspection", "analytics.sidewalk_repair_matrix")

        dag = LineageDAG.from_tracker(tracker)
        json_data = dag.to_json()

        parsed = json.loads(json_data)
        assert "nodes" in parsed
        assert "edges" in parsed
        # Nodes: inspection, raw.inspection, analytics.sidewalk_repair_matrix
        assert len(parsed["nodes"]) == 3

class TestLineageIntegration:
    """Integration tests for complete workflows."""

    def test_multi_mart_lineage(self):
        """Test lineage across multiple mats."""
        tracker = LineageTracker()

        # Two datasets feeding two different mats
        tracker.record_event("fetch", "inspection", "raw.inspection")
        tracker.record_event("fetch", "violations", "raw.violations")
        tracker.record_event("stage", "raw.inspection", "staging.inspection")
        tracker.record_event("stage", "raw.violations", "staging.violations")

        # Both feed sidewalk_repair_matrix
        tracker.record_event(
            "materialize",
            "staging.inspection,staging.violations",
            "analytics.sidewalk_repair_matrix",
        )

        # Single dashboard from mart
        tracker.record_event(
            "dashboard", "analytics.sidewalk_repair_matrix", "dashboards/sidewalk_repair_matrix"
        )

        dag = LineageDAG.from_tracker(tracker)

        # Nodes: inspection, violations, raw.inspection, raw.violations,
        # staging.inspection, staging.violations, analytics.sidewalk_repair_matrix, dashboards/sidewalk_repair_matrix
        assert len(dag.nodes) == 8

    def test_branching_exports(self):
        """Test lineage with multiple export formats from single report."""
        tracker = LineageTracker()

        tracker.record_event("materialize", "staging.inspection", "analytics.raw_counts_summary")
        tracker.record_event("dashboard", "analytics.raw_counts_summary", "dashboards/raw_counts_summary")

        # Export to multiple formats
        tracker.record_event(
            "export",
            "dashboards/raw_counts_summary",
            "reports/raw_counts_summary.pdf",
            metadata={"format": "pdf"},
        )
        tracker.record_event(
            "export",
            "dashboards/raw_counts_summary",
            "reports/raw_counts_summary.xlsx",
            metadata={"format": "xlsx"},
        )
        tracker.record_event(
            "export",
            "dashboards/raw_counts_summary",
            "reports/raw_counts_summary.pptx",
            metadata={"format": "pptx"},
        )

        events = tracker.get_events()
        exports = [e for e in events if e.event_type == "export"]
        assert len(exports) == 3

    def test_error_event_tracking(self):
        """Test tracking failed events in lineage."""
        tracker = LineageTracker()

        tracker.record_event("fetch", "inspection", "raw.inspection", status="success")
        tracker.record_event(
            "stage", "raw.inspection", "staging.inspection", status="failure", metadata={"error": "Schema drift"}
        )

        events = tracker.get_events()
        assert events[0].status == "success"
        assert events[1].status == "failure"
        assert "Schema drift" in events[1].metadata["error"]
