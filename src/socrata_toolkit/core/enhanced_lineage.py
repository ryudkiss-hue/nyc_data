"""Enhanced lineage tracking: full workflow from datasets → marts → dashboards → reports → exports.

Tracks complete data provenance across all stages:
- Fetch: Raw data ingestion from Socrata
- Stage: Deduplication & transformation in staging layer
- Materialize: Analytics mart creation
- Dashboard: Visualization specification
- Export: Report generation (PDF, Excel, PowerPoint, etc.)

Provides:
- Event logging with metadata
- Upstream/downstream chain traversal
- DAG construction and visualization
- Error tracking with recovery paths
"""
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LineageEvent:
    """Single lineage event in the workflow."""

    event_type: str  # fetch, stage, materialize, dashboard, export
    source: str  # Source table/dataset name(s)
    target: str  # Target table/dataset name
    timestamp: str = None  # ISO 8601 timestamp
    row_count: Optional[int] = None
    status: str = "success"  # success, failure, skipped
    metadata: Optional[dict[str, Any]] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON."""
        return json.dumps(self.to_dict())


class LineageNode:
    """Node in the lineage DAG."""

    def __init__(self, name: str, node_type: str, metadata: Optional[dict] = None):
        self.name = name
        self.node_type = node_type  # dataset, staging, mart, dashboard, export
        self.metadata = metadata or {}
        self.incoming_edges = []
        self.outgoing_edges = []

    def to_dict(self) -> dict:
        return {
            "id": self.name,
            "label": self.name,
            "type": self.node_type,
            "metadata": self.metadata,
        }


# Convenience subclasses
class DatasetNode(LineageNode):
    def __init__(self, name: str, metadata: Optional[dict] = None):
        super().__init__(name, "dataset", metadata)


class MartNode(LineageNode):
    def __init__(self, name: str, metadata: Optional[dict] = None):
        super().__init__(name, "mart", metadata)


class DashboardNode(LineageNode):
    def __init__(self, name: str, metadata: Optional[dict] = None):
        super().__init__(name, "dashboard", metadata)


class ReportNode(LineageNode):
    def __init__(self, name: str, metadata: Optional[dict] = None):
        super().__init__(name, "report", metadata)


class ExportNode(LineageNode):
    def __init__(self, name: str, metadata: Optional[dict] = None):
        super().__init__(name, "export", metadata)


class LineageTracker:
    """Track and record lineage events throughout the workflow."""

    def __init__(self):
        self.events: list[LineageEvent] = []

    def record_event(
        self,
        event_type: str,
        source: str,
        target: str,
        row_count: Optional[int] = None,
        status: str = "success",
        metadata: Optional[dict] = None,
    ):
        """Record a lineage event.

        Args:
            event_type: Type of event (fetch, stage, materialize, dashboard, export)
            source: Source table/dataset
            target: Target table/dataset
            row_count: Number of rows processed
            status: Event status (success, failure, skipped)
            metadata: Additional event metadata
        """
        event = LineageEvent(
            event_type=event_type,
            source=source,
            target=target,
            row_count=row_count,
            status=status,
            metadata=metadata,
        )
        self.events.append(event)
        logger.info(f"Lineage event: {event_type} {source} → {target} ({status})")

    def get_events(self) -> list[LineageEvent]:
        """Get all recorded events."""
        return self.events.copy()

    def get_events_by_type(self, event_type: str) -> list[LineageEvent]:
        """Get events filtered by type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_upstream_chain(self, target: str) -> list[LineageEvent]:
        """Get all events that led to this target (upstream lineage)."""
        chain = []
        current_target = target

        # Walk backwards through events to find sources
        for event in reversed(self.events):
            if event.target == current_target:
                chain.insert(0, event)
                current_target = event.source
                if event.event_type == "fetch":
                    break  # Reached the source

        return chain

    def get_downstream_chain(self, source: str) -> list[LineageEvent]:
        """Get all events that depend on this source (downstream lineage)."""
        chain = []
        current_source = source

        # Walk forwards through events to find targets
        for event in self.events:
            if event.source == current_source or current_source in event.source.split(","):
                chain.append(event)
                current_source = event.target

        return chain

    def get_failed_events(self) -> list[LineageEvent]:
        """Get all failed events."""
        return [e for e in self.events if e.status == "failure"]

    def to_dict(self) -> dict:
        """Convert all events to dictionary."""
        return {"events": [e.to_dict() for e in self.events]}

    def to_json(self) -> str:
        """Export all events as JSON."""
        return json.dumps(self.to_dict(), indent=2)


class LineageDAG:
    """Directed Acyclic Graph of lineage nodes and edges."""

    def __init__(self):
        self.nodes: dict[str, LineageNode] = {}
        self.edges: list[tuple] = []

    def add_node(self, name: str, node_type: str, metadata: Optional[dict] = None):
        """Add a node to the DAG."""
        if name not in self.nodes:
            self.nodes[name] = LineageNode(name, node_type, metadata)

    def add_edge(self, source: str, target: str):
        """Add an edge between nodes."""
        self.edges.append((source, target))

    @classmethod
    def from_tracker(cls, tracker: LineageTracker) -> "LineageDAG":
        """Build DAG from a LineageTracker."""
        dag = cls()

        # Extract all unique sources and targets
        for event in tracker.get_events():
            # Add source node(s)
            for src in event.source.split(","):
                src = src.strip()
                dag.add_node(src, cls._infer_node_type(src, event.event_type), {"status": event.status})

            # Add target node
            dag.add_node(event.target, cls._infer_node_type(event.target, event.event_type), {"status": event.status})

            # Add edge
            for src in event.source.split(","):
                src = src.strip()
                dag.add_edge(src, event.target)

        return dag

    @staticmethod
    def _infer_node_type(name: str, event_type: str) -> str:
        """Infer node type from name or event type."""
        if event_type == "fetch":
            return "dataset"
        elif event_type == "stage":
            return "staging"
        elif event_type == "materialize":
            return "mart"
        elif event_type == "dashboard":
            return "dashboard"
        elif event_type == "export":
            return "export"
        else:
            # Infer from name pattern
            if name.startswith("raw."):
                return "dataset"
            elif name.startswith("staging."):
                return "staging"
            elif name.startswith("analytics."):
                return "mart"
            elif name.startswith("dashboards/"):
                return "dashboard"
            elif name.startswith("reports/"):
                return "export"
            else:
                return "unknown"

    def to_dict(self) -> dict:
        """Convert DAG to dictionary."""
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [{"source": s, "target": t} for s, t in self.edges],
        }

    def to_json(self) -> str:
        """Export DAG as JSON."""
        return json.dumps(self.to_dict(), indent=2)

    def to_mermaid(self) -> str:
        """Export DAG as Mermaid diagram."""
        lines = ["graph TD"]

        for node_name, node in self.nodes.items():
            # Sanitize node name for Mermaid
            safe_name = node_name.replace(".", "_").replace("/", "_").replace("-", "_")
            label = node_name.split(".")[-1].split("/")[-1]  # Use last part as label
            lines.append(f'    {safe_name}["{label}"]')

        for source, target in self.edges:
            safe_source = source.replace(".", "_").replace("/", "_").replace("-", "_")
            safe_target = target.replace(".", "_").replace("/", "_").replace("-", "_")
            lines.append(f"    {safe_source} --> {safe_target}")

        return "\n".join(lines)

    def get_upstream_nodes(self, node_name: str) -> list[str]:
        """Get all upstream nodes that feed into this node."""
        upstream = set()

        def traverse_upstream(name: str):
            for source, target in self.edges:
                if target == name:
                    upstream.add(source)
                    traverse_upstream(source)

        traverse_upstream(node_name)
        return list(upstream)

    def get_downstream_nodes(self, node_name: str) -> list[str]:
        """Get all downstream nodes that depend on this node."""
        downstream = set()

        def traverse_downstream(name: str):
            for source, target in self.edges:
                if source == name:
                    downstream.add(target)
                    traverse_downstream(target)

        traverse_downstream(node_name)
        return list(downstream)
