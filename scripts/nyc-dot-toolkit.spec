# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for NYC DOT Sidewalk Toolkit (Windows-focused)
# Build: python scripts/build_exe.py

import sys
from pathlib import Path

block_cipher = None
project_root = Path(SPECPATH).parent
sep = ";" if sys.platform.startswith("win") else ":"

datas = [
    (str(project_root / "config"), "config"),
    (str(project_root / "socrata_toolkit"), "socrata_toolkit"),
]

hiddenimports = [
    "click",
    "pandas",
    "numpy",
    "requests",
    "duckdb",
    "yaml",
    "dotenv",
    "tqdm",
    "tenacity",
    "apscheduler",
    "socrata_toolkit",
    "socrata_toolkit.core",
    "socrata_toolkit.core.cli",
    "socrata_toolkit.install_wizard",
    "socrata_toolkit.analyst",
    "socrata_toolkit.analyst.workflow",
    "socrata_toolkit.analyst.pack",
    "socrata_toolkit.analyst.config",
    "socrata_toolkit.analyst.sources",
    "socrata_toolkit.pipeline",
    "socrata_toolkit.pipeline.sync",
    "psycopg",
    "openpyxl",
]

a = Analysis(
    [str(project_root / "scripts" / "exe_entry.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib.tests", "pandas.tests", "pytest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="nyc-dot-toolkit",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
