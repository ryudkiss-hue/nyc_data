#!/bin/bash

################################################################################
# Airflow Database Initialization Script
# Purpose: Automated setup of Airflow database, admin user, and connections
# Usage: ./init_airflow.sh
################################################################################

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if [[ $(python3 -c "print(1 if float('$PYTHON_VERSION') >= 3.9 else 0)") == "0" ]]; then
    log_error "Python 3.9+ is required, found $PYTHON_VERSION"
    exit 1
fi
log_info "Python version: $PYTHON_VERSION ✓"

if ! command -v pip &> /dev/null; then
    log_error "pip is not installed"
    exit 1
fi
log_info "pip is available ✓"

# Set Airflow home
export AIRFLOW_HOME="${AIRFLOW_HOME:=/opt/airflow}"
log_info "Using AIRFLOW_HOME: $AIRFLOW_HOME"

# Install/upgrade dependencies
log_info "Installing/upgrading dependencies from requirements.txt..."
if [ -f "$(dirname "$0")/requirements.txt" ]; then
    pip install --quiet --upgrade pip setuptools wheel
    pip install --quiet -r "$(dirname "$0")/requirements.txt"
    log_info "Dependencies installed ✓"
else
    log_error "requirements.txt not found in airflow directory"
    exit 1
fi

# Initialize Airflow database
log_info "Initializing Airflow database..."
if airflow db init 2>/dev/null; then
    log_info "Airflow database initialized ✓"
else
    log_warn "Airflow database initialization had warnings (likely already initialized)"
fi

# Create admin user
log_info "Creating Airflow admin user..."
ADMIN_USERNAME="${AIRFLOW_ADMIN_USER:-admin}"
ADMIN_PASSWORD="${AIRFLOW_ADMIN_PASSWORD:-admin}"
ADMIN_EMAIL="${AIRFLOW_ADMIN_EMAIL:-admin@example.com}"

# Check if admin user already exists
if airflow users list | grep -q "$ADMIN_USERNAME"; then
    log_warn "Admin user '$ADMIN_USERNAME' already exists, skipping creation"
else
    if airflow users create \
        --username "$ADMIN_USERNAME" \
        --password "$ADMIN_PASSWORD" \
        --firstname "Admin" \
        --lastname "User" \
        --email "$ADMIN_EMAIL" \
        --role Admin 2>/dev/null; then
        log_info "Admin user created ✓"
    else
        log_error "Failed to create admin user"
        exit 1
    fi
fi

# Add PostgreSQL connection to warehouse database
log_info "Adding PostgreSQL connection..."
POSTGRES_CONN_ID="postgres_warehouse"
POSTGRES_HOST="${POSTGRES_WAREHOUSE_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_WAREHOUSE_PORT:-5432}"
POSTGRES_USER="${POSTGRES_WAREHOUSE_USER:-airflow}"
POSTGRES_PASSWORD="${POSTGRES_WAREHOUSE_PASSWORD:-airflow}"
POSTGRES_DB="${POSTGRES_WAREHOUSE_DB:-nyc_sidewalk}"

airflow connections delete "$POSTGRES_CONN_ID" 2>/dev/null || true

airflow connections add "$POSTGRES_CONN_ID" \
    --conn-type postgres \
    --conn-host "$POSTGRES_HOST" \
    --conn-port "$POSTGRES_PORT" \
    --conn-login "$POSTGRES_USER" \
    --conn-password "$POSTGRES_PASSWORD" \
    --conn-schema "$POSTGRES_DB" 2>/dev/null

log_info "PostgreSQL connection added ✓"

# Add Slack connection (if webhook URL provided)
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    log_info "Adding Slack connection..."
    SLACK_CONN_ID="slack_notifications"
    
    airflow connections delete "$SLACK_CONN_ID" 2>/dev/null || true
    
    airflow connections add "$SLACK_CONN_ID" \
        --conn-type slack \
        --conn-password "$SLACK_WEBHOOK_URL" 2>/dev/null
    
    log_info "Slack connection added ✓"
else
    log_warn "SLACK_WEBHOOK_URL not set, skipping Slack connection"
fi

# Set Airflow variables
log_info "Setting Airflow variables..."

# Dataset IDs for Socrata ingestion
airflow variables set "socrata_dataset_incidents" "a2nx-4u46" 2>/dev/null || true
airflow variables set "socrata_dataset_repairs" "wk7w-ppbj" 2>/dev/null || true

# Freshness thresholds (in hours)
airflow variables set "incident_freshness_threshold" "24" 2>/dev/null || true
airflow variables set "repair_freshness_threshold" "24" 2>/dev/null || true

# Pool configuration
airflow pools delete "contractor_pool" 2>/dev/null || true
airflow pools create "contractor_pool" 4 "Pool for contractor scheduling tasks" 2>/dev/null || true

log_info "Airflow variables set ✓"

# Validate DAG parsing
log_info "Validating DAG parsing..."
DAG_COUNT=$(airflow dags list --output json 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data['dags']))" || echo "0")

if [ "$DAG_COUNT" -gt 0 ]; then
    log_info "Found $DAG_COUNT DAGs ✓"
else
    log_warn "No DAGs found - ensure dags/ directory exists and contains DAG files"
fi

# Summary
log_info "=========================================="
log_info "Airflow initialization completed!"
log_info "=========================================="
log_info "Admin user: $ADMIN_USERNAME"
log_info "Password: $ADMIN_PASSWORD (CHANGE THIS!)"
log_info "Email: $ADMIN_EMAIL"
log_info "Airflow Home: $AIRFLOW_HOME"
log_info "DAGs found: $DAG_COUNT"
log_info ""
log_info "Next steps:"
log_info "1. Update secrets:"
log_info "   - Change admin password in Airflow UI"
log_info "   - Set SLACK_WEBHOOK_URL for alerts"
log_info "   - Set SOCRATA_APP_TOKEN for API access"
log_info "2. Start Airflow:"
log_info "   - docker-compose up -d (for Docker)"
log_info "   - airflow webserver & airflow scheduler (for local)"
log_info "3. Access UI at http://localhost:8080"
log_info "=========================================="
