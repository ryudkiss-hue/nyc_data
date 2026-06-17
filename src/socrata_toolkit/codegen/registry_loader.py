"""Load and validate DATASET_REGISTRY.yaml configuration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class RegistryLoader:
    """Loads and validates DATASET_REGISTRY.yaml."""

    def __init__(self, registry_path: str):
        """Initialize loader.

        Args:
            registry_path: Path to DATASET_REGISTRY.yaml
        """
        self.registry_path = Path(registry_path)
        if not self.registry_path.exists():
            raise FileNotFoundError(f"Registry not found: {registry_path}")

    def load(self) -> dict[str, Any]:
        """Load YAML registry.

        Returns:
            Parsed registry dictionary

        Raises:
            yaml.YAMLError: If YAML is invalid
            KeyError: If required sections missing
        """
        with open(self.registry_path) as f:
            registry = yaml.safe_load(f)

        if not registry:
            raise ValueError("Registry is empty")

        # Validate structure
        self._validate_structure(registry)

        logger.info(
            f"Loaded registry: {registry['registry_metadata']['total_datasets']} datasets"
        )
        return registry

    def _validate_structure(self, registry: dict[str, Any]) -> None:
        """Validate registry structure.

        Args:
            registry: Parsed YAML registry

        Raises:
            KeyError: If required sections missing
            ValueError: If metadata invalid
        """
        required_sections = ["registry_metadata", "datasets", "defaults", "generators"]
        for section in required_sections:
            if section not in registry:
                raise KeyError(f"Missing required section: {section}")

        metadata = registry["registry_metadata"]
        required_metadata = ["version", "total_datasets", "domain"]
        for field in required_metadata:
            if field not in metadata:
                raise KeyError(f"Missing metadata field: {field}")

        # Validate each dataset has required fields
        datasets = registry["datasets"]
        for key, dataset in datasets.items():
            required_fields = ["fourfour", "name", "status"]
            for field in required_fields:
                if field not in dataset:
                    raise KeyError(f"Dataset '{key}' missing field: {field}")

    def get_active_datasets(self, registry: dict[str, Any]) -> dict[str, Any]:
        """Get only active datasets.

        Args:
            registry: Parsed registry

        Returns:
            Dictionary of active datasets only
        """
        return {
            key: ds
            for key, ds in registry["datasets"].items()
            if ds.get("status") == "active"
        }

    def get_datasets_by_tag(
        self, registry: dict[str, Any], tag: str
    ) -> dict[str, Any]:
        """Get datasets by tag.

        Args:
            registry: Parsed registry
            tag: Tag to filter by

        Returns:
            Dictionary of datasets with matching tag
        """
        return {
            key: ds
            for key, ds in registry["datasets"].items()
            if tag in ds.get("tags", [])
        }

    def get_dataset_by_fourfour(
        self, registry: dict[str, Any], fourfour: str
    ) -> tuple[str, Any] | None:
        """Get dataset by fourfour ID.

        Args:
            registry: Parsed registry
            fourfour: Fourfour ID

        Returns:
            Tuple of (key, dataset) or None
        """
        for key, ds in registry["datasets"].items():
            if ds.get("fourfour") == fourfour:
                return (key, ds)
        return None
