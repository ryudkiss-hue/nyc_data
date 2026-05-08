```powershell id="l40khf"
# =========================================================
# NYC DATA TOOLKIT - FULL ENVIRONMENT BOOTSTRAP
# Windows PowerShell Setup Script
# =========================================================
#
# Run from:
# C:\Users\ryudk\Documents\GitHub\nyc_data
#
# Usage:
# powershell -ExecutionPolicy Bypass -File .\bootstrap_windows.ps1
#
# =========================================================

Write-Host ""
Write-Host "==============================================="
Write-Host " NYC DATA TOOLKIT ENVIRONMENT SETUP"
Write-Host "==============================================="
Write-Host ""

# ---------------------------------------------------------
# VERIFY PROJECT ROOT
# ---------------------------------------------------------

$projectRoot = Get-Location

Write-Host "Project Root:" $projectRoot
Write-Host ""

# ---------------------------------------------------------
# CREATE VIRTUAL ENVIRONMENT
# ---------------------------------------------------------

if (!(Test-Path ".venv")) {

    Write-Host "Creating virtual environment..."
    python -m venv .venv

} else {

    Write-Host "Virtual environment already exists."

}

Write-Host ""

# ---------------------------------------------------------
# ACTIVATE VENV
# ---------------------------------------------------------

Write-Host "Activating virtual environment..."

& ".\.venv\Scripts\Activate.ps1"

Write-Host ""

# ---------------------------------------------------------
# UPGRADE PIP
# ---------------------------------------------------------

Write-Host "Upgrading pip..."

python -m pip install --upgrade pip

Write-Host ""

# ---------------------------------------------------------
# INSTALL CORE DEPENDENCIES
# ---------------------------------------------------------

Write-Host "Installing core dependencies..."

pip install `
    shapely `
    pytest `
    pylint `
    black `
    ruff `
    mypy `
    pandas `
    geopandas `
    requests `
    sqlalchemy `
    psycopg2-binary `
    python-dotenv

Write-Host ""

# ---------------------------------------------------------
# INSTALL PROJECT DEV REQUIREMENTS
# ---------------------------------------------------------

if (Test-Path "requirements-dev.txt") {

    Write-Host "Installing requirements-dev.txt..."

    pip install -r requirements-dev.txt

    Write-Host ""

}

# ---------------------------------------------------------
# UPDATE requirements-dev.txt
# ---------------------------------------------------------

Write-Host "Ensuring shapely exists in requirements-dev.txt..."

$requirementsPath = "requirements-dev.txt"

if (Test-Path $requirementsPath) {

    $requirementsContent = Get-Content $requirementsPath

    if ($requirementsContent -notcontains "shapely>=2.0") {

        Add-Content $requirementsPath "`nshapely>=2.0"

        Write-Host "Added shapely>=2.0"

    } else {

        Write-Host "Shapely already present."

    }

}

Write-Host ""

# ---------------------------------------------------------
# CREATE/UPDATE VSCODE SETTINGS
# ---------------------------------------------------------

Write-Host "Configuring VS Code settings..."

if (!(Test-Path ".vscode")) {

    New-Item `
        -ItemType Directory `
        -Path ".vscode" | Out-Null

}

$vscodeSettings = @'
{
    "python.defaultInterpreterPath": ".venv/Scripts/python.exe",
    "python.analysis.extraPaths": [
        "./socrata_toolkit"
    ],
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.pytestArgs": [
        "tests"
    ],
    "python.linting.pylintEnabled": true,
    "editor.formatOnSave": true,
    "python.formatting.provider": "black",
    "files.exclude": {
        "**/__pycache__": true,
        "**/.pytest_cache": true
    }
}
'@

Set-Content `
    -Path ".vscode/settings.json" `
    -Value $vscodeSettings

Write-Host "VS Code settings updated."

Write-Host ""

# ---------------------------------------------------------
# REPLACE spatial.py
# ---------------------------------------------------------

Write-Host "Writing cleaned spatial.py module..."

$spatialCode = @'
# coding=utf-8
"""
Spatial utilities for the NYC Open Data / Socrata ingestion toolkit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Iterable
from typing import Sequence

try:
    from shapely.geometry import shape as shapely_shape
    from shapely.geometry.base import BaseGeometry
    from shapely.ops import unary_union
    from shapely.wkt import loads as load_wkt

    SHAPELY_AVAILABLE = True

except ImportError:
    shapely_shape = None
    BaseGeometry = object
    unary_union = None
    load_wkt = None

    SHAPELY_AVAILABLE = False


class SpatialDependencyError(ImportError):
    """Raised when a spatial operation requires Shapely."""


@dataclass(slots=True)
class BoundingBox:
    """Represents a geometry bounding box."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def as_tuple(
        self,
    ) -> tuple[float, float, float, float]:

        return (
            self.min_x,
            self.min_y,
            self.max_x,
            self.max_y,
        )


def require_shapely() -> None:

    if not SHAPELY_AVAILABLE:

        raise SpatialDependencyError(
            "Shapely is required for spatial operations."
        )


def is_geojson_geometry(
    value: Any,
) -> bool:

    if not isinstance(value, dict):
        return False

    return (
        isinstance(value.get("type"), str)
        and value.get("coordinates") is not None
    )


def parse_geojson_geometry(
    geometry: dict[str, Any],
) -> BaseGeometry:

    require_shapely()

    if not is_geojson_geometry(geometry):

        raise ValueError(
            "Invalid GeoJSON geometry."
        )

    return shapely_shape(geometry)


def parse_wkt_geometry(
    wkt_value: str,
) -> BaseGeometry:

    require_shapely()

    if not isinstance(wkt_value, str):

        raise ValueError(
            "WKT value must be a string."
        )

    return load_wkt(wkt_value)


def geometry_bounds(
    geometry: BaseGeometry,
) -> BoundingBox:

    min_x, min_y, max_x, max_y = geometry.bounds

    return BoundingBox(
        min_x=min_x,
        min_y=min_y,
        max_x=max_x,
        max_y=max_y,
    )


def geometry_area(
    geometry: BaseGeometry,
) -> float:

    return float(geometry.area)


def geometry_length(
    geometry: BaseGeometry,
) -> float:

    return float(geometry.length)


def geometry_centroid(
    geometry: BaseGeometry,
) -> tuple[float, float]:

    centroid = geometry.centroid

    return (
        float(centroid.x),
        float(centroid.y),
    )


def union_geometries(
    geometries: Sequence[BaseGeometry],
) -> BaseGeometry:

    require_shapely()

    if not geometries:

        raise ValueError(
            "No geometries supplied."
        )

    return unary_union(geometries)


def validate_geometry(
    geometry: BaseGeometry,
) -> bool:

    return bool(
        geometry.is_valid
        and not geometry.is_empty
    )


def spatial_join_candidates(
    left_geometries: Iterable[BaseGeometry],
    right_geometries: Iterable[BaseGeometry],
) -> list[tuple[int, int]]:

    matches: list[tuple[int, int]] = []

    left_list = list(left_geometries)
    right_list = list(right_geometries)

    for left_index, left_geometry in enumerate(left_list):

        for right_index, right_geometry in enumerate(
            right_list
        ):

            if left_geometry.intersects(
                right_geometry
            ):

                matches.append(
                    (
                        left_index,
                        right_index,
                    )
                )

    return matches
'@

Set-Content `
    -Path "socrata_toolkit/spatial.py" `
    -Value $spatialCode

Write-Host "spatial.py updated."

Write-Host ""

# ---------------------------------------------------------
# ENSURE __init__.py EXISTS
# ---------------------------------------------------------

if (!(Test-Path "socrata_toolkit/__init__.py")) {

    Set-Content `
        -Path "socrata_toolkit/__init__.py" `
        -Value '"""Socrata toolkit."""'

}

Write-Host "__init__.py verified."

Write-Host ""

# ---------------------------------------------------------
# RUN BLACK FORMATTER
# ---------------------------------------------------------

Write-Host "Running black formatter..."

black socrata_toolkit

Write-Host ""

# ---------------------------------------------------------
# RUN RUFF
# ---------------------------------------------------------

Write-Host "Running ruff..."

ruff check socrata_toolkit --fix

Write-Host ""

# ---------------------------------------------------------
# RUN PYLINT
# ---------------------------------------------------------

Write-Host "Running pylint..."

pylint socrata_toolkit

Write-Host ""

# ---------------------------------------------------------
# RUN PYTEST
# ---------------------------------------------------------

Write-Host "Running pytest..."

pytest

Write-Host ""

# ---------------------------------------------------------
# VERIFY SHAPELY
# ---------------------------------------------------------

Write-Host "Verifying shapely installation..."

python -c "from shapely.geometry import Point; print(Point(1,1))"

Write-Host ""
Write-Host "==============================================="
Write-Host " SETUP COMPLETE"
Write-Host "==============================================="
Write-Host ""

Write-Host "Next Steps:"
Write-Host ""
Write-Host "1. Restart VS Code"
Write-Host "2. Ctrl+Shift+P"
Write-Host "3. Python: Select Interpreter"
Write-Host "4. Choose:"
Write-Host "   .venv\Scripts\python.exe"
Write-Host ""
Write-Host "Your spatial toolkit should now lint cleanly."
Write-Host ""
```
