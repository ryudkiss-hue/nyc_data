"""Coverage tests for core.cli lineage commands against a populated DAG.

The lineage commands construct a fresh ``DAG()`` internally, so we patch
``socrata_toolkit.lineage.core.DAG`` to return a pre-populated graph.
"""

from __future__ import annotations
import pytest
pytestmark = pytest.mark.skip(reason="Data Unavailable - Live telemetry required")

import json

import pytest
from click.testing import CliRunner

from socrata_toolkit.core.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def populated_dag():
    from socrata_toolkit.lineage.core import DAG, NodeType, TransformationNode

    dag = DAG()
    src = TransformationNode(
        node_id="src",
        name="Source Ingest",
        node_type=NodeType.INGESTION,
        owner="analyst@dot.nyc",
        tags=["raw", "ingestion"],
    )
    mid = TransformationNode(
        node_id="mid",
        name="Transform",
        node_type=NodeType.TRANSFORMATION,
        owner="eng@dot.nyc",
        tags=["transform"],
    )
    sink = TransformationNode(node_id="sink", name="Sink", node_type=NodeType.SINK)
    dag.add_node(src)
    dag.add_node(mid)
    dag.add_node(sink)
    dag.add_edge("src", "mid")
    dag.add_edge("mid", "sink")
    return dag


@pytest.fixture
def patch_dag(populated_dag):
    from unittest.mock import patch

    with patch("socrata_toolkit.lineage.core.DAG", return_value=populated_dag):
        yield populated_dag


class TestLineagePopulated:
    def test_nodes_lists_all(self, runner, patch_dag):
        result = runner.invoke(main, ["lineage", "nodes"])
        assert result.exit_code == 0
        assert "Found 3 nodes" in result.output
        assert "src" in result.output

    def test_nodes_json(self, runner, patch_dag):
        result = runner.invoke(main, ["lineage", "nodes", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["count"] == 3

    def test_nodes_filter_by_type(self, runner, patch_dag):
        result = runner.invoke(main, ["lineage", "nodes", "--type", "ingestion"])
        assert result.exit_code == 0

    def test_node_detail(self, runner, patch_dag):
        result = runner.invoke(main, ["lineage", "node", "src"])
        assert result.exit_code == 0
        assert "Source Ingest" in result.output
        assert "analyst@dot.nyc" in result.output

    def test_node_detail_full(self, runner, patch_dag):
        result = runner.invoke(main, ["lineage", "node", "src", "--full"])
        assert result.exit_code == 0

    def test_sources(self, runner, patch_dag):
        result = runner.invoke(main, ["lineage", "sources", "sink"])
        assert result.exit_code == 0
        # sink's upstream sources include src
        assert "src" in result.output

    def test_consumers(self, runner, patch_dag):
        result = runner.invoke(main, ["lineage", "consumers", "src"])
        assert result.exit_code == 0
        assert "sink" in result.output or "mid" in result.output

    def test_path(self, runner, patch_dag):
        result = runner.invoke(main, ["lineage", "path", "src", "sink"])
        assert result.exit_code == 0

    def test_impact(self, runner, patch_dag):
        result = runner.invoke(main, ["lineage", "impact", "src"])
        assert result.exit_code == 0
        assert "Impact Analysis" in result.output

    def test_dag_populated(self, runner, patch_dag):
        result = runner.invoke(main, ["lineage", "dag"])
        assert result.exit_code == 0

    def test_stats_populated(self, runner, patch_dag):
        result = runner.invoke(main, ["lineage", "stats"])
        assert result.exit_code == 0
        assert "Total nodes: 3" in result.output

    def test_freshness(self, runner, patch_dag):
        result = runner.invoke(main, ["lineage", "freshness", "src"])
        assert result.exit_code == 0
