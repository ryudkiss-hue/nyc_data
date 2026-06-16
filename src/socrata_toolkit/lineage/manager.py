"""Data lineage tracking and column-level provenance.

This module provides comprehensive data lineage tracking, capturing how data
flows from source datasets through transformations to target tables. Supports
column-level lineage, cycle detection, and OpenMetadata integration.

Key Classes:
    - LineageEdge: Single source→target data flow
    - LineageGraph: DAG for lineage queries and cycle detection
    - ColumnLineage: Column-level provenance tracking

Usage:
    graph = LineageGraph()
    graph.add_edge('source_dataset', 'target_table', ['id', 'name'], ['id', 'name'])
    upstream = graph.get_upstream_tables('target_table')
    col_lineage = graph.trace_column_lineage('target_table', 'id')
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum

try:
    import sqlparse
except ImportError:
    sqlparse = None  # type: ignore

try:
    import psycopg
    from psycopg import sql as psycopg_sql
except ImportError:
    psycopg = None  # type: ignore
    psycopg_sql = None  # type: ignore

# Logging setup
logger = logging.getLogger(__name__)

class TransformationType(Enum):
    """Categorization of data transformation types."""
    INGESTION = "ingestion"
    AGGREGATION = "aggregation"
    JOIN = "join"
    UNION = "union"
    FILTER = "filter"
    ENRICHMENT = "enrichment"
    CUSTOM_SQL = "custom_sql"
    COPY = "copy"

@dataclass
class LineageEdge:
    """Represents a single source→target data flow relationship.

    Attributes:
        edge_id: Unique edge identifier
        source_dataset_id: Source dataset or table identifier
        target_dataset_id: Target dataset or table identifier
        source_columns: List of source column names involved in flow
        target_columns: List of target column names in transformation
        transformation_type: Category of transformation applied
        transformation_sql: Optional SQL statement defining transformation
        created_at: Timestamp when edge was recorded (ISO 8601, UTC)
    """

    edge_id: str
    source_dataset_id: str
    target_dataset_id: str
    source_columns: list[str]
    target_columns: list[str]
    transformation_type: TransformationType
    transformation_sql: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert edge to dictionary representation.

        Returns:
            dict: Edge as dictionary with serialized timestamps and enums

        Examples:
            >>> edge = LineageEdge(
            ...     edge_id='edge-123',
            ...     source_dataset_id='source',
            ...     target_dataset_id='target',
            ...     source_columns=['id', 'name'],
            ...     target_columns=['id', 'name'],
            ...     transformation_type=TransformationType.INGESTION
            ... )
            >>> d = edge.to_dict()
            >>> d['transformation_type'] == 'ingestion'
            True
        """
        d = asdict(self)
        d["transformation_type"] = self.transformation_type.value
        d["created_at"] = self.created_at.isoformat() + "Z"
        return d

    def to_json(self) -> str:
        """Convert edge to JSON string.

        Returns:
            str: JSON representation of lineage edge

        Examples:
            >>> edge = LineageEdge(
            ...     edge_id='edge-123',
            ...     source_dataset_id='source',
            ...     target_dataset_id='target',
            ...     source_columns=['id', 'name'],
            ...     target_columns=['id', 'name'],
            ...     transformation_type=TransformationType.INGESTION
            ... )
            >>> json_str = edge.to_json()
            >>> 'source_dataset_id' in json_str
            True
        """
        return json.dumps(self.to_dict())

@dataclass
class ColumnLineage:
    """Column-level provenance tracking with upstream dependencies.

    Attributes:
        target_table: Target table name
        target_column: Target column name
        upstream_tables: List of source table names
        upstream_columns: Nested list mapping: upstream_columns[i] are
                          source columns from upstream_tables[i]
        transformation_sql: SQL showing how target column is computed
        lineage_depth: Depth of upstream dependencies (0 = source, 1+ = transformed)
    """

    target_table: str
    target_column: str
    upstream_tables: list[str]
    upstream_columns: list[list[str]]
    transformation_sql: str | None = None
    lineage_depth: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary representation.

        Returns:
            dict: Column lineage as dictionary

        Examples:
            >>> col = ColumnLineage(
            ...     target_table='target',
            ...     target_column='total_revenue',
            ...     upstream_tables=['sales'],
            ...     upstream_columns=[['amount']]
            ... )
            >>> d = col.to_dict()
            >>> d['target_column'] == 'total_revenue'
            True
        """
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string.

        Returns:
            str: JSON representation

        Examples:
            >>> col = ColumnLineage(
            ...     target_table='target',
            ...     target_column='total_revenue',
            ...     upstream_tables=['sales'],
            ...     upstream_columns=[['amount']]
            ... )
            >>> json_str = col.to_json()
            >>> 'target_table' in json_str
            True
        """
        return json.dumps(self.to_dict())

class LineageGraph:
    """Builds and queries lineage DAG with cycle detection.

    Maintains bidirectional graph of data flows, supporting queries for
    upstream/downstream tables, column-level lineage tracing, and cycle detection.

    Attributes:
        edges: Dict mapping edge_id to LineageEdge instances
        upstream_map: Dict mapping table_id to list of upstream LineageEdges
        downstream_map: Dict mapping table_id to list of downstream LineageEdges

    Examples:
        >>> graph = LineageGraph()
        >>> graph.add_edge('raw_sales', 'sales_staging', ['id', 'amount'], ['id', 'amount'])
        >>> graph.add_edge('sales_staging', 'sales_summary', ['amount'], ['total_amount'])
        >>> upstream = graph.get_upstream_tables('sales_summary')
        >>> 'raw_sales' in upstream
        True
    """

    def __init__(self):
        """Initialize empty lineage graph."""
        self.edges: dict[str, LineageEdge] = {}
        self.upstream_map: dict[str, list[LineageEdge]] = {}
        self.downstream_map: dict[str, list[LineageEdge]] = {}
        self._column_lineage_cache: dict[tuple, ColumnLineage] = {}

    def add_edge(
        self,
        source_dataset_id: str,
        target_dataset_id: str,
        source_columns: list[str],
        target_columns: list[str],
        transformation_type: TransformationType = TransformationType.CUSTOM_SQL,
        transformation_sql: str | None = None,
    ) -> str:
        """Add a lineage edge to the graph.

        Args:
            source_dataset_id: Source dataset identifier
            target_dataset_id: Target dataset identifier
            source_columns: Column names from source
            target_columns: Column names in target
            transformation_type: Type of transformation applied
            transformation_sql: Optional SQL definition

        Returns:
            str: Edge ID of newly created edge

        Raises:
            ValueError: If edge would create circular dependency

        Examples:
            >>> graph = LineageGraph()
            >>> edge_id = graph.add_edge(
            ...     'source', 'target',
            ...     ['id', 'name'], ['id', 'name'],
            ...     TransformationType.INGESTION
            ... )
            >>> edge_id in graph.edges
            True
        """
        # Check for cycles before adding
        if self._would_create_cycle(source_dataset_id, target_dataset_id):
            raise ValueError(
                f"Adding edge {source_dataset_id} → {target_dataset_id} "
                "would create circular dependency"
            )

        edge = LineageEdge(
            edge_id=str(uuid.uuid4()),
            source_dataset_id=source_dataset_id,
            target_dataset_id=target_dataset_id,
            source_columns=source_columns,
            target_columns=target_columns,
            transformation_type=transformation_type,
            transformation_sql=transformation_sql,
        )

        self.edges[edge.edge_id] = edge

        # Update upstream map for target
        if target_dataset_id not in self.upstream_map:
            self.upstream_map[target_dataset_id] = []
        self.upstream_map[target_dataset_id].append(edge)

        # Update downstream map for source
        if source_dataset_id not in self.downstream_map:
            self.downstream_map[source_dataset_id] = []
        self.downstream_map[source_dataset_id].append(edge)

        logger.info(
            f"Added lineage edge: {source_dataset_id} → {target_dataset_id} "
            f"({transformation_type.value})"
        )

        return edge.edge_id

    def _would_create_cycle(self, source: str, target: str) -> bool:
        """Check if adding edge would create circular dependency.

        Uses DFS to detect if target can reach source in existing graph.

        Args:
            source: Source dataset ID
            target: Target dataset ID

        Returns:
            bool: True if cycle would be created

        Examples:
            >>> graph = LineageGraph()
            >>> graph.add_edge('a', 'b', [], [])
            >>> graph.add_edge('b', 'c', [], [])
            >>> graph._would_create_cycle('c', 'a')
            True
        """
        visited = set()

        def dfs(node: str) -> bool:
            if node == source:
                return True
            if node in visited:
                return False
            visited.add(node)

            for edge in self.downstream_map.get(node, []):
                if dfs(edge.target_dataset_id):
                    return True
            return False

        return dfs(target)

    def get_upstream_tables(self, table_id: str, include_self: bool = False) -> list[str]:
        """Get all upstream tables (sources) for given table.

        Uses recursive search through upstream edges to find all direct
        and transitive data sources.

        Args:
            table_id: Target table identifier
            include_self: Whether to include target table in results

        Returns:
            list of upstream table IDs

        Examples:
            >>> graph = LineageGraph()
            >>> graph.add_edge('raw', 'staging', [], [])
            >>> graph.add_edge('staging', 'mart', [], [])
            >>> upstream = graph.get_upstream_tables('mart')
            >>> 'raw' in upstream and 'staging' in upstream
            True
        """
        upstream = set()
        if include_self:
            upstream.add(table_id)

        visited = set()

        def collect_upstream(node: str) -> None:
            if node in visited:
                return
            visited.add(node)

            for edge in self.upstream_map.get(node, []):
                upstream.add(edge.source_dataset_id)
                collect_upstream(edge.source_dataset_id)

        collect_upstream(table_id)
        return list(upstream)

    def get_downstream_tables(self, table_id: str, include_self: bool = False) -> list[str]:
        """Get all downstream tables (targets) for given table.

        Uses recursive search through downstream edges to find all direct
        and transitive data consumers.

        Args:
            table_id: Source table identifier
            include_self: Whether to include source table in results

        Returns:
            list of downstream table IDs

        Examples:
            >>> graph = LineageGraph()
            >>> graph.add_edge('raw', 'staging', [], [])
            >>> graph.add_edge('staging', 'mart', [], [])
            >>> downstream = graph.get_downstream_tables('raw')
            >>> 'staging' in downstream and 'mart' in downstream
            True
        """
        downstream = set()
        if include_self:
            downstream.add(table_id)

        visited = set()

        def collect_downstream(node: str) -> None:
            if node in visited:
                return
            visited.add(node)

            for edge in self.downstream_map.get(node, []):
                downstream.add(edge.target_dataset_id)
                collect_downstream(edge.target_dataset_id)

        collect_downstream(table_id)
        return list(downstream)

    def trace_column_lineage(self, table_id: str, column_name: str) -> ColumnLineage | None:
        """Trace column-level lineage through transformations.

        Follows a column from target through upstream edges to find its
        source column(s) and all intermediate transformations.

        Args:
            table_id: Target table identifier
            column_name: Target column name to trace

        Returns:
            ColumnLineage with upstream dependencies, or None if not found

        Examples:
            >>> graph = LineageGraph()
            >>> graph.add_edge('raw', 'clean', ['user_id'], ['id'])
            >>> col = graph.trace_column_lineage('clean', 'id')
            >>> col.upstream_columns[0][0] == 'user_id'
            True
        """
        # Check cache first
        cache_key = (table_id, column_name)
        if cache_key in self._column_lineage_cache:
            return self._column_lineage_cache[cache_key]

        upstream_tables = []
        upstream_columns = []
        depth = 0

        # Find direct upstream edges
        for edge in self.upstream_map.get(table_id, []):
            # Find which source columns map to this target column
            target_idx = None
            try:
                target_idx = edge.target_columns.index(column_name)
            except ValueError:
                continue

            if target_idx is not None and target_idx < len(edge.source_columns):
                upstream_tables.append(edge.source_dataset_id)
                upstream_columns.append([edge.source_columns[target_idx]])
                depth += 1

        if not upstream_tables:
            # This is a source column
            col_lineage = ColumnLineage(
                target_table=table_id,
                target_column=column_name,
                upstream_tables=[],
                upstream_columns=[],
                lineage_depth=0,
            )
        else:
            col_lineage = ColumnLineage(
                target_table=table_id,
                target_column=column_name,
                upstream_tables=upstream_tables,
                upstream_columns=upstream_columns,
                lineage_depth=depth,
            )

        self._column_lineage_cache[cache_key] = col_lineage
        return col_lineage

    def detect_cycles(self) -> list[list[str]]:
        """Detect all circular dependencies in lineage graph.

        Uses DFS to find strongly connected components that indicate cycles.

        Returns:
            list of lists, where each inner list is a cycle path

        Examples:
            >>> graph = LineageGraph()
            >>> graph.add_edge('a', 'b', [], [])
            >>> graph.add_edge('b', 'a', [], [])  # This raises ValueError
        """
        # Note: With our validation during add_edge, this should return empty
        # unless edges were added via direct manipulation
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs_cycle(node: str, path: list[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for edge in self.downstream_map.get(node, []):
                next_node = edge.target_dataset_id
                if next_node not in visited:
                    dfs_cycle(next_node, path)
                elif next_node in rec_stack:
                    # Found cycle
                    cycle_start = path.index(next_node)
                    cycles.append(path[cycle_start:] + [next_node])

            path.pop()
            rec_stack.remove(node)

        for node in set(self.upstream_map.keys()) | set(self.downstream_map.keys()):
            if node not in visited:
                dfs_cycle(node, [])

        return cycles

    def to_dict(self) -> dict:
        """Export graph to dictionary representation.

        Returns:
            dict with 'edges' list and graph structure

        Examples:
            >>> graph = LineageGraph()
            >>> graph.add_edge('a', 'b', ['id'], ['id'])
            >>> d = graph.to_dict()
            >>> len(d['edges']) == 1
            True
        """
        return {
            "edges": [edge.to_dict() for edge in self.edges.values()],
            "num_edges": len(self.edges),
        }

    def to_json(self) -> str:
        """Export graph to JSON string.

        Returns:
            str: JSON representation of lineage graph

        Examples:
            >>> graph = LineageGraph()
            >>> graph.add_edge('a', 'b', ['id'], ['id'])
            >>> json_str = graph.to_json()
            >>> 'edges' in json_str
            True
        """
        return json.dumps(self.to_dict())

    def export_to_openmetadata_format(self) -> dict:
        """Export lineage to OpenMetadata format for UI visualization.

        Returns:
            dict: OpenMetadata-compatible lineage structure

        Examples:
            >>> graph = LineageGraph()
            >>> graph.add_edge('source', 'target', ['id'], ['id'])
            >>> om_format = graph.export_to_openmetadata_format()
            >>> 'lineage' in om_format
            True
        """
        lineage_details = []

        for edge in self.edges.values():
            lineage_details.append({
                "upstream": {
                    "dataset_id": edge.source_dataset_id,
                    "columns": edge.source_columns,
                },
                "downstream": {
                    "dataset_id": edge.target_dataset_id,
                    "columns": edge.target_columns,
                },
                "transformation": {
                    "type": edge.transformation_type.value,
                    "sql": edge.transformation_sql,
                },
            })

        return {
            "lineage": lineage_details,
            "total_edges": len(self.edges),
            "exported_at": datetime.now(timezone.utc).isoformat() + "Z",
        }

class LineageRegistry:
    """Persistent lineage registry with PostgreSQL backend.

    Stores lineage edges and column lineage in PostgreSQL for audit trail,
    historical analysis, and schema evolution tracking.
    """

    def __init__(self, db_dsn: str | None = None, table_name: str = "column_lineage_registry"):
        """Initialize lineage registry.

        Args:
            db_dsn: PostgreSQL connection string
            table_name: Table name for lineage storage
        """
        self.db_dsn = db_dsn
        self.table_name = table_name
        self.graph = LineageGraph()

        if self.db_dsn and psycopg:
            self._init_db()

    def _init_db(self) -> None:
        """Initialize PostgreSQL schema for lineage tracking."""
        if not self.db_dsn:
            return

        try:
            with psycopg.connect(self.db_dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        psycopg_sql.SQL("""
                        CREATE TABLE IF NOT EXISTS {} (
                            id BIGSERIAL PRIMARY KEY,
                            edge_id UUID NOT NULL UNIQUE,
                            source_dataset_id VARCHAR(255) NOT NULL,
                            target_dataset_id VARCHAR(255) NOT NULL,
                            source_columns TEXT[] NOT NULL,
                            target_columns TEXT[] NOT NULL,
                            transformation_type VARCHAR(50),
                            transformation_sql TEXT,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                    """).format(psycopg_sql.Identifier(self.table_name))
                    )

                    cur.execute(
                        psycopg_sql.SQL("""
                        CREATE INDEX IF NOT EXISTS {} ON {} (source_dataset_id);
                    """).format(
                            psycopg_sql.Identifier(f"{self.table_name}_source_idx"),
                            psycopg_sql.Identifier(self.table_name),
                        )
                    )

                    cur.execute(
                        psycopg_sql.SQL("""
                        CREATE INDEX IF NOT EXISTS {} ON {} (target_dataset_id);
                    """).format(
                            psycopg_sql.Identifier(f"{self.table_name}_target_idx"),
                            psycopg_sql.Identifier(self.table_name),
                        )
                    )

                    conn.commit()
                    logger.info(f"Initialized lineage registry table: {self.table_name}")
        except Exception as e:
            logger.error(f"Failed to initialize lineage registry: {e}")

    def add_edge(
        self,
        source_dataset_id: str,
        target_dataset_id: str,
        source_columns: list[str],
        target_columns: list[str],
        transformation_type: TransformationType = TransformationType.CUSTOM_SQL,
        transformation_sql: str | None = None,
    ) -> str:
        """Add edge to lineage graph and persist to database.

        Args:
            source_dataset_id: Source dataset ID
            target_dataset_id: Target dataset ID
            source_columns: Source column names
            target_columns: Target column names
            transformation_type: Type of transformation
            transformation_sql: Optional SQL definition

        Returns:
            str: Edge ID

        Raises:
            ValueError: If edge would create cycle
        """
        edge_id = self.graph.add_edge(
            source_dataset_id,
            target_dataset_id,
            source_columns,
            target_columns,
            transformation_type,
            transformation_sql,
        )

        if self.db_dsn and psycopg:
            self._persist_edge(edge_id, source_dataset_id, target_dataset_id,
                             source_columns, target_columns, transformation_type, transformation_sql)

        return edge_id

    def _persist_edge(
        self,
        edge_id: str,
        source_dataset_id: str,
        target_dataset_id: str,
        source_columns: list[str],
        target_columns: list[str],
        transformation_type: TransformationType,
        transformation_sql: str | None,
    ) -> None:
        """Persist edge to PostgreSQL."""
        if not self.db_dsn:
            return

        try:
            with psycopg.connect(self.db_dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        psycopg_sql.SQL("""
                        INSERT INTO {}
                        (edge_id, source_dataset_id, target_dataset_id,
                         source_columns, target_columns, transformation_type, transformation_sql)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """).format(psycopg_sql.Identifier(self.table_name)),
                        (
                            edge_id,
                            source_dataset_id,
                            target_dataset_id,
                            source_columns,
                            target_columns,
                            transformation_type.value,
                            transformation_sql,
                        ),
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to persist lineage edge: {e}")

    def get_graph(self) -> LineageGraph:
        """Get the lineage graph.

        Returns:
            LineageGraph: Current lineage graph

        Examples:
            >>> registry = LineageRegistry()
            >>> graph = registry.get_graph()
            >>> graph.add_edge('a', 'b', [], [])
        """
        return self.graph
