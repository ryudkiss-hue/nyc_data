"""Tests for install_wizard (mocked prompts, temp project root)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from socrata_toolkit.install_wizard import (
    run_connectivity_checks,
    run_wizard,
    write_analyst_profile,
    write_env_file,
)


@pytest.fixture
def mini_project(tmp_path: Path) -> Path:
    """Minimal repo layout for wizard tests."""
    (tmp_path / "config").mkdir()
    example = tmp_path / "config" / "analyst_profile.example.yaml"
    example.write_text(
        "profile_name: test\n"
        "duckdb_path: data/local_db/nyc_mission_control.duckdb\n"
        "outputs:\n  dir: outputs/analyst_pack\n"
        "sources: {}\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname='t'\n", encoding="utf-8")
    return tmp_path


def test_write_env_and_profile(mini_project: Path) -> None:
    values = {
        "SOCRATA_APP_TOKEN": "test-token",
        "SOCRATA_DOMAIN": "data.cityofnewyork.us",
        "PG_DSN": "",
        "DATA_DIR": str(mini_project / "data"),
        "OUTPUT_DIR": str(mini_project / "outputs"),
        "ANALYST_PROFILE": str(mini_project / "config" / "analyst_profile.yaml"),
        "DUCKDB_PATH": str(mini_project / "db.duckdb"),
    }
    env_path = write_env_file(mini_project, values)
    assert env_path.exists()
    text = env_path.read_text(encoding="utf-8")
    assert "SOCRATA_APP_TOKEN=test-token" in text
    assert "DATA_DIR=" in text

    profile = write_analyst_profile(mini_project, values)
    assert profile is not None and profile.exists()
    data = yaml.safe_load(profile.read_text(encoding="utf-8"))
    assert data["duckdb_path"] == values["DUCKDB_PATH"]
    assert "analyst_pack" in data["outputs"]["dir"]


@patch.dict(
    "os.environ",
    {
        "WIZARD_NONINTERACTIVE": "1",
        "WIZARD_ALLOW_EMPTY_TOKEN": "1",
        "SOCRATA_APP_TOKEN": "",
        "SOCRATA_DOMAIN": "data.cityofnewyork.us",
        "PG_DSN": "",
        "DATA_DIR": "",
        "OUTPUT_DIR": "",
        "ANALYST_PROFILE": "",
        "DUCKDB_PATH": "",
    },
    clear=False,
)
def test_run_wizard_non_interactive(mini_project: Path) -> None:
    with patch.dict(
        "os.environ",
        {
            "DATA_DIR": str(mini_project / "data"),
            "OUTPUT_DIR": str(mini_project / "outputs"),
            "ANALYST_PROFILE": str(mini_project / "config" / "analyst_profile.yaml"),
            "DUCKDB_PATH": str(mini_project / "test.duckdb"),
        },
        clear=False,
    ):
        summary = run_wizard(root=mini_project, non_interactive=True, skip_checks=True)
    assert Path(summary["env_file"]).exists()
    assert Path(summary["analyst_profile"]).exists()


def test_connectivity_checks_skip_duckdb_only(mini_project: Path) -> None:
    values = {
        "SOCRATA_APP_TOKEN": "",
        "SOCRATA_DOMAIN": "data.cityofnewyork.us",
        "PG_DSN": "",
        "DUCKDB_PATH": str(mini_project / "wizard_test.duckdb"),
    }
    results = run_connectivity_checks(values)
    assert results["duckdb"]["ok"] is True


def test_build_exe_script_exists() -> None:
    """Smoke: build script present; full PyInstaller only when PYINSTALLER_BUILD=1."""
    import importlib.util
    import os

    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "build_exe.py"
    assert script.exists()
    spec = importlib.util.spec_from_file_location("build_exe", script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.build_executable)
    if os.getenv("PYINSTALLER_BUILD") != "1":
        return
    out = mod.build_executable()
    assert out.exists()
