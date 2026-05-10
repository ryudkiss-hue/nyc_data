"""Core data lineage and transformation DAG tracking.

This module provides comprehensive data lineage tracking, capturing complete provenance
for data flowing from source datasets through transformations to targets. Supports:
- Transformation dependency graphs (DAGs)
- Execution history and audit trails
- Impact analysis and downstream consumer tracking
- Schema version linking for compliance

Key Classes:
    - TransformationNode: Represents a data source, transformation, or sink
    - ExecutionRecord: Tracks a single execution of a transformation
    - LineageEdge: Represents dependency between nodes
    - DAG: Directed acyclic graph of transformations

Example:
    >>> dag = DAG()
    >>> ingestion = TransformationNode(
    ...     node_id='ingest_construction',
    ...     name='NYC Construction List Ingestion',
    ...     node_type=NodeType.INGESTION,
    ...     owner='data-eng@nyc.gov'
    ... )
    >>> dag.add_node(ingestion)
    >>> sources = dag.get_upstream_dependencies('transform_xyz')
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Dict, List, Set, Tuple, TYPE_CHECKING
from copy import deepcopy

try:
    import networkx as nx
except ImportError:
    nx = None  # type: ignore

if TYPE_CHECKING:
    from networkx import DiGraph
else:
    DiGraph = Any

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Classification of transformation nodes."""
    INGESTION = "ingestion"  # Data source (Socrata, API, file)
    TRANSFORMATION = "transformation"  # Data transformation step
    SINK = "sink"  # Data persistence target
    VALIDATION = "validation"  # Data quality check
    MATERIALIZATION = "materialization"  # Materialized view or table
    AGGREGATION = "aggregation"  # Aggregation operation


class EdgeType(Enum):
    """Type of relationship between nodes."""
    DEPENDENCY = "dependency"  # One node depends on another
    DATA_FLOW = "data_flow"  # Direct data flow
    SCHEMA_DEPENDENCY = "schema_dependency"  # Schema version dependency


class ExecutionStatus(Enum):
    """Status of a transformation execution."""
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


@dataclass
class ExecutionRecord:
    """Tracks execution of a transformation node.
    
    Attributes:
        execution_id: Unique execution identifier
        node_id: ID of the node that was executed
        started_at: Timestamp when execution started
        completed_at: Timestamp when execution completed
        duration_seconds: How long execution took
        status: Execution status (RUNNING, SUCCESS, FAILED, PARTIAL, SKIPPED)
        input_row_count: Number of input rows processed
        output_row_count: Number of output rows produced
        error_message: Error details if failed
        data_quality_metrics: Quality metrics (null%, duplicate%, outliers, etc.)
        user: User who triggered execution
        notes: Additional notes or context
    """
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str = ""
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    status: ExecutionStatus = ExecutionStatus.RUNNING
    input_row_count: int = 0
    output_row_count: int = 0
    error_message: Optional[str] = None
    data_quality_metrics: Dict[str, float] = field(default_factory=dict)
    user: str = "system"
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with serialized enums and timestamps."""
        d = asdict(self)
        d["status"] = self.status.value
        d["started_at"] = self.started_at.isoformat()
        d["completed_at"] = self.completed_at.isoformat() if self.completed_at else None
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutionRecord:
        """Create from dictionary, parsing timestamps and enums."""
        d = deepcopy(data)
        d["status"] = ExecutionStatus(d["status"])
        d["started_at"] = datetime.fromisoformat(d["started_at"])
        d["completed_at"] = (
            datetime.fromisoformat(d["completed_at"]) if d["completed_at"] else None
        )
        return cls(**d)


@dataclass
class LineageEdge:
    """Represents a dependency or data flow between two nodes.
    
    Attributes:
        source_node_id: Upstream node ID
        target_node_id: Downstream node ID
        edge_type: Type of relationship (DEPENDENCY, DATA_FLOW, SCHEMA_DEPENDENCY)
        cardinality: Relationship cardinality (1:1, 1:N, N:1, N:N)
        join_keys: Column names used in join operations
        filter_conditions: SQL conditions that filter data
        created_at: When this edge was created
    """
    source_node_id: str
    target_node_id: str
    edge_type: EdgeType = EdgeType.DATA_FLOW
    cardinality: str = "1:1"  # 1:1, 1:N, N:1, N:N
    join_keys: List[str] = field(default_factory=list)
    filter_conditions: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with serialized values."""
        d = asdict(self)
        d["edge_type"] = self.edge_type.value
        d["created_at"] = self.created_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LineageEdge:
        """Create from dictionary."""
        d = deepcopy(data)
        d["edge_type"] = EdgeType(d["edge_type"])
        d["created_at"] = datetime.fromisoformat(d["created_at"])
        return cls(**d)


@dataclass
class TransformationNode:
    """Represents a transformation, data source, or sink in the lineage.
    
    Attributes:
        node_id: Unique identifier for this node
        name: Human-readable name
        node_type: Type of node (INGESTION, TRANSFORMATION, SINK, etc.)
        description: What this transformation does
        owner: Email or user ID of the owner
        created_at: When node was created
        last_modified: Last modification timestamp
        input_datasets: IDs of upstream dependency nodes
        output_datasets: IDs of downstream consumer nodes
        configuration: Transform parameters, SQL, Python code, filters
        execution_history: List of execution records
        schema_version: Link to schema registry version
        tags: Metadata tags (e.g., ["production", "daily", "high-priority"])
    """
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    node_type: NodeType = NodeType.TRANSFORMATION
    description: str = ""
    owner: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_modified: datetime = field(default_factory=datetime.utcnow)
    input_datasets: List[str] = field(default_factory=list)
    output_datasets: List[str] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    execution_history: List[ExecutionRecord] = field(default_factory=list)
    schema_version: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with serialized nested objects."""
        d = asdict(self)
        d["node_type"] = self.node_type.value
        d["created_at"] = self.created_at.isoformat()
        d["last_modified"] = self.last_modified.isoformat()
        d["execution_history"] = [
            rec.to_dict() for rec in self.execution_history
        ]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TransformationNode:
        """Create from dictionary."""
        d = deepcopy(data)
        d["node_type"] = NodeType(d["node_type"])
        d["created_at"] = datetime.fromisoformat(d["created_at"])
        d["last_modified"] = datetime.fromisoformat(d["last_modified"])
        d["execution_history"] = [
            ExecutionRecord.from_dict(rec) for rec in d.get("execution_history", [])
        ]
        return cls(**d)

    def record_execution(
        self,
        status: ExecutionStatus,
        input_rows: int = 0,
        output_rows: int = 0,
        duration_secs: float = 0.0,
        error_msg: Optional[str] = None,
        metrics: Optional[Dict[str, float]] = None,
        user: str = "system",
        notes: Optional[str] = None,
    ) -> ExecutionRecord:
        """Record an execution of this transformation node.
        
        Args:
            status: Final execution status
            input_rows: Input row count
            output_rows: Output row count
            duration_secs: Execution duration in seconds
            error_msg: Error message if failed
            metrics: Data quality metrics
            user: User who triggered execution
            notes: Additional notes
            
        Returns:
            ExecutionRecord: The recorded execution
        """
        exec_record = ExecutionRecord(
            execution_id=str(uuid.uuid4()),
            node_id=self.node_id,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=duration_secs,
            status=status,
            input_row_count=input_rows,
            output_row_count=output_rows,
            error_message=error_msg,
            data_quality_metrics=metrics or {},
            user=user,
            notes=notes,
        )
        self.execution_history.append(exec_record)
        self.last_modified = datetime.utcnow()
        return exec_record

    def get_latest_execution(self) -> Optional[ExecutionRecord]:
        """Get the most recent execution record."""
        if not self.execution_history:
            return None
        return self.execution_history[-1]

    def get_execution_history(self, limit: int = 10) -> List[ExecutionRecord]:
        """Get recent execution history, newest first."""
        return self.execution_history[-limit:][::-1]


class DAG:
    """Directed Acyclic Graph of transformations and data flows.
    
    Manages a complete data lineage DAG with validation, cycle detection,
    and dependency analysis. Uses NetworkX for graph operations.
    
    Attributes:
        nodes: Dictionary mapping node_id to TransformationNode
        edges: Dictionary mapping (source, target) tuple to LineageEdge
        graph: NetworkX DiGraph for efficient graph operations
    """

    def __init__(self) -> None:
        """Initialize empty DAG."""
        if nx is None:
            raise ImportError("networkx is required for DAG operations")
        self.nodes: Dict[str, TransformationNode] = {}
        self.edges: Dict[Tuple[str, str], LineageEdge] = {}
        self.graph: Any = nx.DiGraph()  # type: ignore

    def add_node(self, node: TransformationNode) -> None:
        """Add a transformation node to the DAG.
        
        Args:
            node: TransformationNode to add
            
        Raises:
            ValueError: If node_id already exists
        """
        if node.node_id in self.nodes:
            raise ValueError(f"Node {node.node_id} already exists in DAG")
        self.nodes[node.node_id] = node
        self.graph.add_node(node.node_id, node_type=node.node_type.value)
        logger.debug(f"Added node {node.node_id} ({node.name})")

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType = EdgeType.DATA_FLOW,
        cardinality: str = "1:1",
        join_keys: Optional[List[str]] = None,
        filter_conditions: Optional[str] = None,
    ) -> LineageEdge:
        """Add a dependency edge between two nodes.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            edge_type: Type of edge
            cardinality: Relationship cardinality
            join_keys: Join key columns if applicable
            filter_conditions: SQL filter conditions if applicable
            
        Returns:
            LineageEdge: The created edge
            
        Raises:
            ValueError: If either node doesn't exist or would create cycle
        """
        if source_id not in self.nodes:
            raise ValueError(f"Source node {source_id} does not exist")
        if target_id not in self.nodes:
            raise ValueError(f"Target node {target_id} does not exist")

        # Check for cycles
        self.graph.add_edge(source_id, target_id)
        if not nx.is_directed_acyclic_graph(self.graph):
            self.graph.remove_edge(source_id, target_id)
            raise ValueError(
                f"Edge {source_id} -> {target_id} would create a cycle"
            )

        edge = LineageEdge(
            source_node_id=source_id,
            target_node_id=target_id,
            edge_type=edge_type,
            cardinality=cardinality,
            join_keys=join_keys or [],
            filter_conditions=filter_conditions,
        )
        self.edges[(source_id, target_id)] = edge

        # Update node references
        if target_id not in self.nodes[source_id].output_datasets:
            self.nodes[source_id].output_datasets.append(target_id)
        if source_id not in self.nodes[target_id].input_datasets:
            self.nodes[target_id].input_datasets.append(source_id)

        logger.debug(f"Added edge {source_id} -> {target_id}")
        return edge

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all its edges from the DAG.
        
        Args:
            node_id: ID of node to remove
            
        Raises:
            ValueError: If node doesn't exist
        """
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} does not exist")

        # Remove all edges involving this node
        edges_to_remove = [
            (s, t) for s, t in self.edges.keys()
            if s == node_id or t == node_id
        ]
        for source_id, target_id in edges_to_remove:
            del self.edges[(source_id, target_id)]

        # Remove from graph and nodes
        self.graph.remove_node(node_id)
        del self.nodes[node_id]
        logger.debug(f"Removed node {node_id}")

    def get_node(self, node_id: str) -> Optional[TransformationNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_upstream_dependencies(self, node_id: str) -> List[str]:
        """Get all upstream dependencies (sources) for a node.
        
        Args:
            node_id: Target node ID
            
        Returns:
            List of upstream node IDs, ordered by distance (closest first)
        """
        if node_id not in self.graph:
            return []
        try:
            ancestors = list(nx.ancestors(self.graph, node_id))
            # Sort by distance (BFS order)
            distances = nx.single_source_shortest_path_length(self.graph, node_id)
            return sorted(ancestors, key=lambda x: distances.get(x, float('inf')))
        except nx.NetworkXError:
            return []

    def get_downstream_consumers(self, node_id: str) -> List[str]:
        """Get all downstream consumers (targets) for a node.
        
        Args:
            node_id: Source node ID
            
        Returns:
            List of downstream node IDs, ordered by distance (closest first)
        """
        if node_id not in self.graph:
            return []
        try:
            descendants = list(nx.descendants(self.graph, node_id))
            # Sort by distance (BFS order from reverse)
            distances = nx.single_source_shortest_path_length(
                self.graph.reverse(), node_id
            )
            return sorted(descendants, key=lambda x: distances.get(x, float('inf')))
        except nx.NetworkXError:
            return []

    def get_critical_path(self) -> List[str]:
        """Get longest dependency chain in the DAG.
        
        Returns:
            List of node IDs representing critical path
        """
        if not self.graph.nodes():
            return []

        try:
            # Find longest path using topological sort
            longest_path = []
            for node in nx.topological_sort(self.graph):  # type: ignore
                paths = list(nx.all_simple_paths(self.graph, source=node))  # type: ignore
                if paths:
                    longest = max(paths, key=len)
                    if len(longest) > len(longest_path):
                        longest_path = longest
            return longest_path
        except (nx.NetworkXError, StopIteration):  # type: ignore
            return []

    def get_impact_scope(self, node_id: str) -> Dict[str, Any]:
        """Analyze impact of changing a node on downstream systems.
        
        Args:
            node_id: Node to analyze
            
        Returns:
            Dictionary with affected nodes, users, and remediation info
        """
        if node_id not in self.nodes:
            return {"error": f"Node {node_id} does not exist", "affected_nodes": []}

        affected = self.get_downstream_consumers(node_id)
        affected_users = set()
        affected_by_type: Dict[str, List[str]] = {}

        for affected_id in affected:
            node = self.nodes.get(affected_id)
            if node:
                if node.owner:
                    affected_users.add(node.owner)
                node_type = node.node_type.value
                if node_type not in affected_by_type:
                    affected_by_type[node_type] = []
                affected_by_type[node_type].append(affected_id)

        # Find critical paths that include this node
        critical_paths = []
        all_paths = list(nx.all_simple_paths(self.graph, source=node_id))
        longest_paths = sorted(all_paths, key=len, reverse=True)[:3]
        critical_paths = [p for p in longest_paths if len(p) > 1]

        return {
            "node_id": node_id,
            "direct_dependents": self.nodes[node_id].output_datasets,
            "all_affected_nodes": affected,
            "affected_count": len(affected),
            "affected_users": list(affected_users),
            "affected_by_type": affected_by_type,
            "critical_paths": critical_paths,
            "critical_path_count": len(critical_paths),
        }

    def validate(self) -> Dict[str, Any]:
        """Validate DAG integrity.
        
        Returns:
            Dictionary with validation results, including any errors/warnings
        """
        issues = {
            "errors": [],
            "warnings": [],
            "is_valid": True,
        }

        # Check for cycles
        if not nx.is_directed_acyclic_graph(self.graph):
            issues["errors"].append("Graph contains cycles")
            issues["is_valid"] = False

        # Check for orphaned nodes (no inputs or outputs)
        for node_id, node in self.nodes.items():
            if (
                node.node_type != NodeType.INGESTION
                and not node.input_datasets
            ):
                issues["warnings"].append(
                    f"Node {node_id} has no inputs (expected for INGESTION only)"
                )

            if (
                node.node_type != NodeType.SINK
                and not node.output_datasets
            ):
                issues["warnings"].append(
                    f"Node {node_id} has no outputs (expected for SINK only)"
                )

        # Check for isolated nodes
        for node_id in self.nodes:
            if self.graph.degree(node_id) == 0:
                issues["warnings"].append(f"Node {node_id} is isolated (no connections)")

        return issues

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire DAG to dictionary."""
        return {
            "nodes": {
                node_id: node.to_dict()
                for node_id, node in self.nodes.items()
            },
            "edges": {
                f"{s}->{t}": edge.to_dict()
                for (s, t), edge in self.edges.items()
            },
            "metadata": {
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
                "is_acyclic": nx.is_directed_acyclic_graph(self.graph),
                "created_at": datetime.utcnow().isoformat(),
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DAG:
        """Reconstruct DAG from dictionary."""
        dag = cls()
        
        # Add all nodes
        for node_id, node_data in data.get("nodes", {}).items():
            node = TransformationNode.from_dict(node_data)
            dag.add_node(node)
        
        # Add all edges
        for edge_str, edge_data in data.get("edges", {}).items():
            edge = LineageEdge.from_dict(edge_data)
            dag.add_edge(
                edge.source_node_id,
                edge.target_node_id,
                edge_type=edge.edge_type,
                cardinality=edge.cardinality,
                join_keys=edge.join_keys,
                filter_conditions=edge.filter_conditions,
            )
        
        return dag

    def get_node_lineage_summary(self, node_id: str) -> Dict[str, Any]:
        """Get complete lineage summary for a node.
        
        Args:
            node_id: Node to summarize
            
        Returns:
            Dictionary with inputs, outputs, execution history, etc.
        """
        if node_id not in self.nodes:
            return {"error": f"Node {node_id} not found"}

        node = self.nodes[node_id]
        latest_exec = node.get_latest_execution()

        return {
            "node_id": node_id,
            "name": node.name,
            "type": node.node_type.value,
            "owner": node.owner,
            "description": node.description,
            "created_at": node.created_at.isoformat(),
            "last_modified": node.last_modified.isoformat(),
            "upstream_dependencies": self.get_upstream_dependencies(node_id),
            "downstream_consumers": self.get_downstream_consumers(node_id),
            "direct_inputs": node.input_datasets,
            "direct_outputs": node.output_datasets,
            "tags": node.tags,
            "schema_version": node.schema_version,
            "latest_execution": latest_exec.to_dict() if latest_exec else None,
            "execution_count": len(node.execution_history),
            "latest_status": latest_exec.status.value if latest_exec else None,
        }
