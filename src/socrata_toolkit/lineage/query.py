"""Query interface for data lineage discovery and analysis.

Provides simple query API for finding lineage relationships, searching nodes,
and analyzing data freshness and completeness.

Classes:
    LineageQuery: Main query interface
    FreshnessInfo: Data freshness metadata
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FreshnessInfo:
    """Information about data freshness and staleness.
    
    Attributes:
        node_id: Node being analyzed
        last_execution_time: When it was last executed
        age_seconds: How old the data is
        is_stale: Whether data is considered stale
        stale_threshold_seconds: What qualifies as stale
        next_expected_update: Expected next update time
    """
    node_id: str
    last_execution_time: datetime | None = None
    age_seconds: float = 0.0
    is_stale: bool = False
    stale_threshold_seconds: float = 86400.0  # 24 hours default
    next_expected_update: datetime | None = None


class LineageQuery:
    """Query interface for data lineage relationships and analysis.
    
    Provides methods to discover data lineage, find dependencies,
    search nodes, and analyze data freshness.
    """

    def __init__(self, dag: Any | None = None, persistence: Any | None = None) -> None:
        """Initialize query interface.
        
        Args:
            dag: DAG object (LineageCore.DAG)
            persistence: LineagePersistence instance for queries
        """
        self.dag = dag
        self.persistence = persistence

    def find_sources(self, node_id: str) -> list[str]:
        """Find all upstream data sources for a node.
        
        Returns direct and indirect sources that feed into this node.
        
        Args:
            node_id: Target node ID
            
        Returns:
            List of upstream source node IDs, ordered by distance
            
        Example:
            sources = query.find_sources('transformation_xyz')
            # Returns: ['ingest.construction_list', 'ingest.complaints']
        """
        if not self.dag:
            return []

        return self.dag.get_upstream_dependencies(node_id)

    def find_consumers(self, node_id: str) -> list[str]:
        """Find all downstream consumers of a node.
        
        Returns nodes that depend on this node's output.
        
        Args:
            node_id: Source node ID
            
        Returns:
            List of downstream consumer node IDs, ordered by distance
            
        Example:
            consumers = query.find_consumers('ingest.construction_list')
            # Returns: ['transform.clean_construction', 'sink.postgres_warehouse']
        """
        if not self.dag:
            return []

        return self.dag.get_downstream_consumers(node_id)

    def find_path(self, source_id: str, target_id: str) -> list[str] | None:
        """Find transformation path between two nodes.
        
        Finds one (shortest) path of transformations from source to target.
        
        Args:
            source_id: Starting node ID
            target_id: Ending node ID
            
        Returns:
            List of node IDs in path (including source and target), or None if no path
            
        Example:
            path = query.find_path('ingest.construction_list', 'sink.reporting_db')
            # Returns: ['ingest.construction_list', 'transform.clean', 'transform.aggregate', 'sink.reporting_db']
        """
        if not self.dag:
            return None

        try:
            import networkx as nx
            path = nx.shortest_path(self.dag.graph, source_id, target_id)  # type: ignore
            return list(path)
        except (nx.NetworkXNoPath, nx.NodeNotFound):  # type: ignore
            return None
        except Exception:
            return None

    def find_all_paths(self, source_id: str, target_id: str, limit: int = 10) -> list[list[str]]:
        """Find all paths between two nodes.
        
        Args:
            source_id: Starting node ID
            target_id: Ending node ID
            limit: Maximum number of paths to return
            
        Returns:
            List of paths (each path is a list of node IDs)
        """
        if not self.dag:
            return []

        try:
            import networkx as nx
            paths = list(
                nx.all_simple_paths(self.dag.graph, source_id, target_id, cutoff=10)  # type: ignore
            )
            return paths[:limit]
        except (nx.NetworkXNoPath, nx.NodeNotFound):  # type: ignore
            return []
        except Exception:
            return []

    def search_nodes(
        self,
        name: str | None = None,
        node_type: str | None = None,
        owner: str | None = None,
        tag: str | None = None,
    ) -> list[str]:
        """Search for nodes matching criteria.
        
        Args:
            name: Substring of node name to match
            node_type: Node type filter (ingestion, transformation, sink, etc.)
            owner: Owner email/user ID filter
            tag: Tag filter (matches if node has this tag)
            
        Returns:
            List of matching node IDs
            
        Example:
            # Find all sinks owned by data-eng team
            sinks = query.search_nodes(node_type='sink', owner='data-eng')
            
            # Find all nodes with 'construction' in name
            construction_nodes = query.search_nodes(name='construction')
        """
        if not self.dag:
            return []

        results = []

        for node_id, node in self.dag.nodes.items():
            # Check name match
            if name and name.lower() not in node.name.lower():
                continue

            # Check type match
            if node_type and node.node_type.value != node_type:
                continue

            # Check owner match
            if owner and node.owner != owner:
                continue

            # Check tag match
            if tag and tag not in node.tags:
                continue

            results.append(node_id)

        return results

    def get_node_info(self, node_id: str) -> dict[str, Any] | None:
        """Get complete information about a node.
        
        Args:
            node_id: Node to retrieve
            
        Returns:
            Dictionary with node details, or None if not found
            
        Example:
            info = query.get_node_info('transform.construction_cleaning')
        """
        if not self.dag:
            if self.persistence:
                node = self.persistence.get_node(node_id)
                if node:
                    return self.dag.get_node_lineage_summary(node_id) if self.dag else None
            return None

        return self.dag.get_node_lineage_summary(node_id)

    def get_freshness(self, node_id: str, stale_threshold_hours: float = 24) -> FreshnessInfo:
        """Analyze data freshness for a node.
        
        Determines if data is current or stale based on last execution time.
        
        Args:
            node_id: Node to analyze
            stale_threshold_hours: Hours after which data is considered stale
            
        Returns:
            FreshnessInfo with staleness analysis
            
        Example:
            freshness = query.get_freshness('ingest.construction_list', stale_threshold_hours=12)
            if freshness.is_stale:
                print(f"Data is {freshness.age_seconds / 3600} hours old")
        """
        stale_threshold_seconds = stale_threshold_hours * 3600

        freshness = FreshnessInfo(
            node_id=node_id,
            stale_threshold_seconds=stale_threshold_seconds,
        )

        if not self.dag:
            return freshness

        node = self.dag.get_node(node_id)
        if not node:
            return freshness

        latest_exec = node.get_latest_execution()
        if not latest_exec or not latest_exec.completed_at:
            freshness.is_stale = True
            return freshness

        freshness.last_execution_time = latest_exec.completed_at
        age = datetime.now(timezone.utc) - latest_exec.completed_at
        freshness.age_seconds = age.total_seconds()
        freshness.is_stale = freshness.age_seconds > stale_threshold_seconds

        # Estimate next update
        if latest_exec.duration_seconds > 0:
            next_update = latest_exec.completed_at + timedelta(
                seconds=latest_exec.duration_seconds * 1.5
            )
            freshness.next_expected_update = next_update

        return freshness

    def get_completeness(self, node_id: str) -> dict[str, Any]:
        """Analyze data completeness metrics for a node.
        
        Returns quality metrics from recent executions.
        
        Args:
            node_id: Node to analyze
            
        Returns:
            Dictionary with completeness metrics
        """
        metrics = {
            "node_id": node_id,
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "success_rate": 0.0,
            "total_rows_processed": 0,
            "average_rows_per_run": 0,
            "average_quality_score": 0.0,
            "recent_issues": [],
        }

        if not self.dag:
            return metrics

        node = self.dag.get_node(node_id)
        if not node:
            return metrics

        if not node.execution_history:
            return metrics

        metrics["total_executions"] = len(node.execution_history)

        successful = sum(
            1 for e in node.execution_history
            if e.status.value in ("success", "partial")
        )
        metrics["successful_executions"] = successful
        metrics["failed_executions"] = metrics["total_executions"] - successful
        metrics["success_rate"] = (
            successful / metrics["total_executions"]
            if metrics["total_executions"] > 0
            else 0.0
        )

        total_rows = sum(e.output_row_count for e in node.execution_history)
        metrics["total_rows_processed"] = total_rows
        metrics["average_rows_per_run"] = (
            total_rows / metrics["total_executions"]
            if metrics["total_executions"] > 0
            else 0
        )

        # Calculate average quality score from metrics
        quality_scores = []
        for execution in node.execution_history:
            if execution.data_quality_metrics:
                # Simple quality score: 100 - (null% + duplicate%)
                null_pct = execution.data_quality_metrics.get("null_percentage", 0)
                duplicate_pct = execution.data_quality_metrics.get("duplicate_percentage", 0)
                quality_score = max(0, 100 - (null_pct + duplicate_pct))
                quality_scores.append(quality_score)

        if quality_scores:
            metrics["average_quality_score"] = sum(quality_scores) / len(quality_scores)

        # Find recent issues
        for execution in node.execution_history[-5:]:  # Check last 5 executions
            if execution.status.value == "failed" and execution.error_message:
                metrics["recent_issues"].append({
                    "execution_id": execution.execution_id,
                    "timestamp": execution.started_at.isoformat() if execution.started_at else None,
                    "error": execution.error_message[:200],  # First 200 chars
                })

        return metrics

    def find_by_tag(self, tag: str) -> list[str]:
        """Find all nodes with a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of node IDs with this tag
            
        Example:
            daily_nodes = query.find_by_tag('daily')
            high_priority = query.find_by_tag('high-priority')
        """
        if not self.dag:
            return []

        return [
            node_id for node_id, node in self.dag.nodes.items()
            if tag in node.tags
        ]

    def find_by_owner(self, owner: str) -> list[str]:
        """Find all nodes owned by a specific user/team.
        
        Args:
            owner: Owner email or user ID
            
        Returns:
            List of node IDs owned by this owner
        """
        if not self.dag:
            return []

        return [
            node_id for node_id, node in self.dag.nodes.items()
            if node.owner == owner
        ]

    def find_by_type(self, node_type: str) -> list[str]:
        """Find all nodes of a specific type.
        
        Args:
            node_type: Type filter (ingestion, transformation, sink, etc.)
            
        Returns:
            List of node IDs of this type
        """
        if not self.dag:
            return []

        return [
            node_id for node_id, node in self.dag.nodes.items()
            if node.node_type.value == node_type
        ]

    def get_statistics(self) -> dict[str, Any]:
        """Get overall lineage statistics.
        
        Returns:
            Dictionary with DAG statistics
        """
        if not self.dag:
            return {}

        stats = {
            "total_nodes": len(self.dag.nodes),
            "total_edges": len(self.dag.edges),
            "nodes_by_type": {},
            "depth": 0,
            "widest_level": 0,
        }

        # Count by type
        for node_id, node in self.dag.nodes.items():
            node_type = node.node_type.value
            if node_type not in stats["nodes_by_type"]:
                stats["nodes_by_type"][node_type] = 0
            stats["nodes_by_type"][node_type] += 1

        # Calculate depth (longest path)
        if self.dag.nodes:
            critical_path = self.dag.get_critical_path()
            stats["depth"] = len(critical_path)

        return stats

    def validate_lineage(self) -> dict[str, Any]:
        """Validate lineage integrity.
        
        Returns:
            Dictionary with validation results
        """
        if not self.dag:
            return {"error": "No DAG loaded"}

        return self.dag.validate()
