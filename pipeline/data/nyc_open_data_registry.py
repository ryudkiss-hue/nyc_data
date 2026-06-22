#!/usr/bin/env python3
"""
NYC OPEN DATA REGISTRY — Authoritative metadata source

Maintains a comprehensive, always-current registry of ALL NYC Open Data datasets
with complete metadata, column names, freshness status, and type information.

Used as the single source of truth for:
- Dataset discovery and validation
- Column definitions and types
- Data freshness SLAs
- Pipeline configuration
- App initialization

Architecture:
  1. Fetches ALL NYC Open Data datasets from Socrata API (3,000+)
  2. Extracts complete metadata for each dataset
  3. Stores as authoritative JSON registry
  4. Syncs on app startup (incremental updates only)
  5. Provides runtime access to metadata

Usage:
  from pipeline.data.nyc_open_data_registry import NYCDataRegistry

  # Initialize (loads cache, syncs updates)
  registry = NYCDataRegistry()

  # Query by Socrata ID
  dataset = registry.get_dataset("6kbp-uz6m")  # Violations

  # Get all DOT datasets
  dot_datasets = registry.filter_by_agency("DOT")

  # Get datasets with specific keyword
  sidewalk_datasets = registry.search("sidewalk")
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

class NYCDataRegistry:
    """Authoritative registry of NYC Open Data datasets."""

    REGISTRY_FILE = Path(__file__).parent / "nyc_open_data_registry.json"
    LL251_ID = "5tqd-u88y"  # Local Law 251 inventory
    DOMAIN = "data.cityofnewyork.us"
    API_BASE = f"https://{DOMAIN}/api/catalog/v1"

    # Agencies whose full column schemas are eagerly fetched on every sync.
    # Substring match against the LL251 "datasetinformation_agency" field.
    PRIORITY_AGENCIES = ("Department of Transportation",)

    def __init__(self, auto_sync: bool = True, priority_agencies: tuple = None):
        """
        Initialize registry.

        Args:
            auto_sync: If True, sync with Socrata on initialization
            priority_agencies: Agency name substrings whose full column schemas
                are fetched eagerly. Defaults to PRIORITY_AGENCIES (DOT). Other
                agencies get base metadata only; columns are lazy-fetched on
                first get_dataset() access.
        """
        self.priority_agencies = priority_agencies or self.PRIORITY_AGENCIES
        self.registry = self._load_registry()
        if auto_sync and self._should_sync():
            self.sync()

    def _load_registry(self) -> Dict:
        """Load registry from local cache or create empty."""
        if self.REGISTRY_FILE.exists():
            try:
                with open(self.REGISTRY_FILE) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load registry cache: {e}")
        return self._create_empty_registry()

    def _create_empty_registry(self) -> Dict:
        """Create empty registry structure."""
        return {
            "metadata": {
                "version": "1.0",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_synced": None,
                "total_datasets": 0,
                "source": "Socrata API + Local Law 251 Inventory",
                "description": "Authoritative registry of all NYC Open Data datasets"
            },
            "datasets": {},
            "index": {
                "by_agency": {},
                "by_keywords": {},
                "by_socrata_id": {}
            }
        }

    def _should_sync(self) -> bool:
        """Check if sync is needed (not synced today)."""
        if not self.registry.get("metadata", {}).get("last_synced"):
            return True
        last_synced = self.registry["metadata"]["last_synced"]
        last_sync_date = datetime.fromisoformat(last_synced).date()
        today = datetime.now(timezone.utc).date()
        return last_sync_date < today

    def sync(self) -> None:
        """Sync registry with Socrata API (pulls all datasets with metadata)."""
        logger.info("Syncing NYC Open Data registry...")

        try:
            # Fetch from Local Law 251 inventory
            inventory = self._fetch_ll251_inventory()
            logger.info(f"Fetched {len(inventory)} datasets from LL251 inventory")

            # Process each dataset
            updated_count = 0
            for row in inventory:
                dataset_id = row.get("uid")
                if not dataset_id:
                    continue

                # Check if we need to update this dataset
                current = self.registry["datasets"].get(dataset_id, {})
                dataset = self._build_dataset_metadata(row, dataset_id, current)

                if dataset:
                    self.registry["datasets"][dataset_id] = dataset
                    updated_count += 1

            # Update indices
            self._rebuild_indices()

            # Update metadata
            self.registry["metadata"]["last_synced"] = datetime.now(timezone.utc).isoformat()
            self.registry["metadata"]["total_datasets"] = len(self.registry["datasets"])

            # Save to disk
            self._save_registry()

            logger.info(f"Registry sync complete: {updated_count} datasets processed")

        except Exception as e:
            logger.error(f"Registry sync failed: {e}")
            raise

    def _fetch_ll251_inventory(self) -> List[Dict]:
        """Fetch Local Law 251 inventory from Socrata."""
        url = f"https://{self.DOMAIN}/resource/{self.LL251_ID}.json?$limit=50000"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.json()

    def _build_dataset_metadata(self, ll251_row: Dict, dataset_id: str, current: Dict) -> Optional[Dict]:
        """Build comprehensive metadata for a dataset."""
        try:
            metadata = {
                "socrata_id": dataset_id,
                "name": ll251_row.get("name", ""),
                "description": ll251_row.get("description", ""),
                "agency": ll251_row.get("datasetinformation_agency", ""),
                "category": ll251_row.get("category", ""),
                "created_at": ll251_row.get("update_datemadepublic", ""),
                "last_updated": ll251_row.get("last_data_updated_date", ""),
                "update_frequency": ll251_row.get("update_updatefrequency", ""),
                "row_count": ll251_row.get("row_count", 0),
                "column_count": ll251_row.get("column_count", 0),
                "url": ll251_row.get("url", ""),
                "has_data_dictionary": ll251_row.get("legislativecompliance_hasdatadictionary", "No") == "Yes",
                "is_geocoded": ll251_row.get("legislativecompliance_geocoded", "N/A"),
                "visits": ll251_row.get("visits", 0),
                "downloads": ll251_row.get("downloads", 0),
            }

            # Eager-fetch full column schemas only for priority agencies (DOT).
            # Other agencies keep base metadata; columns lazy-load on access.
            is_priority = any(a in metadata["agency"] for a in self.priority_agencies)
            if is_priority and self._needs_column_update(current, metadata):
                metadata["columns"] = self._fetch_dataset_columns(dataset_id)
                metadata["columns_fetched"] = True
            elif is_priority:
                metadata["columns"] = current.get("columns", [])
                metadata["columns_fetched"] = current.get("columns_fetched", False)
            else:
                # Preserve any previously lazy-fetched columns
                metadata["columns"] = current.get("columns", [])
                metadata["columns_fetched"] = current.get("columns_fetched", False)

            return metadata

        except Exception as e:
            logger.warning(f"Failed to build metadata for {dataset_id}: {e}")
            return None

    def _needs_column_update(self, current: Dict, new_metadata: Dict) -> bool:
        """Check if columns need to be fetched."""
        if not current:
            return True
        # Fetch columns if dataset was updated recently
        if new_metadata.get("last_updated") != current.get("last_updated"):
            return True
        return False

    def _fetch_dataset_columns(self, dataset_id: str) -> List[Dict]:
        """Fetch column definitions for a dataset via the Socrata views metadata API.

        Uses https://{domain}/api/views/{id}.json which returns the canonical
        column list with field names, datatypes, and descriptions. (The catalog
        API does not expose per-column schema, so it must not be used here.)
        """
        try:
            url = f"https://{self.DOMAIN}/api/views/{dataset_id}.json"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()

            columns = []
            for col in data.get("columns", []):
                # Skip Socrata internal/system columns (negative ids)
                if isinstance(col.get("id"), int) and col["id"] < 0:
                    continue
                columns.append({
                    "name": col.get("name", ""),
                    "field_name": col.get("fieldName", ""),
                    "datatype": col.get("dataTypeName", ""),
                    "description": col.get("description", ""),
                })
            return columns

        except Exception as e:
            logger.debug(f"Could not fetch columns for {dataset_id}: {e}")
            return []

    def _rebuild_indices(self) -> None:
        """Rebuild search indices for fast lookup."""
        self.registry["index"] = {
            "by_agency": {},
            "by_keywords": {},
            "by_socrata_id": {}
        }

        for dataset_id, dataset in self.registry["datasets"].items():
            # Index by agency
            agency = dataset.get("agency", "Unknown")
            if agency not in self.registry["index"]["by_agency"]:
                self.registry["index"]["by_agency"][agency] = []
            self.registry["index"]["by_agency"][agency].append(dataset_id)

            # Index by Socrata ID
            self.registry["index"]["by_socrata_id"][dataset_id] = dataset_id

            # Extract keywords from name and description
            text = (dataset.get("name", "") + " " + dataset.get("description", "")).lower()
            for keyword in text.split():
                if len(keyword) > 3:  # Skip very short words
                    if keyword not in self.registry["index"]["by_keywords"]:
                        self.registry["index"]["by_keywords"][keyword] = []
                    if dataset_id not in self.registry["index"]["by_keywords"][keyword]:
                        self.registry["index"]["by_keywords"][keyword].append(dataset_id)

    def _save_registry(self) -> None:
        """Save registry to disk."""
        self.REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.REGISTRY_FILE, 'w') as f:
            json.dump(self.registry, f, indent=2)
        logger.info(f"Registry saved to {self.REGISTRY_FILE}")

    # Query methods
    def get_dataset(self, socrata_id: str, with_columns: bool = True) -> Optional[Dict]:
        """Get dataset by Socrata ID.

        Args:
            socrata_id: The dataset's Socrata 4x4 identifier.
            with_columns: If True and columns have not been fetched yet
                (non-priority agency), lazy-fetch them now and persist.
        """
        dataset = self.registry["datasets"].get(socrata_id)
        if dataset is None:
            return None

        if with_columns and not dataset.get("columns_fetched"):
            columns = self._fetch_dataset_columns(socrata_id)
            if columns:
                dataset["columns"] = columns
                dataset["columns_fetched"] = True
                self._save_registry()

        return dataset

    def filter_by_agency(self, agency: str) -> List[Dict]:
        """Get all datasets from a specific agency."""
        dataset_ids = self.registry["index"]["by_agency"].get(agency, [])
        return [self.registry["datasets"][did] for did in dataset_ids]

    def search(self, keyword: str) -> List[Dict]:
        """Search datasets by keyword."""
        keyword = keyword.lower()
        dataset_ids = self.registry["index"]["by_keywords"].get(keyword, [])
        return [self.registry["datasets"][did] for did in dataset_ids]

    def get_all_datasets(self) -> List[Dict]:
        """Get all datasets."""
        return list(self.registry["datasets"].values())

    def get_registry_json(self) -> Dict:
        """Get raw registry for export/backup."""
        return self.registry
