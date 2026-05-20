#!/bin/sh
set -e

cd /app

echo "=== NYC DOT Toolkit — setup entrypoint ==="

if [ ! -f .env ] && [ -f config/.env.example ]; then
  echo "Copying config/.env.example -> .env"
  cp config/.env.example .env
elif [ ! -f .env ] && [ -f .env.example ]; then
  echo "Copying .env.example -> .env"
  cp .env.example .env
fi

if [ ! -f config/analyst_profile.yaml ] && [ -f config/analyst_profile.example.yaml ]; then
  echo "Copying analyst profile example"
  cp config/analyst_profile.example.yaml config/analyst_profile.yaml
fi

mkdir -p data outputs outputs/analyst_pack config

if [ "${WIZARD_NONINTERACTIVE:-0}" = "1" ]; then
  python -m socrata_toolkit.install_wizard --non-interactive --skip-checks || true
fi

echo "Running health check..."
python -c "
import os
from pathlib import Path
from socrata_toolkit.install_wizard import test_duckdb_writable, test_socrata

duck = os.getenv('DUCKDB_PATH', 'nyc_mission_control.duckdb')
ok, msg = test_duckdb_writable(duck)
print('DuckDB:', msg)
token = os.getenv('SOCRATA_APP_TOKEN', '')
if token:
    ok, msg = test_socrata(token, os.getenv('SOCRATA_DOMAIN', 'data.cityofnewyork.us'))
    print('Socrata:', msg)
else:
    print('Socrata: skipped (no token)')
print('Setup entrypoint complete.')
"

exec "$@"
