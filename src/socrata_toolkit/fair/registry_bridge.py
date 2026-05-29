"""Build a FAIR catalog from the project dataset registry.

Reads ``config/datasets.yaml`` and maps each registry entry to a
:class:`FairDataset`, deriving Socrata-specific access metadata from the
``fourfour`` identifier. Missing fields degrade gracefully to empty values.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .catalog import FairCatalog
from .model import FairDataset

# NYC Open Data is served by Socrata over the SODA API.
_SOCRATA_HOST = "https://data.cityofnewyork.us"
_LICENSE = "https://www.nyc.gov/home/terms-of-use.page"


def _to_fair_dataset(key: str, entry: dict[str, Any]) -> FairDataset:
    """Map a single registry entry to a FairDataset, tolerating gaps."""
    fourfour = str(entry.get("fourfour", "") or "")
    label = str(entry.get("label", key) or key)
    group = str(entry.get("group", "") or "")

    landing = f"{_SOCRATA_HOST}/d/{fourfour}" if fourfour else ""
    access_url = f"{_SOCRATA_HOST}/resource/{fourfour}.json" if fourfour else ""

    keywords = [k for k in (group, "nyc", "open-data", key) if k]

    return FairDataset(
        persistent_id=landing or key,
        title=label,
        description=f"{label} dataset from NYC Open Data (registry key: {key}).",
        keywords=keywords,
        domain=group,
        fourfour=fourfour,
        landing_page=landing,
        access_url=access_url,
        access_protocol="SODA" if fourfour else "",
        access_rights="public" if fourfour else "",
        license=_LICENSE,
        format="application/json" if fourfour else "",
        conforms_to="https://www.w3.org/TR/vocab-dcat-2/",
        vocabulary="http://www.w3.org/ns/dcat#",
        provenance={
            "source": "NYC Open Data (Socrata)",
            "publisher": "City of New York",
            "issued": "",
            "modified": "",
        },
        usage_rights="Public domain / NYC Open Data Terms of Use.",
        citation=f"City of New York. {label}. NYC Open Data. {landing}".strip(),
    )


def from_registry_yaml(path: str | Path) -> FairCatalog:
    """Build a :class:`FairCatalog` from a ``datasets.yaml`` registry file."""
    text = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    datasets = data.get("datasets", {}) or {}

    catalog = FairCatalog(title="NYC Open Data FAIR Catalog")
    for key, entry in datasets.items():
        entry = entry if isinstance(entry, dict) else {}
        catalog.add(_to_fair_dataset(key, entry), dataset_id=key)
    return catalog
