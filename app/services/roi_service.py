from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

class ProductivityROI(BaseModel):
    """Telemetry for manual-step elimination and time reclaimed. High-fidelity Pydantic model."""
    joins_automated: int = 0
    actionable_discrepancies: int = 0
    lots_validated: int = 0
    spatial_conflicts_checked: int = 0
    contracts_cleared: int = 0
    hours_reclaimed: float = 0.0
    quality_flags: int = 0
    datasets_profiled: int = 0

    def as_dict(self) -> dict[str, float | int]:
        return self.dict()

    @property
    def overall_health(self) -> str:
        """Categorize system health based on reclaimed hours."""
        if self.hours_reclaimed > 10: return "PEAK"
        if self.hours_reclaimed > 5: return "OPTIMAL"
        return "STABLE"

class AssetLifecycleROI(BaseModel):
    """Telemetry for lifecycle cost tracking (Avoided Spend & C2O silos)."""
    avoided_spend_total: float = 0.0
    construction_to_ops_savings: float = 0.0
    data_silo_integration_efficiency: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return self.dict()

class ROIAggregator:
    """Industrial-grade ROI computation engine."""
    
    @staticmethod
    def compute(
        *,
        lots_validated: int = 0,
        spatial_conflicts_checked: int = 0,
        contracts_cleared: int = 0,
        joins_automated: int = 0,
        actionable_discrepancies: int = 0,
        quality_flags: int = 0,
        datasets_profiled: int = 0,
    ) -> ProductivityROI:
        """
        Time-savings matrix (engineering baselines). Sanitizes negative inputs.
          lots * 3 min + conflicts * 15 min + contracts * 5 min + quality_flags * 2 min
        """
        lv = max(0, lots_validated)
        sc = max(0, spatial_conflicts_checked)
        cc = max(0, contracts_cleared)
        qf = max(0, quality_flags)
        
        minutes = (lv * 3) + (sc * 15) + (cc * 5) + (qf * 2)
        return ProductivityROI(
            joins_automated=max(0, joins_automated),
            actionable_discrepancies=max(0, actionable_discrepancies),
            lots_validated=lv,
            spatial_conflicts_checked=sc,
            contracts_cleared=cc,
            hours_reclaimed=round(minutes / 60.0, 2),
            quality_flags=qf,
            datasets_profiled=max(0, datasets_profiled),
        )

    @staticmethod
    def compute_lifecycle(
        *,
        avoided_spend: float = 0.0,
        c2o_savings: float = 0.0,
        silo_efficiency: float = 0.0
    ) -> AssetLifecycleROI:
        """Computes lifecycle cost tracking metrics."""
        return AssetLifecycleROI(
            avoided_spend_total=max(0.0, avoided_spend),
            construction_to_ops_savings=max(0.0, c2o_savings),
            data_silo_integration_efficiency=max(0.0, silo_efficiency)
        )
