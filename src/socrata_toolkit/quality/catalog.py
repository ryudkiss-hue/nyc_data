"""
Data Catalog Quality Integration - Dataset Quality Profiles and Metadata

Integrates quality metrics into data catalogs. Maintains quality scores,
validation results, anomalies, and compliance for each dataset.

Standards: Python 3.9+, full type hints, comprehensive docstrings, logging
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class QualityTrend(Enum):
    """Direction of quality trend."""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"


@dataclass
class DatasetQualityScore:
    """Quality score for a dataset (0-100).
    
    Attributes:
        overall: Overall quality score
        completeness: Completeness score
        validity: Validity score
        consistency: Consistency score
        timeliness: Timeliness score
        accuracy: Accuracy score
    """
    overall: float
    completeness: float = 0.0
    validity: float = 0.0
    consistency: float = 0.0
    timeliness: float = 0.0
    accuracy: float = 0.0

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class DatasetQualityProfile:
    """Complete quality profile for a dataset.
    
    Attributes:
        dataset_id: Unique dataset identifier
        dataset_name: Human-readable name
        last_validation: When validation last occurred
        quality_score: Current quality score
        validation_results: Recent validation results
        anomalies: Recent anomalies
        sla_compliance: SLA compliance percentages
        trend: Quality trend direction
        violation_summary: Summary of violations
        metadata: Additional metadata
    """
    dataset_id: str
    dataset_name: str
    last_validation: datetime
    quality_score: DatasetQualityScore
    validation_results: list[dict[str, Any]] = field(default_factory=list)
    anomalies: list[dict[str, Any]] = field(default_factory=list)
    sla_compliance: dict[str, float] = field(default_factory=dict)
    trend: QualityTrend = QualityTrend.STABLE
    violation_summary: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "last_validation": self.last_validation.isoformat(),
            "quality_score": self.quality_score.to_dict(),
            "validation_results": self.validation_results,
            "anomalies": self.anomalies,
            "sla_compliance": self.sla_compliance,
            "trend": self.trend.value,
            "violation_summary": self.violation_summary,
            "metadata": self.metadata,
        }

    def to_json(self, path: Path | str) -> None:
        """Save profile to JSON.
        
        Args:
            path: File path
        """
        path = Path(path)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    @classmethod
    def from_json(cls, path: Path | str) -> DatasetQualityProfile:
        """Load profile from JSON.
        
        Args:
            path: File path
            
        Returns:
            Loaded profile
        """
        path = Path(path)
        with open(path) as f:
            data = json.load(f)

        return cls(
            dataset_id=data["dataset_id"],
            dataset_name=data["dataset_name"],
            last_validation=datetime.fromisoformat(data["last_validation"]),
            quality_score=DatasetQualityScore(**data["quality_score"]),
            validation_results=data.get("validation_results", []),
            anomalies=data.get("anomalies", []),
            sla_compliance=data.get("sla_compliance", {}),
            trend=QualityTrend(data.get("trend", "stable")),
            violation_summary=data.get("violation_summary", {}),
            metadata=data.get("metadata", {}),
        )


class DataQualityCatalog:
    """Manages dataset quality profiles in a catalog.
    
    Tracks quality scores, metadata, trends, and anomalies for all datasets.
    Enables filtering and discovery by quality.
    """

    def __init__(self, storage_dir: Path | str = "./quality_catalog"):
        """Initialize catalog.
        
        Args:
            storage_dir: Directory for catalog storage
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.profiles: dict[str, DatasetQualityProfile] = {}

    def register_dataset(
        self,
        dataset_id: str,
        dataset_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register a dataset in the catalog.
        
        Args:
            dataset_id: Unique dataset ID
            dataset_name: Human-readable name
            metadata: Optional metadata
        """
        profile = DatasetQualityProfile(
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            last_validation=datetime.now(timezone.utc),
            quality_score=DatasetQualityScore(overall=0.0),
            metadata=metadata or {},
        )
        self.profiles[dataset_id] = profile
        logger.info(f"Registered dataset: {dataset_name}")

    def update_quality_score(
        self,
        dataset_id: str,
        quality_score: DatasetQualityScore,
    ) -> None:
        """Update quality score for a dataset.
        
        Args:
            dataset_id: Dataset identifier
            quality_score: New quality score
        """
        if dataset_id not in self.profiles:
            logger.warning(f"Dataset {dataset_id} not found in catalog")
            return

        profile = self.profiles[dataset_id]
        old_score = profile.quality_score.overall

        profile.quality_score = quality_score
        profile.last_validation = datetime.now(timezone.utc)

        # Determine trend
        if quality_score.overall > old_score + 1:
            profile.trend = QualityTrend.IMPROVING
        elif quality_score.overall < old_score - 1:
            profile.trend = QualityTrend.DEGRADING
        else:
            profile.trend = QualityTrend.STABLE

        logger.info(
            f"Updated {dataset_id}: score={quality_score.overall:.1f}, trend={profile.trend.value}"
        )

    def add_validation_result(
        self,
        dataset_id: str,
        result: dict[str, Any],
    ) -> None:
        """Add validation result to dataset profile.
        
        Args:
            dataset_id: Dataset identifier
            result: Validation result
        """
        if dataset_id not in self.profiles:
            logger.warning(f"Dataset {dataset_id} not found in catalog")
            return

        profile = self.profiles[dataset_id]
        profile.validation_results.append(result)

        # Keep only recent results
        if len(profile.validation_results) > 10:
            profile.validation_results = profile.validation_results[-10:]

    def add_anomaly(
        self,
        dataset_id: str,
        anomaly: dict[str, Any],
    ) -> None:
        """Add anomaly to dataset profile.
        
        Args:
            dataset_id: Dataset identifier
            anomaly: Anomaly data
        """
        if dataset_id not in self.profiles:
            logger.warning(f"Dataset {dataset_id} not found in catalog")
            return

        profile = self.profiles[dataset_id]
        profile.anomalies.append(anomaly)

        # Keep only recent anomalies
        if len(profile.anomalies) > 20:
            profile.anomalies = profile.anomalies[-20:]

    def update_sla_compliance(
        self,
        dataset_id: str,
        sla_compliance: dict[str, float],
    ) -> None:
        """Update SLA compliance for dataset.
        
        Args:
            dataset_id: Dataset identifier
            sla_compliance: Dict mapping SLA names to compliance %
        """
        if dataset_id not in self.profiles:
            logger.warning(f"Dataset {dataset_id} not found in catalog")
            return

        self.profiles[dataset_id].sla_compliance = sla_compliance

    def update_violation_summary(
        self,
        dataset_id: str,
        violation_summary: dict[str, int],
    ) -> None:
        """Update violation summary for dataset.
        
        Args:
            dataset_id: Dataset identifier
            violation_summary: Dict of violation counts by type
        """
        if dataset_id not in self.profiles:
            logger.warning(f"Dataset {dataset_id} not found in catalog")
            return

        self.profiles[dataset_id].violation_summary = violation_summary

    def get_profile(self, dataset_id: str) -> DatasetQualityProfile | None:
        """Get quality profile for dataset.
        
        Args:
            dataset_id: Dataset identifier
            
        Returns:
            DatasetQualityProfile or None
        """
        return self.profiles.get(dataset_id)

    def list_datasets(self) -> list[dict[str, Any]]:
        """List all datasets in catalog.
        
        Returns:
            List of dataset summaries
        """
        return [
            {
                "dataset_id": profile.dataset_id,
                "dataset_name": profile.dataset_name,
                "quality_score": profile.quality_score.overall,
                "trend": profile.trend.value,
                "last_validation": profile.last_validation.isoformat(),
            }
            for profile in self.profiles.values()
        ]

    def list_by_quality(
        self,
        min_score: float = 0.0,
        max_score: float = 100.0,
        order: str = "desc",
    ) -> list[dict[str, Any]]:
        """List datasets filtered by quality score.
        
        Args:
            min_score: Minimum quality score
            max_score: Maximum quality score
            order: 'asc' or 'desc' (default: desc)
            
        Returns:
            Sorted list of datasets
        """
        filtered = [
            {
                "dataset_id": profile.dataset_id,
                "dataset_name": profile.dataset_name,
                "quality_score": profile.quality_score.overall,
                "trend": profile.trend.value,
            }
            for profile in self.profiles.values()
            if min_score <= profile.quality_score.overall <= max_score
        ]

        # Sort by quality score
        reverse = order.lower() == "desc"
        return sorted(filtered, key=lambda x: x["quality_score"], reverse=reverse)

    def list_by_trend(self, trend: QualityTrend) -> list[dict[str, Any]]:
        """List datasets by trend direction.
        
        Args:
            trend: Trend direction to filter by
            
        Returns:
            List of datasets with matching trend
        """
        return [
            {
                "dataset_id": profile.dataset_id,
                "dataset_name": profile.dataset_name,
                "quality_score": profile.quality_score.overall,
                "trend": profile.trend.value,
            }
            for profile in self.profiles.values()
            if profile.trend == trend
        ]

    def get_health_summary(self) -> dict[str, Any]:
        """Get overall catalog health summary.
        
        Returns:
            Summary statistics
        """
        if not self.profiles:
            return {
                "total_datasets": 0,
                "average_quality": 0.0,
                "healthy_count": 0,
                "at_risk_count": 0,
                "critical_count": 0,
            }

        scores = [p.quality_score.overall for p in self.profiles.values()]
        healthy = sum(1 for s in scores if s >= 80)
        at_risk = sum(1 for s in scores if 50 <= s < 80)
        critical = sum(1 for s in scores if s < 50)

        return {
            "total_datasets": len(self.profiles),
            "average_quality": sum(scores) / len(scores) if scores else 0,
            "healthy_count": healthy,
            "at_risk_count": at_risk,
            "critical_count": critical,
            "health_percentage": healthy / len(self.profiles) * 100 if self.profiles else 0,
        }

    def export_to_json(self, filename: str) -> Path:
        """Export catalog to JSON.
        
        Args:
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        filepath = self.storage_dir / filename
        data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "dataset_count": len(self.profiles),
            "health_summary": self.get_health_summary(),
            "datasets": [p.to_dict() for p in self.profiles.values()],
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Exported catalog to {filepath}")
        return filepath

    def save_profile(self, dataset_id: str) -> Path:
        """Save individual dataset profile.
        
        Args:
            dataset_id: Dataset identifier
            
        Returns:
            Path to saved file
        """
        if dataset_id not in self.profiles:
            raise ValueError(f"Dataset {dataset_id} not found")

        profile = self.profiles[dataset_id]
        filename = f"{dataset_id}_quality_profile.json"
        filepath = self.storage_dir / filename
        profile.to_json(filepath)
        return filepath

    def load_profile(self, dataset_id: str, filename: str) -> None:
        """Load dataset profile from JSON.
        
        Args:
            dataset_id: Dataset identifier
            filename: File to load
        """
        filepath = self.storage_dir / filename
        profile = DatasetQualityProfile.from_json(filepath)
        self.profiles[dataset_id] = profile
        logger.info(f"Loaded profile for {dataset_id}")
