"""Dataset governance registry audit.

Integrates three NYC Open Data governance datasets as sources of truth:
1. Dataset Removals (tm5c-buy3)
2. Automated Datasets (7t2y-4fke)
3. LL251 Inventory (5tqd-u88y)

Provides registry_audit() to fetch and consolidate governance metadata for display
in the Settings/Governance panel.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DatasetGovernanceMetadata:
    """Governance metadata for a single dataset."""
    fourfour: str
    label: str
    agency: str
    ll251_compliant: bool
    automation_enabled: bool
    removed_records: bool
    update_frequency: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "fourfour": self.fourfour,
            "label": self.label,
            "agency": self.agency,
            "ll251_compliant": self.ll251_compliant,
            "automation_enabled": self.automation_enabled,
            "removed_records": self.removed_records,
            "update_frequency": self.update_frequency,
            "notes": self.notes,
        }


def _fetch_ll251_inventory(domain: str = "data.cityofnewyork.us", token: str | None = None) -> dict[str, dict[str, Any]]:
    """Fetch LL251 Inventory dataset (5tqd-u88y).

    Returns dict mapping fourfour IDs to governance metadata.
    """
    result = {}
    try:
        from sodapy import Socrata

        client = Socrata(domain, token, timeout=30)
        rows = client.get("5tqd-u88y", limit=50000)

        for row in rows:
            fourfour = row.get("dataset_id") or row.get("fourfour")
            if not fourfour:
                continue

            agency = row.get("agency", "Unknown")
            # Check if dataset is marked as LL251 compliant
            ll251_status = row.get("legislative_requirement", row.get("ll251", ""))
            ll251_compliant = ll251_status and ll251_status.lower() in ("yes", "true", "1")

            # Check for removed records field
            removed_records = row.get("legislativecompliance_removedrecords", "").lower() == "yes"

            # Get update frequency
            update_freq = row.get("update_frequency", "Unknown")

            result[fourfour] = {
                "agency": agency,
                "ll251_compliant": ll251_compliant,
                "removed_records": removed_records,
                "update_frequency": update_freq,
            }

        logger.info(f"Fetched LL251 inventory: {len(result)} datasets")
    except Exception as e:
        logger.warning(f"Failed to fetch LL251 inventory: {e}")

    return result


def _fetch_automated_datasets(domain: str = "data.cityofnewyork.us", token: str | None = None) -> dict[str, bool]:
    """Fetch Automated Datasets (7t2y-4fke).

    Returns dict mapping fourfour IDs to automation status (True/False).
    """
    result = {}
    try:
        from sodapy import Socrata

        client = Socrata(domain, token, timeout=30)
        rows = client.get("7t2y-4fke", limit=50000)

        for row in rows:
            fourfour = row.get("dataset_id") or row.get("fourfour")
            if not fourfour:
                continue

            # Check update_automation field
            automation = row.get("update_automation", "").lower() in ("yes", "true", "1")
            result[fourfour] = automation

        logger.info(f"Fetched automated datasets: {len(result)} datasets")
    except Exception as e:
        logger.warning(f"Failed to fetch automated datasets: {e}")

    return result


def _fetch_dataset_removals(domain: str = "data.cityofnewyork.us", token: str | None = None) -> dict[str, str]:
    """Fetch Dataset Removals (tm5c-buy3).

    Returns dict mapping fourfour IDs to removal reason/notes.
    """
    result = {}
    try:
        from sodapy import Socrata

        client = Socrata(domain, token, timeout=30)
        rows = client.get("tm5c-buy3", limit=50000)

        for row in rows:
            fourfour = row.get("dataset_id") or row.get("fourfour")
            if not fourfour:
                continue

            reason = row.get("reason", "") or row.get("removal_reason", "")
            result[fourfour] = reason

        logger.info(f"Fetched dataset removals: {len(result)} datasets")
    except Exception as e:
        logger.warning(f"Failed to fetch dataset removals: {e}")

    return result


def registry_audit(
    dataset_registry: dict[str, dict[str, str]],
    domain: str = "data.cityofnewyork.us",
    token: str | None = None,
) -> list[DatasetGovernanceMetadata]:
    """Audit the dataset registry against NYC governance datasets.

    Consolidates metadata from three NYC Open Data governance datasets:
    - LL251 Inventory (5tqd-u88y)
    - Automated Datasets (7t2y-4fke)
    - Dataset Removals (tm5c-buy3)

    Args:
        dataset_registry: Dict mapping keys to dataset metadata (with 'fourfour' field)
        domain: Socrata domain (default: data.cityofnewyork.us)
        token: Socrata app token (optional, uses env var if not provided)

    Returns:
        List of DatasetGovernanceMetadata objects, sorted by LL251 compliance (compliant first)
    """
    import os

    if token is None:
        token = os.getenv("SOCRATA_APP_TOKEN", "").strip() or None

    # Fetch governance data
    ll251_data = _fetch_ll251_inventory(domain, token)
    automated_data = _fetch_automated_datasets(domain, token)
    removals_data = _fetch_dataset_removals(domain, token)

    result = []

    # Build governance metadata for each registered dataset
    for key, meta in dataset_registry.items():
        fourfour = meta.get("fourfour", "")
        if not fourfour:
            continue

        label = meta.get("label", key)

        # Get governance metadata with defaults
        ll251_meta = ll251_data.get(fourfour, {})
        agency = ll251_meta.get("agency", "DOT")
        ll251_compliant = ll251_meta.get("ll251_compliant", False)
        removed_records = ll251_meta.get("removed_records", False)
        update_frequency = ll251_meta.get("update_frequency", "Unknown")

        # Get automation status
        automation_enabled = automated_data.get(fourfour, False)

        # Get removal notes if applicable
        removal_notes = removals_data.get(fourfour, "")

        metadata = DatasetGovernanceMetadata(
            fourfour=fourfour,
            label=label,
            agency=agency,
            ll251_compliant=ll251_compliant,
            automation_enabled=automation_enabled,
            removed_records=removed_records,
            update_frequency=update_frequency,
            notes=removal_notes,
        )
        result.append(metadata)

    # Sort: LL251 compliant first, then by agency/label
    result.sort(key=lambda x: (not x.ll251_compliant, x.agency, x.label))

    logger.info(f"Registry audit complete: {len(result)} datasets")
    return result


def registry_audit_summary(
    metadata_list: list[DatasetGovernanceMetadata],
) -> dict[str, int]:
    """Generate summary statistics for registry audit."""
    return {
        "total_datasets": len(metadata_list),
        "ll251_compliant": sum(1 for m in metadata_list if m.ll251_compliant),
        "automated": sum(1 for m in metadata_list if m.automation_enabled),
        "with_removed_records": sum(1 for m in metadata_list if m.removed_records),
    }
