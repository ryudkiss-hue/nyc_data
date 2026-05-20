"""PostgreSQL persistence for data lineage and transformation DAGs.

This module provides CRUD operations for lineage data, execution history,
and audit logging. All operations are thread-safe and include automatic
audit trail logging.

Classes:
    LineagePersistence: Main interface for lineage persistence operations
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    import psycopg  # type: ignore[import]
    from psycopg import sql, Connection  # type: ignore[import]
except ImportError:
    psycopg = None  # type: ignore
    Connection = Any  # type: ignore

from .core import (
    TransformationNode,
    ExecutionRecord,
    LineageEdge,
    NodeType,
    EdgeType,
    ExecutionStatus,
    DAG,
)

logger = logging.getLogger(__name__)


class LineagePersistence:
    """PostgreSQL persistence layer for lineage data.
    
    Provides thread-safe CRUD operations with automatic audit logging.
    All timestamps are UTC-aware.
    """

    def __init__(self, db_connection: Optional[Connection] = None) -> None:
        """Initialize persistence layer.
        
        Args:
            db_connection: PostgreSQL connection. If None, methods will fail.
        """
        if psycopg is None:
            raise ImportError("psycopg is required for persistence")
        self.conn = db_connection

    def save_node(self, node: TransformationNode, user: str = "system") -> str:
        """Save or update a transformation node.
        
        Args:
            node: TransformationNode to save
            user: User performing the operation
            
        Returns:
            node_id of the saved node
            
        Raises:
            RuntimeError: If database operation fails
        """
        if not self.conn:
            raise RuntimeError("No database connection")

        try:
            with self.conn.cursor() as cur:
                # Check if node exists
                cur.execute(
                    "SELECT id FROM public.lineage_nodes WHERE node_id = %s",
                    (node.node_id,),
                )
                exists = cur.fetchone() is not None

                if exists:
                    # Update existing node
                    cur.execute(
                        """
                        UPDATE public.lineage_nodes
                        SET name = %s,
                            description = %s,
                            owner = %s,
                            last_modified = %s,
                            configuration = %s,
                            schema_version = %s,
                            tags = %s
                        WHERE node_id = %s
                        """,
                        (
                            node.name,
                            node.description,
                            node.owner,
                            datetime.now(timezone.utc),
                            json.dumps(node.configuration),
                            node.schema_version,
                            json.dumps(node.tags),
                            node.node_id,
                        ),
                    )
                    logger.info(f"Updated node {node.node_id}")
                else:
                    # Insert new node
                    cur.execute(
                        """
                        INSERT INTO public.lineage_nodes
                        (node_id, name, node_type, description, owner, created_at,
                         last_modified, configuration, schema_version, tags)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            node.node_id,
                            node.name,
                            node.node_type.value,
                            node.description,
                            node.owner,
                            node.created_at,
                            node.last_modified,
                            json.dumps(node.configuration),
                            node.schema_version,
                            json.dumps(node.tags),
                        ),
                    )
                    logger.info(f"Created node {node.node_id}")

                # Log audit event
                self._log_audit(
                    cur,
                    "node_created" if not exists else "node_updated",
                    node_id=node.node_id,
                    new_value=node.to_dict(),
                    user=user,
                )

                self.conn.commit()
                return node.node_id

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to save node {node.node_id}: {e}")
            raise RuntimeError(f"Failed to save node: {e}")

    def get_node(self, node_id: str) -> Optional[TransformationNode]:
        """Retrieve a transformation node by ID.
        
        Args:
            node_id: ID of node to retrieve
            
        Returns:
            TransformationNode or None if not found
        """
        if not self.conn:
            return None

        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT node_id, name, node_type, description, owner,
                           created_at, last_modified, configuration,
                           schema_version, tags
                    FROM public.lineage_nodes
                    WHERE node_id = %s
                    """,
                    (node_id,),
                )
                row = cur.fetchone()

                if not row:
                    return None

                node = TransformationNode(
                    node_id=row[0],
                    name=row[1],
                    node_type=NodeType(row[2]),
                    description=row[3],
                    owner=row[4],
                    created_at=row[5],
                    last_modified=row[6],
                    configuration=json.loads(row[7]) if row[7] else {},
                    schema_version=row[8],
                    tags=json.loads(row[9]) if row[9] else [],
                )

                # Load execution history
                node.execution_history = self.get_execution_history(node_id)
                return node

        except Exception as e:
            logger.error(f"Failed to get node {node_id}: {e}")
            return None

    def save_edge(
        self, edge: LineageEdge, user: str = "system"
    ) -> None:
        """Save a lineage edge (dependency).
        
        Args:
            edge: LineageEdge to save
            user: User performing the operation
            
        Raises:
            RuntimeError: If database operation fails
        """
        if not self.conn:
            raise RuntimeError("No database connection")

        try:
            with self.conn.cursor() as cur:
                # Insert or update edge
                cur.execute(
                    """
                    INSERT INTO public.lineage_edges
                    (source_node_id, target_node_id, edge_type, cardinality,
                     join_keys, filter_conditions, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_node_id, target_node_id)
                    DO UPDATE SET
                        edge_type = EXCLUDED.edge_type,
                        cardinality = EXCLUDED.cardinality,
                        join_keys = EXCLUDED.join_keys,
                        filter_conditions = EXCLUDED.filter_conditions
                    """,
                    (
                        edge.source_node_id,
                        edge.target_node_id,
                        edge.edge_type.value,
                        edge.cardinality,
                        json.dumps(edge.join_keys),
                        edge.filter_conditions,
                        edge.created_at,
                    ),
                )

                self._log_audit(
                    cur,
                    "edge_created",
                    edge_source_id=edge.source_node_id,
                    edge_target_id=edge.target_node_id,
                    new_value=edge.to_dict(),
                    user=user,
                )

                self.conn.commit()
                logger.info(f"Saved edge {edge.source_node_id} -> {edge.target_node_id}")

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to save edge: {e}")
            raise RuntimeError(f"Failed to save edge: {e}")

    def get_edges(self, source_id: Optional[str] = None, target_id: Optional[str] = None) -> List[LineageEdge]:
        """Retrieve edges, optionally filtered by source or target.
        
        Args:
            source_id: Filter by source node ID
            target_id: Filter by target node ID
            
        Returns:
            List of LineageEdge objects
        """
        if not self.conn:
            return []

        try:
            with self.conn.cursor() as cur:
                query = "SELECT source_node_id, target_node_id, edge_type, cardinality, join_keys, filter_conditions, created_at FROM public.lineage_edges WHERE 1=1"
                params = []

                if source_id:
                    query += " AND source_node_id = %s"
                    params.append(source_id)
                if target_id:
                    query += " AND target_node_id = %s"
                    params.append(target_id)

                cur.execute(query, params)
                edges = []

                for row in cur.fetchall():
                    edge = LineageEdge(
                        source_node_id=row[0],
                        target_node_id=row[1],
                        edge_type=EdgeType(row[2]),
                        cardinality=row[3],
                        join_keys=json.loads(row[4]) if row[4] else [],
                        filter_conditions=row[5],
                        created_at=row[6],
                    )
                    edges.append(edge)

                return edges

        except Exception as e:
            logger.error(f"Failed to get edges: {e}")
            return []

    def save_execution(self, execution: ExecutionRecord, user: str = "system") -> str:
        """Save an execution record.
        
        Args:
            execution: ExecutionRecord to save
            user: User performing the operation
            
        Returns:
            execution_id of the saved record
            
        Raises:
            RuntimeError: If database operation fails
        """
        if not self.conn:
            raise RuntimeError("No database connection")

        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.lineage_execution_history
                    (execution_id, node_id, started_at, completed_at, duration_seconds,
                     status, input_row_count, output_row_count, error_message,
                     data_quality_metrics, executed_by, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        execution.execution_id,
                        execution.node_id,
                        execution.started_at,
                        execution.completed_at,
                        execution.duration_seconds,
                        execution.status.value,
                        execution.input_row_count,
                        execution.output_row_count,
                        execution.error_message,
                        json.dumps(execution.data_quality_metrics),
                        user,
                        execution.notes,
                    ),
                )

                self._log_audit(
                    cur,
                    "execution_recorded",
                    node_id=execution.node_id,
                    new_value=execution.to_dict(),
                    user=user,
                )

                self.conn.commit()
                logger.info(f"Saved execution {execution.execution_id}")
                return execution.execution_id

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to save execution: {e}")
            raise RuntimeError(f"Failed to save execution: {e}")

    def get_execution_history(
        self, node_id: str, limit: int = 50
    ) -> List[ExecutionRecord]:
        """Get execution history for a node, newest first.
        
        Args:
            node_id: Node to get history for
            limit: Maximum number of records to return
            
        Returns:
            List of ExecutionRecord objects
        """
        if not self.conn:
            return []

        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT execution_id, node_id, started_at, completed_at,
                           duration_seconds, status, input_row_count, output_row_count,
                           error_message, data_quality_metrics, executed_by, notes
                    FROM public.lineage_execution_history
                    WHERE node_id = %s
                    ORDER BY started_at DESC
                    LIMIT %s
                    """,
                    (node_id, limit),
                )

                records = []
                for row in cur.fetchall():
                    record = ExecutionRecord(
                        execution_id=row[0],
                        node_id=row[1],
                        started_at=row[2],
                        completed_at=row[3],
                        duration_seconds=row[4],
                        status=ExecutionStatus(row[5]),
                        input_row_count=row[6],
                        output_row_count=row[7],
                        error_message=row[8],
                        data_quality_metrics=json.loads(row[9]) if row[9] else {},
                        user=row[10] or "system",
                        notes=row[11],
                    )
                    records.append(record)

                return records

        except Exception as e:
            logger.error(f"Failed to get execution history for {node_id}: {e}")
            return []

    def delete_node(self, node_id: str, user: str = "system") -> bool:
        """Delete a node and all its edges.
        
        Args:
            node_id: Node to delete
            user: User performing the operation
            
        Returns:
            True if successful, False otherwise
        """
        if not self.conn:
            return False

        try:
            with self.conn.cursor() as cur:
                # Get node data for audit log
                cur.execute(
                    "SELECT * FROM public.lineage_nodes WHERE node_id = %s",
                    (node_id,),
                )
                old_value = cur.fetchone()

                if not old_value:
                    return False

                # Delete node (cascades to edges and execution history)
                cur.execute(
                    "DELETE FROM public.lineage_nodes WHERE node_id = %s",
                    (node_id,),
                )

                self._log_audit(
                    cur,
                    "node_deleted",
                    node_id=node_id,
                    old_value=old_value,
                    user=user,
                )

                self.conn.commit()
                logger.info(f"Deleted node {node_id}")
                return True

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to delete node {node_id}: {e}")
            return False

    def export_dag(self, format: str = "json") -> str:
        """Export complete DAG in specified format.
        
        Args:
            format: Export format: 'json', 'graphml', 'mermaid', 'dot'
            
        Returns:
            String representation in specified format
        """
        if not self.conn:
            return ""

        try:
            dag = self.load_dag()
            
            if format == "json":
                return json.dumps(dag.to_dict(), indent=2, default=str)
            elif format == "graphml":
                return self._dag_to_graphml(dag)
            elif format == "mermaid":
                return self._dag_to_mermaid(dag)
            elif format == "dot":
                return self._dag_to_dot(dag)
            else:
                raise ValueError(f"Unknown format: {format}")

        except Exception as e:
            logger.error(f"Failed to export DAG: {e}")
            return ""

    def load_dag(self) -> DAG:
        """Load complete DAG from database.
        
        Returns:
            DAG object with all nodes and edges
        """
        if not self.conn:
            return DAG()

        dag = DAG()

        try:
            # Load all nodes
            with self.conn.cursor() as cur:
                cur.execute("SELECT node_id FROM public.lineage_nodes")
                for (node_id,) in cur.fetchall():
                    node = self.get_node(node_id)
                    if node:
                        dag.add_node(node)

            # Load all edges
            for edge in self.get_edges():
                try:
                    dag.add_edge(
                        edge.source_node_id,
                        edge.target_node_id,
                        edge_type=edge.edge_type,
                        cardinality=edge.cardinality,
                        join_keys=edge.join_keys,
                        filter_conditions=edge.filter_conditions,
                    )
                except ValueError as e:
                    logger.warning(f"Failed to add edge: {e}")

            logger.info(f"Loaded DAG with {len(dag.nodes)} nodes and {len(dag.edges)} edges")
            return dag

        except Exception as e:
            logger.error(f"Failed to load DAG: {e}")
            return dag

    def _log_audit(
        self,
        cursor: Any,
        event_type: str,
        node_id: Optional[str] = None,
        edge_source_id: Optional[str] = None,
        edge_target_id: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        user: str = "system",
    ) -> None:
        """Log an audit event. Internal method."""
        try:
            cursor.execute(
                """
                INSERT INTO public.lineage_audit_log
                (event_type, node_id, edge_source_id, edge_target_id,
                 old_value, new_value, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    event_type,
                    node_id,
                    edge_source_id,
                    edge_target_id,
                    json.dumps(old_value) if old_value else None,
                    json.dumps(new_value) if new_value else None,
                    user,
                ),
            )
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")

    def _dag_to_graphml(self, dag: DAG) -> str:
        """Convert DAG to GraphML format for visualization tools."""
        try:
            import networkx as nx
            graphml = nx.to_string(dag.graph, format="graphml")  # type: ignore
            return graphml
        except Exception as e:
            logger.error(f"Failed to export to GraphML: {e}")
            return ""

    def _dag_to_mermaid(self, dag: DAG) -> str:
        """Convert DAG to Mermaid diagram syntax."""
        lines = ["graph TD"]
        for (source, target) in dag.edges.keys():
            lines.append(f"    {source} --> {target}")
        return "\n".join(lines)

    def _dag_to_dot(self, dag: DAG) -> str:
        """Convert DAG to Graphviz DOT format."""
        try:
            import networkx as nx
            return nx.to_string(dag.graph, format="dot")  # type: ignore
        except Exception as e:
            logger.error(f"Failed to export to DOT: {e}")
            return ""
