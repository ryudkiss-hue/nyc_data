"""
Build script — produces dist/MissionControlLauncher.exe via PyInstaller.
Run from the standalone/ directory:  python build_exe.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAUNCHER = HERE / "launcher.py"
ICON = HERE / "icons" / "icon.ico"
DIST_DIR = HERE / "dist"


def main() -> None:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--windowed",
        "--name",
        "MissionControlLauncher",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(HERE / "build"),
        "--specpath",
        str(HERE),
    ]

    if ICON.exists():
        cmd += ["--icon", str(ICON)]
    else:
        print(f"[INFO] Icon not found at {ICON} — building without --icon")

    cmd.append(str(LAUNCHER))

    print("Running PyInstaller …")
    print("  " + " ".join(cmd))
    result = subprocess.run(cmd, check=False)

    if result.returncode != 0:
        print("\n[ERROR] PyInstaller exited with code", result.returncode)
        sys.exit(result.returncode)

    exe = DIST_DIR / "MissionControlLauncher.exe"
    print("\n" + "=" * 60)
    print("Build complete!")
    print(f"  Executable : {exe}")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Verify the .exe runs: dist\\MissionControlLauncher.exe")
    print("  2. Compile the Inno Setup installer:")
    print('       "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe" standalone\\installer.iss')
    print("  3. The installer will be written to standalone\\Output\\")
    print()


if __name__ == "__main__":
    main()
