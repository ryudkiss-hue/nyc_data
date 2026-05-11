"""
DAG Registry and Validation for NYC DOT Sidewalk Inspection Orchestration.

Provides:
- Central registry of all DAGs
- DAG validation (structure, dependencies, scheduling)
- Health checks
- Metadata queries
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)

# ============================================================================
# DAG REGISTRY
# ============================================================================

DAG_REGISTRY: Dict[str, Dict] = {
    "sidewalk_incident_ingestion": {
        "description": "Daily ingestion of 311 sidewalk complaints and incidents from Socrata",
        "schedule_interval": "0 2 * * *",  # 02:00 UTC daily
        "schedule_human": "Daily at 02:00 UTC",
        "owner": "nyc-dot-data-eng",
        "sla_seconds": 3600,  # 1 hour
        "retries": 3,
        "retry_delay_minutes": 5,
        "depends_on": [],  # Independent DAG
        "downstream_tasks": [
            "kpi_materialization",
            "repair_scheduling",
        ],
        "tags": ["ingestion", "311", "sidewalk", "daily"],
        "doc_md": "Fetch new 311 sidewalk incident data from Socrata, validate, and load to fact_incidents table.",
    },
    "repair_scheduling": {
        "description": "Weekly optimization of repair schedules based on incident severity and contractor availability",
        "schedule_interval": "0 1 * * 0",  # 01:00 UTC on Sunday
        "schedule_human": "Weekly on Sunday at 01:00 UTC",
        "owner": "nyc-dot-data-eng",
        "sla_seconds": 7200,  # 2 hours
        "retries": 2,
        "retry_delay_minutes": 10,
        "depends_on": ["sidewalk_incident_ingestion"],  # Wait for incident ingestion
        "downstream_tasks": ["kpi_materialization"],
        "tags": ["optimization", "scheduling", "repair", "weekly"],
        "doc_md": "Optimize repair schedules using material-aware costs and contractor availability.",
    },
    "kpi_materialization": {
        "description": "Scheduled computation and materialization of NYC DOT operational KPIs for BI dashboards",
        "schedule_interval": "0 3 * * *",  # 03:00 UTC daily
        "schedule_human": "Daily at 03:00 UTC",
        "owner": "nyc-dot-data-eng",
        "sla_seconds": 3600,  # 1 hour
        "retries": 3,
        "retry_delay_minutes": 5,
        "depends_on": ["sidewalk_incident_ingestion", "repair_scheduling"],
        "downstream_tasks": [],  # Terminal DAG (feeds dashboards)
        "tags": ["kpi", "materialization", "daily", "dashboard"],
        "doc_md": "Materialize KPIs (material-aware defect rates, ADA compliance, hazard coverage, cost analysis) for BI dashboards.",
    },
}

# ============================================================================
# FUNCTION: Get DAG metadata
# ============================================================================


def get_dag_metadata(dag_id: str) -> Optional[Dict]:
    """
    Get metadata for a DAG.

    Args:
        dag_id: DAG identifier

    Returns:
        DAG metadata dictionary or None if not found

    Example:
        >>> metadata = get_dag_metadata("sidewalk_incident_ingestion")
        >>> print(metadata["schedule_human"])
        Daily at 02:00 UTC
    """
    return DAG_REGISTRY.get(dag_id)


# ============================================================================
# FUNCTION: List all DAGs
# ============================================================================


def list_all_dags() -> List[str]:
    """
    Get list of all registered DAG IDs.

    Returns:
        List of DAG identifiers

    Example:
        >>> dags = list_all_dags()
        >>> print(dags)
        ['sidewalk_incident_ingestion', 'repair_scheduling', 'kpi_materialization']
    """
    return list(DAG_REGISTRY.keys())


# ============================================================================
# FUNCTION: Validate DAG dependencies
# ============================================================================


def validate_dag_dependencies() -> Tuple[bool, List[str]]:
    """
    Validate that DAG dependencies form a valid DAG (no cycles, valid references).

    Returns:
        Tuple of (is_valid, error_messages)

    Example:
        >>> is_valid, errors = validate_dag_dependencies()
        >>> if not is_valid:
        ...     for error in errors:
        ...         print(error)
    """
    errors: List[str] = []
    all_dag_ids = set(DAG_REGISTRY.keys())

    for dag_id, metadata in DAG_REGISTRY.items():
        # Check that all dependencies exist
        for dep_id in metadata.get("depends_on", []):
            if dep_id not in all_dag_ids:
                errors.append(f"DAG '{dag_id}' depends on non-existent DAG '{dep_id}'")

        # Check that all downstream tasks exist
        for downstream_id in metadata.get("downstream_tasks", []):
            if downstream_id not in all_dag_ids:
                errors.append(
                    f"DAG '{dag_id}' has non-existent downstream task '{downstream_id}'"
                )

    # Check for cycles using depth-first search
    def has_cycle(dag_id: str, visited: set, rec_stack: set) -> bool:
        visited.add(dag_id)
        rec_stack.add(dag_id)

        for dep_id in DAG_REGISTRY[dag_id].get("depends_on", []):
            if dep_id not in visited:
                if has_cycle(dep_id, visited, rec_stack):
                    return True
            elif dep_id in rec_stack:
                return True

        rec_stack.remove(dag_id)
        return False

    visited: set = set()
    for dag_id in all_dag_ids:
        if dag_id not in visited:
            if has_cycle(dag_id, visited, set()):
                errors.append(f"Cyclic dependency detected involving DAG '{dag_id}'")
                break

    return len(errors) == 0, errors


# ============================================================================
# FUNCTION: Get DAG execution order
# ============================================================================


def get_dag_execution_order() -> List[str]:
    """
    Get DAGs in topological order for execution (dependencies first).

    Returns:
        List of DAG IDs in execution order

    Example:
        >>> order = get_dag_execution_order()
        >>> print(order)
        ['sidewalk_incident_ingestion', 'repair_scheduling', 'kpi_materialization']
    """
    all_dag_ids = set(DAG_REGISTRY.keys())
    in_degree = {dag_id: 0 for dag_id in all_dag_ids}
    adj_list = {dag_id: [] for dag_id in all_dag_ids}

    # Build adjacency list and in-degree count
    for dag_id, metadata in DAG_REGISTRY.items():
        for dep_id in metadata.get("depends_on", []):
            adj_list[dep_id].append(dag_id)
            in_degree[dag_id] += 1

    # Kahn's algorithm for topological sort
    queue = [dag_id for dag_id in all_dag_ids if in_degree[dag_id] == 0]
    result = []

    while queue:
        dag_id = queue.pop(0)
        result.append(dag_id)

        for next_dag in adj_list[dag_id]:
            in_degree[next_dag] -= 1
            if in_degree[next_dag] == 0:
                queue.append(next_dag)

    return result


# ============================================================================
# FUNCTION: Get DAG dependencies
# ============================================================================


def get_dag_dependencies(dag_id: str) -> List[str]:
    """
    Get all DAGs that must complete before given DAG can run.

    Args:
        dag_id: Target DAG identifier

    Returns:
        List of dependency DAG IDs (recursively resolved)

    Example:
        >>> deps = get_dag_dependencies("kpi_materialization")
        >>> print(deps)
        ['sidewalk_incident_ingestion', 'repair_scheduling']
    """
    if dag_id not in DAG_REGISTRY:
        return []

    visited = set()
    to_process = [dag_id]
    dependencies = []

    while to_process:
        current_dag = to_process.pop(0)
        if current_dag in visited:
            continue

        visited.add(current_dag)
        direct_deps = DAG_REGISTRY[current_dag].get("depends_on", [])
        dependencies.extend(direct_deps)

        for dep_id in direct_deps:
            if dep_id not in visited:
                to_process.append(dep_id)

    return dependencies


# ============================================================================
# FUNCTION: Get DAG dependents (downstream DAGs)
# ============================================================================


def get_dag_dependents(dag_id: str) -> List[str]:
    """
    Get all DAGs that depend on the given DAG.

    Args:
        dag_id: Source DAG identifier

    Returns:
        List of dependent DAG IDs (recursively resolved)

    Example:
        >>> dependents = get_dag_dependents("sidewalk_incident_ingestion")
        >>> print(dependents)
        ['repair_scheduling', 'kpi_materialization']
    """
    dependents = set()

    for other_dag_id, metadata in DAG_REGISTRY.items():
        if dag_id in metadata.get("depends_on", []):
            dependents.add(other_dag_id)
            # Recursively get dependents of dependents
            dependents.update(get_dag_dependents(other_dag_id))

    return list(dependents)


# ============================================================================
# FUNCTION: Health check
# ============================================================================


def health_check() -> Tuple[bool, Dict]:
    """
    Perform comprehensive DAG registry health checks.

    Returns:
        Tuple of (is_healthy, health_report)

    Example:
        >>> is_healthy, report = health_check()
        >>> if not is_healthy:
        ...     print(f"Issues found: {report['errors']}")
    """
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_dags": len(DAG_REGISTRY),
        "dags": {},
        "errors": [],
        "warnings": [],
    }

    # Validate dependencies
    is_valid, dep_errors = validate_dag_dependencies()
    if not is_valid:
        report["errors"].extend(dep_errors)

    # Check each DAG
    for dag_id, metadata in DAG_REGISTRY.items():
        dag_health = {
            "exists": True,
            "schedule": metadata.get("schedule_human"),
            "sla_seconds": metadata.get("sla_seconds"),
            "retries": metadata.get("retries"),
            "dependencies": metadata.get("depends_on", []),
        }
        report["dags"][dag_id] = dag_health

        # Warn if SLA is too short
        if metadata.get("sla_seconds", 0) < 300:
            report["warnings"].append(
                f"DAG '{dag_id}' has very short SLA ({metadata['sla_seconds']}s)"
            )

    report["is_healthy"] = len(report["errors"]) == 0

    return report["is_healthy"], report


# ============================================================================
# INITIALIZATION & VALIDATION
# ============================================================================

if __name__ == "__main__":
    # Perform health check on import
    is_healthy, report = health_check()

    if not is_healthy:
        print("❌ DAG Registry Health Check Failed:")
        for error in report["errors"]:
            print(f"  ERROR: {error}")
        sys.exit(1)

    print("✅ DAG Registry Health Check Passed")
    print(f"Total DAGs: {report['total_dags']}")

    # Print DAG execution order
    print("\nDAG Execution Order (dependencies first):")
    for i, dag_id in enumerate(get_dag_execution_order(), 1):
        metadata = get_dag_metadata(dag_id)
        print(f"  {i}. {dag_id} ({metadata['schedule_human']})")
