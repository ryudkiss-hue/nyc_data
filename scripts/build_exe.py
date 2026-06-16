"""Build a standalone executable using PyInstaller."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build_executable() -> Path:
    """Build the socrata-toolkit executable via PyInstaller."""
    dist_dir = ROOT / "dist"
    spec_file = ROOT / "socrata_toolkit.spec"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--name",
        "socrata-toolkit",
        "--distpath",
        str(dist_dir),
        str(ROOT / "src" / "socrata_toolkit" / "core" / "cli.py"),
    ]

    if spec_file.exists():
        cmd = [sys.executable, "-m", "PyInstaller", str(spec_file)]

    subprocess.check_call(cmd)
    exe = dist_dir / "socrata-toolkit"
    if not exe.exists():
        exe = dist_dir / "socrata-toolkit.exe"
    return exe


if __name__ == "__main__":
    if os.getenv("PYINSTALLER_BUILD") == "1":
        out = build_executable()
        print(f"Built: {out}")
