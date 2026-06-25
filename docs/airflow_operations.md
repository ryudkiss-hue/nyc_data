# Airflow Operations Guide

## Table of Contents
- [SLA Monitoring](#sla-monitoring)
- [Manual DAG Runs](#manual-dag-runs)
- [Backfilling Historical Data](#backfilling-historical-data)
- [Alerting Setup](#alerting-setup)
- [Log Management](#log-management)
- [Metrics & Observability](#metrics--observability)
- [Recovery Procedures](#recovery-procedures)
- [Performance Tuning](#performance-tuning)

---

## SLA Monitoring

### SLA Overview

Service Level Agreements (SLAs) define maximum allowed execution times for DAGs and tasks. Violations trigger alerts and are tracked in Airflow UI.

### Three Critical DAGs & Their SLAs

#### 1. incident_ingestion

**Purpose**: Fetch new incident data from Socrata API every 6 hours

**SLA Configuration**:
- **Dag SLA**: 1 hour (must complete within 1 hour of scheduled start)
- **Task SLAs**:
  - `fetch_incidents`: 15 minutes (API call with retry)
  - `validate_data`: 10 minutes (schema validation)
  - `upsert_incidents`: 20 minutes (database write)
  - `update_freshness`: 5 minutes (metadata update)

**Schedule**: Every 6 hours (0, 6, 12, 18 UTC)

**Monitor SLA Status**:
```bash
# View SLA history in Airflow UI
# Click: DAGs → incident_ingestion → SLAs

# Via CLI
docker-compose exec scheduler airflow dags show incident_ingestion | grep -i sla

# Check recent SLA violations
docker-compose exec postgres psql -U airflow -d airflow -c \
  "SELECT * FROM sla_miss WHERE dag_id='incident_ingestion' ORDER BY execution_date DESC LIMIT 10;"
```

#### 2. repair_scheduling

**Purpose**: Optimize repair scheduling based on incident data (daily)

**SLA Configuration**:
- **Dag SLA**: 2 hours (complex optimization algorithm)
- **Task SLAs**:
  - `check_incidents_available`: 5 minutes (sensor waits for incident data)
  - `load_incidents`: 10 minutes (read from database)
  - `optimize_schedule`: 60 minutes (optimization algorithm)
  - `publish_schedule`: 15 minutes (write results)

**Schedule**: Daily at 2 AM UTC (after incident ingestion)

**Dependencies**:
- Depends on incident_ingestion DAG completion via ExternalTaskSensor

```bash
# View repair optimization status
docker-compose exec scheduler airflow tasks logs repair_scheduling optimize_schedule 2026-05-10

# Check if waiting on incident data
docker-compose exec postgres psql -U airflow -d airflow -c \
  "SELECT * FROM task_instance WHERE dag_id='repair_scheduling' AND state='sensing';"
```

#### 3. metric_materialization

**Purpose**: Compute Metrics for API queries (hourly)

**SLA Configuration**:
- **Dag SLA**: 30 minutes (Metric computation)
- **Task SLAs**:
  - `get_incidents`: 5 minutes (read from database)
  - `get_repairs`: 5 minutes (read from database)
  - `compute_sidewalk_metric`: 15 minutes (Metric computation)
  - `publish_metric`: 5 minutes (write to API materialization tables)

**Schedule**: Every hour (on the hour)

**Monitor Metric Quality**:
```bash
# View Metric computation duration
docker-compose exec scheduler airflow tasks logs metric_materialization compute_sidewalk_metric 2026-05-10

# Check for data quality issues
docker-compose exec postgres psql -U airflow -d nyc_sidewalk -c \
  "SELECT * FROM metric_materialization ORDER BY computed_at DESC LIMIT 5;"
```

### SLA Violation Handling

**Automatic Response**:
1. Airflow records SLA miss in `sla_miss` table
2. SlackOperator sends alert (if configured)
3. Alert appears in Airflow UI under Admin → SLA Misses

**Manual Investigation**:
```bash
# Find SLA misses
docker-compose exec postgres psql -U airflow -d airflow -c "
SELECT 
  dag_id, 
  execution_date, 
  timestamp, 
  description 
FROM sla_miss 
WHERE dag_id IN ('incident_ingestion', 'repair_scheduling', 'metric_materialization')
ORDER BY timestamp DESC 
LIMIT 20;"

# View associated task logs
docker-compose exec scheduler airflow tasks logs incident_ingestion fetch_incidents 2026-05-10
```

**Resolution Steps**:
1. Check DAG logs for task failures or delays
2. Verify database query performance (slow upserts)
3. Check API rate limits (Socrata quota exceeded)
4. Monitor system resources (CPU, memory, disk)
5. If infrastructure constraint: scale horizontally or tune parameters
6. If data issue: run recovery task (see Recovery Procedures)

---

## Manual DAG Runs

### Trigger DAG from UI

1. Open http://localhost:8080
2. Click DAG name (e.g., "incident_ingestion")
3. Click "Trigger DAG" button (top right)
4. Set execution date (defaults to current time)
5. Click "Trigger"

### Trigger DAG from CLI

```bash
# Trigger with default execution date (now)
docker-compose exec scheduler airflow dags trigger incident_ingestion

# Trigger with specific execution date
docker-compose exec scheduler airflow dags trigger incident_ingestion \
  --exec-date 2026-05-10T06:00:00Z

# List recent DAG runs
docker-compose exec scheduler airflow dags list-runs --dag-id incident_ingestion

# Expected output:
# incident_ingestion  2026-05-10T06:00:00+00:00  2026-05-10T06:35:12+00:00  success
# incident_ingestion  2026-05-10T00:00:00+00:00  2026-05-10T00:28:45+00:00  success
```

### Run Specific Task

```bash
# Run single task in isolation
docker-compose exec scheduler airflow tasks run \
  incident_ingestion \
  fetch_incidents \
  2026-05-10T06:00:00Z

# Run with local executor (no dependencies)
docker-compose exec scheduler airflow tasks run \
  incident_ingestion \
  validate_data \
  2026-05-10T06:00:00Z \
  --local

# Test task without executing
docker-compose exec scheduler airflow tasks test \
  incident_ingestion \
  fetch_incidents \
  2026-05-10T06:00:00Z
```

### Monitor Running DAG

```bash
# Watch DAG progress in real-time
watch -n 5 'docker-compose exec scheduler airflow dags list-runs --dag-id incident_ingestion'

# View task instance status
docker-compose exec postgres psql -U airflow -d airflow -c "
SELECT 
  task_id, 
  state, 
  start_date, 
  end_date, 
  duration 
FROM task_instance 
WHERE dag_id='incident_ingestion' 
AND execution_date='2026-05-10T06:00:00Z'
ORDER BY start_date;"

# View task logs
docker-compose logs -f scheduler | grep incident_ingestion
```

### Clear DAG State

```bash
# Clear all tasks for a DAG run
docker-compose exec scheduler airflow dags clear \
  --dag-id incident_ingestion \
  --start-date 2026-05-10 \
  --end-date 2026-05-10 \
  --confirm

# Clear specific task
docker-compose exec scheduler airflow tasks clear \
  --dag-id incident_ingestion \
  --task-id fetch_incidents \
  --start-date 2026-05-10 \
  --confirm

# Verify cleared
docker-compose exec postgres psql -U airflow -d airflow -c "
SELECT COUNT(*) FROM task_instance 
WHERE dag_id='incident_ingestion' 
AND execution_date='2026-05-10T06:00:00Z';"
```

---

## Backfilling Historical Data

### Scenario: Reprocessing After Schema Change

When incident schema changes (e.g., new address field added), backfill to reprocess all historical data:

```bash
# Backfill last 30 days of incident data
docker-compose exec scheduler airflow dags backfill \
  --dag-id incident_ingestion \
  --start-date 2026-04-10 \
  --end-date 2026-05-10 \
  --clear-only-dependencies

# Backfill with parallelism (run multiple tasks concurrently)
docker-compose exec scheduler airflow dags backfill \
  --dag-id incident_ingestion \
  --start-date 2026-04-10 \
  --end-date 2026-05-10 \
  --reset-dag-run \
  --rerun-failed-tasks \
  -c parallel_dag_processes=4
```

### Backfill Repair Scheduling

After optimization algorithm change, rebuild repair schedules:

```bash
# Backfill last 14 days
docker-compose exec scheduler airflow dags backfill \
  --dag-id repair_scheduling \
  --start-date 2026-04-26 \
  --end-date 2026-05-10 \
  --reset-dag-run

# Monitor progress
watch -n 10 'docker-compose exec postgres psql -U airflow -d airflow -c \
  "SELECT COUNT(*) as total, 
          SUM(CASE WHEN state='\''success'\'' THEN 1 ELSE 0 END) as success,
          SUM(CASE WHEN state='\''failed'\'' THEN 1 ELSE 0 END) as failed
   FROM task_instance 
   WHERE dag_id='\''repair_scheduling'\'';"'
```

### Backfill Metric Materialization

Recalculate Metrics for past period:

```bash
# Backfill last 7 days (hourly = 168 runs)
docker-compose exec scheduler airflow dags backfill \
  --dag-id metric_materialization \
  --start-date 2026-05-03 \
  --end-date 2026-05-10 \
  --reset-dag-run

# Backfill specific hours only
for hour in {0..23}; do
  docker-compose exec scheduler airflow dags trigger metric_materialization \
    --exec-date 2026-05-10T${hour}:00:00Z
done
```

### Verify Backfill Completion

```bash
# Check final state
docker-compose exec postgres psql -U airflow -d airflow -c "
SELECT 
  dag_id,
  COUNT(*) as total_runs,
  SUM(CASE WHEN state='success' THEN 1 ELSE 0 END) as success_count,
  SUM(CASE WHEN state='failed' THEN 1 ELSE 0 END) as fail_count,
  ROUND(100.0 * SUM(CASE WHEN state='success' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM task_instance
WHERE dag_id IN ('incident_ingestion', 'repair_scheduling', 'metric_materialization')
AND execution_date BETWEEN '2026-04-10' AND '2026-05-10'
GROUP BY dag_id
ORDER BY dag_id;"

# Expected:
# dag_id                  | total_runs | success_count | fail_count | success_rate
# incident_ingestion      | 120        | 120           | 0          | 100.00
# repair_scheduling       | 30         | 30            | 0          | 100.00
# metric_materialization     | 168        | 168           | 0          | 100.00
```

---

## Alerting Setup

### Slack Integration

#### Configure Slack Webhook

1. Go to Slack workspace → Settings & administration → Manage apps
2. Click "Build" → Create a custom app
3. Select your workspace
4. Give app a name: "Airflow Alerts"
5. Activate Incoming Webhooks
6. Create New Webhook to Channel (select #airflow-alerts)
7. Copy webhook URL: https://hooks.slack.com/services/YOUR/WEBHOOK/URL

#### Add Slack Connection to Airflow

```bash
# Via docker-compose environment variable
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
docker-compose up -d

# OR manually add via Airflow UI
# Admin → Connections → Create
# Conn ID: slack_notifications
# Conn Type: Slack
# Password: <webhook_url>

# Verify connection
docker-compose exec scheduler airflow connections test slack_notifications
```

#### Configure DAG Alert Handlers

Example task with on_failure alert:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator
from datetime import datetime

def task_failure_callback(context):
    """Send Slack alert on task failure"""
    op = SlackWebhookOperator(
        task_id='failure_alert',
        http_conn_id='slack_notifications',
        message=f"""
        :x: Task Failed
        DAG: {context['task'].dag_id}
        Task: {context['task'].task_id}
        Execution Date: {context['execution_date']}
        Log: {context['task_instance'].log_url}
        """
    )
    return op.execute(context)

dag = DAG('example_dag', start_date=datetime(2026, 5, 1))

task = PythonOperator(
    task_id='my_task',
    python_callable=lambda: print("Processing..."),
    on_failure_callback=task_failure_callback,
    dag=dag
)
```

### Alert Thresholds

Define alert conditions in Airflow variables:

```bash
# Set via init_airflow.sh or Airflow UI

docker-compose exec scheduler airflow variables set \
  "alert_on_sla_miss" "true"

docker-compose exec scheduler airflow variables set \
  "alert_on_task_retry" "true"

docker-compose exec scheduler airflow variables set \
  "alert_on_dag_failure" "true"

docker-compose exec scheduler airflow variables set \
  "incident_data_freshness_alert_hours" "30"
```

### Email Alerts (Optional)

Configure SMTP for email notifications:

```bash
# Add to docker-compose.yml environment
AIRFLOW__EMAIL__EMAIL_BACKEND: airflow.providers.sendgrid.utils.sendgrid.SendgridEmailBackend
AIRFLOW__SENDGRID__SENDGRID_MAIL_FROM: alerts@example.com
AIRFLOW__SENDGRID__SENDGRID_API_KEY: sg.xxxx

# OR use Gmail
AIRFLOW__SMTP__SMTP_HOST: smtp.gmail.com
AIRFLOW__SMTP__SMTP_PORT: 587
AIRFLOW__SMTP__SMTP_USER: your-email@gmail.com
AIRFLOW__SMTP__SMTP_PASSWORD: your-app-password
```

---

## Log Management

### Accessing Logs

#### Via Airflow UI

1. Click DAG → Click run → Click task → View logs
2. Shows: task_id, execution_date, duration, status, exception details

#### Via CLI

```bash
# View task logs
docker-compose exec scheduler airflow tasks logs \
  incident_ingestion \
  fetch_incidents \
  2026-05-10T06:00:00Z

# View last N lines
docker-compose exec scheduler airflow tasks logs \
  incident_ingestion \
  fetch_incidents \
  2026-05-10T06:00:00Z \
  -n 50

# Stream logs in real-time
docker-compose logs -f scheduler | grep fetch_incidents
```

#### Via Docker Logs

```bash
# Container logs with timestamps
docker-compose logs --timestamps scheduler | tail -100

# Follow logs
docker-compose logs -f scheduler

# Logs since specific time
docker-compose logs --since 2026-05-10T06:00:00 scheduler
```

### Log Storage

By default, logs are stored in `airflow/logs/` directory:

```
airflow/logs/
├── incident_ingestion/
│   ├── fetch_incidents/2026-05-10T06:00:00+00:00/
│   │   ├── attempt-1.log
│   │   ├── attempt-2.log  (if retried)
│   │   └── task_logs.json
│   ├── validate_data/
│   └── upsert_incidents/
├── repair_scheduling/
└── metric_materialization/
```

### Log Parsing for Errors

```bash
# Find all failures in last 24 hours
docker-compose logs scheduler --since 24h | grep -i "error\|failed\|exception"

# Find specific error pattern
docker-compose logs scheduler | grep "ConflictError"

# Count error frequency
docker-compose logs scheduler | grep -i "error" | wc -l

# Extract failed task summary
docker-compose exec postgres psql -U airflow -d airflow -c "
SELECT 
  dag_id, 
  task_id, 
  COUNT(*) as fail_count,
  MAX(end_date) as last_failure
FROM task_instance
WHERE state='failed'
AND end_date > NOW() - INTERVAL '24 hours'
GROUP BY dag_id, task_id
ORDER BY fail_count DESC;"
```

### Log Aggregation (Production)

Forward logs to centralized system:

```yaml
# docker-compose.yml with ELK stack
filebeat:
  image: docker.elastic.co/beats/filebeat:8.0.0
  volumes:
    - ./airflow/logs:/var/log/airflow:ro
    - ./filebeat.yml:/usr/share/filebeat/filebeat.yml
  command: filebeat -e -strict.perms=false
```

---

## Metrics & Observability

### Prometheus Metrics

Airflow exports metrics in Prometheus format on port 9090:

```bash
# Scrape metrics
curl http://localhost:9090/metrics | head -50

# Key metrics to track
# DAG success rate
airflow_dag_status_total{dag_id="incident_ingestion",status="success"}

# Task duration
airflow_task_duration_seconds{dag_id="incident_ingestion",task_id="fetch_incidents"}

# Scheduler heartbeat
airflow_scheduler_heartbeat{scheduler_id="airflow-scheduler"}
```

### Query Metrics via Grafana

If Grafana is running (http://localhost:3000):

1. Add Prometheus data source: http://localhost:9090
2. Create dashboard panels:
   - **DAG Success Rate**: `rate(airflow_dag_status_total{status="success"}[1h])`
   - **Task Duration**: `histogram_quantile(0.95, airflow_task_duration_seconds)`
   - **Scheduler Health**: `rate(airflow_scheduler_heartbeat[5m])`

### Operational Logging

Phase 3 uses OperationalLogger from Phase 2 for structured logging:

```python
from socrata_toolkit.observability import OperationalLogger

logger = OperationalLogger(__name__)

# Log with context
logger.log_event(
    event_name="incident_fetch_started",
    event_type="dag_task",
    dag_id="incident_ingestion",
    task_id="fetch_incidents",
    metadata={
        "dataset_id": "a2nx-4u46",
        "estimated_records": 5000,
        "api_quota_remaining": 49500
    }
)
```

---

## Recovery Procedures

### Clear Failed Tasks and Retry

```bash
# Clear failed task
docker-compose exec scheduler airflow tasks clear \
  --dag-id incident_ingestion \
  --task-id fetch_incidents \
  --start-date 2026-05-10 \
  --confirm

# Re-run DAG from failure point
docker-compose exec scheduler airflow dags trigger incident_ingestion \
  --exec-date 2026-05-10T06:00:00Z

# Monitor retry
docker-compose exec scheduler airflow tasks logs \
  incident_ingestion fetch_incidents 2026-05-10T06:00:00Z
```

### Recover from Database Connection Loss

```bash
# Check PostgreSQL connection
docker-compose exec postgres pg_isready -U airflow

# Restart PostgreSQL if needed
docker-compose restart postgres

# Verify Airflow can reconnect
docker-compose exec scheduler airflow dags list

# If still failing, reinitialize database
# WARNING: This deletes Airflow metadata!
docker-compose exec scheduler airflow db reset
bash init_airflow.sh
```

### Recover from Checkpoint Data Corruption

Incident, repair, and Metric data use checkpoints to track processed records. If corrupted:

```bash
# View checkpoint table
docker-compose exec postgres psql -U airflow -d nyc_sidewalk -c \
  "SELECT * FROM data_checkpoint WHERE source='socrata_incidents';"

# Manually reset checkpoint to reprocess all data
docker-compose exec postgres psql -U airflow -d nyc_sidewalk -c "
UPDATE data_checkpoint 
SET last_processed_id = NULL, 
    last_processed_date = '2026-04-10'
WHERE source = 'socrata_incidents';"

# Trigger DAG to reprocess
docker-compose exec scheduler airflow dags trigger incident_ingestion
```

### Recover from Full Disk

```bash
# Check disk usage
df -h

# Clear old logs
find airflow/logs -name "*.log" -mtime +30 -delete

# Clear Docker images
docker system prune -a

# Verify space freed
df -h
```

---

## Performance Tuning

### Parallel Task Execution

```yaml
# docker-compose.yml scheduler environment
AIRFLOW__CORE__PARALLELISM: 32        # Max tasks across all DAGs
AIRFLOW__CORE__DAG_CONCURRENCY: 16    # Max tasks per DAG
AIRFLOW__CORE__MAX_ACTIVE_RUNS_PER_DAG: 3  # Max concurrent DAG runs
```

### Database Query Optimization

```sql
-- Create indexes for faster queries
CREATE INDEX idx_task_instance_dag_execution 
ON task_instance(dag_id, execution_date);

CREATE INDEX idx_sla_miss_dag_execution 
ON sla_miss(dag_id, execution_date);

-- Vacuum and analyze
VACUUM ANALYZE task_instance;
VACUUM ANALYZE sla_miss;
```

### Memory Optimization

```bash
# Monitor memory usage
docker stats airflow-scheduler airflow-webserver

# Reduce in-memory cache
docker-compose exec scheduler airflow config get-value core max_map_length

# Set limits
export AIRFLOW__CORE__MAX_MAP_LENGTH=1024
```

---

## Next Steps

- [Deployment Guide](./airflow_deployment.md): Infrastructure setup
- [DAG Development Guide](./airflow_migration_guide.md): Writing new DAGs
- [Phase 3 Integration Guide](./PHASE3_INTEGRATION_GUIDE.md): Integration architecture
