# Apache Airflow Deployment Guide

## Table of Contents
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Deployment Steps](#deployment-steps)
- [Health Checks](#health-checks)
- [Accessing Airflow UI](#accessing-airflow-ui)
- [Monitoring](#monitoring)
- [Production Scaling](#production-scaling)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

**One-command Docker Compose deployment:**

```bash
# From project root
cd airflow
docker-compose up -d
bash init_airflow.sh
```

Access Airflow UI: http://localhost:8080 (admin/admin)

---

## Prerequisites

### System Requirements
- **Docker**: 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose**: 2.0+ ([Install Docker Compose](https://docs.docker.com/compose/install/))
- **Linux/macOS/Windows 10+**: Docker Desktop
- **Disk Space**: 5GB+ for containers and database
- **Memory**: 4GB+ RAM allocated to Docker

### Verify Installation

```bash
docker --version
# Docker version 20.10.x or higher

docker-compose --version
# Docker Compose version v2.x.x or higher
```

### API Requirements
- **Socrata App Token**: For NYC Open Data access
- **Slack Webhook URL** (optional): For alert notifications
- **PostgreSQL 14**: Included in docker-compose.yml

---

## Configuration

### Environment Variables

Create `.env` file in `airflow/` directory for local deployment, or set in docker-compose.yml for production:

```bash
# .env file
export SOCRATA_APP_TOKEN="your_app_token_here"
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
export AIRFLOW_ADMIN_USER="admin"
export AIRFLOW_ADMIN_PASSWORD="change_me_in_production"
export POSTGRES_WAREHOUSE_PASSWORD="postgres_password"
```

### Airflow Configuration Variables

These are set by `init_airflow.sh`, but can be modified via Airflow UI (Admin → Variables):

```
socrata_dataset_incidents: a2nx-4u46
socrata_dataset_repairs: wk7w-ppbj
incident_freshness_threshold: 24 (hours)
repair_freshness_threshold: 24 (hours)
```

### Connection Setup

#### PostgreSQL Connection (postgres_warehouse)
- **Host**: postgres (or hostname in production)
- **Port**: 5432
- **Database**: nyc_sidewalk
- **User**: airflow
- **Password**: airflow (change in production)

Auto-configured by `init_airflow.sh`.

#### Slack Connection (slack_notifications)
- **Type**: Slack
- **Webhook URL**: Set via SLACK_WEBHOOK_URL environment variable
- **Purpose**: Send alert notifications on DAG/task failures

#### Socrata API
- **Type**: HTTP
- **Base URL**: https://data.cityofnewyork.us
- **Authentication**: App token in headers

---

## Deployment Steps

### Step 1: Verify Docker Installation

```bash
docker run hello-world
# Should output "Hello from Docker!"
```

### Step 2: Build Docker Images

```bash
cd airflow
docker-compose build scheduler webserver
# Builds both Airflow scheduler and webserver containers
```

### Step 3: Start Services

```bash
docker-compose up -d
# -d flag runs services in background

# Monitor startup progress
docker-compose logs -f scheduler
# Ctrl+C to exit log stream
```

### Step 4: Wait for Services to Be Healthy

```bash
# Check health of all services
docker-compose ps
# All services should show "healthy" status after 30-60 seconds

# NAME                  STATUS              PORTS
# airflow-postgres      healthy (x seconds)
# airflow-redis         healthy (x seconds)
# airflow-scheduler     healthy (x seconds)
# airflow-webserver     healthy (x seconds)
```

### Step 5: Initialize Airflow Database

```bash
# Option A: Using provided initialization script (RECOMMENDED)
bash init_airflow.sh
# Creates admin user, sets up connections, validates DAGs

# Option B: Manual steps
docker-compose exec scheduler airflow db init

# Create admin user interactively
docker-compose exec scheduler airflow users create \
  --username admin \
  --password admin \
  --firstname Admin \
  --lastname User \
  --email admin@example.com \
  --role Admin

# Add connections manually (see Configuration section)
```

### Step 6: Verify DAG Discovery

```bash
docker-compose exec scheduler airflow dags list
# Should output all three DAGs:
# - incident_ingestion
# - repair_scheduling
# - metric_materialization
```

### Step 7: Trigger Test DAG Run

```bash
# List all DAG runs
docker-compose exec scheduler airflow dags list-runs

# Trigger incident_ingestion DAG manually
docker-compose exec scheduler airflow dags test incident_ingestion 2026-05-10

# Monitor logs
docker-compose logs -f scheduler | grep incident_ingestion
```

---

## Health Checks

### Verify All Services Running

```bash
# Check container status
docker-compose ps

# Expected output:
# SERVICE         STATUS              PORTS
# postgres        healthy (x seconds) 0.0.0.0:5432->5432/tcp
# redis           healthy (x seconds) 0.0.0.0:6379->6379/tcp
# scheduler       healthy (x seconds)
# webserver       healthy (x seconds) 0.0.0.0:8080->8080/tcp
```

### Test PostgreSQL Connection

```bash
# Connect to PostgreSQL container
docker-compose exec postgres psql -U airflow -d nyc_sidewalk -c "SELECT 1;"
# Should return: 1

# Check airflow_db schema
docker-compose exec postgres psql -U airflow -d airflow -c "\dt" | head
# Should list Airflow tables
```

### Test Redis Connection

```bash
docker-compose exec redis redis-cli ping
# Should return: PONG
```

### Test Scheduler Health

```bash
docker-compose exec scheduler airflow jobs check
# Should return success code

# Check recent scheduler logs
docker-compose logs scheduler --tail 20
```

### Test Webserver Health

```bash
curl http://localhost:8080/api/v1/pools
# Should return JSON response with pool information
```

---

## Accessing Airflow UI

### Local Access

**URL**: http://localhost:8080

**Default Credentials**:
- Username: `admin`
- Password: `admin`

### Features in Airflow UI

1. **DAGs**: View all scheduled DAGs
   - Click DAG name → see run history
   - Click "Trigger DAG" → start manual run

2. **Graph View**: Visualize task dependencies
   - Shows incident → repair → Metric flow
   - Color-coded by task status

3. **Admin Panel**:
   - **Connections**: Manage database/API connections
   - **Variables**: Store dataset IDs, thresholds, etc.
   - **Pools**: Limit concurrent task execution
   - **Users**: Manage access control

4. **Logs**: Debug task failures
   - Click task → view logs
   - Timestamp, retry info, exceptions shown

### Security Notes

- **Change default password** before production deployment
- Use RBAC (Admin → Security) to limit user access
- Store secrets in environment variables, not code
- Rotate API tokens regularly

---

## Monitoring

### Prometheus Integration

Airflow exposes metrics on port 9090 (configured in docker-compose.yml):

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'airflow'
    static_configs:
      - targets: ['localhost:9090']
```

### Key Metrics to Monitor

```
# Scheduler metrics
airflow_scheduler_heartbeat
airflow_scheduler_critical_section_duration_seconds

# DAG metrics
airflow_dag_status{dag_id="incident_ingestion",status="success"}
airflow_dag_duration_seconds{dag_id="repair_scheduling"}

# Task metrics
airflow_task_duration_seconds{dag_id="incident_ingestion",task_id="fetch_incidents"}
airflow_task_fail_total{dag_id="metric_materialization"}

# Database metrics
airflow_pool_queued_tasks{pool_id="contractor_pool"}
```

### Grafana Dashboard Setup

1. Add Prometheus data source: http://localhost:9090
2. Import Airflow dashboard template: [Official Airflow Grafana Dashboard](https://grafana.com/grafana/dashboards/15289)
3. Create custom panels for:
   - DAG success rate
   - Average task duration
   - SLA violations
   - Data freshness

### Log Aggregation

Configure centralized logging for production:

```yaml
# docker-compose.yml additions for ELK stack
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.0.0
  environment:
    - xpack.security.enabled=false
    - discovery.type=single-node

logstash:
  image: docker.elastic.co/logstash/logstash:8.0.0
  volumes:
    - ./logs:/var/log/airflow:ro
```

---

## Production Scaling

### CeleryExecutor Configuration

For high-volume DAG execution, upgrade from LocalExecutor to CeleryExecutor:

```yaml
# docker-compose.yml environment variables
AIRFLOW__CORE__EXECUTOR: CeleryExecutor
AIRFLOW__CELERY__BROKER_URL: redis://redis:6379/0
AIRFLOW__CELERY__RESULT_BACKEND: postgresql://airflow:password@postgres:5432/airflow
AIRFLOW__CELERY__WORKER_PREFETCH_MULTIPLIER: 4
AIRFLOW__CELERY__WORKER_MAX_TASKS_PER_CHILD: 100
```

### Multiple Workers

Add Celery workers to docker-compose.yml:

```yaml
worker1:
  build:
    context: ..
    dockerfile: airflow/Dockerfile.scheduler
  command: celery worker --queues default,high_priority
  environment:
    AIRFLOW__CORE__EXECUTOR: CeleryExecutor
    # ... other config ...
  depends_on:
    - postgres
    - redis
  networks:
    - airflow

worker2:
  build:
    context: ..
    dockerfile: airflow/Dockerfile.scheduler
  command: celery worker --queues default,low_priority
  environment:
    AIRFLOW__CORE__EXECUTOR: CeleryExecutor
    # ... other config ...
  depends_on:
    - postgres
    - redis
  networks:
    - airflow
```

### Redis Cluster (Advanced)

For production Redis (cluster mode):

```bash
# Create Redis cluster with 6 nodes (3 primary, 3 replica)
docker-compose exec redis redis-cli --cluster create \
  127.0.0.1:6379 127.0.0.1:6380 127.0.0.1:6381 \
  127.0.0.1:6382 127.0.0.1:6383 127.0.0.1:6384 \
  --cluster-replicas 1
```

### Database Tuning

```sql
-- Connect to PostgreSQL
docker-compose exec postgres psql -U airflow -d airflow

-- Increase connection pool
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = 256MB;

-- Restart PostgreSQL
docker-compose restart postgres
```

### Resource Limits

Set resource limits in docker-compose.yml:

```yaml
scheduler:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G

webserver:
  deploy:
    resources:
      limits:
        cpus: '1'
        memory: 1G
      reservations:
        cpus: '0.5'
        memory: 512M
```

---

## Troubleshooting

### Services Won't Start

```bash
# View startup logs
docker-compose logs scheduler

# Check common issues
# 1. Port already in use
netstat -tulpn | grep 8080  # Kill process using port 8080

# 2. Insufficient disk space
docker system prune -a

# 3. Corrupted volumes
docker-compose down -v  # WARNING: Deletes all data!
docker-compose up -d
bash init_airflow.sh
```

### DAGs Not Appearing in UI

```bash
# Verify DAG files exist
ls -la airflow/dags/*.py

# Check DAG parsing errors
docker-compose exec scheduler airflow dags list
# Look for error messages

# Validate DAG file syntax
docker-compose exec scheduler python -m py_compile airflow/dags/incident_ingestion.py
```

### Database Connection Errors

```bash
# Check PostgreSQL is running
docker-compose exec postgres pg_isready -U airflow

# Test connection
docker-compose exec scheduler airflow connections test postgres_warehouse

# Verify credentials in docker-compose.yml environment section
grep POSTGRES_WAREHOUSE docker-compose.yml
```

### Memory Issues

```bash
# Monitor container memory usage
docker stats airflow-scheduler airflow-webserver

# Increase Docker memory allocation
# Docker Desktop → Preferences → Resources → Memory: Set to 6GB or higher

# Check system memory
free -h
```

### Scheduler Not Triggering DAGs

```bash
# Check scheduler process is running
docker-compose exec scheduler ps aux | grep scheduler

# Review scheduler logs
docker-compose logs scheduler --tail 100

# Verify DAG schedule
docker-compose exec scheduler airflow dags show incident_ingestion
# Look for schedule_interval field

# Check SLA configuration
docker-compose exec scheduler airflow dags list --output json | \
  python3 -c "import sys, json; d=json.load(sys.stdin); print([x for x in d if 'sla' in x])"
```

### Task Failures

```bash
# View failed task logs
docker-compose logs scheduler | grep FAILED

# Inspect specific task execution
docker-compose exec scheduler airflow tasks logs incident_ingestion fetch_incidents 2026-05-10

# Retry failed task
docker-compose exec scheduler airflow tasks run incident_ingestion fetch_incidents 2026-05-10 --local
```

### Slack Notifications Not Sending

```bash
# Verify Slack connection exists
docker-compose exec scheduler airflow connections test slack_notifications

# Check webhook URL validity
curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
  -d '{"text":"Test message"}'

# Verify task has alert handler configured
grep -n "SlackOperator\|on_failure_callback" airflow/dags/*.py
```

### Performance Issues

```bash
# Check database query performance
docker-compose exec postgres psql -U airflow -d airflow -c "\timing on"
SELECT * FROM task_instance WHERE state='running' LIMIT 10;

# Analyze query plans
EXPLAIN ANALYZE SELECT * FROM task_instance WHERE dag_id='incident_ingestion';

# Increase PostgreSQL connection pool
docker-compose exec postgres psql -U airflow -d airflow -c \
  "ALTER SYSTEM SET max_connections = 200;"
docker-compose restart postgres
```

---

## Cleanup & Decommissioning

### Stop All Services

```bash
docker-compose down
# Stops containers but preserves volumes
```

### Stop and Remove All Data

```bash
docker-compose down -v
# WARNING: Deletes all Airflow metadata and database!
# Only use if decommissioning completely
```

### Remove Docker Images

```bash
docker-compose down --rmi all
# Removes images but preserves volumes
```

### Backup Database Before Cleanup

```bash
# Export PostgreSQL database
docker-compose exec postgres pg_dump -U airflow nyc_sidewalk > backup_$(date +%Y%m%d).sql

# Export Airflow metadata
docker-compose exec postgres pg_dump -U airflow airflow > airflow_metadata_$(date +%Y%m%d).sql
```

---

## Next Steps

- [Airflow Operations Guide](./airflow_operations.md): Daily operations & monitoring
- [DAG Development Guide](./airflow_migration_guide.md): Adding new DAGs and operators
- [Phase 3 Integration Guide](./PHASE3_INTEGRATION_GUIDE.md): How Phase 3 integrates with Phase 1/2
