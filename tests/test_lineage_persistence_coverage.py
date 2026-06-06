"""Tests for socrata_toolkit.lineage.persistence — LineagePersistence CRUD layer.

All database calls are intercepted by unittest.mock so no real PostgreSQL
connection is required.  The tests cover:

- save_node (insert and update branches)
- get_node (found and not-found paths)
- save_edge
- get_edges (unfiltered, source-filtered, target-filtered)
- save_execution
- get_execution_history
- delete_node (found and not-found)
- export_dag (json, mermaid, unknown format)
- load_dag
- _dag_to_mermaid (via export_dag)
- error / rollback paths

psycopg is mocked at the module level so the import guard in persistence.py
does not prevent the class from being instantiated.
"""
from __future__ import annotations

import json

# Patch psycopg before importing the module under test
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

_psycopg_mock = MagicMock()
sys.modules.setdefault("psycopg", _psycopg_mock)

from socrata_toolkit.lineage.core import (  # noqa: E402
    DAG,
    EdgeType,
    ExecutionRecord,
    ExecutionStatus,
    LineageEdge,
    NodeType,
    TransformationNode,
)

# ---------------------------------------------------------------------------
# Helpers to build mock cursors / connections
# ---------------------------------------------------------------------------

def _make_cursor(fetchone_result=None, fetchall_result=None):
    """Return a MagicMock cursor with configurable fetch results."""
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchone.return_value = fetchone_result
    cur.fetchall.return_value = fetchall_result or []
    return cur


def _make_conn(cursor: MagicMock):
    """Return a MagicMock connection that yields the given cursor."""
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cursor
    return conn


def _make_node(node_id: str = "node-001", name: str = "Test Node") -> TransformationNode:
    """Build a minimal TransformationNode."""
    return TransformationNode(
        node_id=node_id,
        name=name,
        node_type=NodeType.TRANSFORMATION,
        owner="test@example.com",
    )


def _make_edge(src: str = "n1", tgt: str = "n2") -> LineageEdge:
    """Build a minimal LineageEdge."""
    return LineageEdge(
        source_node_id=src,
        target_node_id=tgt,
        edge_type=EdgeType.DATA_FLOW,
    )


def _make_execution(node_id: str = "node-001") -> ExecutionRecord:
    """Build a minimal ExecutionRecord."""
    return ExecutionRecord(
        node_id=node_id,
        status=ExecutionStatus.SUCCESS,
        input_row_count=100,
        output_row_count=90,
    )


# ---------------------------------------------------------------------------
# Import persistence using the patched psycopg
# ---------------------------------------------------------------------------

with patch.dict("sys.modules", {"psycopg": _psycopg_mock}):
    from socrata_toolkit.lineage.persistence import LineagePersistence  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_conn():
    """Fresh mock connection for each test."""
    return MagicMock()


@pytest.fixture()
def persistence(mock_conn):
    """LineagePersistence backed by a mock connection."""
    return LineagePersistence(db_connection=mock_conn)


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestLineagePersistenceInit:
    """Verify basic initialisation behaviour."""

    def test_stores_connection(self, mock_conn):
        """The injected connection must be stored as self.conn."""
        p = LineagePersistence(db_connection=mock_conn)
        assert p.conn is mock_conn

    def test_none_connection_stored(self):
        """None connection is accepted (methods will short-circuit)."""
        p = LineagePersistence(db_connection=None)
        assert p.conn is None


# ---------------------------------------------------------------------------
# save_node
# ---------------------------------------------------------------------------

class TestSaveNode:
    """Tests for LineagePersistence.save_node."""

    def test_save_new_node_returns_node_id(self, persistence, mock_conn):
        """Inserting a new node must return its node_id."""
        cur = _make_cursor(fetchone_result=None)  # node does not exist
        mock_conn.cursor.return_value = cur
        node = _make_node()
        result = persistence.save_node(node)
        assert result == node.node_id

    def test_save_existing_node_returns_node_id(self, persistence, mock_conn):
        """Updating an existing node must return its node_id."""
        cur = _make_cursor(fetchone_result=(1,))  # node exists
        mock_conn.cursor.return_value = cur
        node = _make_node()
        result = persistence.save_node(node)
        assert result == node.node_id

    def test_save_node_commits(self, persistence, mock_conn):
        """A successful save_node must commit the transaction."""
        cur = _make_cursor(fetchone_result=None)
        mock_conn.cursor.return_value = cur
        persistence.save_node(_make_node())
        mock_conn.commit.assert_called_once()

    def test_save_node_no_conn_raises_runtime_error(self):
        """save_node with no connection must raise RuntimeError."""
        p = LineagePersistence(db_connection=None)
        with pytest.raises(RuntimeError, match="No database connection"):
            p.save_node(_make_node())

    def test_save_node_db_error_raises_runtime_error(self, persistence, mock_conn):
        """A database exception must be wrapped as RuntimeError."""
        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.execute.side_effect = Exception("DB error")
        mock_conn.cursor.return_value = cur
        with pytest.raises(RuntimeError):
            persistence.save_node(_make_node())

    def test_save_node_rollback_on_error(self, persistence, mock_conn):
        """A failed save_node must roll back the connection."""
        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.execute.side_effect = Exception("DB error")
        mock_conn.cursor.return_value = cur
        try:
            persistence.save_node(_make_node())
        except RuntimeError:
            pass
        mock_conn.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# get_node
# ---------------------------------------------------------------------------

class TestGetNode:
    """Tests for LineagePersistence.get_node."""

    def test_get_node_not_found_returns_none(self, persistence, mock_conn):
        """When the DB returns no row, get_node must return None."""
        cur = _make_cursor(fetchone_result=None, fetchall_result=[])
        mock_conn.cursor.return_value = cur
        result = persistence.get_node("missing-id")
        assert result is None

    def test_get_node_no_conn_returns_none(self):
        """With no connection get_node must return None."""
        p = LineagePersistence(db_connection=None)
        assert p.get_node("any") is None

    def test_get_node_found_returns_transformation_node(self, persistence, mock_conn):
        """A found DB row must be hydrated into a TransformationNode."""
        now = datetime.now(timezone.utc)
        row = (
            "node-001", "My Node", "transformation",
            "desc", "owner@example.com",
            now, now,
            json.dumps({}), "v1", json.dumps(["tag1"]),
        )
        cur = _make_cursor(fetchone_result=row, fetchall_result=[])
        mock_conn.cursor.return_value = cur
        result = persistence.get_node("node-001")
        assert result is not None
        assert result.node_id == "node-001"
        assert result.name == "My Node"

    def test_get_node_db_error_returns_none(self, persistence, mock_conn):
        """A database error during get_node must return None (not raise)."""
        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.execute.side_effect = Exception("timeout")
        mock_conn.cursor.return_value = cur
        result = persistence.get_node("node-001")
        assert result is None


# ---------------------------------------------------------------------------
# save_edge
# ---------------------------------------------------------------------------

class TestSaveEdge:
    """Tests for LineagePersistence.save_edge."""

    def test_save_edge_commits(self, persistence, mock_conn):
        """A successful save_edge must commit."""
        cur = _make_cursor()
        mock_conn.cursor.return_value = cur
        persistence.save_edge(_make_edge())
        mock_conn.commit.assert_called_once()

    def test_save_edge_no_conn_raises(self):
        """save_edge with no connection must raise RuntimeError."""
        p = LineagePersistence(db_connection=None)
        with pytest.raises(RuntimeError):
            p.save_edge(_make_edge())

    def test_save_edge_db_error_rolls_back(self, persistence, mock_conn):
        """A DB exception during save_edge must roll back."""
        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.execute.side_effect = Exception("constraint")
        mock_conn.cursor.return_value = cur
        try:
            persistence.save_edge(_make_edge())
        except RuntimeError:
            pass
        mock_conn.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# get_edges
# ---------------------------------------------------------------------------

class TestGetEdges:
    """Tests for LineagePersistence.get_edges."""

    def _make_edge_row(self, src="n1", tgt="n2"):
        """Return a raw DB row tuple for a LineageEdge."""
        now = datetime.now(timezone.utc)
        return (src, tgt, "data_flow", "1:1", json.dumps([]), None, now)

    def test_get_edges_no_conn_returns_empty(self):
        """With no connection get_edges must return an empty list."""
        p = LineagePersistence(db_connection=None)
        assert p.get_edges() == []

    def test_get_edges_unfiltered_returns_all(self, persistence, mock_conn):
        """Without filters all edge rows are returned."""
        rows = [self._make_edge_row("n1", "n2"), self._make_edge_row("n2", "n3")]
        cur = _make_cursor(fetchall_result=rows)
        mock_conn.cursor.return_value = cur
        edges = persistence.get_edges()
        assert len(edges) == 2

    def test_get_edges_source_filter(self, persistence, mock_conn):
        """source_id filter is appended to the query."""
        rows = [self._make_edge_row("n1", "n2")]
        cur = _make_cursor(fetchall_result=rows)
        mock_conn.cursor.return_value = cur
        edges = persistence.get_edges(source_id="n1")
        assert len(edges) == 1
        assert edges[0].source_node_id == "n1"

    def test_get_edges_target_filter(self, persistence, mock_conn):
        """target_id filter is appended to the query."""
        rows = [self._make_edge_row("n1", "n2")]
        cur = _make_cursor(fetchall_result=rows)
        mock_conn.cursor.return_value = cur
        edges = persistence.get_edges(target_id="n2")
        assert len(edges) == 1
        assert edges[0].target_node_id == "n2"

    def test_get_edges_db_error_returns_empty(self, persistence, mock_conn):
        """A DB error during get_edges must return an empty list."""
        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.execute.side_effect = Exception("error")
        mock_conn.cursor.return_value = cur
        result = persistence.get_edges()
        assert result == []


# ---------------------------------------------------------------------------
# save_execution
# ---------------------------------------------------------------------------

class TestSaveExecution:
    """Tests for LineagePersistence.save_execution."""

    def test_save_execution_returns_execution_id(self, persistence, mock_conn):
        """save_execution must return the execution_id."""
        cur = _make_cursor()
        mock_conn.cursor.return_value = cur
        rec = _make_execution()
        result = persistence.save_execution(rec)
        assert result == rec.execution_id

    def test_save_execution_commits(self, persistence, mock_conn):
        """A successful save_execution must commit."""
        cur = _make_cursor()
        mock_conn.cursor.return_value = cur
        persistence.save_execution(_make_execution())
        mock_conn.commit.assert_called_once()

    def test_save_execution_no_conn_raises(self):
        """save_execution with no connection must raise RuntimeError."""
        p = LineagePersistence(db_connection=None)
        with pytest.raises(RuntimeError):
            p.save_execution(_make_execution())

    def test_save_execution_db_error_rolls_back(self, persistence, mock_conn):
        """A DB exception must cause rollback and raise RuntimeError."""
        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.execute.side_effect = Exception("insert error")
        mock_conn.cursor.return_value = cur
        with pytest.raises(RuntimeError):
            persistence.save_execution(_make_execution())
        mock_conn.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# get_execution_history
# ---------------------------------------------------------------------------

class TestGetExecutionHistory:
    """Tests for LineagePersistence.get_execution_history."""

    def _make_exec_row(self, node_id: str = "node-001"):
        """Return a raw DB row tuple for an ExecutionRecord."""
        now = datetime.now(timezone.utc)
        return (
            "exec-001", node_id, now, now,
            1.5, "success", 100, 90,
            None, json.dumps({}), "system", None,
        )

    def test_no_conn_returns_empty(self):
        """With no connection get_execution_history returns []."""
        p = LineagePersistence(db_connection=None)
        assert p.get_execution_history("n") == []

    def test_returns_list_of_execution_records(self, persistence, mock_conn):
        """Rows are hydrated into ExecutionRecord objects."""
        rows = [self._make_exec_row()]
        cur = _make_cursor(fetchall_result=rows)
        mock_conn.cursor.return_value = cur
        records = persistence.get_execution_history("node-001")
        assert len(records) == 1
        assert records[0].node_id == "node-001"
        assert records[0].status == ExecutionStatus.SUCCESS

    def test_limit_parameter_forwarded(self, persistence, mock_conn):
        """The limit parameter is passed to the SQL query."""
        cur = _make_cursor(fetchall_result=[])
        mock_conn.cursor.return_value = cur
        persistence.get_execution_history("n", limit=5)
        args = cur.execute.call_args[0]
        assert 5 in args[1]

    def test_db_error_returns_empty(self, persistence, mock_conn):
        """A DB exception during history fetch returns an empty list."""
        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.execute.side_effect = Exception("timeout")
        mock_conn.cursor.return_value = cur
        result = persistence.get_execution_history("n")
        assert result == []


# ---------------------------------------------------------------------------
# delete_node
# ---------------------------------------------------------------------------

class TestDeleteNode:
    """Tests for LineagePersistence.delete_node."""

    def test_delete_existing_node_returns_true(self, persistence, mock_conn):
        """Deleting a node that exists must return True."""
        cur = _make_cursor(fetchone_result=(1, "node-001", "transformation"))
        mock_conn.cursor.return_value = cur
        result = persistence.delete_node("node-001")
        assert result is True

    def test_delete_missing_node_returns_false(self, persistence, mock_conn):
        """Deleting a node that does not exist must return False."""
        cur = _make_cursor(fetchone_result=None)
        mock_conn.cursor.return_value = cur
        result = persistence.delete_node("missing")
        assert result is False

    def test_delete_no_conn_returns_false(self):
        """delete_node with no connection returns False."""
        p = LineagePersistence(db_connection=None)
        assert p.delete_node("n") is False

    def test_delete_commits(self, persistence, mock_conn):
        """A successful delete_node must commit."""
        cur = _make_cursor(fetchone_result=("x",))
        mock_conn.cursor.return_value = cur
        persistence.delete_node("node-001")
        mock_conn.commit.assert_called_once()

    def test_delete_db_error_rolls_back(self, persistence, mock_conn):
        """A DB exception during delete must roll back and return False."""
        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.execute.side_effect = Exception("fk constraint")
        mock_conn.cursor.return_value = cur
        result = persistence.delete_node("node-001")
        assert result is False
        mock_conn.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# export_dag
# ---------------------------------------------------------------------------

class TestExportDag:
    """Tests for LineagePersistence.export_dag."""

    def test_export_dag_no_conn_returns_empty_string(self):
        """With no connection export_dag returns an empty string."""
        p = LineagePersistence(db_connection=None)
        assert p.export_dag() == ""

    def test_export_dag_json_format(self, persistence, mock_conn):
        """JSON export of an empty DAG must be valid JSON."""
        cur = _make_cursor(fetchone_result=None, fetchall_result=[])
        mock_conn.cursor.return_value = cur
        result = persistence.export_dag(format="json")
        parsed = json.loads(result)
        assert "nodes" in parsed or isinstance(parsed, dict)

    def test_export_dag_mermaid_format(self, persistence, mock_conn):
        """Mermaid export must include 'graph TD' header."""
        cur = _make_cursor(fetchone_result=None, fetchall_result=[])
        mock_conn.cursor.return_value = cur
        result = persistence.export_dag(format="mermaid")
        assert "graph TD" in result

    def test_export_dag_unknown_format_raises(self, persistence, mock_conn):
        """An unrecognised format raises ValueError (caught → empty string)."""
        cur = _make_cursor(fetchone_result=None, fetchall_result=[])
        mock_conn.cursor.return_value = cur
        result = persistence.export_dag(format="xlsx")
        assert result == ""


# ---------------------------------------------------------------------------
# load_dag
# ---------------------------------------------------------------------------

class TestLoadDag:
    """Tests for LineagePersistence.load_dag."""

    def test_load_dag_no_conn_returns_dag(self):
        """With no connection load_dag must return an empty DAG instance."""
        p = LineagePersistence(db_connection=None)
        dag = p.load_dag()
        assert isinstance(dag, DAG)
        assert len(dag.nodes) == 0

    def test_load_dag_empty_db_returns_empty_dag(self, persistence, mock_conn):
        """An empty database produces an empty DAG."""
        cur = _make_cursor(fetchone_result=None, fetchall_result=[])
        mock_conn.cursor.return_value = cur
        dag = persistence.load_dag()
        assert isinstance(dag, DAG)
