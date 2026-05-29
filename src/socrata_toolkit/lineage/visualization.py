"""Visualization and export utilities for data lineage DAGs.

Exports lineage in multiple formats for visualization tools and analysis:
- JSON: Complete lineage dump with all metadata
- GraphML: For Gephi, yEd, and other graph visualization tools
- Mermaid: For GitHub/markdown rendering
- DOT: Graphviz format for custom visualization
- ASCII: Terminal-friendly DAG visualization

Classes:
    LineageVisualizer: Main visualization interface
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class LineageVisualizer:
    """Exports lineage in multiple formats for visualization and analysis."""

    def __init__(self, dag: Any | None = None) -> None:
        """Initialize visualizer.

        Args:
            dag: DAG object to visualize (LineageCore.DAG)
        """
        self.dag = dag

    def to_json(self, indent: bool = True) -> str:
        """Export complete DAG as JSON.

        Includes all nodes, edges, execution history, and metadata.
        This is the most complete export format.

        Args:
            indent: Whether to pretty-print JSON

        Returns:
            JSON string representation of DAG
        """
        if not self.dag:
            return "{}"

        dag_dict = self.dag.to_dict()
        return json.dumps(dag_dict, indent=2 if indent else None, default=str)

    def to_graphml(self) -> str:
        """Export DAG as GraphML for visualization tools.

        GraphML can be imported into tools like Gephi, yEd, and others
        for interactive graph visualization and analysis.

        Returns:
            GraphML XML string
        """
        if not self.dag:
            return ""

        try:
            import networkx as nx
            graphml = nx.to_string(self.dag.graph, format="graphml")  # type: ignore
            return graphml
        except Exception as e:
            logger.error(f"Failed to export to GraphML: {e}")
            return ""

    def to_mermaid(self, subgraph_node_id: str | None = None) -> str:
        """Export DAG as Mermaid diagram syntax.

        Mermaid diagrams can be embedded in GitHub README files and markdown.
        Useful for documentation and analysis.

        Args:
            subgraph_node_id: If specified, only show this node and its connections

        Returns:
            Mermaid diagram syntax
        """
        if not self.dag:
            return "graph TD"

        lines = ["graph TD"]

        if subgraph_node_id:
            # Show node and its neighbors only
            node_ids = {subgraph_node_id}

            # Add upstream dependencies
            for upstream in self.dag.get_upstream_dependencies(subgraph_node_id):
                node_ids.add(upstream)

            # Add downstream consumers
            for downstream in self.dag.get_downstream_consumers(subgraph_node_id):
                node_ids.add(downstream)

            # Find edges between these nodes
            for (source, target) in self.dag.edges.keys():
                if source in node_ids and target in node_ids:
                    lines.append(f"    {self._sanitize_id(source)} --> {self._sanitize_id(target)}")
        else:
            # Show all edges
            for (source, target) in self.dag.edges.keys():
                lines.append(f"    {self._sanitize_id(source)} --> {self._sanitize_id(target)}")

        return "\n".join(lines)

    def to_dot(self) -> str:
        """Export DAG as Graphviz DOT format.

        DOT files can be rendered using Graphviz tools (dot, neato, etc.)
        for custom graph visualization.

        Returns:
            DOT format string
        """
        if not self.dag:
            return "digraph G {}"

        try:
            import networkx as nx
            return nx.to_string(self.dag.graph, format="dot")  # type: ignore
        except Exception as e:
            logger.error(f"Failed to export to DOT: {e}")
            return "digraph G {}"

    def to_ascii(self, max_depth: int = 5) -> str:
        """Generate ASCII visualization of DAG.

        Shows the DAG in a text-friendly format suitable for terminal output.
        Useful for quick inspection and debugging.

        Args:
            max_depth: Maximum depth to display (limits recursion)

        Returns:
            ASCII art representation of DAG
        """
        if not self.dag or not self.dag.nodes:
            return "Empty DAG"

        output = []
        output.append("=" * 80)
        output.append("DATA LINEAGE DAG - ASCII VISUALIZATION")
        output.append("=" * 80)
        output.append("")

        # Find root nodes (no inputs)
        root_nodes = [
            nid for nid, node in self.dag.nodes.items()
            if node.node_type.value == "ingestion" or not node.input_datasets
        ]

        for root_id in root_nodes[:10]:  # Limit to 10 roots for clarity
            output.append(f"Root: {root_id}")
            output.extend(self._ascii_subtree(root_id, depth=0, max_depth=max_depth))
            output.append("")

        output.append("=" * 80)
        output.append(f"Total Nodes: {len(self.dag.nodes)}")
        output.append(f"Total Edges: {len(self.dag.edges)}")
        output.append("=" * 80)

        return "\n".join(output)

    def to_html_table(self) -> str:
        """Export DAG as HTML table for web display.

        Returns:
            HTML table representation of nodes and edges
        """
        if not self.dag:
            return "<p>Empty DAG</p>"

        html = []
        html.append("<h2>Data Lineage DAG</h2>")

        # Nodes table
        html.append("<h3>Transformation Nodes</h3>")
        html.append("<table border='1' cellpadding='10'>")
        html.append("<tr>")
        html.append("<th>Node ID</th><th>Name</th><th>Type</th><th>Owner</th>")
        html.append("<th>Inputs</th><th>Outputs</th>")
        html.append("</tr>")

        for node_id, node in self.dag.nodes.items():
            html.append("<tr>")
            html.append(f"<td>{node_id}</td>")
            html.append(f"<td>{node.name}</td>")
            html.append(f"<td>{node.node_type.value}</td>")
            html.append(f"<td>{node.owner}</td>")
            html.append(f"<td>{', '.join(node.input_datasets)}</td>")
            html.append(f"<td>{', '.join(node.output_datasets)}</td>")
            html.append("</tr>")

        html.append("</table>")

        # Edges table
        html.append("<h3>Data Dependencies</h3>")
        html.append("<table border='1' cellpadding='10'>")
        html.append("<tr>")
        html.append("<th>Source</th><th>Target</th><th>Type</th><th>Cardinality</th>")
        html.append("</tr>")

        for (source, target), edge in self.dag.edges.items():
            html.append("<tr>")
            html.append(f"<td>{source}</td>")
            html.append(f"<td>{target}</td>")
            html.append(f"<td>{edge.edge_type.value}</td>")
            html.append(f"<td>{edge.cardinality}</td>")
            html.append("</tr>")

        html.append("</table>")

        return "\n".join(html)

    def get_subgraph(self, node_id: str, include_downstream: bool = True) -> Any | None:
        """Extract a subgraph containing a node and related nodes.

        Args:
            node_id: Central node
            include_downstream: If True, include downstream consumers; else include only upstream

        Returns:
            Subgraph DAG or None if node doesn't exist
        """
        if not self.dag or node_id not in self.dag.nodes:
            return None

        try:
            from .core import DAG
            subgraph = DAG()

            # Add central node
            node = self.dag.get_node(node_id)
            if node:
                subgraph.add_node(node)

            # Add upstream dependencies
            for upstream_id in self.dag.get_upstream_dependencies(node_id):
                upstream_node = self.dag.get_node(upstream_id)
                if upstream_node:
                    subgraph.add_node(upstream_node)

            # Optionally add downstream consumers
            if include_downstream:
                for downstream_id in self.dag.get_downstream_consumers(node_id):
                    downstream_node = self.dag.get_node(downstream_id)
                    if downstream_node:
                        subgraph.add_node(downstream_node)

            # Add edges between nodes in subgraph
            for (source, target), edge in self.dag.edges.items():
                if source in subgraph.nodes and target in subgraph.nodes:
                    subgraph.add_edge(
                        source, target,
                        edge_type=edge.edge_type,
                        cardinality=edge.cardinality,
                        join_keys=edge.join_keys,
                        filter_conditions=edge.filter_conditions,
                    )

            return subgraph
        except Exception as e:
            logger.error(f"Failed to extract subgraph: {e}")
            return None

    def get_lineage_summary_by_type(self) -> dict[str, list[str]]:
        """Get summary of nodes grouped by type.

        Returns:
            Dictionary mapping node types to lists of node IDs
        """
        if not self.dag:
            return {}

        summary: dict[str, list[str]] = {}

        for node_id, node in self.dag.nodes.items():
            node_type = node.node_type.value
            if node_type not in summary:
                summary[node_type] = []
            summary[node_type].append(node_id)

        return summary

    def get_execution_summary(self) -> dict[str, Any]:
        """Get summary of recent executions across all nodes.

        Returns:
            Dictionary with execution statistics
        """
        if not self.dag:
            return {}

        summary = {
            "total_executions": 0,
            "successful": 0,
            "failed": 0,
            "total_rows_processed": 0,
            "average_duration_seconds": 0.0,
            "nodes_with_failures": [],
            "latest_executions": [],
        }

        total_duration = 0.0
        execution_count = 0

        for node_id, node in self.dag.nodes.items():
            if not node.execution_history:
                continue

            for execution in node.execution_history:
                summary["total_executions"] += 1
                execution_count += 1

                if execution.status.value == "success":
                    summary["successful"] += 1
                elif execution.status.value == "failed":
                    summary["failed"] += 1
                    if node_id not in summary["nodes_with_failures"]:
                        summary["nodes_with_failures"].append(node_id)

                summary["total_rows_processed"] += execution.output_row_count
                total_duration += execution.duration_seconds

                # Capture latest executions
                summary["latest_executions"].append({
                    "node_id": node_id,
                    "execution_id": execution.execution_id,
                    "timestamp": execution.started_at.isoformat() if execution.started_at else None,
                    "status": execution.status.value,
                    "duration": execution.duration_seconds,
                })

        # Calculate average
        if execution_count > 0:
            summary["average_duration_seconds"] = total_duration / execution_count

        # Sort and limit latest executions
        summary["latest_executions"].sort(
            key=lambda x: x["timestamp"] or "", reverse=True
        )
        summary["latest_executions"] = summary["latest_executions"][:20]

        return summary

    def _sanitize_id(self, node_id: str) -> str:
        """Sanitize node ID for use in Mermaid/DOT format."""
        return node_id.replace(".", "_").replace("-", "_")

    def _ascii_subtree(
        self, node_id: str, depth: int = 0, max_depth: int = 5, visited: set[str] | None = None
    ) -> list[str]:
        """Generate ASCII representation of node subtree."""
        if visited is None:
            visited = set()

        if depth > max_depth or node_id in visited:
            return []

        visited.add(node_id)
        lines = []
        indent = "  " * depth
        prefix = "├─ " if depth > 0 else ""

        node = self.dag.get_node(node_id) if self.dag else None
        if node:
            node_type = node.node_type.value
            lines.append(f"{indent}{prefix}{node_id} ({node_type})")

            # Add downstream consumers
            if self.dag:
                consumers = self.dag.get_downstream_consumers(node_id)
                for consumer_id in consumers:
                    lines.extend(
                        self._ascii_subtree(consumer_id, depth + 1, max_depth, visited)
                    )

        return lines
