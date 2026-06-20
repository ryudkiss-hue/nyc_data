#!/bin/bash
set -e
echo "Running NYC DOT Fuzzy Router Demo..."
cd "$(dirname "$0")/.."
python3 training/demo_workflow.py
