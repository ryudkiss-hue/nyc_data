"""Tests for quality.catalog module - Data catalog quality integration."""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from socrata_toolkit.quality.catalog import (
    DataQualityCatalog,
    DatasetQualityProfile,
    DatasetQualityScore,
    QualityTrend,
)


class TestQualityTrend:
    """Tests for QualityTrend enum."""

    def test_quality_trend_improving(self):
        """Test QualityTrend.IMPROVING value."""
        assert QualityTrend.IMPROVING.value == "improving"

    def test_quality_trend_stable(self):
        """Test QualityTrend.STABLE value."""
        assert QualityTrend.STABLE.value == "stable"

    def test_quality_trend_degrading(self):
        """Test QualityTrend.DEGRADING value."""
        assert QualityTrend.DEGRADING.value == "degrading"

    def test_quality_trend_comparison(self):
        """Test QualityTrend enum comparison."""
        assert QualityTrend.IMPROVING != QualityTrend.STABLE


class TestDatasetQualityScore:
    """Tests for DatasetQualityScore dataclass."""

    def test_quality_score_creation(self):
        """Test creating a DatasetQualityScore."""
        score = DatasetQualityScore(
            overall=85.0,
            completeness=90.0,
            validity=85.0,
            consistency=80.0,
            timeliness=85.0,
            accuracy=82.0,
        )
        assert score.overall == 85.0
        assert score.completeness == 90.0
        assert score.validity == 85.0

    def test_quality_score_defaults(self):
        """Test DatasetQualityScore with default values."""
        score = DatasetQualityScore(overall=75.0)
        assert score.overall == 75.0
        assert score.completeness == 0.0
        assert score.validity == 0.0
        assert score.consistency == 0.0

    def test_quality_score_to_dict(self):
        """Test serializing DatasetQualityScore to dict."""
        score = DatasetQualityScore(
            overall=85.0,
            completeness=90.0,
            validity=85.0,
        )
        result = score.to_dict()
        assert result["overall"] == 85.0
        assert result["completeness"] == 90.0
        assert result["validity"] == 85.0


class TestDatasetQualityProfile:
    """Tests for DatasetQualityProfile dataclass."""

    def test_profile_creation(self):
        """Test creating a DatasetQualityProfile."""
        now = datetime.now(timezone.utc)
        score = DatasetQualityScore(overall=80.0)
        profile = DatasetQualityProfile(
            dataset_id="test-dataset",
            dataset_name="Test Dataset",
            last_validation=now,
            quality_score=score,
        )
        assert profile.dataset_id == "test-dataset"
        assert profile.dataset_name == "Test Dataset"
        assert profile.quality_score.overall == 80.0
        assert profile.trend == QualityTrend.STABLE

    def test_profile_to_dict(self):
        """Test serializing DatasetQualityProfile to dict."""
        now = datetime.now(timezone.utc)
        score = DatasetQualityScore(overall=85.0)
        profile = DatasetQualityProfile(
            dataset_id="test",
            dataset_name="Test",
            last_validation=now,
            quality_score=score,
            trend=QualityTrend.IMPROVING,
        )
        result = profile.to_dict()
        assert result["dataset_id"] == "test"
        assert result["quality_score"]["overall"] == 85.0
        assert result["trend"] == "improving"

    def test_profile_to_json_and_from_json(self):
        """Test saving and loading profile from JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            now = datetime.now(timezone.utc)
            score = DatasetQualityScore(overall=90.0)
            profile = DatasetQualityProfile(
                dataset_id="test",
                dataset_name="Test Dataset",
                last_validation=now,
                quality_score=score,
                metadata={"source": "test"},
            )

            # Save to JSON
            filepath = Path(tmpdir) / "profile.json"
            profile.to_json(filepath)
            assert filepath.exists()

            # Load from JSON
            loaded = DatasetQualityProfile.from_json(filepath)
            assert loaded.dataset_id == "test"
            assert loaded.dataset_name == "Test Dataset"
            assert loaded.quality_score.overall == 90.0


class TestDataQualityCatalog:
    """Tests for DataQualityCatalog class."""

    def test_catalog_initialization(self):
        """Test initializing DataQualityCatalog."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            assert catalog.storage_dir == Path(tmpdir)
            assert catalog.profiles == {}

    def test_register_dataset(self):
        """Test registering a dataset."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")
            assert "ds1" in catalog.profiles
            assert catalog.profiles["ds1"].dataset_name == "Dataset 1"

    def test_register_dataset_with_metadata(self):
        """Test registering dataset with metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset(
                "ds1", "Dataset 1", metadata={"owner": "team-a"}
            )
            assert catalog.profiles["ds1"].metadata == {"owner": "team-a"}

    def test_update_quality_score(self):
        """Test updating quality score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")
            new_score = DatasetQualityScore(overall=85.0)
            catalog.update_quality_score("ds1", new_score)
            assert catalog.profiles["ds1"].quality_score.overall == 85.0

    def test_update_quality_score_trend_improving(self):
        """Test trend detection when score improves."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")

            # Set initial score to 50
            catalog.update_quality_score("ds1", DatasetQualityScore(overall=50.0))
            initial_trend = catalog.profiles["ds1"].trend

            # Improve score by more than 1 point
            catalog.update_quality_score("ds1", DatasetQualityScore(overall=52.0))
            assert catalog.profiles["ds1"].trend == QualityTrend.IMPROVING

    def test_update_quality_score_trend_degrading(self):
        """Test trend detection when score degrades."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")

            # Initial score
            catalog.update_quality_score("ds1", DatasetQualityScore(overall=80.0))

            # Degrade score
            catalog.update_quality_score("ds1", DatasetQualityScore(overall=70.0))
            assert catalog.profiles["ds1"].trend == QualityTrend.DEGRADING

    def test_add_validation_result(self):
        """Test adding validation result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")
            catalog.add_validation_result("ds1", {"check": "passed"})
            assert len(catalog.profiles["ds1"].validation_results) == 1

    def test_validation_results_limit(self):
        """Test that validation results are limited to 10."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")

            # Add 15 results
            for i in range(15):
                catalog.add_validation_result("ds1", {"result": i})

            # Should keep only last 10
            assert len(catalog.profiles["ds1"].validation_results) == 10

    def test_add_anomaly(self):
        """Test adding anomaly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")
            catalog.add_anomaly("ds1", {"type": "outlier"})
            assert len(catalog.profiles["ds1"].anomalies) == 1

    def test_anomalies_limit(self):
        """Test that anomalies are limited to 20."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")

            # Add 25 anomalies
            for i in range(25):
                catalog.add_anomaly("ds1", {"anomaly": i})

            # Should keep only last 20
            assert len(catalog.profiles["ds1"].anomalies) == 20

    def test_update_sla_compliance(self):
        """Test updating SLA compliance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")
            catalog.update_sla_compliance("ds1", {"freshness": 95.0, "availability": 99.0})
            assert catalog.profiles["ds1"].sla_compliance == {
                "freshness": 95.0,
                "availability": 99.0,
            }

    def test_update_violation_summary(self):
        """Test updating violation summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")
            catalog.update_violation_summary("ds1", {"missing_values": 5, "duplicates": 2})
            assert catalog.profiles["ds1"].violation_summary == {
                "missing_values": 5,
                "duplicates": 2,
            }

    def test_get_profile(self):
        """Test getting a profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")
            profile = catalog.get_profile("ds1")
            assert profile is not None
            assert profile.dataset_name == "Dataset 1"

    def test_get_profile_not_found(self):
        """Test getting non-existent profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            profile = catalog.get_profile("nonexistent")
            assert profile is None

    def test_list_datasets(self):
        """Test listing all datasets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")
            catalog.register_dataset("ds2", "Dataset 2")
            catalog.update_quality_score("ds1", DatasetQualityScore(overall=85.0))

            datasets = catalog.list_datasets()
            assert len(datasets) == 2
            assert datasets[0]["dataset_name"] in ["Dataset 1", "Dataset 2"]

    def test_list_by_quality_filter(self):
        """Test filtering datasets by quality score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")
            catalog.register_dataset("ds2", "Dataset 2")
            catalog.register_dataset("ds3", "Dataset 3")

            catalog.update_quality_score("ds1", DatasetQualityScore(overall=85.0))
            catalog.update_quality_score("ds2", DatasetQualityScore(overall=75.0))
            catalog.update_quality_score("ds3", DatasetQualityScore(overall=65.0))

            # Filter by min score
            results = catalog.list_by_quality(min_score=70.0)
            assert len(results) == 2

    def test_list_by_quality_sort_desc(self):
        """Test sorting datasets by quality descending."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")
            catalog.register_dataset("ds2", "Dataset 2")

            catalog.update_quality_score("ds1", DatasetQualityScore(overall=85.0))
            catalog.update_quality_score("ds2", DatasetQualityScore(overall=75.0))

            results = catalog.list_by_quality(order="desc")
            assert results[0]["quality_score"] > results[1]["quality_score"]

    def test_list_by_quality_sort_asc(self):
        """Test sorting datasets by quality ascending."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")
            catalog.register_dataset("ds2", "Dataset 2")

            catalog.update_quality_score("ds1", DatasetQualityScore(overall=85.0))
            catalog.update_quality_score("ds2", DatasetQualityScore(overall=75.0))

            results = catalog.list_by_quality(order="asc")
            assert results[0]["quality_score"] < results[1]["quality_score"]

    def test_list_by_trend(self):
        """Test listing datasets by trend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")
            catalog.register_dataset("ds2", "Dataset 2")

            # Set up improving trend
            catalog.update_quality_score("ds1", DatasetQualityScore(overall=50.0))
            catalog.update_quality_score("ds1", DatasetQualityScore(overall=85.0))

            # Set up degrading trend
            catalog.update_quality_score("ds2", DatasetQualityScore(overall=90.0))
            catalog.update_quality_score("ds2", DatasetQualityScore(overall=70.0))

            improving = catalog.list_by_trend(QualityTrend.IMPROVING)
            assert len(improving) == 1
            assert improving[0]["dataset_id"] == "ds1"

    def test_get_health_summary_empty(self):
        """Test health summary on empty catalog."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            summary = catalog.get_health_summary()
            assert summary["total_datasets"] == 0
            assert summary["average_quality"] == 0.0

    def test_get_health_summary_with_data(self):
        """Test health summary with data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")
            catalog.register_dataset("ds2", "Dataset 2")
            catalog.register_dataset("ds3", "Dataset 3")

            catalog.update_quality_score("ds1", DatasetQualityScore(overall=90.0))  # healthy
            catalog.update_quality_score("ds2", DatasetQualityScore(overall=70.0))  # at_risk
            catalog.update_quality_score("ds3", DatasetQualityScore(overall=40.0))  # critical

            summary = catalog.get_health_summary()
            assert summary["total_datasets"] == 3
            assert summary["healthy_count"] == 1
            assert summary["at_risk_count"] == 1
            assert summary["critical_count"] == 1

    def test_export_to_json(self):
        """Test exporting catalog to JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")
            catalog.update_quality_score("ds1", DatasetQualityScore(overall=85.0))

            filepath = catalog.export_to_json("export.json")
            assert filepath.exists()

            # Verify JSON content
            with open(filepath) as f:
                data = json.load(f)
            assert data["dataset_count"] == 1
            assert "health_summary" in data

    def test_save_profile(self):
        """Test saving individual profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)
            catalog.register_dataset("ds1", "Dataset 1")

            filepath = catalog.save_profile("ds1")
            assert filepath.exists()
            assert "ds1_quality_profile.json" in str(filepath)

    def test_load_profile(self):
        """Test loading profile from JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = DataQualityCatalog(storage_dir=tmpdir)

            # Create and save profile
            catalog.register_dataset("ds1", "Dataset 1")
            catalog.update_quality_score("ds1", DatasetQualityScore(overall=85.0))
            catalog.save_profile("ds1")

            # Create new catalog and load profile
            catalog2 = DataQualityCatalog(storage_dir=tmpdir)
            catalog2.load_profile("ds1", "ds1_quality_profile.json")

            assert "ds1" in catalog2.profiles
            assert catalog2.profiles["ds1"].quality_score.overall == 85.0
