"""Tests for data lineage tracking and column provenance.

Tests cover lineage graph construction, column tracing, and cycle detection.
"""

import pytest
from socrata_toolkit.lineage import (
    LineageGraph,
    LineageEdge,
    LineageRegistry,
    ColumnLineage,
    TransformationType,
)


class TestLineageEdge:
    """Tests for LineageEdge class."""

    def test_edge_creation(self):
        """Test basic lineage edge creation."""
        edge = LineageEdge(
            edge_id="edge-1",
            source_dataset_id="source",
            target_dataset_id="target",
            source_columns=["id", "name"],
            target_columns=["id", "name"],
            transformation_type=TransformationType.INGESTION,
        )
        assert edge.source_dataset_id == "source"
        assert edge.target_dataset_id == "target"
        assert len(edge.source_columns) == 2

    def test_edge_to_dict(self):
        """Test edge to dictionary conversion."""
        edge = LineageEdge(
            edge_id="edge-1",
            source_dataset_id="source",
            target_dataset_id="target",
            source_columns=["id"],
            target_columns=["id"],
            transformation_type=TransformationType.COPY,
        )
        d = edge.to_dict()
        assert d["source_dataset_id"] == "source"
        assert d["transformation_type"] == "copy"

    def test_edge_to_json(self):
        """Test edge to JSON conversion."""
        edge = LineageEdge(
            edge_id="edge-1",
            source_dataset_id="source",
            target_dataset_id="target",
            source_columns=["id"],
            target_columns=["id"],
            transformation_type=TransformationType.INGESTION,
        )
        json_str = edge.to_json()
        assert "source_dataset_id" in json_str
        assert "target_dataset_id" in json_str


class TestColumnLineage:
    """Tests for ColumnLineage class."""

    def test_column_lineage_creation(self):
        """Test basic column lineage creation."""
        col = ColumnLineage(
            target_table="sales_summary",
            target_column="total_amount",
            upstream_tables=["sales"],
            upstream_columns=[["amount"]],
        )
        assert col.target_column == "total_amount"
        assert col.upstream_tables == ["sales"]

    def test_column_lineage_to_dict(self):
        """Test column lineage to dictionary."""
        col = ColumnLineage(
            target_table="sales_summary",
            target_column="total_amount",
            upstream_tables=["sales"],
            upstream_columns=[["amount"]],
        )
        d = col.to_dict()
        assert d["target_column"] == "total_amount"
        assert d["upstream_tables"] == ["sales"]

    def test_column_lineage_to_json(self):
        """Test column lineage to JSON."""
        col = ColumnLineage(
            target_table="sales_summary",
            target_column="total_amount",
            upstream_tables=["sales"],
            upstream_columns=[["amount"]],
        )
        json_str = col.to_json()
        assert "total_amount" in json_str


class TestLineageGraph:
    """Tests for LineageGraph class."""

    def test_graph_initialization(self):
        """Test lineage graph initialization."""
        graph = LineageGraph()
        assert len(graph.edges) == 0
        assert len(graph.upstream_map) == 0

    def test_add_edge(self):
        """Test adding edge to graph."""
        graph = LineageGraph()
        edge_id = graph.add_edge(
            "source",
            "target",
            ["id", "name"],
            ["id", "name"],
            TransformationType.INGESTION,
        )
        assert edge_id in graph.edges
        assert len(graph.edges) == 1

    def test_add_multiple_edges(self):
        """Test adding multiple edges."""
        graph = LineageGraph()
        graph.add_edge("a", "b", ["id"], ["id"], TransformationType.COPY)
        graph.add_edge("b", "c", ["id"], ["id"], TransformationType.COPY)
        graph.add_edge("c", "d", ["id"], ["id"], TransformationType.COPY)
        assert len(graph.edges) == 3

    def test_get_upstream_tables(self):
        """Test getting upstream tables."""
        graph = LineageGraph()
        graph.add_edge("raw", "staging", [], [])
        graph.add_edge("staging", "mart", [], [])
        upstream = graph.get_upstream_tables("mart")
        assert "staging" in upstream
        assert "raw" in upstream
        assert len(upstream) == 2

    def test_get_upstream_tables_direct_only(self):
        """Test getting direct upstream tables only."""
        graph = LineageGraph()
        graph.add_edge("raw", "staging", [], [])
        graph.add_edge("staging", "mart", [], [])
        upstream = graph.get_upstream_tables("staging")
        assert "raw" in upstream
        assert "mart" not in upstream
        assert len(upstream) == 1

    def test_get_downstream_tables(self):
        """Test getting downstream tables."""
        graph = LineageGraph()
        graph.add_edge("raw", "staging", [], [])
        graph.add_edge("staging", "mart", [], [])
        downstream = graph.get_downstream_tables("raw")
        assert "staging" in downstream
        assert "mart" in downstream
        assert len(downstream) == 2

    def test_cycle_detection_prevented(self):
        """Test that cycles are prevented."""
        graph = LineageGraph()
        graph.add_edge("a", "b", [], [])
        graph.add_edge("b", "c", [], [])
        with pytest.raises(ValueError):
            graph.add_edge("c", "a", [], [])

    def test_trace_column_lineage(self):
        """Test column-level lineage tracing."""
        graph = LineageGraph()
        graph.add_edge("raw", "clean", ["user_id", "name"], ["id", "full_name"])
        col = graph.trace_column_lineage("clean", "id")
        assert col.target_column == "id"
        assert col.upstream_columns[0][0] == "user_id"

    def test_trace_column_lineage_multiple_hops(self):
        """Test column tracing through multiple transformations."""
        graph = LineageGraph()
        graph.add_edge("raw", "staging", ["user_id"], ["id"])
        graph.add_edge("staging", "mart", ["id"], ["user_id"])
        col = graph.trace_column_lineage("mart", "user_id")
        assert col.target_column == "user_id"
        assert col.upstream_tables == ["staging"]

    def test_to_dict(self):
        """Test graph to dictionary conversion."""
        graph = LineageGraph()
        graph.add_edge("a", "b", [], [])
        d = graph.to_dict()
        assert "edges" in d
        assert len(d["edges"]) == 1
        assert d["num_edges"] == 1

    def test_to_json(self):
        """Test graph to JSON conversion."""
        graph = LineageGraph()
        graph.add_edge("a", "b", [], [])
        json_str = graph.to_json()
        assert "edges" in json_str
        assert len(json_str) > 0

    def test_export_to_openmetadata_format(self):
        """Test export to OpenMetadata format."""
        graph = LineageGraph()
        graph.add_edge("source", "target", ["id"], ["id"], TransformationType.INGESTION)
        om = graph.export_to_openmetadata_format()
        assert "lineage" in om
        assert len(om["lineage"]) == 1
        assert om["lineage"][0]["upstream"]["dataset_id"] == "source"

    def test_complex_lineage_scenario(self):
        """Test complex lineage with multiple sources and targets."""
        graph = LineageGraph()
        # Create a more complex lineage
        graph.add_edge("customers", "customer_staging", ["id", "name"], ["cust_id", "cust_name"])
        graph.add_edge("orders", "order_staging", ["id", "customer_id"], ["order_id", "cust_id"])
        graph.add_edge("customer_staging", "customer_mart", ["cust_id"], ["id"])
        graph.add_edge("order_staging", "order_mart", ["order_id"], ["id"])
        graph.add_edge("customer_mart", "final_report", ["id"], ["customer_id"])
        graph.add_edge("order_mart", "final_report", ["id"], ["order_id"])

        # Test upstream from final report
        upstream = graph.get_upstream_tables("final_report")
        assert "customer_mart" in upstream
        assert "order_mart" in upstream
        assert "customers" in upstream
        assert "orders" in upstream

    def test_detect_cycles_empty_graph(self):
        """Test cycle detection on empty graph."""
        graph = LineageGraph()
        cycles = graph.detect_cycles()
        assert len(cycles) == 0

    def test_column_lineage_caching(self):
        """Test column lineage caching."""
        graph = LineageGraph()
        graph.add_edge("a", "b", ["id"], ["id"])
        col1 = graph.trace_column_lineage("b", "id")
        col2 = graph.trace_column_lineage("b", "id")
        # Should return same cached instance
        assert col1 is col2


class TestLineageRegistry:
    """Tests for LineageRegistry class."""

    def test_registry_initialization_no_db(self):
        """Test registry initialization without database."""
        registry = LineageRegistry()
        assert registry.db_dsn is None
        assert isinstance(registry.graph, LineageGraph)

    def test_registry_add_edge(self):
        """Test adding edge through registry."""
        registry = LineageRegistry()
        edge_id = registry.add_edge("source", "target", ["id"], ["id"])
        graph = registry.get_graph()
        assert edge_id in graph.edges

    def test_registry_get_graph(self):
        """Test getting graph from registry."""
        registry = LineageRegistry()
        registry.add_edge("a", "b", [], [])
        graph = registry.get_graph()
        assert len(graph.edges) == 1

    def test_registry_cycle_detection(self):
        """Test cycle detection through registry."""
        registry = LineageRegistry()
        registry.add_edge("a", "b", [], [])
        registry.add_edge("b", "c", [], [])
        with pytest.raises(ValueError):
            registry.add_edge("c", "a", [], [])


class TestLineageEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_self_referential_edge(self):
        """Test preventing self-referential edges (should work as no cycle)."""
        graph = LineageGraph()
        # Self-referential should be prevented as a cycle
        with pytest.raises(ValueError):
            graph.add_edge("table", "table", [], [])

    def test_empty_column_lists(self):
        """Test edge with empty column lists."""
        graph = LineageGraph()
        edge_id = graph.add_edge("a", "b", [], [])
        assert edge_id in graph.edges

    def test_missing_column_lineage(self):
        """Test column lineage for non-existent column."""
        graph = LineageGraph()
        graph.add_edge("a", "b", ["id"], ["id"])
        col = graph.trace_column_lineage("b", "nonexistent")
        # Should return column with no upstream
        assert col.target_column == "nonexistent"
        assert len(col.upstream_tables) == 0

    def test_large_graph(self):
        """Test lineage graph with many nodes."""
        graph = LineageGraph()
        # Create a chain of 100 nodes
        for i in range(99):
            graph.add_edge(f"table_{i}", f"table_{i+1}", [], [])

        # Verify upstream traversal works efficiently
        upstream = graph.get_upstream_tables("table_99")
        assert len(upstream) == 99

    def test_transformation_type_variety(self):
        """Test various transformation types."""
        graph = LineageGraph()
        graph.add_edge("a", "b", [], [], TransformationType.INGESTION)
        graph.add_edge("b", "c", [], [], TransformationType.AGGREGATION)
        graph.add_edge("c", "d", [], [], TransformationType.JOIN)
        graph.add_edge("d", "e", [], [], TransformationType.FILTER)
        assert len(graph.edges) == 4
