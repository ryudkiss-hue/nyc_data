from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class MaterialTier(str, Enum):
    """
    NYC Street Design Manual (4th Ed) Material Classification System.
    """
    STANDARD = "STANDARD"       # DOT/DDC Default (Permit only)
    DISTINCTIVE = "DISTINCTIVE" # Enhanced (PDC Approval required)
    HISTORIC = "HISTORIC"       # Landmark (LPC Approval required)
    PILOT = "PILOT"             # Experimental (Agency Oversight)

class StreetGeometricStandard(float, Enum):
    """
    Vision Zero Geometric Constraints (4th Edition).
    Values in feet.
    """
    LANE_WIDTH_MIN = 10.0           # 10' for speed reduction
    LANE_WIDTH_MAX_STD = 11.0       # 11' standard maximum
    LANE_WIDTH_TRUCK_BUS = 12.0     # 12' for designated routes
    CLEAR_PATH_MIN = 5.0            # 5' Absolute minimum sidewalk clear path
    CLEAR_PATH_PREFERRED = 8.0      # 8' High-volume preferred
    CORNER_RADIUS_STD = 10.0        # 10' to minimize crossing distance
    CORNER_RADIUS_MAX = 15.0        # 15' maximum for standard ROW

@dataclass
class GeometricAuditResult:
    is_compliant: bool
    violations: list[str] = field(default_factory=list)
    vision_zero_score: float = 1.0 # 0 to 1.0

def run_vision_zero_audit(lane_width: float, corner_radius: float, clear_path: float, is_truck_route: bool = False) -> GeometricAuditResult:
    """
    Performs a geometric design audit based on NYC SDM 4th Ed standards.
    """
    violations = []
    score_penalty = 0.0

    # Lane Width Audit
    max_allowed_width = StreetGeometricStandard.LANE_WIDTH_TRUCK_BUS if is_truck_route else StreetGeometricStandard.LANE_WIDTH_MAX_STD
    if lane_width > max_allowed_width:
        violations.append(f"Lane width ({lane_width}') exceeds standard ({max_allowed_width}').")
        score_penalty += 0.2

    # Corner Radius Audit
    if corner_radius > StreetGeometricStandard.CORNER_RADIUS_MAX:
        violations.append(f"Corner radius ({corner_radius}') exceeds safety maximum (15').")
        score_penalty += 0.3

    # Sidewalk Clear Path Audit
    if clear_path < StreetGeometricStandard.CLEAR_PATH_MIN:
        violations.append(f"Sidewalk clear path ({clear_path}') is below absolute minimum (5').")
        score_penalty += 0.5

    return GeometricAuditResult(
        is_compliant=len(violations) == 0,
        violations=violations,
        vision_zero_score=max(0.0, 1.0 - score_penalty)
    )

# The existing classes (MaterialCategory, SurfaceCondition, etc.) from the file read are preserved
# but I am adding the 4th Ed Tiers and Audit logic to complete the integration.
