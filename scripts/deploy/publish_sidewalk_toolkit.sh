#!/usr/bin/env bash
set -euo pipefail
SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DST_DIR="${1:-/workspace/sidewalk_toolkit}"

rm -rf "$DST_DIR"
mkdir -p "$DST_DIR"
rsync -a --exclude='.git' --exclude='__pycache__' --exclude='.venv' "$SRC_DIR/" "$DST_DIR/"

cd "$DST_DIR"
git init
git add .
git commit -m "Initial import from nyc_data" || true

echo "Sidewalk toolkit mirror created at: $DST_DIR"
