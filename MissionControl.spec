# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all submodules for socrata_toolkit
hidden_imports = collect_submodules('socrata_toolkit')
# Add common hidden imports for LangChain and DuckDB
hidden_imports += [
    'langchain_openai',
    'duckdb_engine',
    'sqlalchemy.sql.functions',
    'sqlalchemy.sql.expression',
    'tenacity',
    'apscheduler',
    'apscheduler.schedulers.blocking',
    'apscheduler.triggers.cron'
]

datas = []
# If you have specific data files (like DuckDB extensions), add them here:
# datas += [('path/to/spatial.duckdb_extension', '.')]

a = Analysis(
    ['socrata_toolkit/core/cli.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='MissionControl',
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
    icon=['resources/icon.ico'] if os.path.exists('resources/icon.ico') else None,
)
