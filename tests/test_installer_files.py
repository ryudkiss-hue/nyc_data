"""Installer asset checks (no full Inno compile unless INNO_SETUP=1)."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ISS_FILE = REPO_ROOT / "installer" / "nyc_dot_toolkit.iss"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_installer.ps1"

pytestmark = pytest.mark.skipif(
    not ISS_FILE.exists(),
    reason="installer/nyc_dot_toolkit.iss not present — skip installer checks",
)
DIST_EXE = REPO_ROOT / "dist" / "nyc-dot-toolkit.exe"
SETUP_OUTPUT = REPO_ROOT / "installer" / "output" / "NYC-DOT-Sidewalk-Toolkit-Setup.exe"

SOURCE_RE = re.compile(
    r'^Source:\s*"(?:\{\#RepoRoot\}\\|\.\.\\)?([^"]+)"',
    re.MULTILINE,
)


def _iss_source_paths() -> list[Path]:
    text = ISS_FILE.read_text(encoding="utf-8")
    paths: list[Path] = []
    for match in SOURCE_RE.finditer(text):
        raw = match.group(1).replace("/", "\\")
        raw = raw.replace("{#MyAppExeName}", "nyc-dot-toolkit.exe")
        if raw == "INSTALL.txt":
            paths.append(ISS_FILE.parent / "INSTALL.txt")
            continue
        if "*" in raw:
            base = raw.split("*", 1)[0].rstrip("\\")
            if base:
                paths.append(REPO_ROOT / base)
            continue
        paths.append(REPO_ROOT / raw)
    return paths


def test_iss_file_exists() -> None:
    assert ISS_FILE.is_file(), f"Missing Inno Setup script: {ISS_FILE}"


def test_build_installer_script_exists() -> None:
    assert BUILD_SCRIPT.is_file()


def test_iss_install_txt_in_script_folder() -> None:
    assert "INSTALL.txt" in ISS_FILE.read_text(encoding="utf-8")


def test_iss_referenced_paths_exist() -> None:
    missing: list[str] = []
    for path in _iss_source_paths():
        if path.name.endswith(".exe") and path == DIST_EXE:
            if not path.is_file():
                pytest.skip(f"PyInstaller output not built: {path}")
            continue
        if path.is_dir() or path.is_file():
            continue
        if any(path.parent.glob(path.name)):
            continue
        missing.append(str(path.relative_to(REPO_ROOT)))
    assert not missing, f"ISS references missing paths: {missing}"


def test_helper_scripts_exist() -> None:
    for name in (
        "register_scheduled_task.ps1",
        "launch_gui.ps1",
        "launch_dashboard.bat",
    ):
        assert (REPO_ROOT / "scripts" / name).is_file()


def test_install_txt_exists() -> None:
    assert (REPO_ROOT / "installer" / "INSTALL.txt").is_file()


def test_build_installer_ps1_contents() -> None:
    text = BUILD_SCRIPT.read_text(encoding="utf-8")
    assert "build_exe.py" in text
    assert "nyc_dot_toolkit.iss" in text
    assert "Find-InnoCompiler" in text
    assert "jrsoftware.org" in text
    assert "NYC-DOT-Sidewalk-Toolkit-Setup.exe" in text


@pytest.mark.skipif(os.getenv("INNO_SETUP") != "1", reason="Set INNO_SETUP=1 to compile installer")
def test_build_installer_produces_setup_exe() -> None:
    subprocess.run(
        ["powershell", "-NoProfile", "-File", str(BUILD_SCRIPT)],
        cwd=REPO_ROOT,
        check=True,
    )
    assert SETUP_OUTPUT.is_file()
