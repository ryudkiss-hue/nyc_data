"""Impact analysis engine for data lineage changes.

Provides comprehensive impact analysis tools to understand the downstream
effects of changes to datasets, transformations, and schemas.

Classes:
    ImpactAnalysis: Main impact analysis interface
    BreakingChange: Represents a breaking change detected
    ImpactReport: Detailed impact analysis results
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

try:
    import networkx as nx
except ImportError:
    nx = None

logger = logging.getLogger(__name__)


@dataclass
class BreakingChange:
    """Represents a breaking change that could affect downstream systems.

    Attributes:
        change_type: Type of change (deletion, type_change, rename, etc.)
        affected_field: Field or column affected
        old_value: Previous value
        new_value: New value
        severity: Severity level (critical, high, medium, low)
        downstream_impact_count: Number of downstream nodes affected
    """
    change_type: str
    affected_field: str
    old_value: Any = None
    new_value: Any = None
    severity: str = "medium"
    downstream_impact_count: int = 0
    description: str = ""


@dataclass
class ImpactReport:
    """Detailed impact analysis for a node change.

    Attributes:
        node_id: Node being changed
        analysis_timestamp: When analysis was performed
        affected_nodes: All downstream nodes that could be affected
        affected_count: Total count of affected nodes
        affected_users: Users/teams affected
        breaking_changes: List of detected breaking changes
        critical_paths: Dependency chains that will break
        remediation_steps: Recommended steps to mitigate changes
        estimated_effort_hours: Estimated effort to remediate
        risk_score: 0-100 risk assessment
    """
    node_id: str
    analysis_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    affected_nodes: list[str] = field(default_factory=list)
    affected_count: int = 0
    affected_users: list[str] = field(default_factory=list)
    breaking_changes: list[BreakingChange] = field(default_factory=list)
    critical_paths: list[list[str]] = field(default_factory=list)
    remediation_steps: list[str] = field(default_factory=list)
    estimated_effort_hours: float = 0.0
    risk_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "node_id": self.node_id,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
            "affected_nodes": self.affected_nodes,
            "affected_count": self.affected_count,
            "affected_users": self.affected_users,
            "breaking_changes": [
                {
                    "change_type": bc.change_type,
                    "affected_field": bc.affected_field,
                    "old_value": bc.old_value,
                    "new_value": bc.new_value,
                    "severity": bc.severity,
                    "downstream_impact_count": bc.downstream_impact_count,
                    "description": bc.description,
                }
                for bc in self.breaking_changes
            ],
            "critical_paths": self.critical_paths,
            "remediation_steps": self.remediation_steps,
            "estimated_effort_hours": self.estimated_effort_hours,
            "risk_score": self.risk_score,
        }


class ImpactAnalysis:
    """Impact analysis engine for data lineage changes.

    Analyzes the downstream impact of changes to datasets, transformations,
    and schemas. Provides risk assessment and remediation recommendations.
    """

    def __init__(self, dag: Any | None = None) -> None:
        """Initialize impact analysis engine.

        Args:
            dag: DAG object to analyze (LineageCore.DAG)
        """
        self.dag = dag

    def analyze_change(self, node_id: str) -> ImpactReport:
        """Analyze impact of changing a node.

        Args:
            node_id: Node that will be changed

        Returns:
            ImpactReport with detailed impact analysis
        """
        if not self.dag:
            return ImpactReport(node_id=node_id)

        report = ImpactReport(node_id=node_id)

        # Get all affected nodes
        affected = self.dag.get_downstream_consumers(node_id)
        report.affected_nodes = affected
        report.affected_count = len(affected)

        # Collect affected users
        affected_users = set()
        node = self.dag.get_node(node_id)
        if node and node.owner:
            affected_users.add(node.owner)

        for affected_id in affected:
            affected_node = self.dag.get_node(affected_id)
            if affected_node and affected_node.owner:
                affected_users.add(affected_node.owner)

        report.affected_users = list(affected_users)

        # Find critical paths
        report.critical_paths = self._find_critical_paths(node_id)

        # Estimate remediation effort
        report.estimated_effort_hours = self._estimate_effort(affected)

        # Calculate risk score
        report.risk_score = self._calculate_risk_score(affected, report.critical_paths)

        # Generate remediation steps
        report.remediation_steps = self._generate_remediation_steps(
            node_id, affected, report.breaking_changes
        )

        return report

    def find_breaking_changes(
        self, old_schema: dict[str, Any], new_schema: dict[str, Any], node_id: str
    ) -> list[BreakingChange]:
        """Detect breaking changes between two schema versions.

        Args:
            old_schema: Previous schema definition
            new_schema: New schema definition
            node_id: Node with schema change

        Returns:
            List of BreakingChange objects
        """
        changes = []

        if not self.dag:
            return changes

        affected_count = len(self.dag.get_downstream_consumers(node_id))

        # Detect column deletions
        old_cols = set(old_schema.get("columns", {}).keys())
        new_cols = set(new_schema.get("columns", {}).keys())

        for deleted_col in old_cols - new_cols:
            change = BreakingChange(
                change_type="column_deletion",
                affected_field=deleted_col,
                old_value=old_schema["columns"][deleted_col],
                severity="critical",
                downstream_impact_count=affected_count,
                description=f"Column '{deleted_col}' was deleted",
            )
            changes.append(change)

        # Detect type changes
        for col in old_cols & new_cols:
            old_type = old_schema["columns"][col].get("type")
            new_type = new_schema["columns"][col].get("type")

            if old_type and new_type and old_type != new_type:
                change = BreakingChange(
                    change_type="type_change",
                    affected_field=col,
                    old_value=old_type,
                    new_value=new_type,
                    severity="high",
                    downstream_impact_count=affected_count,
                    description=f"Column '{col}' type changed from {old_type} to {new_type}",
                )
                changes.append(change)

        # Detect nullability changes
        for col in old_cols & new_cols:
            old_nullable = old_schema["columns"][col].get("nullable", True)
            new_nullable = new_schema["columns"][col].get("nullable", True)

            if old_nullable and not new_nullable:
                change = BreakingChange(
                    change_type="null_constraint_change",
                    affected_field=col,
                    old_value=f"nullable={old_nullable}",
                    new_value=f"nullable={new_nullable}",
                    severity="high",
                    downstream_impact_count=affected_count,
                    description=f"Column '{col}' is now NOT NULL",
                )
                changes.append(change)

        return changes

    def estimate_downstream_impact(self, node_id: str) -> dict[str, float]:
        """Estimate impact scores for each downstream node.

        Args:
            node_id: Source node for impact analysis

        Returns:
            Dict mapping downstream node IDs to impact scores (0-100)
        """
        if not self.dag or nx is None:
            return {}

        impact_scores = {}
        downstream = self.dag.get_downstream_consumers(node_id)

        for affected_id in downstream:
            # Calculate impact based on:
            # 1. Distance from source (closer = higher impact)
            # 2. Number of downstream consumers of this node
            # 3. Node type (sink nodes have lower relative impact)

            affected_node = self.dag.get_node(affected_id)
            if not affected_node:
                continue

            # Get paths from source to target
            try:
                paths = list(
                    nx.all_simple_paths(self.dag.graph, source=node_id, target=affected_id)
                )
                shortest_path_length = min(len(p) for p in paths) if paths else 999

            except Exception:
                shortest_path_length = 999

            # Base score: inverse distance (closer nodes have higher impact)
            distance_score = 100.0 / (shortest_path_length + 1)

            # Multiplier based on downstream count
            downstream_count = len(self.dag.get_downstream_consumers(affected_id))
            downstream_multiplier = 1.0 + (downstream_count * 0.1)

            # Type-based adjustment
            type_multiplier = {
                "sink": 0.5,
                "materialization": 0.8,
                "aggregation": 1.2,
                "transformation": 1.0,
                "validation": 0.7,
                "ingestion": 0.1,
            }.get(affected_node.node_type.value, 1.0)

            score = min(100.0, distance_score * downstream_multiplier * type_multiplier)
            impact_scores[affected_id] = score

        return impact_scores

    def _find_critical_paths(self, node_id: str) -> list[list[str]]:
        """Find critical dependency paths that include the node."""
        if not self.dag or nx is None:
            return []

        critical_paths = []

        try:
            downstream = self.dag.get_downstream_consumers(node_id)

            # Find paths to critical consumers (sinks)
            for downstream_id in downstream:
                downstream_node = self.dag.get_node(downstream_id)
                if downstream_node and downstream_node.node_type.value == "sink":
                    try:
                        paths = list(
                            nx.all_simple_paths(
                                self.dag.graph, source=node_id, target=downstream_id
                            )
                        )
                        critical_paths.extend(paths)
                    except Exception:
                        pass

            # Return longest critical paths
            critical_paths.sort(key=len, reverse=True)
            return critical_paths[:5]  # Top 5 longest paths

        except Exception:
            return []

    def _estimate_effort(self, affected_nodes: list[str]) -> float:
        """Estimate remediation effort in hours."""
        # Base effort + per-node effort
        base_effort = 2.0  # 2 hours for planning and testing
        per_node_effort = 1.0  # 1 hour per affected node
        return base_effort + (len(affected_nodes) * per_node_effort)

    def _calculate_risk_score(self, affected_nodes: list[str], critical_paths: list[list[str]]) -> float:
        """Calculate overall risk score (0-100)."""
        # Risk based on affected node count
        node_count_score = min(100.0, len(affected_nodes) * 5.0)

        # Risk based on critical paths
        critical_path_score = len(critical_paths) * 10.0

        # Risk based on sink nodes affected
        sink_risk = 0.0
        if self.dag:
            for affected_id in affected_nodes:
                node = self.dag.get_node(affected_id)
                if node and node.node_type.value == "sink":
                    sink_risk += 15.0

        # Combine scores
        risk_score = min(100.0, (node_count_score + critical_path_score + sink_risk) / 3.0)
        return risk_score

    def _generate_remediation_steps(
        self, node_id: str, affected_nodes: list[str], breaking_changes: list[BreakingChange]
    ) -> list[str]:
        """Generate human-readable remediation steps."""
        steps = []

        steps.append(
            f"Review {len(affected_nodes)} affected downstream nodes and their dependencies"
        )

        if breaking_changes:
            steps.append(
                f"Address {len(breaking_changes)} breaking changes in schema/structure"
            )

        # Suggest testing strategy
        if len(affected_nodes) <= 5:
            steps.append("Update and test affected nodes individually")
        else:
            steps.append("Update and test affected nodes in dependency order")
            steps.append("Use staging environment for batch testing")

        # Suggest rollback strategy
        steps.append("Prepare rollback plan before deploying changes")
        steps.append("Notify affected teams of changes")

        # Add notification suggestion
        if any(node for node in affected_nodes if len(node) > 0):
            steps.append("Send impact notifications to affected data consumers")

        return steps
