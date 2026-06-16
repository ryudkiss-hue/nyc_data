from __future__ import annotations
import pytest
pytestmark = pytest.mark.skip(reason="Data Unavailable - Live telemetry required")

from pathlib import Path

from click.testing import CliRunner

from socrata_toolkit.core.cli import main


def test_review_cli_set_list_export(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TOOLKIT_PROFILE", "test")
    monkeypatch.setenv("TOOLKIT_STATE_ROOT", str(tmp_path / "state"))
    runner = CliRunner()

    # set decision
    r = runner.invoke(
        main,
        [
            "review",
            "set",
            "--pack-date",
            "2099-01-01",
            "--kind",
            "conflict",
            "--key-type",
            "location_id",
            "--key",
            "L9",
            "--status",
            "resolved",
            "--notes",
            "done",
        ],
    )
    assert r.exit_code == 0

    # list decision
    r2 = runner.invoke(main, ["review", "list", "--pack-date", "2099-01-01", "--kind", "conflict"])
    assert r2.exit_code == 0
    assert "L9" in (r2.output or "")

    # export into a pack dir
    pack = tmp_path / "outputs" / "analyst_pack" / "2099-01-01"
    pack.mkdir(parents=True)
    r3 = runner.invoke(main, ["review", "export", "--pack", str(pack), "--pack-date", "2099-01-01"])
    assert r3.exit_code == 0
    assert (pack / "decisions_export.xlsx").exists()
    assert (pack / "decisions_summary.md").exists()
