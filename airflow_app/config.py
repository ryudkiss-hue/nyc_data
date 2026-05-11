"""
Airflow Configuration Management for NYC DOT Sidewalk Inspection.

Handles:
- Connection definitions (PostgreSQL warehouse, Socrata API, Slack)
- DAG defaults (retries, timeouts, SLAs)
- Executor configuration (LocalExecutor for dev, CeleryExecutor for prod)
- Logging configuration
- Scheduler settings
"""

import os
from datetime import timedelta
from typing import Dict, Any

# ============================================================================
# ENVIRONMENT & DEPLOYMENT CONFIGURATION
# ============================================================================

AIRFLOW_HOME = os.getenv("AIRFLOW_HOME", "/opt/airflow")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# ============================================================================
# CORE AIRFLOW CONFIGURATION
# ============================================================================

# Database connection for Airflow metadata store
AIRFLOW_DB_USER = os.getenv("AIRFLOW_DB_USER", "airflow_user")
AIRFLOW_DB_PASSWORD = os.getenv("AIRFLOW_DB_PASSWORD", "airflow_password")
AIRFLOW_DB_HOST = os.getenv("AIRFLOW_DB_HOST", "postgres")
AIRFLOW_DB_PORT = os.getenv("AIRFLOW_DB_PORT", "5432")
AIRFLOW_DB_NAME = os.getenv("AIRFLOW_DB_NAME", "airflow")

SQLALCHEMY_CONN = (
    f"postgresql://{AIRFLOW_DB_USER}:{AIRFLOW_DB_PASSWORD}@"
    f"{AIRFLOW_DB_HOST}:{AIRFLOW_DB_PORT}/{AIRFLOW_DB_NAME}"
)

# Executor selection
EXECUTOR_TYPE = "CeleryExecutor" if IS_PRODUCTION else "LocalExecutor"

# Parallelism settings
PARALLELISM = 8 if IS_PRODUCTION else 4  # Max concurrent task slots
DAG_CONCURRENCY = 4  # Max concurrent tasks per DAG
MAX_ACTIVE_RUNS_PER_DAG = 2

# Scheduler settings
SCHEDULER_HEARTBEAT_SEC = 5  # Scheduler loop frequency (seconds)
CATCHUP_BY_DEFAULT = False  # Don't backfill historical DAG runs by default

# ============================================================================
# DIRECTORIES
# ============================================================================

DAGS_FOLDER = os.path.join(AIRFLOW_HOME, "dags")
LOGS_FOLDER = os.path.join(AIRFLOW_HOME, "logs")
PLUGINS_FOLDER = os.path.join(AIRFLOW_HOME, "plugins")
BASE_LOG_FOLDER = os.getenv("BASE_LOG_FOLDER", LOGS_FOLDER)

# Ensure directories exist
for folder in [DAGS_FOLDER, LOGS_FOLDER, PLUGINS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOG_FORMAT = "[%(asctime)s] {{%(filename)s:%(lineno)d}} %(levelname)s - %(message)s"
SIMPLE_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Structured logging for observability
ENABLE_STRUCTURED_LOGGING = True

# ============================================================================
# SMTP & ALERTING CONFIGURATION
# ============================================================================

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_MAIL_FROM = os.getenv("SMTP_MAIL_FROM", "airflow@nycdot.local")

# Slack alerting (for DAG failures)
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_CHANNEL_ALERTS = os.getenv("SLACK_CHANNEL_ALERTS", "#data-pipelines-alerts")

# ============================================================================
# CONNECTION DEFINITIONS (PostgreSQL, Socrata, Slack, Redis)
# ============================================================================

# PostgreSQL Warehouse Connection (stores fact tables, dimensions, checkpoints)
POSTGRES_WAREHOUSE_CONN = {
    "conn_id": "postgres_warehouse",
    "conn_type": "postgres",
    "host": os.getenv("POSTGRES_WAREHOUSE_HOST", "postgres"),
    "port": int(os.getenv("POSTGRES_WAREHOUSE_PORT", "5432")),
    "login": os.getenv("POSTGRES_WAREHOUSE_USER", "postgres"),
    "password": os.getenv("POSTGRES_WAREHOUSE_PASSWORD", "postgres"),
    "schema": os.getenv("POSTGRES_WAREHOUSE_DB", "nyc_sidewalk"),
}

# Socrata API Connection (311 data source)
SOCRATA_API_CONN = {
    "conn_id": "socrata_api",
    "conn_type": "http",
    "host": "data.cityofnewyork.us",
    "extra": {
        "dataset_id": os.getenv("SOCRATA_311_DATASET_ID", "a2nx-4u46"),
        "app_token": os.getenv("SOCRATA_APP_TOKEN", ""),
        "verify_ssl": not IS_PRODUCTION or os.getenv("SOCRATA_VERIFY_SSL", "true").lower() == "true",
    },
}

# Slack Connection (for notifications)
SLACK_CONN = {
    "conn_id": "slack_alerts",
    "conn_type": "slack",
    "host": "hooks.slack.com",
    "extra": {
        "webhook_token": os.getenv("SLACK_WEBHOOK_TOKEN", ""),
    },
}

# Redis Connection (Celery broker + result backend for production)
REDIS_CONN = {
    "conn_id": "redis_broker",
    "conn_type": "redis",
    "host": os.getenv("REDIS_HOST", "redis"),
    "port": int(os.getenv("REDIS_PORT", "6379")),
    "db": int(os.getenv("REDIS_DB", "0")),
    "password": os.getenv("REDIS_PASSWORD", ""),
}

# ============================================================================
# CELERY CONFIGURATION (for production CeleryExecutor)
# ============================================================================

CELERY_BROKER_URL = (
    f"redis://{REDIS_CONN['host']}:{REDIS_CONN['port']}/{REDIS_CONN['db']}"
)
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# ============================================================================
# DAG DEFAULT SETTINGS
# ============================================================================

DAG_DEFAULT_ARGS = {
    "owner": "nyc-dot-data-eng",
    "depends_on_past": False,  # Each run is independent (idempotent)
    "start_date": "2024-01-01",
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,  # Retry failed tasks up to 3 times
    "retry_delay": timedelta(minutes=5),  # Initial backoff: 5 minutes
    "retry_exponential_backoff": True,  # Exponential backoff: 5m, 10m, 20m
    "max_retry_delay": timedelta(minutes=60),  # Cap backoff at 60 minutes
    "execution_timeout": timedelta(hours=2),  # Kill task if it takes >2 hours
    "pool": "default_pool",  # Default task pool
    "pool_slots": 1,  # Each task occupies 1 slot
}

# ============================================================================
# SLA CONFIGURATION (Service Level Agreements per DAG)
# ============================================================================

SLA_CONFIG = {
    "sidewalk_incident_ingestion": {
        "sla_seconds": 3600,  # Must complete within 1 hour
        "alert_email": os.getenv("ALERT_EMAIL", "data-eng@nycdot.local"),
    },
    "repair_scheduling": {
        "sla_seconds": 7200,  # Must complete within 2 hours
        "alert_email": os.getenv("ALERT_EMAIL", "data-eng@nycdot.local"),
    },
    "kpi_materialization": {
        "sla_seconds": 3600,  # Must complete within 1 hour
        "alert_email": os.getenv("ALERT_EMAIL", "data-eng@nycdot.local"),
    },
}

# ============================================================================
# CHECKPOINT CONFIGURATION (for incremental loads)
# ============================================================================

CHECKPOINT_CONFIG = {
    "incident_ingestion": {
        "table_name": "incident_ingestion_checkpoint",
        "checkpoint_column": "max_update_timestamp",
        "record_count_column": "record_count",
        "lookback_hours": 24,  # Always look back 24h for safety
    },
    "kpi_materialization": {
        "table_name": "kpi_materialization_checkpoint",
        "checkpoint_column": "max_fact_timestamp",
        "record_count_column": "materialized_record_count",
        "lookback_hours": 24,
    },
}

# ============================================================================
# SCHEMA REGISTRY CONFIGURATION
# ============================================================================

SCHEMA_REGISTRY_PATH = os.path.join(
    os.path.dirname(__file__), "..", "socrata_toolkit", "schema_registry.py"
)

# ============================================================================
# OBSERVABILITY & METRICS CONFIGURATION
# ============================================================================

# Prometheus metrics endpoint
METRICS_ENDPOINT = "http://localhost:9090"
METRICS_ENABLED = True

# Freshness tracking (Phase 2 integration)
FRESHNESS_CHECK_ENABLED = True
FRESHNESS_MAX_STALE_HOURS = 24

# Lineage tracking (Phase 2 integration)
LINEAGE_TRACKING_ENABLED = True

# Audit logging (Phase 2 integration)
AUDIT_LOG_TABLE = "audit_log"
AUDIT_LOG_ENABLED = True

# ============================================================================
# FEATURE FLAGS
# ============================================================================

FEATURES = {
    "incremental_load": True,  # Use checkpoint-based incremental loads
    "schema_drift_detection": True,  # Detect breaking schema changes
    "data_quality_checks": True,  # Run data quality validations
    "freshness_monitoring": True,  # Monitor source data freshness
    "slack_notifications": bool(SLACK_WEBHOOK_URL),  # Send alerts to Slack
    "email_notifications": bool(SMTP_USER),  # Send alerts via email
}

# ============================================================================
# FUNCTION: Get DAG defaults with SLA
# ============================================================================


def get_dag_defaults(dag_id: str) -> Dict[str, Any]:
    """
    Get DAG-specific defaults including SLA settings.

    Args:
        dag_id: DAG identifier string

    Returns:
        Dictionary of DAG default settings with SLA configuration
    """
    defaults = DAG_DEFAULT_ARGS.copy()

    if dag_id in SLA_CONFIG:
        defaults["sla"] = timedelta(seconds=SLA_CONFIG[dag_id]["sla_seconds"])

    return defaults


# ============================================================================
# FUNCTION: Get connection details
# ============================================================================


def get_connection(conn_id: str) -> Dict[str, Any]:
    """
    Get connection configuration by ID.

    Args:
        conn_id: Connection identifier

    Returns:
        Connection configuration dictionary

    Raises:
        ValueError: If connection ID not found
    """
    connections = {
        "postgres_warehouse": POSTGRES_WAREHOUSE_CONN,
        "socrata_api": SOCRATA_API_CONN,
        "slack_alerts": SLACK_CONN,
        "redis_broker": REDIS_CONN,
    }

    if conn_id not in connections:
        raise ValueError(f"Connection '{conn_id}' not found in configuration")

    return connections[conn_id]


# ============================================================================
# VALIDATION: Ensure required environment variables are set
# ============================================================================

if IS_PRODUCTION:
    required_vars = [
        "AIRFLOW_DB_HOST",
        "POSTGRES_WAREHOUSE_HOST",
        "SOCRATA_APP_TOKEN",
        "SLACK_WEBHOOK_URL",
        "REDIS_HOST",
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise EnvironmentError(
            f"Missing required environment variables for production: {missing_vars}"
        )
