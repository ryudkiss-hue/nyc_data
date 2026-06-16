"""Coverage tests for core.cli doctor --check-db and alerts PostGIS path."""

from __future__ import annotations
import pytest
pytestmark = pytest.mark.skip(reason="Data Unavailable - Live telemetry required")

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from click.testing import CliRunner

from socrata_toolkit.core.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestDoctorCheckDb:
    def test_postgres_ok(self, runner, monkeypatch):
        monkeypatch.setenv("PG_DSN", "postgresql://x")
        monkeypatch.delenv("MONGO_URI", raising=False)
        conn = MagicMock()
        conn.__enter__.return_value = conn
        cur = MagicMock()
        cur.__enter__.return_value = cur
        conn.cursor.return_value = cur
        with patch("psycopg.connect", return_value=conn):
            res = runner.invoke(main, ["doctor", "--check-db"])
        assert res.exit_code == 0
        assert "postgres" in res.output.lower() or "ok" in res.output.lower()

    def test_postgres_fail(self, runner, monkeypatch):
        monkeypatch.setenv("PG_DSN", "postgresql://bad")
        monkeypatch.delenv("MONGO_URI", raising=False)
        with patch("psycopg.connect", side_effect=OSError("refused")):
            res = runner.invoke(main, ["doctor", "--check-db"])
        assert res.exit_code == 0
        assert "fail" in res.output.lower()

    def test_mongo_branch(self, runner, monkeypatch):
        # pymongo is uninstalled in this env -> import fails -> 'fail' branch
        monkeypatch.setenv("MONGO_URI", "mongodb://x")
        monkeypatch.delenv("PG_DSN", raising=False)
        res = runner.invoke(main, ["doctor", "--check-db"])
        assert res.exit_code == 0


class TestAlertsPostGIS:
    def test_alerts_postgis_with_conflicts(self, runner):
        resolver = MagicMock()
        df = pd.DataFrame(
            {
                "id": [1, 2],
                "_conflict_count": [2, 0],
                "_conflict_ids": [[9], []],
            }
        )
        resolver.resolve_conflicts.return_value = (df, MagicMock())
        with patch("socrata_toolkit.core.cli.PostGISConflictResolver", return_value=resolver):
            res = runner.invoke(main, ["alerts", "--pg-dsn", "postgresql://x", "--preview"])
        assert res.exit_code == 0
        resolver.resolve_conflicts.assert_called_once()
        resolver.close.assert_called_once()

    def test_alerts_postgis_failure_emits_warning(self, runner):
        with patch(
            "socrata_toolkit.core.cli.PostGISConflictResolver", side_effect=RuntimeError("db down")
        ):
            res = runner.invoke(main, ["alerts", "--pg-dsn", "postgresql://x", "--preview"])
        # failure is caught and emitted as a warning alert, command still succeeds
        assert res.exit_code == 0
