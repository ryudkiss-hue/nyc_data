import logging
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from app.analytics import (
    contract_dispatch_clearance,
    productivity_ada_dashboard,
    qa_qc_inventory_ledger,
    spatial_conflict_detection,
)

logger = logging.getLogger(__name__)

class WorkflowStrategy(ABC):
    """Abstract base class for workflow strategies."""
    @abstractmethod
    def execute(self, frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
        pass

class QAQCStrategy(WorkflowStrategy):
    """Strategy for quality assurance and control."""
    def execute(self, frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
        for _key in ("lot_info", "mappluto", "complaints_311"):
            if frames.get(_key, pd.DataFrame()).empty:
                logger.warning("QAQC: required input '%s' is empty or missing; results may be incomplete", _key)

        ledger, stale, joins, flags = qa_qc_inventory_ledger(
            frames.get("lot_info", pd.DataFrame()),
            frames.get("mappluto", pd.DataFrame()),
            frames.get("complaints_311", pd.DataFrame())
        )
        return {"ledger": ledger, "stale_311": stale, "joins": joins, "flags": flags}

class SpatialStrategy(WorkflowStrategy):
    """Strategy for spatial conflict detection."""
    def execute(self, frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
        conflicts, joins = spatial_conflict_detection(
            frames.get("weekly_construction", pd.DataFrame()),
            frames.get("street_permits", pd.DataFrame()),
            frames.get("capital_blocks", pd.DataFrame())
        )
        return {"conflicts": conflicts, "joins": joins}

class ContractStrategy(WorkflowStrategy):
    """Strategy for contract clearance."""
    def execute(self, frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
        cleared, parks, joins = contract_dispatch_clearance(
            frames.get("violations", pd.DataFrame()),
            frames.get("tree_damage", pd.DataFrame())
        )
        return {"cleared": cleared, "parks": parks, "joins": joins}

class ProductivityStrategy(WorkflowStrategy):
    """Strategy for productivity analytics."""
    def execute(self, frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
        data = productivity_ada_dashboard(
            frames.get("built", pd.DataFrame()),
            frames.get("ramp_progress", pd.DataFrame()),
            frames.get("pedestrian_demand", pd.DataFrame())
        )
        return {"productivity": data}

class WorkflowOrchestrator:
    """Service for event aggregation and multi-agency operational workflow modeling."""

    def __init__(self):
        self.strategies = {
            "qa": QAQCStrategy(),
            "spatial": SpatialStrategy(),
            "contract": ContractStrategy(),
            "productivity": ProductivityStrategy()
        }

    def run_all(self, frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
        results = {}
        for name, strategy in self.strategies.items():
            results[name] = strategy.execute(frames)
        return results

    def aggregate_events(self, events):
        """Aggregate events across multiple agencies."""
        logger.info("Aggregating operational events...")
        return {"aggregated_count": len(events), "status": "processed"}

    def model_operational_workflow(self, workflow_id, data):
        """Model an operational workflow."""
        logger.info(f"Modeling workflow: {workflow_id}")
        self.workflows[workflow_id] = data
        return {"workflow_id": workflow_id, "status": "modeled"}
