"""NYC Open Data Dataset Registry for DOT Sidewalk Toolkit.

Pre-configured dataset IDs, domains, and column mappings for commonly
used NYC Open Data sources. Eliminates manual config every time you
need to fetch sidewalk-related data.

Example::

    from socrata_toolkit.nyc_datasets import DATASETS, fetch_sidewalk_complaints

    # Direct fetch with pre-configured columns
    df = fetch_sidewalk_complaints(max_rows=500)

    # Or use the registry
    ds = DATASETS["sidewalk_complaints"]
    print(ds.fourfour, ds.columns)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class DatasetConfig:
    """Configuration for a known NYC Open Data dataset."""
    name: str
    fourfour: str
    domain: str = "data.cityofnewyork.us"
    description: str = ""
    key_columns: List[str] = field(default_factory=list)
    date_column: Optional[str] = None
    borough_column: Optional[str] = None
    geo_columns: Optional[Dict[str, str]] = None
    column_mapping: Dict[str, str] = field(default_factory=dict)


#: Registry of pre-configured NYC datasets relevant to DOT sidewalk work.
DATASETS: Dict[str, DatasetConfig] = {
    "311_service_requests": DatasetConfig(
        name="311 Service Requests",
        fourfour="erm2-nwe9",
        description="All 311 service requests including sidewalk complaints",
        key_columns=["unique_key"],
        date_column="created_date",
        borough_column="borough",
        geo_columns={"latitude": "latitude", "longitude": "longitude"},
    ),
    "sidewalk_violations": DatasetConfig(
        name="DOT Sidewalk Violations",
        fourfour="2bic-bpnm",
        description="Sidewalk inspection violations issued by DOT",
        key_columns=["violation_number"],
        date_column="issuance_date",
        borough_column="borough",
    ),
    "dot_permits": DatasetConfig(
        name="DOT Permits",
        fourfour="mqk4-wgtq",
        description="Street/sidewalk work permits issued by DOT",
        key_columns=["permit_number"],
        date_column="permit_start_date",
        borough_column="borough",
    ),
    "pedestrian_ramps": DatasetConfig(
        name="Pedestrian Ramp Inspections",
        fourfour="if8w-mqkr",
        description="Pedestrian ramp inspection records",
        key_columns=["ramp_id"],
        borough_column="borough",
    ),
    "capital_projects": DatasetConfig(
        name="DOT Capital Projects",
        fourfour="qhc4-jwcy",
        description="DOT capital project tracking (may include sidewalk projects)",
        key_columns=["project_id"],
        date_column="start_date",
        borough_column="borough",
    ),
    "street_construction_permits": DatasetConfig(
        name="Street Construction Permits",
        fourfour="tqtj-sjs8",
        description="Active street construction permits (for conflict detection)",
        key_columns=["permit_id"],
        date_column="permit_start",
        borough_column="borough",
    ),
    "nyc_community_boards": DatasetConfig(
        name="Community Board Boundaries",
        fourfour="jp9i-3b7y",
        description="NYC community board geographic boundaries (GeoJSON)",
    ),
}


def fetch_dataset(
    dataset_key: str,
    max_rows: int = 10000,
    where: Optional[str] = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """Fetch a pre-configured dataset by its registry key.

    Args:
        dataset_key: Key from DATASETS dict (e.g., "311_service_requests").
        max_rows: Maximum rows to fetch.
        where: Optional SoQL WHERE filter.
    """
    from .client import SocrataClient

    if dataset_key not in DATASETS:
        raise KeyError(f"Unknown dataset '{dataset_key}'. Available: {list(DATASETS.keys())}")

    ds = DATASETS[dataset_key]
    client = SocrataClient()
    return client.fetch_dataframe(ds.domain, ds.fourfour, where=where, max_rows=max_rows, **kwargs)


def fetch_sidewalk_complaints(
    max_rows: int = 1000,
    since: Optional[str] = None,
    borough: Optional[str] = None,
) -> pd.DataFrame:
    """Convenience: fetch 311 sidewalk complaints with common filters."""
    where_parts = ["complaint_type IN ('Sidewalk Condition','Broken Sidewalk','Curb Condition')"]
    if since:
        where_parts.append(f"created_date > '{since}'")
    if borough:
        where_parts.append(f"upper(borough) = '{borough.upper()}'")
    where = " AND ".join(where_parts)
    return fetch_dataset("311_service_requests", max_rows=max_rows, where=where)


def fetch_active_permits(max_rows: int = 5000) -> pd.DataFrame:
    """Convenience: fetch currently active DOT permits for conflict detection."""
    return fetch_dataset("dot_permits", max_rows=max_rows)


def list_available_datasets() -> List[Dict[str, str]]:
    """List all pre-configured datasets with their descriptions."""
    return [
        {"key": k, "name": v.name, "fourfour": v.fourfour, "description": v.description}
        for k, v in DATASETS.items()
    ]
