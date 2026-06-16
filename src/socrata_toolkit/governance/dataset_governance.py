"""Dataset Governance Module - NYC Open Data Governance Sources

Integrates three NYC Open Data governance datasets as sources of truth:
- tm5c-buy3: Dataset Removals (407 datasets)
- 7t2y-4fke: Automated Datasets (423 datasets)
- 5tqd-u88y: LL251 Inventory (271 DOT datasets)

Provides functions to cross-reference any dataset against these sources
and audit the registry for governance compliance.

Example::

    from socrata_toolkit.governance.dataset_governance import cross_reference, registry_audit

    # Check a single dataset
    metadata = cross_reference("dntt-gqwq")
    print(metadata["ll251_compliant"])  # True or False

    # Audit all 26 registry datasets
    audit = registry_audit()
    print(f"{audit['ll251_confirmed']}/26 confirmed in LL251")
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

# Governance dataset fourfours
DATASET_REMOVALS_FOURFOUR = "tm5c-buy3"
AUTOMATED_DATASETS_FOURFOUR = "7t2y-4fke"
LL251_INVENTORY_FOURFOUR = "5tqd-u88y"

SOCRATA_DOMAIN = "data.cityofnewyork.us"
SOCRATA_TIMEOUT = 60
CACHE_DIR = Path(".cache")
CACHE_FILE = CACHE_DIR / "governance_audit.json"
CACHE_VALIDITY_SECONDS = 3600  # 1 hour

def _ensure_cache_dir() -> None:
    """Create cache directory if it does not exist."""
    CACHE_DIR.mkdir(exist_ok=True)

def _is_cache_valid() -> bool:
    """Check if cached audit is still valid (less than 1 hour old)."""
    if not CACHE_FILE.exists():
        return False
    try:
        age = datetime.now(timezone.utc).timestamp() - CACHE_FILE.stat().st_mtime
        return age < CACHE_VALIDITY_SECONDS
    except OSError:
        return False

def _load_cache() -> dict[str, Any] | None:
    """Load governance audit from cache if valid."""
    if not _is_cache_valid():
        return None
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        logger.debug(f"Loaded governance audit from cache: {CACHE_FILE}")
        return data
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to load cache: {e}")
        return None

def _save_cache(data: dict[str, Any]) -> None:
    """Save governance audit to cache."""
    try:
        _ensure_cache_dir()
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        logger.debug(f"Saved governance audit to cache: {CACHE_FILE}")
    except OSError as e:
        logger.warning(f"Failed to save cache: {e}")

def _extract_fourfour(row: dict[str, Any]) -> str:
    """Extract fourfour ID from a row, trying multiple field names.

    Args:
        row: Dictionary row from Socrata dataset

    Returns:
        Fourfour ID string (empty if not found)
    """
    return (row.get("fourfour", "").strip() or row.get("dataset_id", "").strip())

def _fetch_socrata_json(fourfour: str, select: str | None = None, limit: int = 50000) -> list[dict[str, Any]]:
    """Fetch JSON data from a Socrata dataset.

    Args:
        fourfour: Dataset ID (e.g., "tm5c-buy3")
        select: Optional SoQL SELECT clause (defaults to *)
        limit: Maximum rows to fetch

    Returns:
        List of dictionaries from the dataset

    Raises:
        URLError: If the HTTP request fails
        json.JSONDecodeError: If response is not valid JSON
    """
    url = f"https://{SOCRATA_DOMAIN}/api/views/{fourfour}/rows.json"
    params: dict[str, str | int] = {"limit": limit, "accessType": "DOWNLOAD"}
    if select:
        params["$select"] = select

    query_string = urlencode(params)
    full_url = f"{url}?{query_string}"

    req = Request(full_url)
    req.add_header("Accept", "application/json")

    try:
        with urlopen(req, timeout=SOCRATA_TIMEOUT) as response:
            data = response.read().decode("utf-8")

        response_json = json.loads(data)
        # Socrata /rows.json endpoint returns {meta: {...}, data: [...]}
        if isinstance(response_json, dict) and "data" in response_json:
            raw_data = response_json["data"]
            meta = response_json.get("meta", {})

            # Convert raw array rows to dicts using column names from meta
            if meta and isinstance(raw_data, list) and len(raw_data) > 0:
                if isinstance(raw_data[0], list):
                    columns = meta.get("view", {}).get("columns", [])
                    col_names = [col.get("fieldName") for col in columns]
                    return [dict(zip(col_names, row)) for row in raw_data]

            return raw_data

        return response_json
    except URLError as e:
        logger.error(f"Failed to fetch {fourfour}: {e}")
        raise

def _fetch_ll251_metadata() -> dict[str, dict[str, Any]]:
    """Fetch LL251 Inventory dataset and return fourfour -> metadata mapping.

    Returns:
        Dictionary mapping fourfour IDs to metadata dicts with keys:
        - automation: bool
        - update_frequency: str
        - removed_records: bool
    """
    try:
        rows = _fetch_socrata_json(LL251_INVENTORY_FOURFOUR)
    except (URLError, json.JSONDecodeError) as e:
        logger.error(f"Failed to fetch LL251 Inventory: {e}")
        return {}

    metadata = {}
    for row in rows:
        fourfour = row.get("datasetid", "").strip()
        if not fourfour:
            continue

        metadata[fourfour] = {
            "automation": row.get("update_automation", "").lower() == "yes",
            "update_frequency": str(row.get("update_updatefrequency", "")).strip() or None,
            "removed_records": row.get("legislativecompliance_removedrecords", "").lower() == "yes",
            "can_be_automated": row.get("legislativecompliance_candatasetfeasiblybeautomated", "").lower() == "yes",
            "has_data_dictionary": row.get("legislativecompliance_hasdatadictionary", "").lower() == "yes",
            "from_open_data_plan": row.get("legislativecompliance_datasetfromtheopendataplan", "").lower() == "yes",
        }

    logger.info(f"Fetched LL251 metadata for {len(metadata)} datasets")
    return metadata

def _fetch_removal_list() -> set[str]:
    """Fetch Dataset Removals dataset and return set of fourfour IDs marked for removal.

    Returns:
        Set of fourfour IDs (empty set if no removals, or none match registry)
    """
    try:
        rows = _fetch_socrata_json(DATASET_REMOVALS_FOURFOUR)
    except (URLError, json.JSONDecodeError) as e:
        logger.error(f"Failed to fetch Dataset Removals: {e}")
        return set()

    removal_list = set()
    for row in rows:
        fourfour = _extract_fourfour(row)
        if fourfour:
            removal_list.add(fourfour)

    logger.info(f"Fetched removal list: {len(removal_list)} datasets marked for removal")
    return removal_list

def _fetch_automation_status() -> dict[str, bool]:
    """Fetch Automated Datasets dataset and return fourfour -> automation_status mapping.

    Returns:
        Dictionary mapping fourfour IDs to automation status (True if automated)
    """
    try:
        rows = _fetch_socrata_json(AUTOMATED_DATASETS_FOURFOUR)
    except (URLError, json.JSONDecodeError) as e:
        logger.error(f"Failed to fetch Automated Datasets: {e}")
        return {}

    automation = {}
    for row in rows:
        fourfour = _extract_fourfour(row)
        if fourfour:
            automation[fourfour] = True

    logger.info(f"Fetched automation status for {len(automation)} datasets")
    return automation

def cross_reference(fourfour: str) -> dict[str, Any]:
    """Get governance metadata for a single dataset.

    Cross-references the given fourfour ID against all three governance sources
    and returns compliance/removal/automation status.

    Args:
        fourfour: Dataset ID (e.g., "dntt-gqwq")

    Returns:
        Dictionary with keys:
        - ll251_compliant: bool (True if found in LL251)
        - ll251_metadata: dict or None (if compliant)
        - removal_flagged: bool
        - automated: bool
    """
    audit = registry_audit()

    # Find this fourfour in the audit results
    for ds in audit.get("datasets", []):
        if ds["fourfour"] == fourfour:
            return {
                "ll251_compliant": ds["ll251_compliant"],
                "ll251_metadata": ds.get("ll251_metadata"),
                "removal_flagged": ds["removal_flagged"],
                "automated": ds["automated"],
            }

    # Not found in registry
    logger.warning(f"Dataset {fourfour} not found in registry")
    return {
        "ll251_compliant": False,
        "ll251_metadata": None,
        "removal_flagged": False,
        "automated": False,
    }

def registry_audit() -> dict[str, Any]:
    """Audit all registry datasets against governance sources.

    Fetches the three governance datasets (with caching) and cross-references
    the entire 26-dataset registry against them. Returns a comprehensive audit report.

    Returns:
        Dictionary with keys:
        - total_registry: int (26 datasets)
        - ll251_confirmed: int (count of datasets found in LL251)
        - removal_flagged: int (count of datasets on removal list)
        - automation_status: dict mapping fourfour -> bool
        - datasets: list of dicts, one per registry dataset, with keys:
            - fourfour: str
            - name: str
            - ll251_compliant: bool
            - ll251_metadata: dict or None
            - removal_flagged: bool
            - automated: bool
        - timestamp: ISO8601 datetime
    """
    cached = _load_cache()
    if cached:
        return cached

    logger.info("Starting governance audit (fetching from NYC Open Data)")

    # Fetch all governance sources
    ll251_metadata = _fetch_ll251_metadata()
    removal_list = _fetch_removal_list()
    automation_status = _fetch_automation_status()

    # Load registry datasets
    try:
        from ..discovery.nyc import DATASETS
        registry = DATASETS
    except ImportError as e:
        logger.error(f"Failed to import registry: {e}")
        registry = {}

    # Build audit result
    datasets = []
    ll251_confirmed = 0
    removal_flagged = 0

    for key, config in registry.items():
        fourfour = config.fourfour
        is_ll251_compliant = fourfour in ll251_metadata

        if is_ll251_compliant:
            ll251_confirmed += 1

        is_removal_flagged = fourfour in removal_list
        if is_removal_flagged:
            removal_flagged += 1

        is_automated = automation_status.get(fourfour, False)

        datasets.append({
            "fourfour": fourfour,
            "name": config.name,
            "ll251_compliant": is_ll251_compliant,
            "ll251_metadata": ll251_metadata.get(fourfour),
            "removal_flagged": is_removal_flagged,
            "automated": is_automated,
        })

    audit_result = {
        "total_registry": len(registry),
        "ll251_confirmed": ll251_confirmed,
        "removal_flagged": removal_flagged,
        "automation_status": automation_status,
        "datasets": datasets,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    _save_cache(audit_result)
    logger.info(f"Governance audit complete: {ll251_confirmed}/{len(registry)} confirmed in LL251")

    return audit_result
