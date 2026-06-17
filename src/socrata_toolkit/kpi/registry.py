"""
KPI Registry — Singleton registry for loading and querying all 51 KPIs.

Loads KPI definitions from DATASET_REGISTRY.yaml and provides query methods
for filtering by category, dashboard, dataset, and other attributes.
Thread-safe singleton pattern with in-memory caching.
"""

import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from socrata_toolkit.kpi.models import (
    DimensionConfig,
    KPIDefinition,
    ThresholdConfig,
    TimeSeriesMetadata,
)

logger = logging.getLogger(__name__)


class KPIRegistry:
    """Singleton registry for all 51 KPI definitions."""

    _instance: Optional["KPIRegistry"] = None
    _lock = threading.Lock()

    def __init__(self):
        """Initialize registry (private)."""
        self._kpis: Dict[str, KPIDefinition] = {}
        self._loaded = False

    @classmethod
    def instance(cls) -> "KPIRegistry":
        """Get singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def load(cls, registry_path: Optional[str] = None) -> "KPIRegistry":
        """
        Load KPI registry from YAML file.

        Args:
            registry_path: Path to DATASET_REGISTRY.yaml.
                          If None, uses default location.

        Returns:
            KPIRegistry singleton instance.
        """
        registry = cls.instance()
        if not registry._loaded:
            registry.load_definitions(registry_path)
        return registry

    def load_definitions(self, registry_path: Optional[str] = None) -> None:
        """
        Load all KPI definitions from DATASET_REGISTRY.yaml.

        Args:
            registry_path: Path to DATASET_REGISTRY.yaml.
                          If None, searches for it in common locations.
        """
        if self._loaded:
            logger.warning("Registry already loaded; skipping reload")
            return

        # Determine registry path
        if registry_path is None:
            registry_path = self._find_registry_file()

        if not registry_path or not Path(registry_path).exists():
            raise FileNotFoundError(
                f"DATASET_REGISTRY.yaml not found at {registry_path}"
            )

        logger.info(f"Loading KPI registry from {registry_path}")

        try:
            with open(registry_path, "r") as f:
                data = yaml.safe_load(f)

            if not data or "datasets" not in data:
                logger.warning("No datasets found in registry")
                self._loaded = True
                return

            # Extract KPIs from each dataset
            kpi_count = 0
            for dataset_key, dataset_config in data["datasets"].items():
                if "kpis" in dataset_config:
                    for kpi_id in dataset_config["kpis"]:
                        # Try to build KPI definition from available data
                        kpi_def = self._build_kpi_definition(
                            kpi_id, dataset_key, dataset_config
                        )
                        if kpi_def:
                            self._kpis[kpi_id] = kpi_def
                            kpi_count += 1

            logger.info(f"Loaded {kpi_count} KPIs from registry")
            self._loaded = True

        except yaml.YAMLError as e:
            logger.error(f"Failed to parse registry: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            raise

    def _find_registry_file(self) -> Optional[str]:
        """Find DATASET_REGISTRY.yaml in common locations."""
        candidates = [
            Path.cwd() / "docs" / "DATASET_REGISTRY.yaml",
            Path.cwd() / "DATASET_REGISTRY.yaml",
            Path(__file__).parent.parent.parent.parent / "docs" / "DATASET_REGISTRY.yaml",
        ]

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        return None

    def _build_kpi_definition(
        self, kpi_id: str, dataset_key: str, dataset_config: Dict
    ) -> Optional[KPIDefinition]:
        """
        Build KPI definition from dataset config.

        Args:
            kpi_id: KPI identifier (e.g., "PRM-001")
            dataset_key: Dataset key from registry
            dataset_config: Dataset configuration dictionary

        Returns:
            KPIDefinition or None if unable to build.
        """
        try:
            # Extract dataset metadata
            dataset_name = dataset_config.get("name", dataset_key)
            fourfour = dataset_config.get("fourfour", "")
            dataset_category = dataset_config.get("category", "core_daily")
            frequency = dataset_config.get("frequency", "daily")

            # Map dataset category to KPI category
            kpi_category = self._map_category(dataset_category, kpi_id)

            # Build KPI definition with defaults
            kpi_def = KPIDefinition(
                kpi_id=kpi_id,
                name=self._get_kpi_name(kpi_id),
                category=kpi_category,
                description=f"Computed from {dataset_name}",
                source_dataset_key=dataset_key,
                source_fourfour=fourfour,
                refresh_frequency=frequency,
            )

            # Set chart type based on KPI ID
            kpi_def.primary_chart_type = self._get_chart_type(kpi_id)
            kpi_def.alternative_chart_types = self._get_alternative_charts(
                kpi_id
            )

            return kpi_def

        except Exception as e:
            logger.warning(
                f"Failed to build KPI definition for {kpi_id}: {e}"
            )
            return None

    def _map_category(self, dataset_category: str, kpi_id: str) -> str:
        """Map dataset category to KPI category."""
        # Map dataset categories to KPI categories
        category_map = {
            "core_daily": "permits",
            "accessibility": "pedestrian",
            "coordination": "safety",
            "budget": "budget",
            "compliance": "compliance",
        }

        # Try dataset category first
        if dataset_category in category_map:
            return category_map[dataset_category]

        # Infer from KPI ID prefix
        prefix = kpi_id.split("-")[0]
        prefix_map = {
            "PRM": "permits",
            "CLS": "permits",
            "PED": "pedestrian",
            "APS": "pedestrian",
            "PLZ": "pedestrian",
            "ADA": "pedestrian",
            "PARK": "safety",
            "SAF": "safety",
            "CONF": "safety",
            "VZ": "safety",
            "CAP": "budget",
            "VEND": "budget",
            "COORD": "budget",
            "GEO": "compliance",
            "CMP": "compliance",
        }

        return prefix_map.get(prefix, "other")

    def _get_kpi_name(self, kpi_id: str) -> str:
        """Get human-readable KPI name from ID."""
        # Extract name from KPI ID (e.g., PRM-001 → "Permit Metrics 001")
        prefix = kpi_id.split("-")[0]
        number = kpi_id.split("-")[1] if "-" in kpi_id else "000"

        name_map = {
            "PRM": "Permit Fee Revenue",
            "CLS": "Construction Closure",
            "PED": "Pedestrian Infrastructure",
            "APS": "Accessible Signal",
            "PLZ": "Plaza Inspection",
            "ADA": "ADA Ramp Coverage",
            "PARK": "Parking Meter",
            "SAF": "Safety Infrastructure",
            "CONF": "Public Space Conflict",
            "VZ": "Vision Zero Crossing",
            "CAP": "Capital Pipeline",
            "VEND": "Vendor Contract",
            "COORD": "Coordination",
            "GEO": "Geospatial Data",
            "CMP": "Compliance",
        }

        base_name = name_map.get(prefix, prefix)
        return f"{base_name} ({number})"

    def _get_chart_type(self, kpi_id: str) -> str:
        """Get primary chart type for KPI."""
        # Chart type mapping from EXPANDED_KPI_CHART_REGISTRY.md
        chart_map = {
            "PRM-001": "bar",
            "PRM-002": "indicator",
            "PRM-003": "bar",
            "PRM-004": "scatter",
            "PRM-005": "scatter",
            "PRM-006": "bar",
            "PRM-007": "scatter",
            "PRM-008": "scatter",
            "PRM-009": "indicator",
            "CLS-001": "indicator",
            "CLS-002": "indicator",
            "CLS-003": "bar",
            "CLS-004": "indicator",
            "PED-001": "indicator",
            "PED-002": "indicator",
            "PED-003": "heatmap",
            "PED-004": "choropleth",
            "PED-005": "bar",
            "APS-001": "indicator",
            "APS-002": "indicator",
            "APS-003": "bar",
            "PLZ-001": "indicator",
            "PLZ-002": "indicator",
            "PLZ-003": "pie",
            "ADA-001": "indicator",
            "ADA-002": "indicator",
            "ADA-003": "indicator",
            "PARK-001": "choropleth",
            "PARK-002": "bar",
            "SAF-001": "indicator",
            "SAF-002": "indicator",
            "SAF-003": "indicator",
            "SAF-004": "indicator",
            "CONF-001": "indicator",
            "CONF-002": "choropleth",
            "VZ-001": "indicator",
            "VZ-002": "pie",
            "CAP-001": "funnel",
            "CAP-002": "indicator",
            "VEND-001": "indicator",
            "VEND-002": "indicator",
            "VEND-003": "indicator",
            "COORD-001": "funnel",
            "COORD-002": "bar",
            "GEO-001": "indicator",
            "GEO-002": "indicator",
            "CMP-001": "indicator",
            "CMP-002": "indicator",
            "CMP-003": "indicator",
        }

        return chart_map.get(kpi_id, "indicator")

    def _get_alternative_charts(self, kpi_id: str) -> List[str]:
        """Get alternative chart types for KPI."""
        # Default alternatives based on primary chart
        primary = self._get_chart_type(kpi_id)

        alternatives_map = {
            "indicator": ["gauge", "number", "bar"],
            "bar": ["horizontal_bar", "line", "area"],
            "scatter": ["line", "bubble"],
            "heatmap": ["bar", "scatter"],
            "choropleth": ["bar", "map"],
            "pie": ["donut", "bar"],
            "funnel": ["bar", "waterfall"],
        }

        return alternatives_map.get(primary, ["bar", "line"])

    def get_kpi(self, kpi_id: str) -> Optional[KPIDefinition]:
        """
        Get KPI definition by ID.

        Args:
            kpi_id: KPI identifier (e.g., "PRM-001")

        Returns:
            KPIDefinition or None if not found.
        """
        return self._kpis.get(kpi_id)

    def get_all_kpis(self) -> List[KPIDefinition]:
        """Get all KPI definitions."""
        return list(self._kpis.values())

    def get_kpis_by_category(self, category: str) -> List[KPIDefinition]:
        """
        Get all KPIs in a category.

        Args:
            category: Category name (permits, pedestrian, safety, budget, compliance)

        Returns:
            List of KPIDefinition objects.
        """
        return [
            kpi
            for kpi in self._kpis.values()
            if kpi.category == category
        ]

    def get_kpis_by_dataset(self, dataset_key: str) -> List[KPIDefinition]:
        """
        Get all KPIs from a dataset.

        Args:
            dataset_key: Dataset key (e.g., "inspection", "violations")

        Returns:
            List of KPIDefinition objects.
        """
        return [
            kpi
            for kpi in self._kpis.values()
            if kpi.source_dataset_key == dataset_key
        ]

    def get_kpis_by_dashboard(self, section: str) -> List[KPIDefinition]:
        """
        Get KPIs for a dashboard section.

        Args:
            section: Dashboard section name

        Returns:
            List of KPIDefinition objects.
        """
        return [
            kpi
            for kpi in self._kpis.values()
            if section in kpi.dashboard_sections
        ]

    def get_chart_recommendations(
        self, kpi_id: str
    ) -> Dict[str, List[str]]:
        """
        Get chart recommendations for a KPI.

        Args:
            kpi_id: KPI identifier

        Returns:
            Dictionary with primary and alternative chart types.
        """
        kpi = self.get_kpi(kpi_id)
        if not kpi:
            return {}

        return {
            "primary": kpi.primary_chart_type,
            "alternatives": kpi.alternative_chart_types,
        }

    def validate_registry(self) -> Dict[str, any]:
        """
        Validate registry for completeness and consistency.

        Returns:
            Dictionary with validation results.
        """
        results = {
            "total_kpis": len(self._kpis),
            "duplicate_ids": [],
            "missing_required_fields": [],
            "invalid_definitions": [],
            "by_category": {},
        }

        # Check for duplicates (should not happen)
        seen_ids = set()
        for kpi_id in self._kpis:
            if kpi_id in seen_ids:
                results["duplicate_ids"].append(kpi_id)
            seen_ids.add(kpi_id)

        # Validate each KPI
        for kpi_id, kpi_def in self._kpis.items():
            # Check required fields
            if not kpi_def.name or not kpi_def.category:
                results["missing_required_fields"].append(kpi_id)

            # Check validity
            validation_errors = kpi_def.validate()
            if validation_errors:
                results["invalid_definitions"].append({
                    "kpi_id": kpi_id,
                    "errors": validation_errors,
                })

            # Count by category
            category = kpi_def.category
            if category not in results["by_category"]:
                results["by_category"][category] = 0
            results["by_category"][category] += 1

        return results

    def to_dict(self) -> Dict[str, any]:
        """Export registry as dictionary."""
        return {
            kpi_id: {
                "name": kpi_def.name,
                "category": kpi_def.category,
                "target": kpi_def.target,
                "unit": kpi_def.unit,
                "chart_type": kpi_def.primary_chart_type,
                "source_dataset": kpi_def.source_dataset_key,
            }
            for kpi_id, kpi_def in self._kpis.items()
        }

    def __len__(self) -> int:
        """Return number of KPIs in registry."""
        return len(self._kpis)

    def __iter__(self):
        """Iterate over KPI definitions."""
        return iter(self._kpis.values())
