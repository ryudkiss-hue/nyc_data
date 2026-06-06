from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

class SurfaceRating(IntEnum):
    """NYSDOT Pavement Surface Rating (SR) Scale 1-10."""
    EXCELLENT_NEW = 10
    EXCELLENT = 9
    GOOD_STABLE = 8
    GOOD_MINIOR_DISTRESS = 7
    FAIR_CORRECTIVE_TRIGGER = 6
    POOR_REHAB_TRIGGER = 5
    POOR_STRUCTURAL_DISTRESS = 4
    FAILED_RECONSTRUCTION_TRIGGER = 3
    FAILED_EXTREME = 2
    FAILED_IMPASSABLE = 1

    @classmethod
    def get_strategy(cls, sr: int) -> str:
        if sr >= 7:
            return "PREVENTIVE_MAINTENANCE"
        elif sr == 6:
            return "CORRECTIVE_MAINTENANCE"
        elif sr >= 4:
            return "REHABILITATION"
        else:
            return "RECONSTRUCTION"

class PavementType(Enum):
    FLEXIBLE_HMA = "flexible" # Hot Mix Asphalt
    RIGID_PCC = "rigid"       # Portland Cement Concrete
    OVERLAY = "overlay"

@dataclass
class PavementDesignParameters:
    aadt: float
    truck_percent: float
    truck_factor: float
    growth_rate: float
    design_life_years: int
    directional_factor: float = 0.5
    lane_factor: float = 0.8

class NYSDOTPavementEngine:
    """
    Core engineering logic derived from NYSDOT HDM Chapter 18 and FHWA-RD-02-057.
    """

    @staticmethod
    def calculate_esal(params: PavementDesignParameters) -> float:
        """
        Calculate cumulative 80kN (18kip) Equivalent Single Axle Loads (ESALs).
        Formula: ESAL = AADT * %Trucks * Tf * G * D * L * 365 * Y
        """
        # Calculate Growth Factor (G)
        if params.growth_rate == 0:
            growth_factor = params.design_life_years
        else:
            r = params.growth_rate
            n = params.design_life_years
            growth_factor = ((1 + r)**n - 1) / r
            
        esal = (
            params.aadt * 
            (params.truck_percent / 100.0) * 
            params.truck_factor * 
            growth_factor * 
            params.directional_factor * 
            params.lane_factor * 
            365
        )
        return float(esal)

    @staticmethod
    def estimate_iri_progression(iri_initial: float, cumulative_esal: float, pavement_type: PavementType) -> float:
        """
        Predict International Roughness Index (IRI) progression.
        Heuristic based on FHWA research: IRI_t = IRI_0 + a(ESAL)^b
        """
        # Coefficients typical for NY environments
        if pavement_type == PavementType.RIGID_PCC:
            a, b = 0.015, 0.6
        else:
            a, b = 0.025, 0.7
            
        iri_t = iri_initial + a * (cumulative_esal / 1e6)**b
        return float(iri_t)

    @staticmethod
    def calculate_user_cost_impact(iri: float, baseline_iri: float = 1.0) -> dict[str, float]:
        """
        Quantitative economic impact of pavement roughness on Vehicle Operating Costs (VOC).
        Derived from FHWA-RD-02-057.
        """
        delta_iri = max(0.0, iri - baseline_iri)
        
        # Heuristic: 1.0 m/km increase in IRI -> 1.5% fuel increase, 10% maintenance increase
        fuel_increase_pct = delta_iri * 1.5
        maintenance_increase_pct = delta_iri * 10.0
        
        return {
            "iri": iri,
            "fuel_cost_increase_factor": 1.0 + (fuel_increase_pct / 100.0),
            "maintenance_cost_increase_factor": 1.0 + (maintenance_increase_pct / 100.0),
            "total_voc_penalty_pct": fuel_increase_pct + (maintenance_increase_pct * 0.4) # weighted average
        }

    @staticmethod
    def get_mr_recommendation(sr: int, pavement_type: PavementType) -> dict[str, Any]:
        """
        Provides specific NYSDOT M&R strategy and typical actions.
        """
        strategy = SurfaceRating.get_strategy(sr)
        
        actions = {
            "PREVENTIVE_MAINTENANCE": ["Crack Sealing", "Microsurfacing", "6.3mm Polymer Overlay"],
            "CORRECTIVE_MAINTENANCE": ["Mill and Fill (1.5-2\")", "Localized Patching"],
            "REHABILITATION": ["Thick HMA Overlay", "Rubblization", "Base Repair"],
            "RECONSTRUCTION": ["Full Depth Replacement", "Subgrade Stabilization"]
        }
        
        return {
            "surface_rating": sr,
            "strategy": strategy,
            "recommended_actions": actions.get(strategy, []),
            "nysdot_standard": "HDM Chapter 18"
        }

def evaluate_pavement_safety_risk(iri: float, rut_depth_mm: float = 0.0) -> float:
    """
    Calculates a safety risk score (0-1.0) based on IRI and Rutting (Hydroplaning risk).
    """
    # IRI risk: tire hop and braking distance
    iri_risk = min(0.5, (max(0.0, iri - 1.5) / 4.0) * 0.5)
    
    # Rut risk: hydroplaning/birdbaths
    rut_risk = min(0.5, (rut_depth_mm / 25.0) * 0.5)
    
    return float(iri_risk + rut_risk)
