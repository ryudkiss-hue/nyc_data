#!/usr/bin/env bash
set -euo pipefail
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements-dev.txt
python -m spacy download en_core_web_sm || true
python -m textblob.download_corpora || true
echo "Bootstrap complete. Run: source .venv/bin/activate && socrata doctor"
