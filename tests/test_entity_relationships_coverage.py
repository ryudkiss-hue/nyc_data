"""Comprehensive tests for entity.relationships module."""
from __future__ import annotations

import pytest

from socrata_toolkit.entity.relationships import (
    EntityRelationship,
    RelationshipGraph,
    RelationshipType,
)

# ---------------------------------------------------------------------------
# RelationshipType enum
# ---------------------------------------------------------------------------

class TestRelationshipTypeEnum:
    """Tests for RelationshipType string enum."""

    def test_all_values_are_lowercase_strings(self):
        for member in RelationshipType:
            assert member.value == member.value.lower()

    def test_contains_expected_members(self):
        expected = {
            "contains", "belongs_to", "adjacent_to", "part_of",
            "composed_of", "intersects", "references", "derived_from",
        }
        actual = {m.value for m in RelationshipType}
        assert expected == actual

    def test_can_construct_from_string(self):
        rt = RelationshipType("contains")
        assert rt == RelationshipType.CONTAINS

# ---------------------------------------------------------------------------
# EntityRelationship dataclass
# ---------------------------------------------------------------------------

class TestEntityRelationship:
    """Tests for EntityRelationship dataclass."""

    def test_repr_contains_source_and_target(self):
        rel = EntityRelationship(
            relationship_id="r1",
            source_entity_id="block_123",
            target_entity_id="segment_456",
            relationship_type=RelationshipType.CONTAINS,
        )
        text = repr(rel)
        assert "block_123" in text
        assert "segment_456" in text

    def test_default_confidence_is_one(self):
        rel = EntityRelationship(
            relationship_id="r1",
            source_entity_id="a",
            target_entity_id="b",
            relationship_type=RelationshipType.REFERENCES,
        )
        assert rel.confidence == 1.0

    def test_attributes_default_empty_dict(self):
        rel = EntityRelationship(
            relationship_id="r1",
            source_entity_id="a",
            target_entity_id="b",
            relationship_type=RelationshipType.ADJACENT_TO,
        )
        assert rel.attributes == {}

    def test_created_by_defaults_to_system(self):
        rel = EntityRelationship(
            relationship_id="r1",
            source_entity_id="a",
            target_entity_id="b",
            relationship_type=RelationshipType.PART_OF,
        )
        assert rel.created_by == "system"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def graph() -> RelationshipGraph:
    """Empty relationship graph."""
    return RelationshipGraph()

@pytest.fixture()
def populated_graph() -> RelationshipGraph:
    """Graph with a small hierarchy: borough -> block -> segment."""
    g = RelationshipGraph()
    g.add_relationship("borough_MN", "block_001", RelationshipType.CONTAINS)
    g.add_relationship("block_001", "seg_A", RelationshipType.CONTAINS)
    g.add_relationship("block_001", "seg_B", RelationshipType.CONTAINS)
    g.add_relationship("seg_A", "seg_B", RelationshipType.ADJACENT_TO)
    return g

# ---------------------------------------------------------------------------
# RelationshipGraph.add_relationship
# ---------------------------------------------------------------------------

class TestAddRelationship:
    """Tests for RelationshipGraph.add_relationship."""

    def test_returns_string_id(self, graph):
        rel_id = graph.add_relationship("a", "b", RelationshipType.CONTAINS)
        assert isinstance(rel_id, str)
        assert len(rel_id) > 0

    def test_relationship_retrievable_by_id(self, graph):
        rel_id = graph.add_relationship("x", "y", RelationshipType.REFERENCES)
        rel = graph.get_relationship(rel_id)
        assert rel is not None
        assert rel.source_entity_id == "x"
        assert rel.target_entity_id == "y"

    def test_accepts_string_rel_type(self, graph):
        rel_id = graph.add_relationship("a", "b", "contains")
        rel = graph.get_relationship(rel_id)
        assert rel.relationship_type == RelationshipType.CONTAINS

    def test_confidence_clamped_to_one(self, graph):
        rel_id = graph.add_relationship("a", "b", RelationshipType.PART_OF, confidence=2.5)
        rel = graph.get_relationship(rel_id)
        assert rel.confidence == 1.0

    def test_confidence_clamped_to_zero(self, graph):
        rel_id = graph.add_relationship("a", "b", RelationshipType.PART_OF, confidence=-0.5)
        rel = graph.get_relationship(rel_id)
        assert rel.confidence == 0.0

    def test_attributes_stored(self, graph):
        attrs = {"weight": 42, "label": "test"}
        rel_id = graph.add_relationship(
            "a", "b", RelationshipType.INTERSECTS, attributes=attrs
        )
        rel = graph.get_relationship(rel_id)
        assert rel.attributes == attrs

    def test_notes_stored(self, graph):
        rel_id = graph.add_relationship(
            "a", "b", RelationshipType.DERIVED_FROM, notes="manual entry"
        )
        rel = graph.get_relationship(rel_id)
        assert rel.notes == "manual entry"

# ---------------------------------------------------------------------------
# RelationshipGraph.get_relationship
# ---------------------------------------------------------------------------

class TestGetRelationship:
    """Tests for RelationshipGraph.get_relationship."""

    def test_returns_none_for_missing_id(self, graph):
        assert graph.get_relationship("nonexistent-id") is None

    def test_returns_correct_relationship(self, graph):
        rel_id = graph.add_relationship("e1", "e2", RelationshipType.BELONGS_TO)
        rel = graph.get_relationship(rel_id)
        assert rel.relationship_id == rel_id

# ---------------------------------------------------------------------------
# RelationshipGraph.remove_relationship
# ---------------------------------------------------------------------------

class TestRemoveRelationship:
    """Tests for RelationshipGraph.remove_relationship."""

    def test_remove_existing_returns_true(self, graph):
        rel_id = graph.add_relationship("a", "b", RelationshipType.CONTAINS)
        assert graph.remove_relationship(rel_id) is True

    def test_remove_nonexistent_returns_false(self, graph):
        assert graph.remove_relationship("no-such-id") is False

    def test_removed_relationship_no_longer_retrievable(self, graph):
        rel_id = graph.add_relationship("a", "b", RelationshipType.CONTAINS)
        graph.remove_relationship(rel_id)
        assert graph.get_relationship(rel_id) is None

    def test_indexes_cleaned_up_after_remove(self, graph):
        rel_id = graph.add_relationship("src", "tgt", RelationshipType.PART_OF)
        graph.remove_relationship(rel_id)
        assert graph.get_related_entities("src") == []

# ---------------------------------------------------------------------------
# RelationshipGraph.add_bidirectional_relationship
# ---------------------------------------------------------------------------

class TestAddBidirectionalRelationship:
    """Tests for RelationshipGraph.add_bidirectional_relationship."""

    def test_returns_two_ids(self, graph):
        fwd, bwd = graph.add_bidirectional_relationship(
            "a", "b", RelationshipType.CONTAINS
        )
        assert fwd != bwd

    def test_forward_direction_stored(self, graph):
        fwd, _ = graph.add_bidirectional_relationship("a", "b", RelationshipType.CONTAINS)
        rel = graph.get_relationship(fwd)
        assert rel.source_entity_id == "a"
        assert rel.target_entity_id == "b"
        assert rel.relationship_type == RelationshipType.CONTAINS

    def test_reverse_direction_is_opposite(self, graph):
        _, bwd = graph.add_bidirectional_relationship("a", "b", RelationshipType.CONTAINS)
        rel = graph.get_relationship(bwd)
        assert rel.source_entity_id == "b"
        assert rel.target_entity_id == "a"
        assert rel.relationship_type == RelationshipType.PART_OF

    def test_adjacent_to_reverses_to_adjacent_to(self, graph):
        _, bwd = graph.add_bidirectional_relationship(
            "a", "b", RelationshipType.ADJACENT_TO
        )
        rel = graph.get_relationship(bwd)
        assert rel.relationship_type == RelationshipType.ADJACENT_TO

# ---------------------------------------------------------------------------
# RelationshipGraph._get_reverse_type
# ---------------------------------------------------------------------------

class TestGetReverseType:
    """Tests for RelationshipGraph._get_reverse_type."""

    def test_contains_reverses_to_part_of(self, graph):
        assert graph._get_reverse_type(RelationshipType.CONTAINS) == RelationshipType.PART_OF

    def test_belongs_to_reverses_to_composed_of(self, graph):
        assert graph._get_reverse_type(RelationshipType.BELONGS_TO) == RelationshipType.COMPOSED_OF

    def test_derived_from_reverses_to_references(self, graph):
        assert graph._get_reverse_type(RelationshipType.DERIVED_FROM) == RelationshipType.REFERENCES

    def test_accepts_string_input(self, graph):
        result = graph._get_reverse_type("contains")
        assert result == RelationshipType.PART_OF

# ---------------------------------------------------------------------------
# RelationshipGraph.get_related_entities
# ---------------------------------------------------------------------------

class TestGetRelatedEntities:
    """Tests for RelationshipGraph.get_related_entities."""

    def test_outgoing_returns_targets(self, populated_graph):
        results = populated_graph.get_related_entities("block_001", direction="outgoing")
        targets = [r[0] for r in results]
        assert "seg_A" in targets
        assert "seg_B" in targets

    def test_incoming_returns_sources(self, populated_graph):
        results = populated_graph.get_related_entities("block_001", direction="incoming")
        sources = [r[0] for r in results]
        assert "borough_MN" in sources

    def test_filter_by_type(self, populated_graph):
        results = populated_graph.get_related_entities(
            "block_001", relationship_type=RelationshipType.CONTAINS, direction="outgoing"
        )
        assert len(results) == 2

    def test_filter_by_string_type(self, populated_graph):
        results = populated_graph.get_related_entities(
            "block_001", relationship_type="contains", direction="outgoing"
        )
        assert len(results) == 2

    def test_no_relationships_returns_empty(self, graph):
        results = graph.get_related_entities("isolated_entity")
        assert results == []

    def test_result_tuple_structure(self, populated_graph):
        results = populated_graph.get_related_entities("borough_MN", direction="outgoing")
        assert len(results) == 1
        entity_id, rel_type, confidence = results[0]
        assert entity_id == "block_001"
        assert isinstance(rel_type, RelationshipType)
        assert isinstance(confidence, float)

# ---------------------------------------------------------------------------
# RelationshipGraph.get_all_relationships
# ---------------------------------------------------------------------------

class TestGetAllRelationships:
    """Tests for RelationshipGraph.get_all_relationships."""

    def test_no_filter_returns_all(self, populated_graph):
        all_rels = populated_graph.get_all_relationships()
        assert len(all_rels) == 4

    def test_filter_by_source(self, populated_graph):
        rels = populated_graph.get_all_relationships(source_id="block_001")
        assert all(r.source_entity_id == "block_001" for r in rels)

    def test_filter_by_type(self, populated_graph):
        rels = populated_graph.get_all_relationships(rel_type=RelationshipType.ADJACENT_TO)
        assert len(rels) == 1

    def test_filter_by_type_string(self, populated_graph):
        rels = populated_graph.get_all_relationships(rel_type="adjacent_to")
        assert len(rels) == 1

    def test_empty_graph_returns_empty(self, graph):
        assert graph.get_all_relationships() == []

# ---------------------------------------------------------------------------
# RelationshipGraph.find_path
# ---------------------------------------------------------------------------

class TestFindPath:
    """Tests for RelationshipGraph.find_path (BFS)."""

    def test_same_node_returns_self_path(self, populated_graph):
        path = populated_graph.find_path("borough_MN", "borough_MN")
        assert path == ["borough_MN"]

    def test_direct_connection_found(self, populated_graph):
        path = populated_graph.find_path("borough_MN", "block_001")
        assert path == ["borough_MN", "block_001"]

    def test_two_hop_path_found(self, populated_graph):
        path = populated_graph.find_path("borough_MN", "seg_A")
        assert path is not None
        assert path[0] == "borough_MN"
        assert path[-1] == "seg_A"

    def test_no_path_returns_none(self, populated_graph):
        path = populated_graph.find_path("seg_A", "borough_MN")
        assert path is None

    def test_max_depth_limits_search(self, populated_graph):
        path = populated_graph.find_path("borough_MN", "seg_A", max_depth=1)
        assert path is None

# ---------------------------------------------------------------------------
# RelationshipGraph.find_all_paths
# ---------------------------------------------------------------------------

class TestFindAllPaths:
    """Tests for RelationshipGraph.find_all_paths."""

    def test_returns_list_of_paths(self, populated_graph):
        paths = populated_graph.find_all_paths("borough_MN", "seg_A")
        assert isinstance(paths, list)
        assert len(paths) > 0

    def test_no_paths_returns_empty_list(self, populated_graph):
        paths = populated_graph.find_all_paths("seg_A", "borough_MN")
        assert paths == []

    def test_paths_start_and_end_correctly(self, populated_graph):
        paths = populated_graph.find_all_paths("borough_MN", "seg_B")
        for path in paths:
            assert path[0] == "borough_MN"
            assert path[-1] == "seg_B"

# ---------------------------------------------------------------------------
# RelationshipGraph.get_transitive_closure
# ---------------------------------------------------------------------------

class TestGetTransitiveClosure:
    """Tests for RelationshipGraph.get_transitive_closure.

    NOTE: The source implementation contains a variable-shadowing bug on
    line 387 of relationships.py — the loop variable `entity_id` overwrites
    the `entity_id` parameter, so `visited.discard(entity_id)` removes the
    last-visited related entity rather than the original source.  These tests
    document actual (buggy) behaviour without modifying the source.
    """

    def test_closure_returns_set(self, populated_graph):
        """Closure always returns a set object."""
        reachable = populated_graph.get_transitive_closure("borough_MN")
        assert isinstance(reachable, set)

    def test_closure_includes_intermediate_nodes(self, populated_graph):
        """block_001 is reachable from borough_MN via CONTAINS."""
        reachable = populated_graph.get_transitive_closure("borough_MN")
        assert "block_001" in reachable

    def test_closure_includes_direct_child(self, populated_graph):
        """seg_A is reachable from block_001 via CONTAINS."""
        reachable = populated_graph.get_transitive_closure("block_001")
        assert "seg_A" in reachable

    def test_leaf_node_closure_empty_or_only_adjacent(self, graph):
        """A node with no outgoing edges produces an empty (or discarded-only) closure."""
        graph.add_relationship("a", "b", RelationshipType.CONTAINS)
        reachable = graph.get_transitive_closure("b")
        # b has no outgoing edges, so visited = {b}; discard("b") -> empty
        assert reachable == set()

    def test_filter_by_relationship_type_no_matching_edges(self, populated_graph):
        """Filtering by a type with no outgoing edges from source yields empty set."""
        # borough_MN only has CONTAINS outgoing edges, not REFERENCES
        reachable = populated_graph.get_transitive_closure(
            "borough_MN", relationship_type=RelationshipType.REFERENCES
        )
        assert reachable == set()

# ---------------------------------------------------------------------------
# RelationshipGraph.export_graph
# ---------------------------------------------------------------------------

class TestExportGraph:
    """Tests for RelationshipGraph.export_graph."""

    def test_empty_graph_export(self, graph):
        result = graph.export_graph()
        assert result["nodes"] == []
        assert result["edges"] == []
        assert result["node_count"] == 0
        assert result["edge_count"] == 0

    def test_nodes_include_all_entities(self, populated_graph):
        result = populated_graph.export_graph()
        nodes = set(result["nodes"])
        assert "borough_MN" in nodes
        assert "block_001" in nodes
        assert "seg_A" in nodes

    def test_edge_count_matches_relationships(self, populated_graph):
        result = populated_graph.export_graph()
        assert result["edge_count"] == 4

    def test_edge_structure(self, graph):
        graph.add_relationship(
            "s1", "t1", RelationshipType.CONTAINS,
            confidence=0.9, attributes={"key": "val"}
        )
        result = graph.export_graph()
        edge = result["edges"][0]
        assert edge["source"] == "s1"
        assert edge["target"] == "t1"
        assert edge["type"] == "contains"
        assert edge["confidence"] == pytest.approx(0.9)
        assert edge["attributes"] == {"key": "val"}

# ---------------------------------------------------------------------------
# RelationshipGraph.get_statistics
# ---------------------------------------------------------------------------

class TestGetStatistics:
    """Tests for RelationshipGraph.get_statistics."""

    def test_empty_graph_statistics(self, graph):
        stats = graph.get_statistics()
        assert stats["total_relationships"] == 0
        assert stats["total_entities"] == 0
        assert stats["avg_confidence"] == 0.0

    def test_populated_graph_statistics(self, populated_graph):
        stats = populated_graph.get_statistics()
        assert stats["total_relationships"] == 4
        assert stats["total_entities"] >= 4

    def test_relationship_types_listed(self, populated_graph):
        stats = populated_graph.get_statistics()
        assert "contains" in stats["relationship_types"]
        assert "adjacent_to" in stats["relationship_types"]

    def test_avg_confidence_default_one(self, graph):
        graph.add_relationship("a", "b", RelationshipType.PART_OF)
        graph.add_relationship("b", "c", RelationshipType.PART_OF)
        stats = graph.get_statistics()
        assert stats["avg_confidence"] == pytest.approx(1.0)

    def test_max_outgoing_degree(self, populated_graph):
        stats = populated_graph.get_statistics()
        assert stats["max_outgoing_degree"] >= 2

    def test_relationships_by_type_counts(self, graph):
        graph.add_relationship("a", "b", RelationshipType.CONTAINS)
        graph.add_relationship("a", "c", RelationshipType.CONTAINS)
        graph.add_relationship("a", "d", RelationshipType.REFERENCES)
        stats = graph.get_statistics()
        assert stats["relationships_by_type"]["contains"] == 2
        assert stats["relationships_by_type"]["references"] == 1
