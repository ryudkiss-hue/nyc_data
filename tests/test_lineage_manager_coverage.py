"""Tests for socrata_toolkit.lineage.manager — LineageGraph, LineageEdge, ColumnLineage,
LineageRegistry, and TransformationType.

Covers all public methods plus key branches: cycle detection, cache hits,
OpenMetadata export, JSON round-trips, and the in-memory (no-DB) registry path.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from socrata_toolkit.lineage.manager import (
    ColumnLineage,
    LineageEdge,
    LineageGraph,
    LineageRegistry,
    TransformationType,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def simple_graph() -> LineageGraph:
    """LineageGraph with a two-hop chain: raw → staging → mart."""
    g = LineageGraph()
    g.add_edge("raw", "staging", ["id", "amount"], ["id", "amount"],
               TransformationType.INGESTION)
    g.add_edge("staging", "mart", ["amount"], ["total"],
               TransformationType.AGGREGATION)
    return g

@pytest.fixture()
def minimal_edge() -> LineageEdge:
    """A single LineageEdge for serialisation tests."""
    return LineageEdge(
        edge_id="edge-001",
        source_dataset_id="src",
        target_dataset_id="tgt",
        source_columns=["col_a"],
        target_columns=["col_b"],
        transformation_type=TransformationType.COPY,
    )

# ---------------------------------------------------------------------------
# TransformationType
# ---------------------------------------------------------------------------

class TestTransformationType:
    """Verify enum membership and values."""

    def test_all_expected_members_exist(self):
        """All seven transformation types should be accessible."""
        names = {t.name for t in TransformationType}
        assert {"INGESTION", "AGGREGATION", "JOIN", "UNION", "FILTER",
                "ENRICHMENT", "CUSTOM_SQL", "COPY"}.issubset(names)

    def test_values_are_lowercase_strings(self):
        """Enum values must be lowercase strings for JSON compatibility."""
        for member in TransformationType:
            assert isinstance(member.value, str)
            assert member.value == member.value.lower()

# ---------------------------------------------------------------------------
# LineageEdge
# ---------------------------------------------------------------------------

class TestLineageEdge:
    """Tests for LineageEdge dataclass serialisation."""

    def test_to_dict_serialises_transformation_type(self, minimal_edge: LineageEdge):
        """transformation_type must be the .value string in the dict."""
        d = minimal_edge.to_dict()
        assert d["transformation_type"] == "copy"

    def test_to_dict_serialises_created_at(self, minimal_edge: LineageEdge):
        """created_at must be an ISO-8601 string ending with Z."""
        d = minimal_edge.to_dict()
        assert isinstance(d["created_at"], str)
        assert d["created_at"].endswith("Z")

    def test_to_dict_contains_all_fields(self, minimal_edge: LineageEdge):
        """Dict must include edge_id, source, target, and column lists."""
        d = minimal_edge.to_dict()
        assert d["edge_id"] == "edge-001"
        assert d["source_dataset_id"] == "src"
        assert d["target_dataset_id"] == "tgt"
        assert d["source_columns"] == ["col_a"]
        assert d["target_columns"] == ["col_b"]

    def test_to_json_produces_valid_json(self, minimal_edge: LineageEdge):
        """to_json must return a string that parses without error."""
        json_str = minimal_edge.to_json()
        parsed = json.loads(json_str)
        assert parsed["source_dataset_id"] == "src"

    def test_to_json_round_trips_source_dataset_id(self, minimal_edge: LineageEdge):
        """JSON round-trip preserves source_dataset_id."""
        assert "source_dataset_id" in minimal_edge.to_json()

    def test_edge_without_sql_has_none(self, minimal_edge: LineageEdge):
        """transformation_sql defaults to None."""
        assert minimal_edge.transformation_sql is None

# ---------------------------------------------------------------------------
# ColumnLineage
# ---------------------------------------------------------------------------

class TestColumnLineage:
    """Tests for ColumnLineage dataclass."""

    def test_to_dict_preserves_all_fields(self):
        """All dataclass fields must survive the to_dict round-trip."""
        cl = ColumnLineage(
            target_table="sales_mart",
            target_column="revenue",
            upstream_tables=["raw_sales"],
            upstream_columns=[["amount"]],
            transformation_sql="SUM(amount)",
            lineage_depth=1,
        )
        d = cl.to_dict()
        assert d["target_table"] == "sales_mart"
        assert d["target_column"] == "revenue"
        assert d["upstream_tables"] == ["raw_sales"]
        assert d["lineage_depth"] == 1

    def test_to_json_includes_target_table(self):
        """JSON must contain target_table key."""
        cl = ColumnLineage(
            target_table="t",
            target_column="c",
            upstream_tables=[],
            upstream_columns=[],
        )
        assert "target_table" in cl.to_json()

    def test_default_lineage_depth_is_zero(self):
        """lineage_depth defaults to 0 (source column, no upstream)."""
        cl = ColumnLineage(
            target_table="t",
            target_column="c",
            upstream_tables=[],
            upstream_columns=[],
        )
        assert cl.lineage_depth == 0

# ---------------------------------------------------------------------------
# LineageGraph — add_edge and basic structure
# ---------------------------------------------------------------------------

class TestLineageGraphAddEdge:
    """Tests for LineageGraph.add_edge."""

    def test_add_edge_returns_string_id(self):
        """add_edge should return a non-empty string edge ID."""
        g = LineageGraph()
        eid = g.add_edge("a", "b", ["x"], ["x"])
        assert isinstance(eid, str) and eid

    def test_added_edge_stored_in_edges_dict(self):
        """Returned edge ID must be a key in g.edges."""
        g = LineageGraph()
        eid = g.add_edge("a", "b", [], [])
        assert eid in g.edges

    def test_upstream_map_updated_for_target(self):
        """After adding a→b, upstream_map["b"] must include the edge."""
        g = LineageGraph()
        eid = g.add_edge("a", "b", [], [])
        assert any(e.edge_id == eid for e in g.upstream_map.get("b", []))

    def test_downstream_map_updated_for_source(self):
        """After adding a→b, downstream_map["a"] must include the edge."""
        g = LineageGraph()
        eid = g.add_edge("a", "b", [], [])
        assert any(e.edge_id == eid for e in g.downstream_map.get("a", []))

    def test_cycle_raises_value_error(self):
        """Adding an edge that would close a loop must raise ValueError."""
        g = LineageGraph()
        g.add_edge("a", "b", [], [])
        g.add_edge("b", "c", [], [])
        with pytest.raises(ValueError, match="circular"):
            g.add_edge("c", "a", [], [])

    def test_self_loop_raises_value_error(self):
        """A direct self-reference edge must be rejected."""
        g = LineageGraph()
        with pytest.raises(ValueError):
            g.add_edge("a", "a", [], [])

    def test_default_transformation_type_is_custom_sql(self):
        """Omitting transformation_type should default to CUSTOM_SQL."""
        g = LineageGraph()
        eid = g.add_edge("a", "b", [], [])
        assert g.edges[eid].transformation_type == TransformationType.CUSTOM_SQL

    def test_sql_stored_on_edge(self):
        """Provided SQL must be accessible on the stored edge."""
        g = LineageGraph()
        eid = g.add_edge("a", "b", [], [], transformation_sql="SELECT 1")
        assert g.edges[eid].transformation_sql == "SELECT 1"

# ---------------------------------------------------------------------------
# LineageGraph — upstream / downstream traversal
# ---------------------------------------------------------------------------

class TestLineageGraphTraversal:
    """Tests for get_upstream_tables and get_downstream_tables."""

    def test_upstream_includes_transitive_sources(self, simple_graph: LineageGraph):
        """get_upstream_tables('mart') must return both 'raw' and 'staging'."""
        upstream = simple_graph.get_upstream_tables("mart")
        assert "raw" in upstream
        assert "staging" in upstream

    def test_upstream_include_self_option(self, simple_graph: LineageGraph):
        """include_self=True must add the queried table to the result."""
        upstream = simple_graph.get_upstream_tables("mart", include_self=True)
        assert "mart" in upstream

    def test_upstream_for_leaf_node_is_empty(self, simple_graph: LineageGraph):
        """A source node with no parents should have no upstream tables."""
        assert simple_graph.get_upstream_tables("raw") == []

    def test_downstream_includes_transitive_targets(self, simple_graph: LineageGraph):
        """get_downstream_tables('raw') must return both 'staging' and 'mart'."""
        downstream = simple_graph.get_downstream_tables("raw")
        assert "staging" in downstream
        assert "mart" in downstream

    def test_downstream_include_self_option(self, simple_graph: LineageGraph):
        """include_self=True must add the queried table to the downstream list."""
        downstream = simple_graph.get_downstream_tables("raw", include_self=True)
        assert "raw" in downstream

    def test_downstream_for_terminal_node_is_empty(self, simple_graph: LineageGraph):
        """A sink node with no children should have no downstream tables."""
        assert simple_graph.get_downstream_tables("mart") == []

    def test_unknown_table_returns_empty_upstream(self):
        """Querying a non-existent table should return an empty list."""
        g = LineageGraph()
        assert g.get_upstream_tables("ghost") == []

# ---------------------------------------------------------------------------
# LineageGraph — column lineage tracing
# ---------------------------------------------------------------------------

class TestLineageGraphColumnLineage:
    """Tests for trace_column_lineage."""

    def test_traces_direct_column_mapping(self):
        """Column renamed from user_id→id should be traced back to user_id."""
        g = LineageGraph()
        g.add_edge("raw", "clean", ["user_id"], ["id"])
        cl = g.trace_column_lineage("clean", "id")
        assert cl is not None
        assert cl.upstream_tables == ["raw"]
        assert cl.upstream_columns[0] == ["user_id"]

    def test_source_column_returns_empty_upstream(self):
        """A column that has no upstream mapping returns empty lists."""
        g = LineageGraph()
        g.add_edge("raw", "clean", ["user_id"], ["id"])
        cl = g.trace_column_lineage("raw", "user_id")
        assert cl is not None
        assert cl.upstream_tables == []
        assert cl.lineage_depth == 0

    def test_cache_hit_avoids_recomputation(self):
        """Second call for the same (table, column) pair returns cached object."""
        g = LineageGraph()
        g.add_edge("raw", "clean", ["user_id"], ["id"])
        first = g.trace_column_lineage("clean", "id")
        second = g.trace_column_lineage("clean", "id")
        assert first is second  # same object from cache

    def test_nonexistent_column_returns_empty_upstream(self):
        """Tracing an unknown column yields ColumnLineage with no upstream."""
        g = LineageGraph()
        g.add_edge("raw", "clean", ["user_id"], ["id"])
        cl = g.trace_column_lineage("clean", "missing_col")
        assert cl is not None
        assert cl.upstream_tables == []

    def test_lineage_depth_increments_per_upstream_source(self):
        """Each upstream table increments lineage_depth by one."""
        g = LineageGraph()
        g.add_edge("src1", "target", ["a"], ["x"])
        g.add_edge("src2", "target", ["b"], ["y"])
        cl_x = g.trace_column_lineage("target", "x")
        assert cl_x is not None and cl_x.lineage_depth == 1

# ---------------------------------------------------------------------------
# LineageGraph — detect_cycles
# ---------------------------------------------------------------------------

class TestLineageGraphDetectCycles:
    """Tests for detect_cycles (post-hoc cycle inspection)."""

    def test_acyclic_graph_has_no_cycles(self, simple_graph: LineageGraph):
        """A well-formed DAG should report zero cycles."""
        assert simple_graph.detect_cycles() == []

    def test_empty_graph_has_no_cycles(self):
        """An empty graph must not report any cycles."""
        g = LineageGraph()
        assert g.detect_cycles() == []

# ---------------------------------------------------------------------------
# LineageGraph — serialisation
# ---------------------------------------------------------------------------

class TestLineageGraphSerialisation:
    """Tests for to_dict, to_json, export_to_openmetadata_format."""

    def test_to_dict_edge_count_matches(self, simple_graph: LineageGraph):
        """num_edges in the dict must equal len(graph.edges)."""
        d = simple_graph.to_dict()
        assert d["num_edges"] == len(simple_graph.edges)

    def test_to_dict_edges_list_length(self, simple_graph: LineageGraph):
        """'edges' list in the dict must have the correct number of elements."""
        d = simple_graph.to_dict()
        assert len(d["edges"]) == 2

    def test_to_json_is_valid_json(self, simple_graph: LineageGraph):
        """to_json must produce a parseable JSON string."""
        parsed = json.loads(simple_graph.to_json())
        assert "edges" in parsed

    def test_empty_graph_to_dict(self):
        """Empty graph should serialise with zero edges."""
        g = LineageGraph()
        d = g.to_dict()
        assert d["num_edges"] == 0
        assert d["edges"] == []

    def test_openmetadata_format_has_lineage_key(self, simple_graph: LineageGraph):
        """OpenMetadata export must include a 'lineage' key."""
        om = simple_graph.export_to_openmetadata_format()
        assert "lineage" in om

    def test_openmetadata_format_edge_count(self, simple_graph: LineageGraph):
        """total_edges in OpenMetadata export must match graph edge count."""
        om = simple_graph.export_to_openmetadata_format()
        assert om["total_edges"] == 2

    def test_openmetadata_format_has_exported_at(self, simple_graph: LineageGraph):
        """OpenMetadata export must include an exported_at timestamp."""
        om = simple_graph.export_to_openmetadata_format()
        assert "exported_at" in om

    def test_openmetadata_upstream_downstream_keys(self, simple_graph: LineageGraph):
        """Each OpenMetadata edge entry must have 'upstream' and 'downstream'."""
        om = simple_graph.export_to_openmetadata_format()
        for entry in om["lineage"]:
            assert "upstream" in entry
            assert "downstream" in entry
            assert "transformation" in entry

# ---------------------------------------------------------------------------
# LineageRegistry (no-DB path)
# ---------------------------------------------------------------------------

class TestLineageRegistryNoDb:
    """Tests for LineageRegistry when no database DSN is provided."""

    def test_registry_initialises_without_db(self):
        """Registry can be created with db_dsn=None without errors."""
        registry = LineageRegistry(db_dsn=None)
        assert registry.graph is not None

    def test_add_edge_updates_graph(self):
        """add_edge must delegate to the internal LineageGraph."""
        registry = LineageRegistry(db_dsn=None)
        eid = registry.add_edge("src", "tgt", ["x"], ["y"])
        assert eid in registry.graph.edges

    def test_get_graph_returns_lineage_graph_instance(self):
        """get_graph must return a LineageGraph instance."""
        registry = LineageRegistry(db_dsn=None)
        g = registry.get_graph()
        assert isinstance(g, LineageGraph)

    def test_add_edge_cycle_raises(self):
        """Cycle detection flows through the registry correctly."""
        registry = LineageRegistry(db_dsn=None)
        registry.add_edge("a", "b", [], [])
        registry.add_edge("b", "c", [], [])
        with pytest.raises(ValueError):
            registry.add_edge("c", "a", [], [])

    def test_custom_table_name_stored(self):
        """Provided table_name is stored on the registry."""
        registry = LineageRegistry(db_dsn=None, table_name="my_lineage")
        assert registry.table_name == "my_lineage"
