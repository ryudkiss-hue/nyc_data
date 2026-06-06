"""Coverage tests for small core utility modules.

Covers DatasetMetadata (models), TemporalQuery (temporal), redact_secrets
(logging_utils), profile slug/listing (profiles), and MasterDataManager
(master_data).
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# core.models — DatasetMetadata
# ---------------------------------------------------------------------------

class TestDatasetMetadata:
    def _meta(self, columns):
        from socrata_toolkit.core.models import DatasetMetadata

        return DatasetMetadata(
            domain="data.cityofnewyork.us",
            fourfour="abc1-2345",
            name="Test",
            description="desc",
            row_count=100,
            license="CC0",
            columns=columns,
        )

    def test_is_geo_true_for_point(self):
        meta = self._meta([{"name": "loc", "dataTypeName": "Point"}])
        assert meta.is_geo is True

    def test_is_geo_true_for_location_substring(self):
        meta = self._meta([{"name": "x", "dataTypeName": "location_1"}])
        assert meta.is_geo is True

    def test_is_geo_false(self):
        meta = self._meta([{"name": "n", "dataTypeName": "text"}])
        assert meta.is_geo is False

    def test_summary(self):
        meta = self._meta([{"name": "loc", "dataTypeName": "polygon"}])
        s = meta.summary()
        assert s["fourfour"] == "abc1-2345"
        assert s["row_count"] == 100
        assert s["is_geo"] is True

    def test_column_dict(self):
        meta = self._meta([
            {"name": "a", "fieldName": "a", "dataTypeName": "number", "description": "d", "position": 1},
        ])
        cols = meta.column_dict()
        assert cols[0]["name"] == "a"
        assert cols[0]["dataTypeName"] == "number"


# ---------------------------------------------------------------------------
# core.temporal — TemporalQuery
# ---------------------------------------------------------------------------

class TestTemporalQuery:
    def test_get_as_of_returns_none(self):
        from datetime import datetime

        from socrata_toolkit.core.temporal import TemporalQuery

        q = TemporalQuery(dsn="postgresql://x")
        assert q.get_as_of("t", "key", datetime(2024, 1, 1)) is None

    def test_get_history_returns_empty(self):
        from socrata_toolkit.core.temporal import TemporalQuery

        q = TemporalQuery()
        assert q.get_history("t", "key") == []


# ---------------------------------------------------------------------------
# core.logging_utils — redact_secrets
# ---------------------------------------------------------------------------

class TestRedactSecrets:
    def test_redacts_known_keys(self):
        from socrata_toolkit.core.logging_utils import redact_secrets

        out = redact_secrets("password=abc token=xyz secret=123")
        assert "[REDACTED_KEY]" in out
        assert "password" not in out

    def test_no_secrets_unchanged(self):
        from socrata_toolkit.core.logging_utils import redact_secrets

        assert redact_secrets("hello world") == "hello world"


# ---------------------------------------------------------------------------
# core.profiles — _slug / list_profiles
# ---------------------------------------------------------------------------

class TestProfilesHelpers:
    def test_slug_empty_returns_default(self):
        from socrata_toolkit.core.profiles import _slug

        assert _slug("") == "default"
        assert _slug("   ") == "default"

    def test_slug_sanitizes(self):
        from socrata_toolkit.core.profiles import _slug

        out = _slug("My Profile!@#")
        assert " " not in out
        assert "!" not in out

    def test_list_profiles_no_dir(self, tmp_path):
        from socrata_toolkit.core.profiles import list_profiles

        assert list_profiles(root=tmp_path / "missing") == []

    def test_list_profiles_with_dirs(self, tmp_path):
        from socrata_toolkit.core.profiles import list_profiles, profiles_root

        root = profiles_root(tmp_path)
        root.mkdir(parents=True, exist_ok=True)
        (root / "alpha").mkdir()
        (root / "beta").mkdir()
        names = list_profiles(root=tmp_path)
        assert "alpha" in names
        assert "beta" in names


# ---------------------------------------------------------------------------
# core.master_data — MasterDataManager
# ---------------------------------------------------------------------------

class TestMasterDataManager:
    def test_register_and_get_record(self):
        from socrata_toolkit.core.master_data import MasterDataManager

        m = MasterDataManager()
        assert m.register_master_data("k1", {"v": 1}) is True
        assert m.get_record("k1") == {"v": 1}
        assert m.get_record("missing") is None

    def test_register_entity(self):
        from socrata_toolkit.core.master_data import MasterDataManager, MasterEntity

        m = MasterDataManager()
        ent = MasterEntity(entity_id="e1", canonical_record={"a": 1}, source_record_ids=["s1"], entity_type="x")
        assert m.register_entity("e1", ent) is True
        assert m.get_statistics()["total_entities"] == 1

    def test_create_master_entity(self):
        from socrata_toolkit.core.master_data import MasterDataManager

        m = MasterDataManager()
        eid = m.create_master_entity({"name": "A"}, {"name": "B"}, entity_type="contractor")
        assert isinstance(eid, str)
        ent = m.get_master_entity(eid)
        assert ent is not None

    def test_create_master_entity_requires_records(self):
        from socrata_toolkit.core.master_data import MasterDataManager

        m = MasterDataManager()
        with pytest.raises(ValueError):
            m.create_master_entity()

    def test_validate_merge_missing_entity(self):
        from socrata_toolkit.core.master_data import MasterDataManager

        m = MasterDataManager()
        ok, issues = m.validate_merge("nope", ["a"])
        assert ok is False
        assert "Entity not found" in issues

    def test_validate_merge_missing_fields(self):
        from socrata_toolkit.core.master_data import MasterDataManager

        m = MasterDataManager()
        eid = m.create_master_entity({"name": "A"}, entity_type="x")
        ok, issues = m.validate_merge(eid, ["name", "phone"])
        assert ok is False
        assert any("phone" in i for i in issues)

    def test_get_master_record_module_helper(self):
        from socrata_toolkit.core.master_data import get_master_record

        assert get_master_record("anything") == {}
