"""Comprehensive test suite for data lineage and transformation DAG tracking.

Tests cover:
- Core DAG construction and validation
- Transformation nodes and execution tracking
- Lineage edges and dependency relationships
- Cycle detection
- Impact analysis
- Query interface
- Visualization and export
- Persistence layer
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from socrata_toolkit.governance import (
    DAG,
    EdgeType,
    ExecutionRecord,
    ExecutionStatus,
    ImpactAnalysis,
    LineageEdge,
    LineageQuery,
    LineageVisualizer,
    NodeType,
    TransformationNode,
)


class TestTransformationNode:
    """Tests for TransformationNode."""

    def test_node_creation(self):
        """Test creating a transformation node."""
        node = TransformationNode(
            node_id="test_node",
            name="Test Transformation",
            node_type=NodeType.TRANSFORMATION,
            owner="test@example.com",
        )
        assert node.node_id == "test_node"
        assert node.name == "Test Transformation"
        assert node.node_type == NodeType.TRANSFORMATION
        assert node.owner == "test@example.com"

    def test_node_to_dict(self):
        """Test node serialization to dictionary."""
        node = TransformationNode(
            node_id="test",
            name="Test",
            node_type=NodeType.INGESTION,
            owner="owner@example.com",
        )
        d = node.to_dict()
        assert d["node_id"] == "test"
        assert d["name"] == "Test"
        assert d["node_type"] == "ingestion"
        assert d["owner"] == "owner@example.com"

    def test_node_from_dict(self):
        """Test node deserialization from dictionary."""
        d = {
            "node_id": "test",
            "name": "Test",
            "node_type": "transformation",
            "owner": "owner@example.com",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_modified": datetime.now(timezone.utc).isoformat(),
            "input_datasets": ["input1"],
            "output_datasets": ["output1"],
            "configuration": {"key": "value"},
            "execution_history": [],
            "schema_version": None,
            "tags": ["test"],
        }
        node = TransformationNode.from_dict(d)
        assert node.node_id == "test"
        assert node.name == "Test"
        assert node.node_type == NodeType.TRANSFORMATION

    def test_record_execution(self):
        """Test recording an execution on a node."""
        node = TransformationNode(node_id="test", name="Test")
        record = node.record_execution(
            status=ExecutionStatus.SUCCESS,
            input_rows=100,
            output_rows=95,
            duration_secs=5.0,
        )
        assert record.status == ExecutionStatus.SUCCESS
        assert record.input_row_count == 100
        assert record.output_row_count == 95
        assert len(node.execution_history) == 1

    def test_get_latest_execution(self):
        """Test getting latest execution."""
        node = TransformationNode(node_id="test", name="Test")
        node.record_execution(ExecutionStatus.SUCCESS)
        node.record_execution(ExecutionStatus.FAILED)
        latest = node.get_latest_execution()
        assert latest is not None
        assert latest.status == ExecutionStatus.FAILED

    def test_get_execution_history(self):
        """Test retrieving execution history."""
        node = TransformationNode(node_id="test", name="Test")
        for i in range(5):
            node.record_execution(ExecutionStatus.SUCCESS)
        history = node.get_execution_history(limit=3)
        assert len(history) == 3

class TestExecutionRecord:
    """Tests for ExecutionRecord."""

    def test_execution_record_creation(self):
        """Test creating an execution record."""
        record = ExecutionRecord(
            node_id="test",
            status=ExecutionStatus.SUCCESS,
            input_row_count=100,
            output_row_count=95,
        )
        assert record.node_id == "test"
        assert record.status == ExecutionStatus.SUCCESS
        assert record.input_row_count == 100

    def test_execution_record_to_dict(self):
        """Test execution record serialization."""
        record = ExecutionRecord(
            node_id="test",
            status=ExecutionStatus.SUCCESS,
            data_quality_metrics={"null_percentage": 2.5},
        )
        d = record.to_dict()
        assert d["node_id"] == "test"
        assert d["status"] == "success"
        assert d["data_quality_metrics"] == {"null_percentage": 2.5}

    def test_execution_record_from_dict(self):
        """Test execution record deserialization."""
        d = {
            "execution_id": "exec-123",
            "node_id": "test",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": 5.0,
            "status": "success",
            "input_row_count": 100,
            "output_row_count": 95,
            "error_message": None,
            "data_quality_metrics": {},
            "user": "system",
            "notes": None,
        }
        record = ExecutionRecord.from_dict(d)
        assert record.node_id == "test"
        assert record.status == ExecutionStatus.SUCCESS

class TestLineageEdge:
    """Tests for LineageEdge."""

    def test_edge_creation(self):
        """Test creating a lineage edge."""
        edge = LineageEdge(
            source_node_id="source",
            target_node_id="target",
            edge_type=EdgeType.DATA_FLOW,
            cardinality="1:N",
        )
        assert edge.source_node_id == "source"
        assert edge.target_node_id == "target"
        assert edge.edge_type == EdgeType.DATA_FLOW

    def test_edge_with_join_keys(self):
        """Test edge with join keys."""
        edge = LineageEdge(
            source_node_id="source",
            target_node_id="target",
            join_keys=["id", "date"],
        )
        assert "id" in edge.join_keys
        assert "date" in edge.join_keys

    def test_edge_to_dict_and_from_dict(self):
        """Test edge serialization/deserialization."""
        edge = LineageEdge(
            source_node_id="source",
            target_node_id="target",
            edge_type=EdgeType.DEPENDENCY,
        )
        d = edge.to_dict()
        restored = LineageEdge.from_dict(d)
        assert restored.source_node_id == "source"
        assert restored.target_node_id == "target"

class TestDAG:
    """Tests for DAG (Directed Acyclic Graph)."""

    def test_dag_creation(self):
        """Test creating an empty DAG."""
        dag = DAG()
        assert len(dag.nodes) == 0
        assert len(dag.edges) == 0

    def test_add_node(self):
        """Test adding a node to DAG."""
        dag = DAG()
        node = TransformationNode(
            node_id="node1",
            name="Node 1",
            node_type=NodeType.INGESTION,
        )
        dag.add_node(node)
        assert "node1" in dag.nodes
        assert dag.nodes["node1"].name == "Node 1"

    def test_add_duplicate_node_raises_error(self):
        """Test that adding duplicate node raises ValueError."""
        dag = DAG()
        node = TransformationNode(node_id="node1", name="Node 1")
        dag.add_node(node)
        with pytest.raises(ValueError):
            dag.add_node(node)

    def test_add_edge(self):
        """Test adding an edge between nodes."""
        dag = DAG()
        dag.add_node(TransformationNode(node_id="n1", name="Node 1"))
        dag.add_node(TransformationNode(node_id="n2", name="Node 2"))
        edge = dag.add_edge("n1", "n2")
        assert ("n1", "n2") in dag.edges
        assert edge.source_node_id == "n1"
        assert edge.target_node_id == "n2"

    def test_add_edge_nonexistent_nodes_raises_error(self):
        """Test that adding edge with nonexistent nodes raises error."""
        dag = DAG()
        with pytest.raises(ValueError):
            dag.add_edge("n1", "n2")

    def test_cycle_detection(self):
        """Test that cycles are detected."""
        dag = DAG()
        dag.add_node(TransformationNode(node_id="n1", name="N1"))
        dag.add_node(TransformationNode(node_id="n2", name="N2"))
        dag.add_node(TransformationNode(node_id="n3", name="N3"))

        dag.add_edge("n1", "n2")
        dag.add_edge("n2", "n3")

        # Creating a cycle should raise error
        with pytest.raises(ValueError):
            dag.add_edge("n3", "n1")

    def test_remove_node(self):
        """Test removing a node."""
        dag = DAG()
        dag.add_node(TransformationNode(node_id="n1", name="N1"))
        dag.remove_node("n1")
        assert "n1" not in dag.nodes

    def test_remove_nonexistent_node_raises_error(self):
        """Test removing nonexistent node raises error."""
        dag = DAG()
        with pytest.raises(ValueError):
            dag.remove_node("nonexistent")

    def test_get_upstream_dependencies(self):
        """Test getting upstream dependencies."""
        dag = DAG()
        dag.add_node(TransformationNode(node_id="n1", name="N1"))
        dag.add_node(TransformationNode(node_id="n2", name="N2"))
        dag.add_node(TransformationNode(node_id="n3", name="N3"))

        dag.add_edge("n1", "n2")
        dag.add_edge("n2", "n3")

        upstream = dag.get_upstream_dependencies("n3")
        assert "n1" in upstream
        assert "n2" in upstream

    def test_get_downstream_consumers(self):
        """Test getting downstream consumers."""
        dag = DAG()
        dag.add_node(TransformationNode(node_id="n1", name="N1"))
        dag.add_node(TransformationNode(node_id="n2", name="N2"))
        dag.add_node(TransformationNode(node_id="n3", name="N3"))

        dag.add_edge("n1", "n2")
        dag.add_edge("n2", "n3")

        downstream = dag.get_downstream_consumers("n1")
        assert "n2" in downstream
        assert "n3" in downstream

    def test_validate_dag_valid(self):
        """Test validating a valid DAG."""
        dag = DAG()
        dag.add_node(TransformationNode(node_id="n1", name="N1", node_type=NodeType.INGESTION))
        dag.add_node(TransformationNode(node_id="n2", name="N2", node_type=NodeType.TRANSFORMATION))
        dag.add_edge("n1", "n2")

        validation = dag.validate()
        assert validation["is_valid"]
        assert len(validation["errors"]) == 0

    def test_dag_to_dict_and_from_dict(self):
        """Test DAG serialization and deserialization."""
        dag = DAG()
        dag.add_node(TransformationNode(node_id="n1", name="N1"))
        dag.add_node(TransformationNode(node_id="n2", name="N2"))
        dag.add_edge("n1", "n2")

        d = dag.to_dict()
        assert d["metadata"]["node_count"] == 2
        assert d["metadata"]["edge_count"] == 1

        # Reconstruct
        dag2 = DAG.from_dict(d)
        assert len(dag2.nodes) == 2
        assert len(dag2.edges) == 1

    def test_get_impact_scope(self):
        """Test impact scope analysis."""
        dag = DAG()
        dag.add_node(TransformationNode(node_id="n1", name="N1", owner="user1"))
        dag.add_node(TransformationNode(node_id="n2", name="N2", owner="user2"))
        dag.add_edge("n1", "n2")

        impact = dag.get_impact_scope("n1")
        assert "n2" in impact["all_affected_nodes"]
        assert "user2" in impact["affected_users"]

class TestLineageQuery:
    """Tests for LineageQuery interface."""

    def setup_method(self):
        """Setup test DAG."""
        self.dag = DAG()
        self.dag.add_node(
            TransformationNode(
                node_id="ingest_construction",
                name="Construction List Ingestion",
                node_type=NodeType.INGESTION,
                owner="data-eng@example.com",
                tags=["daily"],
            )
        )
        self.dag.add_node(
            TransformationNode(
                node_id="transform_clean",
                name="Clean Construction Data",
                node_type=NodeType.TRANSFORMATION,
                owner="data-eng@example.com",
            )
        )
        self.dag.add_node(
            TransformationNode(
                node_id="sink_warehouse",
                name="Warehouse Sink",
                node_type=NodeType.SINK,
                owner="analytics@example.com",
            )
        )
        self.dag.add_edge("ingest_construction", "transform_clean")
        self.dag.add_edge("transform_clean", "sink_warehouse")
        self.query = LineageQuery(self.dag)

    def test_find_sources(self):
        """Test finding upstream sources."""
        sources = self.query.find_sources("sink_warehouse")
        assert "ingest_construction" in sources
        assert "transform_clean" in sources

    def test_find_consumers(self):
        """Test finding downstream consumers."""
        consumers = self.query.find_consumers("ingest_construction")
        assert "transform_clean" in consumers
        assert "sink_warehouse" in consumers

    def test_find_path(self):
        """Test finding path between nodes."""
        path = self.query.find_path("ingest_construction", "sink_warehouse")
        assert path is not None
        assert path[0] == "ingest_construction"
        assert path[-1] == "sink_warehouse"

    def test_find_path_no_connection(self):
        """Test finding path when no path exists."""
        # Add isolated node
        self.dag.add_node(TransformationNode(node_id="isolated", name="Isolated"))
        path = self.query.find_path("ingest_construction", "isolated")
        assert path is None

    def test_search_nodes_by_type(self):
        """Test searching nodes by type."""
        sinks = self.query.search_nodes(node_type="sink")
        assert "sink_warehouse" in sinks

    def test_search_nodes_by_owner(self):
        """Test searching nodes by owner."""
        owned_by_analytics = self.query.search_nodes(owner="analytics@example.com")
        assert "sink_warehouse" in owned_by_analytics

    def test_search_nodes_by_tag(self):
        """Test searching nodes by tag."""
        daily = self.query.search_nodes(tag="daily")
        assert "ingest_construction" in daily

    def test_find_by_tag(self):
        """Test finding nodes by tag."""
        results = self.query.find_by_tag("daily")
        assert "ingest_construction" in results

    def test_find_by_owner(self):
        """Test finding nodes by owner."""
        results = self.query.find_by_owner("data-eng@example.com")
        assert "ingest_construction" in results

    def test_find_by_type(self):
        """Test finding nodes by type."""
        ingestions = self.query.find_by_type("ingestion")
        assert "ingest_construction" in ingestions

    def test_get_node_info(self):
        """Test getting node information."""
        info = self.query.get_node_info("ingest_construction")
        assert info is not None
        assert info["node_id"] == "ingest_construction"
        assert "upstream_dependencies" in info

    def test_get_freshness_current(self):
        """Test freshness check for current data."""
        node = self.dag.get_node("ingest_construction")
        node.record_execution(ExecutionStatus.SUCCESS)

        freshness = self.query.get_freshness("ingest_construction")
        assert not freshness.is_stale
        assert freshness.last_execution_time is not None

    def test_get_freshness_stale(self):
        """Test freshness check for stale data."""
        node = self.dag.get_node("ingest_construction")
        # Record execution 48 hours ago
        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        exec_record = ExecutionRecord(
            node_id="ingest_construction",
            status=ExecutionStatus.SUCCESS,
            started_at=old_time,
            completed_at=old_time,
        )
        node.execution_history.append(exec_record)

        freshness = self.query.get_freshness("ingest_construction", stale_threshold_hours=24)
        assert freshness.is_stale

    def test_get_statistics(self):
        """Test getting DAG statistics."""
        stats = self.query.get_statistics()
        assert stats["total_nodes"] == 3
        assert stats["total_edges"] == 2

    def test_validate_lineage(self):
        """Test lineage validation."""
        validation = self.query.validate_lineage()
        assert validation["is_valid"]

class TestImpactAnalysis:
    """Tests for ImpactAnalysis engine."""

    def setup_method(self):
        """Setup test DAG."""
        self.dag = DAG()
        self.dag.add_node(TransformationNode(node_id="n1", name="N1", owner="user1"))
        self.dag.add_node(TransformationNode(node_id="n2", name="N2", owner="user2"))
        self.dag.add_node(TransformationNode(node_id="n3", name="N3", owner="user2"))
        self.dag.add_node(
            TransformationNode(node_id="n4", name="N4", node_type=NodeType.SINK, owner="user3")
        )

        self.dag.add_edge("n1", "n2")
        self.dag.add_edge("n2", "n3")
        self.dag.add_edge("n3", "n4")

        self.analyzer = ImpactAnalysis(self.dag)

    def test_analyze_change(self):
        """Test impact analysis."""
        report = self.analyzer.analyze_change("n1")
        assert report.affected_count > 0
        assert len(report.affected_users) > 0

    def test_find_breaking_changes(self):
        """Test detecting breaking changes."""
        old_schema = {
            "columns": {
                "id": {"type": "int", "nullable": False},
                "name": {"type": "string", "nullable": True},
                "age": {"type": "int", "nullable": True},
            }
        }

        new_schema = {
            "columns": {
                "id": {"type": "bigint", "nullable": False},  # type change
                "name": {"type": "string", "nullable": False},  # null constraint change
                # age column deleted
            }
        }

        changes = self.analyzer.find_breaking_changes(old_schema, new_schema, "n1")
        assert len(changes) > 0

        # Check for type change
        type_changes = [c for c in changes if c.change_type == "type_change"]
        assert len(type_changes) > 0

        # Check for deletion
        deletions = [c for c in changes if c.change_type == "column_deletion"]
        assert len(deletions) > 0

    def test_estimate_downstream_impact(self):
        """Test impact estimation."""
        impact_scores = self.analyzer.estimate_downstream_impact("n1")
        assert len(impact_scores) > 0
        for node_id, score in impact_scores.items():
            assert 0 <= score <= 100

class TestLineageVisualizer:
    """Tests for LineageVisualizer."""

    def setup_method(self):
        """Setup test DAG."""
        self.dag = DAG()
        self.dag.add_node(TransformationNode(node_id="n1", name="Source"))
        self.dag.add_node(TransformationNode(node_id="n2", name="Transform"))
        self.dag.add_edge("n1", "n2")
        self.viz = LineageVisualizer(self.dag)

    def test_to_json(self):
        """Test JSON export."""
        json_str = self.viz.to_json()
        data = json.loads(json_str)
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 2

    def test_to_mermaid(self):
        """Test Mermaid export."""
        mermaid = self.viz.to_mermaid()
        assert "graph TD" in mermaid
        assert "-->" in mermaid

    def test_to_ascii(self):
        """Test ASCII export."""
        ascii_viz = self.viz.to_ascii()
        assert "DATA LINEAGE" in ascii_viz
        assert "n1" in ascii_viz

    def test_to_html_table(self):
        """Test HTML table export."""
        html = self.viz.to_html_table()
        assert "<table" in html
        assert "n1" in html

    def test_get_subgraph(self):
        """Test subgraph extraction."""
        subgraph = self.viz.get_subgraph("n1")
        assert subgraph is not None
        assert "n1" in subgraph.nodes
        assert "n2" in subgraph.nodes

    def test_get_lineage_summary_by_type(self):
        """Test getting summary by type."""
        summary = self.viz.get_lineage_summary_by_type()
        assert "transformation" in summary
        assert "ingestion" not in summary  # Nodes are default transformation type

    def test_get_execution_summary(self):
        """Test execution summary."""
        # Add executions
        node = self.dag.get_node("n1")
        node.record_execution(ExecutionStatus.SUCCESS)
        node.record_execution(ExecutionStatus.FAILED)

        summary = self.viz.get_execution_summary()
        assert summary["total_executions"] == 2
        assert summary["successful"] == 1
        assert summary["failed"] == 1

class TestIntegration:
    """Integration tests combining multiple components."""

    def test_end_to_end_lineage_tracking(self):
        """Test complete lineage tracking workflow."""
        # Create DAG
        dag = DAG()

        # Add nodes representing complete pipeline
        ingestion_node = TransformationNode(
            node_id="ingest.socrata",
            name="Socrata Ingestion",
            node_type=NodeType.INGESTION,
            owner="data-eng@example.com",
        )
        dag.add_node(ingestion_node)

        transform_node = TransformationNode(
            node_id="transform.clean",
            name="Data Cleaning",
            node_type=NodeType.TRANSFORMATION,
            owner="data-eng@example.com",
        )
        dag.add_node(transform_node)

        sink_node = TransformationNode(
            node_id="sink.postgres",
            name="PostgreSQL Warehouse",
            node_type=NodeType.SINK,
            owner="analytics@example.com",
        )
        dag.add_node(sink_node)

        # Add edges
        dag.add_edge("ingest.socrata", "transform.clean")
        dag.add_edge("transform.clean", "sink.postgres")

        # Record executions
        ingestion_node.record_execution(
            status=ExecutionStatus.SUCCESS,
            input_rows=1000,
            output_rows=1000,
            duration_secs=10,
        )

        transform_node.record_execution(
            status=ExecutionStatus.SUCCESS,
            input_rows=1000,
            output_rows=950,
            duration_secs=5,
        )

        # Query the lineage
        query = LineageQuery(dag)

        # Test basic queries
        sources = query.find_sources("sink.postgres")
        assert len(sources) == 2

        consumers = query.find_consumers("ingest.socrata")
        assert len(consumers) == 2

        # Test impact analysis
        analyzer = ImpactAnalysis(dag)
        impact = analyzer.analyze_change("ingest.socrata")
        assert impact.affected_count == 2

        # Test visualization
        viz = LineageVisualizer(dag)
        json_export = viz.to_json()
        assert json.loads(json_export)["metadata"]["node_count"] == 3

        # Validate DAG
        validation = query.validate_lineage()
        assert validation["is_valid"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
