"""
Build script — produces the Windows executables via PyInstaller.
Run from the standalone/ directory:  python build_exe.py

Builds two executables into dist/:
  - MissionControlLauncher.exe : tkinter install/config wizard (opens in browser)
  - MissionControl.exe         : native desktop window (pywebview, no browser)

Pass --launcher-only or --desktop-only to build just one.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAUNCHER = HERE / "launcher.py"
DESKTOP = HERE / "desktop_app.py"
ICON = HERE / "icons" / "icon.ico"
DIST_DIR = HERE / "dist"


def _run_pyinstaller(script: Path, name: str, *, collect_webview: bool) -> int:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--windowed",
        "--name",
        name,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(HERE / "build"),
        "--specpath",
        str(HERE),
        "--noconfirm",
    ]
    if collect_webview:
        # pywebview loads its platform backend dynamically — bundle it all.
        cmd += ["--collect-all", "webview"]
    if ICON.exists():
        cmd += ["--icon", str(ICON)]
    else:
        print(f"[INFO] Icon not found at {ICON} — building {name} without --icon")
    cmd.append(str(script))

    print(f"\nRunning PyInstaller for {name} …")
    print("  " + " ".join(cmd))
    return subprocess.run(cmd, check=False).returncode


def main() -> None:
    args = set(sys.argv[1:])
    build_launcher = "--desktop-only" not in args
    build_desktop = "--launcher-only" not in args

    if build_launcher:
        rc = _run_pyinstaller(LAUNCHER, "MissionControlLauncher", collect_webview=False)
        if rc != 0:
            print("\n[ERROR] Launcher build failed with code", rc)
            sys.exit(rc)

    if build_desktop:
        rc = _run_pyinstaller(DESKTOP, "MissionControl", collect_webview=True)
        if rc != 0:
            print("\n[ERROR] Desktop build failed with code", rc)
            sys.exit(rc)

    print("\n" + "=" * 60)
    print("Build complete!")
    if build_launcher:
        print(f"  Launcher (browser) : {DIST_DIR / 'MissionControlLauncher.exe'}")
    if build_desktop:
        print(f"  Desktop (native)   : {DIST_DIR / 'MissionControl.exe'}")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Verify an .exe runs (e.g. dist\\MissionControl.exe)")
    print("  2. Compile the Inno Setup installer:")
    print('       "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe" standalone\\installer.iss')
    print("  3. The installer is written to standalone\\Output\\")
    print()
    print("Note: the native desktop app needs pywebview installed in the")
    print("      Python that runs it:  pip install pywebview")
    print()


if __name__ == "__main__":
    main()
