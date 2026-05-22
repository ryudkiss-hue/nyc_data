#!/usr/bin/env bash
# Build standalone binaries on macOS or Linux (CLI + optional Mission Control bundle).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Building NYC DOT Toolkit on $(uname -s)…"

python -m pip install -U pip pyinstaller
pip install -e ".[exe,xlsx,mission]" -q

echo "--- CLI / analyst executable (PyInstaller spec) ---"
python scripts/build_exe.py

echo "--- Mission Control (Streamlit) one-dir bundle ---"
pyinstaller --noconfirm --onedir --name "NYCDataToolkit" \
  --paths "$ROOT/src" \
  --paths "$ROOT" \
  --add-data "app:app" \
  --add-data "config:config" \
  --add-data ".streamlit:.streamlit" \
  --hidden-import=streamlit \
  --hidden-import=pandas \
  --hidden-import=geopandas \
  --hidden-import=sodapy \
  --hidden-import=socrata_toolkit \
  --collect-all streamlit \
  "$ROOT/main.py"

echo ""
echo "Build complete."
echo "  CLI:     dist/nyc-dot-toolkit (or nyc-dot-toolkit.exe on Windows cross-build)"
echo "  Mission: dist/NYCDataToolkit/"
if [ "$(uname -s)" = "Darwin" ]; then
  echo "  macOS: open dist/NYCDataToolkit/NYCDataToolkit to run Mission Control."
fi
