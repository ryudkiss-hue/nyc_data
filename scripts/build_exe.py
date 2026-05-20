"""Build standalone Windows executable with PyInstaller."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def build_executable(*, setup_only: bool = False) -> Path:
    """Compile NYC DOT Toolkit into dist/nyc-dot-toolkit.exe (or platform binary)."""
    print("--- Building NYC DOT Toolkit standalone executable ---")

    try:
        import PyInstaller  # noqa: F401

        print("PyInstaller is ready.")
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    project_root = Path(__file__).parent.parent.resolve()
    spec = project_root / "scripts" / "nyc-dot-toolkit.spec"
    if not spec.exists():
        raise FileNotFoundError(f"Spec file not found: {spec}")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(spec),
        "--clean",
        "--noconfirm",
        f"--distpath={project_root / 'dist'}",
        f"--workpath={project_root / 'build'}",
    ]
    if setup_only:
        cmd.extend(["--name", "nyc-dot-setup"])
        # Alternate one-file setup binary from same entry with wizard-only argv
        print("Note: setup-only alias uses main exe; run: nyc-dot-toolkit.exe wizard")

    print("Compiling (2–8 minutes depending on dependencies)...")
    subprocess.run(cmd, cwd=project_root, check=True, env={**os.environ, "SPECPATH": str(project_root / "scripts")})

    out = project_root / "dist" / "nyc-dot-toolkit.exe"
    if not out.exists():
        # Linux/macOS build name has no .exe
        candidates = list((project_root / "dist").glob("nyc-dot-toolkit*"))
        out = candidates[0] if candidates else out

    print(f"Build complete: {out}")
    if out.exists():
        size_mb = out.stat().st_size / (1024 * 1024)
        print(f"Approximate size: {size_mb:.1f} MB")
    return out


if __name__ == "__main__":
    build_executable()
