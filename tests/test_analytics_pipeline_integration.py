"""Tests for Analytics Pipeline Integration."""

from __future__ import annotations

import pytest
import pandas as pd
from socrata_toolkit.pipeline.sync import sync_dataset
from socrata_toolkit.core import DuckDBManager

class TestPipelineAnalytics:
    def test_sync_triggers_audit(self, monkeypatch, tmp_path):
        # We need to mock SocrataClient to avoid network calls
        class MockClient:
            def __init__(self, *args, **kwargs):
                self.config = type('obj', (object,), {'app_token': ''})
            def fetch_json(self, *args, **kwargs):
                yield [{"Unique Key": "1", "val": 10}, {"Unique Key": "2", "val": 20}]
            def _headers(self): return {}

        monkeypatch.setattr("socrata_toolkit.pipeline.sync.SocrataClient", MockClient)
        
        # Mock requests.get for the probe
        class MockResponse:
            status_code = 200
            def json(self): return [{"count": 2}]
        monkeypatch.setattr("requests.get", lambda *args, **kwargs: MockResponse())

        db_path = str(tmp_path / "test.duckdb")
        table_name = "test_sync_audit"
        
        count = sync_dataset(
            domain="data.cityofnewyork.us",
            fourfour="test-4444",
            db_path=db_path,
            table_name=table_name,
            updated_col="val"
        )
        
        assert count == 2
        
        # Verify analysis_history exists and contains a record
        manager = DuckDBManager(db_path)
        tables = manager.conn.execute("SHOW TABLES").fetchall()
        assert any(t[0] == "analysis_history" for t in tables)
        
        history = manager.conn.execute("SELECT * FROM analysis_history").df()
        assert len(history) > 0
        assert history.iloc[0]["skill_name"] == "DataQualityAudit"
        assert history.iloc[0]["table_name"] == table_name
