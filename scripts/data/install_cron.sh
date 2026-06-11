#!/usr/bin/env bash
# Install cron jobs for the DOT Sidewalk Toolkit
# Usage: bash scripts/install_cron.sh
#
# This script adds nightly ingest and weekly report generation to the
# system crontab. Adjust paths and schedule as needed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="$(command -v python3 || echo python)"
VENV_PYTHON="${PROJECT_DIR}/.venv/bin/python"

# Use virtualenv Python if available
if [ -f "$VENV_PYTHON" ]; then
    PYTHON="$VENV_PYTHON"
fi

echo "Installing cron jobs for DOT Sidewalk Toolkit"
echo "Project dir: $PROJECT_DIR"
echo "Python: $PYTHON"
echo ""

# Build crontab entries
NIGHTLY="0 2 * * * cd $PROJECT_DIR && $PYTHON -c \"from socrata_toolkit.workflow_engine import WorkflowEngine, create_nightly_ingest_workflow; e=WorkflowEngine(); e.register(create_nightly_ingest_workflow('data.cityofnewyork.us','h9gi-nx95')); e.run('nightly_ingest')\" >> $PROJECT_DIR/outputs/cron.log 2>&1"

WEEKLY_REPORT="0 8 * * 1 cd $PROJECT_DIR && $PYTHON -c \"from socrata_toolkit.workflow_engine import WorkflowEngine, create_construction_list_workflow; e=WorkflowEngine(); e.register(create_construction_list_workflow('data.cityofnewyork.us','h9gi-nx95')); e.run('build_construction_list')\" >> $PROJECT_DIR/outputs/cron.log 2>&1"

# Check if already installed
EXISTING=$(crontab -l 2>/dev/null || true)
if echo "$EXISTING" | grep -q "socrata_toolkit"; then
    echo "Cron jobs already installed. Skipping."
    echo "To reinstall, first run: crontab -l | grep -v socrata_toolkit | crontab -"
    exit 0
fi

# Install
(echo "$EXISTING"; echo "# DOT Sidewalk Toolkit - Nightly Ingest (2 AM daily)"; echo "$NIGHTLY"; echo "# DOT Sidewalk Toolkit - Weekly Construction List (8 AM Monday)"; echo "$WEEKLY_REPORT") | crontab -

echo "Cron jobs installed:"
echo "  - Nightly ingest: 2:00 AM daily"
echo "  - Weekly construction list: 8:00 AM every Monday"
echo ""
echo "View with: crontab -l"
echo "Logs at: $PROJECT_DIR/outputs/cron.log"
