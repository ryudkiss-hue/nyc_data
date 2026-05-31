"""
Build script — produces the NYC DOT Analyst Toolkit .exe via PyInstaller.
Run from the standalone/ directory:  python build_exe.py

Produces:
  dist/NYCDOTToolkit.exe  — native desktop window (pywebview + Streamlit, no browser)

Usage:
  python build_exe.py            # build the desktop .exe
  python build_exe.py --debug    # keep console window for troubleshooting
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DESKTOP = HERE / "desktop_app.py"
ICON = HERE / "icons" / "icon.ico"
DIST_DIR = HERE / "dist"

# Data files that must be bundled: (source, dest_dir_in_bundle)
DATA_FILES: list[tuple[str, str]] = [
    (str(ROOT / "config"), "config"),
    (str(ROOT / "app"), "app"),
    (str(ROOT / "src"), "src"),
]


def _run_pyinstaller(*, debug: bool) -> int:
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "NYCDOTToolkit",
        "--distpath", str(DIST_DIR),
        "--workpath", str(HERE / "build"),
        "--specpath", str(HERE),
        "--noconfirm",
        "--collect-all", "webview",
        "--collect-all", "streamlit",
        "--hidden-import", "streamlit.web.cli",
        "--hidden-import", "streamlit.runtime",
        "--hidden-import", "plotly",
        "--hidden-import", "openpyxl",
        "--hidden-import", "duckdb",
        "--hidden-import", "pandas",
        "--hidden-import", "numpy",
        "--hidden-import", "altair",
        "--hidden-import", "pydeck",
    ]

    if not debug:
        cmd.append("--windowed")

    for src, dst in DATA_FILES:
        if Path(src).exists():
            cmd += ["--add-data", f"{src}{';' if sys.platform == 'win32' else ':'}{dst}"]

    if ICON.exists():
        cmd += ["--icon", str(ICON)]
    else:
        print(f"[INFO] Icon not found at {ICON} — building without --icon")

    cmd.append(str(DESKTOP))

    print("\nRunning PyInstaller …")
    print("  " + " ".join(cmd))
    return subprocess.run(cmd, check=False).returncode


def main() -> None:
    args = set(sys.argv[1:])
    debug = "--debug" in args

    rc = _run_pyinstaller(debug=debug)
    if rc != 0:
        print(f"\n[ERROR] Build failed with exit code {rc}")
        sys.exit(rc)

    exe_path = DIST_DIR / ("NYCDOTToolkit.exe" if sys.platform == "win32" else "NYCDOTToolkit")
    print("\n" + "=" * 60)
    print("✅  Build complete!")
    print(f"   Executable : {exe_path}")
    print("=" * 60)
    print()
    print("To run:")
    print(f"   {exe_path}")
    print()
    print("To build the Windows installer (Inno Setup):")
    print('   "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe" standalone\\installer.iss')
    print()


if __name__ == "__main__":
    main()
