"""Unit tests for dataset governance module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from socrata_toolkit.governance.dataset_governance import (
    _fetch_automation_status,
    _fetch_ll251_metadata,
    _fetch_removal_list,
    _fetch_socrata_json,
    _is_cache_valid,
    _load_cache,
    cross_reference,
    registry_audit,
)


class TestFetchSocrataJson:
    """Tests for _fetch_socrata_json function."""

    def test_fetch_socrata_json_success(self, monkeypatch):
        """Test successful fetch from Socrata API."""
        mock_data = [{"id": "1", "name": "Dataset 1"}, {"id": "2", "name": "Dataset 2"}]
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)

        monkeypatch.setattr("socrata_toolkit.governance.dataset_governance.urlopen", MagicMock(return_value=mock_response))

        result = _fetch_socrata_json("test-fourfour")
        assert result == mock_data
        assert len(result) == 2

    def test_fetch_socrata_json_with_select(self, monkeypatch):
        """Test fetch with SELECT parameter."""
        mock_data = [{"id": "1"}]
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)

        mock_urlopen = MagicMock(return_value=mock_response)
        monkeypatch.setattr("socrata_toolkit.governance.dataset_governance.urlopen", mock_urlopen)

        result = _fetch_socrata_json("test-fourfour", select="id,name")
        assert result == mock_data

    def test_fetch_socrata_json_url_error(self, monkeypatch):
        """Test handling of URLError during fetch."""
        from urllib.error import URLError

        def mock_urlopen(*args, **kwargs):
            raise URLError("Connection failed")

        monkeypatch.setattr("socrata_toolkit.governance.dataset_governance.urlopen", mock_urlopen)

        with pytest.raises(URLError):
            _fetch_socrata_json("test-fourfour")


class TestFetchLL251Metadata:
    """Tests for _fetch_ll251_metadata function."""

    def test_fetch_ll251_metadata_success(self, monkeypatch):
        """Test successful fetch and parsing of LL251 data."""
        mock_data = [
            {
                "datasetid": "dntt-gqwq",
                "update_automation": "yes",
                "update_updatefrequency": "daily",
                "legislativecompliance_removedrecords": "no",
                "legislativecompliance_candatasetfeasiblybeautomated": "yes",
                "legislativecompliance_hasdatadictionary": "yes",
                "legislativecompliance_datasetfromtheopendataplan": "yes",
            },
            {
                "datasetid": "6kbp-uz6m",
                "update_automation": "no",
                "update_updatefrequency": "weekly",
                "legislativecompliance_removedrecords": "yes",
                "legislativecompliance_candatasetfeasiblybeautomated": "no",
                "legislativecompliance_hasdatadictionary": "yes",
                "legislativecompliance_datasetfromtheopendataplan": "no",
            },
        ]

        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance._fetch_socrata_json",
            MagicMock(return_value=mock_data),
        )

        result = _fetch_ll251_metadata()
        assert len(result) == 2
        assert "dntt-gqwq" in result
        assert result["dntt-gqwq"]["automation"] is True
        assert result["dntt-gqwq"]["update_frequency"] == "daily"
        assert result["dntt-gqwq"]["removed_records"] is False
        assert result["6kbp-uz6m"]["automation"] is False
        assert result["6kbp-uz6m"]["removed_records"] is True

    def test_fetch_ll251_metadata_empty(self, monkeypatch):
        """Test handling of empty LL251 data."""
        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance._fetch_socrata_json",
            MagicMock(return_value=[]),
        )

        result = _fetch_ll251_metadata()
        assert result == {}

    def test_fetch_ll251_metadata_fetch_error(self, monkeypatch):
        """Test handling of fetch errors."""
        from urllib.error import URLError

        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance._fetch_socrata_json",
            MagicMock(side_effect=URLError("Connection failed")),
        )

        result = _fetch_ll251_metadata()
        assert result == {}


class TestFetchRemovalList:
    """Tests for _fetch_removal_list function."""

    def test_fetch_removal_list_success(self, monkeypatch):
        """Test successful fetch of removal list."""
        mock_data = [
            {"fourfour": "old-ds-1", "name": "Old Dataset 1"},
            {"fourfour": "old-ds-2", "name": "Old Dataset 2"},
        ]

        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance._fetch_socrata_json",
            MagicMock(return_value=mock_data),
        )

        result = _fetch_removal_list()
        assert "old-ds-1" in result
        assert "old-ds-2" in result
        assert len(result) == 2

    def test_fetch_removal_list_empty(self, monkeypatch):
        """Test handling of empty removal list."""
        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance._fetch_socrata_json",
            MagicMock(return_value=[]),
        )

        result = _fetch_removal_list()
        assert result == set()

    def test_fetch_removal_list_fetch_error(self, monkeypatch):
        """Test handling of fetch errors."""
        from urllib.error import URLError

        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance._fetch_socrata_json",
            MagicMock(side_effect=URLError("Connection failed")),
        )

        result = _fetch_removal_list()
        assert result == set()


class TestFetchAutomationStatus:
    """Tests for _fetch_automation_status function."""

    def test_fetch_automation_status_success(self, monkeypatch):
        """Test successful fetch of automation status."""
        mock_data = [
            {"fourfour": "dntt-gqwq", "automated": "yes"},
            {"fourfour": "6kbp-uz6m", "automated": "no"},
        ]

        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance._fetch_socrata_json",
            MagicMock(return_value=mock_data),
        )

        result = _fetch_automation_status()
        assert "dntt-gqwq" in result
        assert result["dntt-gqwq"] is True
        assert "6kbp-uz6m" in result

    def test_fetch_automation_status_empty(self, monkeypatch):
        """Test handling of empty automation data."""
        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance._fetch_socrata_json",
            MagicMock(return_value=[]),
        )

        result = _fetch_automation_status()
        assert result == {}

    def test_fetch_automation_status_fetch_error(self, monkeypatch):
        """Test handling of fetch errors."""
        from urllib.error import URLError

        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance._fetch_socrata_json",
            MagicMock(side_effect=URLError("Connection failed")),
        )

        result = _fetch_automation_status()
        assert result == {}


class TestCaching:
    """Tests for caching functionality."""

    def test_cache_valid_and_load(self, monkeypatch, tmp_path):
        """Test cache validation and loading."""
        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance.CACHE_FILE",
            tmp_path / "test_cache.json",
        )

        cache_data = {
            "total_registry": 26,
            "ll251_confirmed": 23,
            "removal_flagged": 0,
            "automation_status": {},
            "datasets": [],
            "timestamp": "2026-06-02T00:00:00+00:00",
        }

        cache_file = tmp_path / "test_cache.json"
        cache_file.write_text(json.dumps(cache_data))

        loaded = _load_cache()
        assert loaded is not None
        assert loaded["total_registry"] == 26

    def test_cache_invalid_age(self, monkeypatch, tmp_path):
        """Test that old cache is invalidated."""
        import time

        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance.CACHE_FILE",
            tmp_path / "test_cache.json",
        )
        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance.CACHE_VALIDITY_SECONDS",
            1,
        )

        cache_file = tmp_path / "test_cache.json"
        cache_file.write_text(json.dumps({"test": "data"}))

        time.sleep(1.1)

        assert not _is_cache_valid()


class TestCrossReference:
    """Tests for cross_reference function."""

    def test_cross_reference_found(self, monkeypatch):
        """Test cross_reference for a dataset found in LL251."""
        mock_audit = {
            "total_registry": 26,
            "ll251_confirmed": 23,
            "removal_flagged": 0,
            "automation_status": {"dntt-gqwq": True},
            "datasets": [
                {
                    "fourfour": "dntt-gqwq",
                    "name": "SMD Inspection",
                    "ll251_compliant": True,
                    "ll251_metadata": {
                        "automation": True,
                        "update_frequency": "daily",
                        "removed_records": False,
                    },
                    "removal_flagged": False,
                    "automated": True,
                }
            ],
            "timestamp": "2026-06-02T00:00:00+00:00",
        }

        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance.registry_audit",
            MagicMock(return_value=mock_audit),
        )

        result = cross_reference("dntt-gqwq")
        assert result["ll251_compliant"] is True
        assert result["ll251_metadata"]["automation"] is True
        assert result["removal_flagged"] is False
        assert result["automated"] is True

    def test_cross_reference_not_found(self, monkeypatch):
        """Test cross_reference for a dataset not in registry."""
        mock_audit = {
            "total_registry": 26,
            "ll251_confirmed": 23,
            "removal_flagged": 0,
            "automation_status": {},
            "datasets": [],
            "timestamp": "2026-06-02T00:00:00+00:00",
        }

        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance.registry_audit",
            MagicMock(return_value=mock_audit),
        )

        result = cross_reference("unknown-fourfour")
        assert result["ll251_compliant"] is False
        assert result["ll251_metadata"] is None
        assert result["removal_flagged"] is False
        assert result["automated"] is False


class TestRegistryAudit:
    """Tests for registry_audit function."""

    def test_registry_audit_with_cache(self, monkeypatch):
        """Test that registry_audit returns cached result if available."""
        cached_data = {
            "total_registry": 26,
            "ll251_confirmed": 23,
            "removal_flagged": 0,
            "automation_status": {},
            "datasets": [],
            "timestamp": "2026-06-02T00:00:00+00:00",
        }

        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance._load_cache",
            MagicMock(return_value=cached_data),
        )

        result = registry_audit()
        assert result == cached_data

    def test_registry_audit_fresh_fetch(self, monkeypatch):
        """Test registry_audit when no cache exists."""
        import sys

        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance._load_cache",
            MagicMock(return_value=None),
        )
        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance._fetch_ll251_metadata",
            MagicMock(return_value={"dntt-gqwq": {"automation": True, "update_frequency": "daily", "removed_records": False}}),
        )
        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance._fetch_removal_list",
            MagicMock(return_value=set()),
        )
        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance._fetch_automation_status",
            MagicMock(return_value={"dntt-gqwq": True}),
        )

        mock_registry = {
            "inspection": MagicMock(
                fourfour="dntt-gqwq",
                name="SMD Inspection",
            ),
        }

        # Patch the import to use our mock
        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance._save_cache",
            MagicMock(),
        )

        mock_discovery = MagicMock()
        mock_discovery.DATASETS = mock_registry
        monkeypatch.setitem(sys.modules, "socrata_toolkit.discovery.nyc", mock_discovery)

        result = registry_audit()
        assert result["total_registry"] == 1
        assert result["ll251_confirmed"] == 1
        assert result["removal_flagged"] == 0

    def test_registry_audit_structure(self, monkeypatch):
        """Test that registry_audit returns properly structured result."""
        cached_data = {
            "total_registry": 26,
            "ll251_confirmed": 23,
            "removal_flagged": 0,
            "automation_status": {"dntt-gqwq": True},
            "datasets": [
                {
                    "fourfour": "dntt-gqwq",
                    "name": "SMD Inspection",
                    "ll251_compliant": True,
                    "ll251_metadata": {"automation": True},
                    "removal_flagged": False,
                    "automated": True,
                }
            ],
            "timestamp": "2026-06-02T00:00:00+00:00",
        }

        monkeypatch.setattr(
            "socrata_toolkit.governance.dataset_governance._load_cache",
            MagicMock(return_value=cached_data),
        )

        result = registry_audit()
        assert "total_registry" in result
        assert "ll251_confirmed" in result
        assert "removal_flagged" in result
        assert "automation_status" in result
        assert "datasets" in result
        assert "timestamp" in result
        assert len(result["datasets"]) >= 0
