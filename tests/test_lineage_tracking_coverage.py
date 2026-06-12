"""Tests for socrata_toolkit.lineage.tracking — decorators and context managers
for automatic lineage capture.

Covers:
- set_global_persistence
- track_transformation decorator (success, failure, row-count detection)
- lineage_context context manager (success, failure branch)
- register_ingestion_node
- register_sink_node
- register_validation_node
- get_tracked_node
- get_all_tracked_nodes

Each test resets the module-level globals (_lineage_nodes, _lineage_persistence)
via fixtures so tests are fully independent.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import socrata_toolkit.lineage.tracking as tracking_mod
from socrata_toolkit.lineage.core import (
    ExecutionStatus,
    NodeType,
    TransformationNode,
)
from socrata_toolkit.lineage.tracking import (
    get_all_tracked_nodes,
    get_tracked_node,
    lineage_context,
    register_ingestion_node,
    register_sink_node,
    register_validation_node,
    set_global_persistence,
    track_transformation,
)

# ---------------------------------------------------------------------------
# Fixtures — reset module globals before every test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_globals():
    """Ensure module-level lineage state is clean for each test."""
    tracking_mod._lineage_nodes.clear()
    tracking_mod._lineage_persistence = None
    yield
    tracking_mod._lineage_nodes.clear()
    tracking_mod._lineage_persistence = None

@pytest.fixture()
def mock_persistence():
    """A MagicMock that acts as a LineagePersistence instance."""
    return MagicMock()

# ---------------------------------------------------------------------------
# set_global_persistence
# ---------------------------------------------------------------------------

class TestSetGlobalPersistence:
    """Tests for set_global_persistence helper."""

    def test_sets_module_level_persistence(self, mock_persistence):
        """After the call, _lineage_persistence must point to the provided object."""
        set_global_persistence(mock_persistence)
        assert tracking_mod._lineage_persistence is mock_persistence

    def test_overrides_previous_value(self, mock_persistence):
        """Calling twice replaces the previous persistence instance."""
        set_global_persistence(mock_persistence)
        new_p = MagicMock()
        set_global_persistence(new_p)
        assert tracking_mod._lineage_persistence is new_p

    def test_accepts_none(self):
        """Passing None is a valid way to unset the global persistence."""
        set_global_persistence(None)
        assert tracking_mod._lineage_persistence is None

# ---------------------------------------------------------------------------
# track_transformation decorator
# ---------------------------------------------------------------------------

class TestTrackTransformation:
    """Tests for @track_transformation decorator."""

    def test_decorated_function_returns_result(self):
        """The decorator must not swallow the wrapped function's return value."""
        @track_transformation(inputs=["raw"], outputs=["clean"])
        def identity(x):
            return x * 2

        assert identity(5) == 10

    def test_node_registered_in_lineage_nodes(self):
        """After the first call, a node must be stored in _lineage_nodes."""
        @track_transformation(inputs=["raw"], outputs=["clean"], owner="eng@nyc.gov")
        def my_func():
            return []

        my_func()
        assert any("my_func" in k for k in tracking_mod._lineage_nodes)

    def test_node_has_correct_owner(self):
        """The node stored in _lineage_nodes must carry the provided owner."""
        @track_transformation(inputs=[], outputs=[], owner="owner@test.com")
        def func_with_owner():
            return None

        func_with_owner()
        node_id = next(k for k in tracking_mod._lineage_nodes if "func_with_owner" in k)
        assert tracking_mod._lineage_nodes[node_id].owner == "owner@test.com"

    def test_node_reused_on_second_call(self):
        """Calling the decorated function twice must not create duplicate nodes."""
        @track_transformation()
        def reused_func():
            return None

        reused_func()
        reused_func()
        matching = [k for k in tracking_mod._lineage_nodes if "reused_func" in k]
        assert len(matching) == 1

    def test_exception_in_wrapped_function_is_re_raised(self):
        """Exceptions from the wrapped function must propagate to the caller."""
        @track_transformation()
        def boom():
            raise ValueError("deliberate error")

        with pytest.raises(ValueError, match="deliberate error"):
            boom()

    def test_execution_recorded_on_failure(self):
        """Even when the function raises, an execution record should be appended."""
        @track_transformation()
        def failing():
            raise RuntimeError("oops")

        try:
            failing()
        except RuntimeError:
            pass

        node_id = next(k for k in tracking_mod._lineage_nodes if "failing" in k)
        node = tracking_mod._lineage_nodes[node_id]
        assert len(node.execution_history) == 1
        assert node.execution_history[0].status == ExecutionStatus.FAILED

    def test_output_rows_counted_for_list_result(self):
        """When the wrapped function returns a list, output_row_count is set."""
        @track_transformation()
        def returns_list():
            return [1, 2, 3]

        returns_list()
        node_id = next(k for k in tracking_mod._lineage_nodes if "returns_list" in k)
        node = tracking_mod._lineage_nodes[node_id]
        assert node.execution_history[-1].output_row_count == 3

    def test_persistence_save_node_called_on_first_execution(self, mock_persistence):
        """When persistence is set, save_node must be called for a new node."""
        set_global_persistence(mock_persistence)

        @track_transformation()
        def func_with_persistence():
            return None

        func_with_persistence()
        mock_persistence.save_node.assert_called_once()

    def test_persistence_save_execution_called(self, mock_persistence):
        """After execution, save_execution must be called on the persistence layer."""
        set_global_persistence(mock_persistence)

        @track_transformation()
        def func_exec():
            return None

        func_exec()
        mock_persistence.save_execution.assert_called_once()

    def test_tags_assigned_to_node(self):
        """Tags provided to the decorator must appear on the created node."""
        @track_transformation(tags=["daily", "production"])
        def tagged_func():
            return None

        tagged_func()
        node_id = next(k for k in tracking_mod._lineage_nodes if "tagged_func" in k)
        node = tracking_mod._lineage_nodes[node_id]
        assert "daily" in node.tags
        assert "production" in node.tags

# ---------------------------------------------------------------------------
# lineage_context context manager
# ---------------------------------------------------------------------------

class TestLineageContext:
    """Tests for lineage_context context manager."""

    def test_yields_tracking_info_dict(self):
        """The context manager must yield a dict with tracking metadata."""
        with lineage_context("test_ctx") as info:
            assert isinstance(info, dict)
            assert "node_id" in info
            assert "context_name" in info

    def test_node_id_prefixed_with_context(self):
        """node_id in the yielded dict must start with 'context.'."""
        with lineage_context("my_block") as info:
            assert info["node_id"].startswith("context.")
            assert "my_block" in info["node_id"]

    def test_context_name_in_tracking_info(self):
        """context_name in the yielded dict must match the argument."""
        with lineage_context("borough_agg") as info:
            assert info["context_name"] == "borough_agg"

    def test_exception_in_context_re_raises(self):
        """Exceptions inside the with-block must propagate out."""
        with pytest.raises(KeyError):
            with lineage_context("error_ctx"):
                raise KeyError("missing key")

    def test_persistence_save_execution_called_on_success(self, mock_persistence):
        """On successful completion, save_execution must be called."""
        set_global_persistence(mock_persistence)
        with lineage_context("ctx_persist"):
            pass
        mock_persistence.save_execution.assert_called_once()

    def test_persistence_save_execution_called_on_failure(self, mock_persistence):
        """Even on failure, save_execution must be called."""
        set_global_persistence(mock_persistence)
        try:
            with lineage_context("ctx_fail"):
                raise ValueError("boom")
        except ValueError:
            pass
        mock_persistence.save_execution.assert_called_once()

    def test_inputs_and_outputs_stored_on_node(self, mock_persistence):
        """Inputs and outputs passed to lineage_context must be on the saved node."""
        set_global_persistence(mock_persistence)
        with lineage_context("agg", inputs=["raw"], outputs=["summary"]):
            pass
        saved_node: TransformationNode = mock_persistence.save_node.call_args[0][0]
        assert "raw" in saved_node.input_datasets
        assert "summary" in saved_node.output_datasets

# ---------------------------------------------------------------------------
# register_ingestion_node
# ---------------------------------------------------------------------------

class TestRegisterIngestionNode:
    """Tests for register_ingestion_node."""

    def test_returns_transformation_node(self):
        """Must return a TransformationNode instance."""
        node = register_ingestion_node("violations", "Violations Dataset")
        assert isinstance(node, TransformationNode)

    def test_node_id_prefixed_with_ingest(self):
        """Node ID must be prefixed with 'ingest.'."""
        node = register_ingestion_node("violations", "Violations")
        assert node.node_id.startswith("ingest.")

    def test_node_type_is_ingestion(self):
        """Node type must be NodeType.INGESTION."""
        node = register_ingestion_node("ds", "Dataset")
        assert node.node_type == NodeType.INGESTION

    def test_node_stored_in_global_dict(self):
        """Registered node must appear in _lineage_nodes."""
        node = register_ingestion_node("inspections", "Inspections")
        assert node.node_id in tracking_mod._lineage_nodes

    def test_tags_include_source_name(self):
        """Node tags must include 'ingestion' and the source system."""
        node = register_ingestion_node("d", "D", source="socrata")
        assert "ingestion" in node.tags
        assert "socrata" in node.tags

    def test_schema_version_stored(self):
        """Provided schema_version must be stored on the node."""
        node = register_ingestion_node("d", "D", schema_version="v2.0")
        assert node.schema_version == "v2.0"

    def test_persistence_save_called(self, mock_persistence):
        """When persistence is set, save_node must be called."""
        set_global_persistence(mock_persistence)
        register_ingestion_node("ds", "Dataset")
        mock_persistence.save_node.assert_called_once()

# ---------------------------------------------------------------------------
# register_sink_node
# ---------------------------------------------------------------------------

class TestRegisterSinkNode:
    """Tests for register_sink_node."""

    def test_returns_transformation_node(self):
        """Must return a TransformationNode."""
        node = register_sink_node("pg_violations", "PG Violations", "postgres", [])
        assert isinstance(node, TransformationNode)

    def test_node_id_prefixed_with_sink(self):
        """Node ID must be prefixed with 'sink.'."""
        node = register_sink_node("pg", "PG", "postgres", [])
        assert node.node_id.startswith("sink.")

    def test_node_type_is_sink(self):
        """Node type must be NodeType.SINK."""
        node = register_sink_node("pg", "PG", "postgres", [])
        assert node.node_type == NodeType.SINK

    def test_input_datasets_stored(self):
        """Provided input_datasets must appear on the node."""
        node = register_sink_node("pg", "PG", "postgres", ["raw", "staging"])
        assert "raw" in node.input_datasets
        assert "staging" in node.input_datasets

    def test_sink_stored_in_global_dict(self):
        """Sink node must be stored in _lineage_nodes."""
        node = register_sink_node("dw", "DW", "parquet", [])
        assert node.node_id in tracking_mod._lineage_nodes

# ---------------------------------------------------------------------------
# register_validation_node
# ---------------------------------------------------------------------------

class TestRegisterValidationNode:
    """Tests for register_validation_node."""

    def test_returns_transformation_node(self):
        """Must return a TransformationNode."""
        node = register_validation_node("val-001", "Completeness Check", "violations")
        assert isinstance(node, TransformationNode)

    def test_node_id_prefixed_with_validate(self):
        """Node ID must be prefixed with 'validate.'."""
        node = register_validation_node("val-001", "Check", "violations")
        assert node.node_id.startswith("validate.")

    def test_node_type_is_validation(self):
        """Node type must be NodeType.VALIDATION."""
        node = register_validation_node("v", "V", "d")
        assert node.node_type == NodeType.VALIDATION

    def test_input_dataset_recorded(self):
        """input_dataset must appear in the node's input_datasets list."""
        node = register_validation_node("v", "V", "violations_raw")
        assert "violations_raw" in node.input_datasets

    def test_rules_stored_in_configuration(self):
        """Validation rules must be accessible in node.configuration."""
        rules = {"null_threshold": 0.05}
        node = register_validation_node("v", "V", "d", rules=rules)
        assert node.configuration.get("rules") == rules

# ---------------------------------------------------------------------------
# get_tracked_node / get_all_tracked_nodes
# ---------------------------------------------------------------------------

class TestGetTrackedNodes:
    """Tests for query helpers."""

    def test_get_tracked_node_returns_none_for_unknown(self):
        """Querying a node ID not yet registered returns None."""
        assert get_tracked_node("nonexistent") is None

    def test_get_tracked_node_returns_registered_node(self):
        """After registration, get_tracked_node returns the stored node."""
        node = register_ingestion_node("ds", "Dataset")
        assert get_tracked_node(node.node_id) is node

    def test_get_all_tracked_nodes_returns_copy(self):
        """get_all_tracked_nodes must return a copy, not the live dict."""
        register_ingestion_node("ds1", "Dataset 1")
        all_nodes = get_all_tracked_nodes()
        assert isinstance(all_nodes, dict)
        # Mutating the returned copy must not affect the module-level dict
        all_nodes["phantom"] = MagicMock()
        assert "phantom" not in tracking_mod._lineage_nodes

    def test_get_all_tracked_nodes_includes_all_registered(self):
        """All registered nodes (ingestion, sink, validation) must appear."""
        n1 = register_ingestion_node("ds", "DS")
        n2 = register_sink_node("sk", "SK", "postgres", [])
        n3 = register_validation_node("vl", "VL", "ds")
        all_nodes = get_all_tracked_nodes()
        assert n1.node_id in all_nodes
        assert n2.node_id in all_nodes
        assert n3.node_id in all_nodes
