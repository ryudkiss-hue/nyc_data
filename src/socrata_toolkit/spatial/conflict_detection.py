"""
GIS Conflict Detection for Construction Planning

Detects spatial conflicts between active permits and scheduled inspections
to help analysts avoid scheduling conflicts and coordinate work between
permit holders and inspectors.

Key Features:
- Identifies spatial conflicts within a given buffer distance
- Classifies conflicts by severity (HIGH, MEDIUM, LOW)
- Provides actionable recommendations
- Works with coordinate-based data (lat/lon pairs)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass
class SpatialConflict:
    """Represents a spatial conflict between a permit and inspection location.

    Attributes:
        permit_block: Block ID of the permit
        inspection_block: Block ID of the inspection location
        permit_lat: Latitude of the permit location
        permit_lon: Longitude of the permit location
        inspection_lat: Latitude of the inspection location
        inspection_lon: Longitude of the inspection location
        distance_meters: Calculated distance between locations in meters
        severity: Severity level (HIGH, MEDIUM, or LOW)
        recommendation: Actionable recommendation for the analyst
    """

    permit_block: int
    inspection_block: int
    permit_lat: float
    permit_lon: float
    inspection_lat: float
    inspection_lon: float
    distance_meters: float
    severity: str
    recommendation: str

    def __post_init__(self):
        """Validate severity level after initialization."""
        valid_severities = {"HIGH", "MEDIUM", "LOW"}
        if self.severity not in valid_severities:
            raise ValueError(f"Severity must be one of {valid_severities}, got {self.severity}")


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in meters using Haversine formula.

    Uses the approximate mean radius of Earth (6,371 km). Suitable for
    distances up to several hundred kilometers.

    Args:
        lat1: Latitude of first point in decimal degrees
        lon1: Longitude of first point in decimal degrees
        lat2: Latitude of second point in decimal degrees
        lon2: Longitude of second point in decimal degrees

    Returns:
        Distance in meters
    """
    earth_radius_m = 6_371_000  # Earth's radius in meters

    # Convert to radians
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))

    return earth_radius_m * c


def _classify_severity(distance_meters: float) -> tuple[str, str]:
    """Classify conflict severity and provide recommendation.

    Severity thresholds:
    - HIGH (<20m): Critical situation requiring immediate action
    - MEDIUM (20-50m): Warning level requiring coordination
    - LOW (50-100m): Caution level for monitoring

    Args:
        distance_meters: Distance between locations in meters

    Returns:
        Tuple of (severity_level, recommendation_text)
    """
    if distance_meters < 20:
        return "HIGH", "CRITICAL: Reschedule inspection or halt permit work"
    elif distance_meters < 50:
        return "MEDIUM", "WARNING: Coordinate with permit holder"
    else:
        # distance_meters < 100 (or up to buffer)
        return "LOW", "CAUTION: Monitor for safety issues"


def detect_spatial_conflicts(
    permits_df: pd.DataFrame,
    inspections_df: pd.DataFrame,
    buffer_meters: float = 50,
) -> list[SpatialConflict]:
    """Detect spatial conflicts between active permits and scheduled inspections.

    Filters to active permits and scheduled inspections, calculates distances,
    and classifies conflicts by severity within the buffer distance.

    Args:
        permits_df: DataFrame with permit data. Expected columns:
            - permit_block (or block_id): Block identifier
            - permit_lat (or latitude): Permit location latitude
            - permit_lon (or longitude): Permit location longitude
            - permit_status (or status): Status field (filters for 'Active')
        inspections_df: DataFrame with inspection data. Expected columns:
            - inspection_block (or block_id): Block identifier
            - inspection_lat (or latitude): Inspection location latitude
            - inspection_lon (or longitude): Inspection location longitude
            - inspection_status (or status): Status field (filters for 'Scheduled')
        buffer_meters: Buffer distance in meters for conflict detection (default: 50)

    Returns:
        List of SpatialConflict objects sorted by distance (nearest first),
        only including conflicts within buffer_meters distance.

    Raises:
        ValueError: If required columns are missing from input DataFrames
        TypeError: If input is not a pandas DataFrame
    """
    if not isinstance(permits_df, pd.DataFrame):
        raise TypeError(f"permits_df must be a pandas DataFrame, got {type(permits_df)}")
    if not isinstance(inspections_df, pd.DataFrame):
        raise TypeError(f"inspections_df must be a pandas DataFrame, got {type(inspections_df)}")

    # Normalize column names - try different naming conventions
    permit_copy = permits_df.copy()
    insp_copy = inspections_df.copy()

    # Handle permit columns
    perm_block_col = None
    perm_lat_col = None
    perm_lon_col = None
    perm_status_col = None

    for col_variant in ["permit_block", "block_id", "block", "BLOCK"]:
        if col_variant in permit_copy.columns:
            perm_block_col = col_variant
            break
    if not perm_block_col:
        raise ValueError(f"Permits DataFrame missing block identifier. Available: {list(permit_copy.columns)}")

    for col_variant in ["permit_lat", "latitude", "lat", "LAT"]:
        if col_variant in permit_copy.columns:
            perm_lat_col = col_variant
            break
    if not perm_lat_col:
        raise ValueError(f"Permits DataFrame missing latitude column. Available: {list(permit_copy.columns)}")

    for col_variant in ["permit_lon", "longitude", "lon", "LON"]:
        if col_variant in permit_copy.columns:
            perm_lon_col = col_variant
            break
    if not perm_lon_col:
        raise ValueError(f"Permits DataFrame missing longitude column. Available: {list(permit_copy.columns)}")

    for col_variant in ["permit_status", "status", "STATUS"]:
        if col_variant in permit_copy.columns:
            perm_status_col = col_variant
            break
    if not perm_status_col:
        raise ValueError(f"Permits DataFrame missing status column. Available: {list(permit_copy.columns)}")

    # Handle inspection columns
    insp_block_col = None
    insp_lat_col = None
    insp_lon_col = None
    insp_status_col = None

    for col_variant in ["inspection_block", "block_id", "block", "BLOCK"]:
        if col_variant in insp_copy.columns:
            insp_block_col = col_variant
            break
    if not insp_block_col:
        raise ValueError(f"Inspections DataFrame missing block identifier. Available: {list(insp_copy.columns)}")

    for col_variant in ["inspection_lat", "latitude", "lat", "LAT"]:
        if col_variant in insp_copy.columns:
            insp_lat_col = col_variant
            break
    if not insp_lat_col:
        raise ValueError(f"Inspections DataFrame missing latitude column. Available: {list(insp_copy.columns)}")

    for col_variant in ["inspection_lon", "longitude", "lon", "LON"]:
        if col_variant in insp_copy.columns:
            insp_lon_col = col_variant
            break
    if not insp_lon_col:
        raise ValueError(f"Inspections DataFrame missing longitude column. Available: {list(insp_copy.columns)}")

    for col_variant in ["inspection_status", "status", "STATUS"]:
        if col_variant in insp_copy.columns:
            insp_status_col = col_variant
            break
    if not insp_status_col:
        raise ValueError(f"Inspections DataFrame missing status column. Available: {list(insp_copy.columns)}")

    # Filter to active permits and scheduled inspections
    active_permits = permit_copy[permit_copy[perm_status_col] == "Active"].reset_index(drop=True)
    scheduled_inspections = insp_copy[insp_copy[insp_status_col] == "Scheduled"].reset_index(drop=True)

    conflicts = []

    # Check each permit-inspection pair for spatial conflicts
    for _, perm_row in active_permits.iterrows():
        perm_block = perm_row[perm_block_col]
        perm_lat = perm_row[perm_lat_col]
        perm_lon = perm_row[perm_lon_col]

        # Skip rows with missing coordinates
        if pd.isna(perm_lat) or pd.isna(perm_lon):
            continue

        for _, insp_row in scheduled_inspections.iterrows():
            insp_block = insp_row[insp_block_col]
            insp_lat = insp_row[insp_lat_col]
            insp_lon = insp_row[insp_lon_col]

            # Skip rows with missing coordinates
            if pd.isna(insp_lat) or pd.isna(insp_lon):
                continue

            # Calculate distance
            distance = _haversine_distance(
                float(perm_lat),
                float(perm_lon),
                float(insp_lat),
                float(insp_lon),
            )

            # Only include conflicts within buffer distance
            if distance <= buffer_meters:
                severity, recommendation = _classify_severity(distance)

                conflict = SpatialConflict(
                    permit_block=int(perm_block),
                    inspection_block=int(insp_block),
                    permit_lat=float(perm_lat),
                    permit_lon=float(perm_lon),
                    inspection_lat=float(insp_lat),
                    inspection_lon=float(insp_lon),
                    distance_meters=float(distance),
                    severity=severity,
                    recommendation=recommendation,
                )
                conflicts.append(conflict)

    # Sort by distance (nearest first)
    conflicts.sort(key=lambda c: c.distance_meters)

    return conflicts


def summarize_conflicts_by_severity(
    conflicts: Iterable[SpatialConflict],
) -> dict[str, int]:
    """Summarize conflict counts by severity level.

    Args:
        conflicts: Iterable of SpatialConflict objects

    Returns:
        Dictionary with counts: {"HIGH": count, "MEDIUM": count, "LOW": count}
    """
    summary = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for conflict in conflicts:
        if conflict.severity in summary:
            summary[conflict.severity] += 1

    return summary
