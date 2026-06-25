# Metric Analytics Production Deployment Checklist

**Status:** ✅ READY FOR DEPLOYMENT

---

## Pre-Deployment (One-Time Setup)

### Environment & Credentials

- [ ] **MotherDuck Token** set in `MOTHERDUCK_TOKEN` env var
  ```bash
  export MOTHERDUCK_TOKEN="your_token_here"
  ```

- [ ] **Slack Webhook** (optional) set in `SLACK_WEBHOOK_URL` env var
  ```bash
  export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
  ```

- [ ] **Python 3.11+** installed
  ```bash
  python --version  # Should be ≥ 3.11
  ```

- [ ] **Required packages** installed
  ```bash
  pip install duckdb numpy scipy statsmodels requests pytest
  ```

### Schema Creation (One-Time)

- [ ] **Create MotherDuck databases**
  ```sql
  CREATE SCHEMA analytics;
  CREATE SCHEMA app_queries;
  ```

- [ ] **Deploy DDL** (run in sequence)
  ```bash
  python -c "
  import duckdb
  import os
  conn = duckdb.connect('md:', config={'motherduck_token': os.getenv('MOTHERDUCK_TOKEN')})
  
  # Run each DDL file in order
  for file in [
    'src/socrata_toolkit/motherduck/schemas/01_raw_landing_metric_metrics.sql',
    'src/socrata_toolkit/motherduck/schemas/02_staging_metric_metrics_staged.sql',
    'src/socrata_toolkit/motherduck/schemas/03_analytics_metric_statistics_by_borough.sql',
    'src/socrata_toolkit/motherduck/schemas/04_serving_metric_metrics_comprehensive.sql'
  ]:
    with open(file) as f:
      conn.execute(f.read())
      print(f'✓ Deployed {file}')
  
  conn.close()
  "
  ```

- [ ] **Seed Metric metadata** (18 Metrics)
  ```bash
  python -c "
  import json
  import duckdb
  import os
  
  conn = duckdb.connect('md:', config={'motherduck_token': os.getenv('MOTHERDUCK_TOKEN')})
  
  with open('scripts/metric_dives_manifest.json') as f:
    manifest = json.load(f)
  
  for dive in manifest['dives']:
    conn.execute('''
      INSERT INTO analytics.metric_metadata (metric_name, metric_id, phase, unit, description, risk_threshold, benchmark_value)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (dive['metric_id'], dive['metric_id'], dive['phase'], dive['unit'], dive['description'], dive['risk_threshold'], dive['benchmark']))
  
  print(f'✓ Seeded {len(manifest[\"dives\"])} Metric definitions')
  conn.close()
  "
  ```

---

## Nightly Execution (Automated)

### Option 1: Manual (For Testing)

```bash
#!/bin/bash
# run_nightly_pipeline.sh

export MOTHERDUCK_TOKEN="your_token_here"
export SLACK_WEBHOOK_URL="your_webhook_here"  # optional

echo "🌙 Starting nightly Metric analytics pipeline..."

# Step 1: Compute metrics (120 seconds expected)
python -c "
from src.socrata_toolkit.motherduck.metric_statistics_engine import MetricStatisticsEngine

engine = MetricStatisticsEngine(motherduck_token='$MOTHERDUCK_TOKEN')
engine.connect()

print('⏱️  Computing 60+ metrics for 18 Metrics × 5 boroughs...')
result = engine.compute_all_metrics()
print(f'✓ {result.rows_computed} rows computed in {result.computation_duration_seconds:.2f}s')
print(f'Status: {result.status}')

if result.status == 'FAILED':
  print(f'Error: {result.error_message}')
  exit(1)

engine.close()
"

# Step 2: Validate data quality
python -c "
import duckdb
import os
from src.socrata_toolkit.motherduck.metric_validation import MetricValidator

conn = duckdb.connect('md:', config={'motherduck_token': os.getenv('MOTHERDUCK_TOKEN')})
validator = MetricValidator(conn)
report = validator.validate_all()

print('\n✓ Validation Report:')
for check in [report.timestamp_check, report.row_count_check, report.null_check, 
               report.column_count_check, report.freshness_check, report.schema_check,
               report.metric_ranges_check, report.anomaly_check]:
  status = '✓' if check.passed else '✗'
  print(f'  {status} {check.check_name}: {check.message}')

if not report.all_passed:
  print('\n⚠️  Validation failed!')
  exit(1)

conn.close()
"

# Step 3: Monitor & Alert
python -c "
import duckdb
import os
from src.socrata_toolkit.motherduck.metric_monitoring import MetricMonitor

conn = duckdb.connect('md:', config={'motherduck_token': os.getenv('MOTHERDUCK_TOKEN')})
monitor = MetricMonitor(conn, os.getenv('SLACK_WEBHOOK_URL'))

alerts = monitor.monitor_all()
monitor.log_monitoring_result(alerts)

if alerts:
  print(f'\n⚠️  {len(alerts)} alerts detected and logged')
else:
  print('\n✅ All monitoring checks passed')

conn.close()
"

echo "✅ Nightly pipeline complete!"
```

### Option 2: Scheduled with cron (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add this line to run at 3:30 AM daily
30 3 * * * /path/to/run_nightly_pipeline.sh >> /var/log/metric_pipeline.log 2>&1
```

### Option 3: Scheduled with APScheduler (Python)

```python
# src/socrata_toolkit/motherduck/scheduler.py

import schedule
import time
import logging
import os
from metric_statistics_engine import MetricStatisticsEngine
from metric_validation import MetricValidator
from metric_monitoring import MetricMonitor
import duckdb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_nightly_pipeline():
    """Run complete nightly analytics pipeline (all processes in sequence)."""
    logger.info("🌙 Starting nightly Metric analytics pipeline...")
    
    try:
        engine = MetricStatisticsEngine(motherduck_token=os.getenv('MOTHERDUCK_TOKEN'))
        engine.connect()
        
        # Step 1: Core metrics computation (4:00 PM)
        logger.info("Computing core 60+ metrics...")
        result = engine.compute_all_metrics()
        
        if result.status == 'FAILED':
            logger.error(f"Metrics computation failed: {result.error_message}")
            engine.close()
            return False
        
        # Step 2: Advanced metrics (normality, variance, seasonal, autocorr) (4:05 PM)
        logger.info("Computing advanced statistical metrics...")
        adv_result = engine.update_advanced_metrics_batch()
        logger.info(f"Advanced metrics: {adv_result['computed']}/{adv_result['total']} computed")
        
        # Step 3: Time series metrics (stationarity, ARIMA, VAR) (4:10 PM)
        logger.info("Computing time series metrics (ARIMA, stationarity, VAR)...")
        ts_result = engine.compute_weekly_timeseries_metrics()
        logger.info(f"Time series metrics: {ts_result['stationarity']} stationarity, {ts_result['arima']} ARIMA, {ts_result['var']} VAR")
        
        # Step 4: Validation (all layers)
        logger.info("Running validation checks...")
        conn = duckdb.connect('md:', config={'motherduck_token': os.getenv('MOTHERDUCK_TOKEN')})
        validator = MetricValidator(conn)
        report = validator.validate_all()
        
        if not report.all_passed:
            logger.error("Data validation failed")
            conn.close()
            engine.close()
            return False
        
        # Step 5: Monitoring & Alerts
        logger.info("Running monitoring checks...")
        monitor = MetricMonitor(conn, os.getenv('SLACK_WEBHOOK_URL'))
        alerts = monitor.monitor_all()
        monitor.log_monitoring_result(alerts)
        
        conn.close()
        engine.close()
        
        logger.info("✅ Nightly pipeline complete (core + advanced + time series)!")
        return True
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Schedule for 4:00 PM daily (all steps run sequentially)
    schedule.every().day.at("16:00").do(run_nightly_pipeline)
    
    logger.info("Scheduler started. Daily pipeline runs at 4:00 PM.")
    logger.info("  4:00 PM - Core metrics (60+)")
    logger.info("  4:05 PM - Advanced metrics (normality, variance, seasonal)")
    logger.info("  4:10 PM - Time series metrics (ARIMA, stationarity, VAR)")
    logger.info("  4:15 PM - Validation & monitoring")
    
    while True:
        schedule.run_pending()
        time.sleep(60)
```

---

## Weekly Execution (Optional Advanced Metrics)

### Core Advanced Metrics (normality, variance, seasonal, autocorr, robust)

```bash
#!/bin/bash
# run_weekly_advanced_metrics.sh

export MOTHERDUCK_TOKEN="your_token_here"
export SLACK_WEBHOOK_URL="your_webhook_here"

echo "📊 Computing advanced statistical metrics (weekly)..."

python -c "
import duckdb
import os
from src.socrata_toolkit.motherduck.metric_statistics_engine import MetricStatisticsEngine

engine = MetricStatisticsEngine(motherduck_token=os.getenv('MOTHERDUCK_TOKEN'))
engine.connect()

print('⏱️  Computing advanced metrics (normality, variance, seasonal, autocorr, robust)...')
result = engine.update_advanced_metrics_batch()

print(f'✓ {result[\"computed\"]}/{result[\"total\"]} METRIC-borough pairs computed in {result[\"duration_seconds\"]:.2f}s')

engine.close()
"

echo "✅ Advanced metrics update complete!"
```

### Time Series & Advanced Metrics (Integrated Daily)

All advanced metrics computation (stationarity, ARIMA, VAR, normality tests, seasonal analysis) runs as part of the core daily pipeline.

**Requirements:**
```bash
pip install statsmodels scipy
```

**Daily execution (all steps run in sequence):**

```
4:00 PM - Core metrics computation (60+ metrics, 90 rows)
4:05 PM - Advanced metrics (normality tests, Levene, Cohen's d, STL, Ljung-Box, robust regression)
4:10 PM - Time series metrics (ADF/KPSS stationarity, ARIMA forecasting, VAR multivariate)
4:15 PM - Validation & monitoring (8 checks, Slack alerts)
```

**Features:**
- Stationarity testing (ADF, KPSS) with automatic differencing detection
- ARIMA/SARIMAX forecasting with 95% confidence intervals
- VAR multivariate analysis with Granger causality testing
- Graceful degradation: if statsmodels/scipy unavailable, skips with warning (core metrics unaffected)

**Schema:**
11 new columns added to `analytics.metric_statistics_by_borough`:
- `adf_p_value`, `adf_is_stationary` (stationarity)
- `kpss_p_value`, `kpss_is_stationary` (stationarity)
- `arima_order`, `arima_aic` (ARIMA model)
- `forecast_value`, `forecast_ci_lower`, `forecast_ci_upper` (95% CI forecast)
- `var_lag_order`, `var_aic` (multivariate)

**Cron schedule (single daily entry):**

```bash
crontab -e
# Add single entry for complete nightly pipeline at 4:00 PM
0 16 * * * /path/to/run_nightly_pipeline.sh >> /var/log/metric_pipeline.log 2>&1
```

The nightly script calls `run_nightly_pipeline()` which executes all steps in sequence (core → advanced → time series → validation).

---

## Deployment Validation

### Test Nightly Pipeline Locally

```bash
bash run_nightly_pipeline.sh
# Expected output:
# ⏱️  Computing 60+ metrics...
# ✓ 90 rows computed in ~135s
# ✓ Validation Report:
#   ✓ timestamp_freshness: Data is 2 minutes old ✓
#   ✓ row_count: Exactly 90 rows ✓
#   ✓ null_metrics: All core metrics non-NULL ✓
#   ...
# ✅ All monitoring checks passed
# ✅ Nightly pipeline complete!
```

### Run Unit Tests

```bash
python -m pytest tests/test_metric_statistics_engine.py -v

# Expected: 12+ tests passing
# ✓ test_engine_connect
# ✓ test_compute_all_metrics_returns_result
# ✓ test_validate_completeness_structure
# ...
```

### Manually Query Serving Layer

```bash
# Check row counts
duckdb -D ":memory:" "SELECT COUNT(*) FROM read_parquet('md:app_queries.analytics.metric_metrics_comprehensive')"
# Expected: 90

# Check metric availability
duckdb -D ":memory:" "SELECT COUNT(*) as metric_cols FROM parquet_schema('md:app_queries.analytics.metric_metrics_comprehensive')"
# Expected: 50+
```

---

## Post-Deployment

### Monitor Live Pipeline

1. **Check dashboard** (MotherDuck workspace)
   - Navigate to `analytics.metric_statistics_by_borough`
   - Verify recent `analytics_timestamp`

2. **Check Slack** (if configured)
   - Should receive daily status updates
   - Check for any warning/error alerts

3. **Query serving layer** (analysts)
   - Navigate to `app_queries.v_metric_statistics`
   - Open 18 Metric Dives (live, interactive)

### Monitor Logs

```bash
# Check pipeline logs
tail -f /var/log/metric_pipeline.log

# Check monitoring logs (in database)
duckdb -D ":memory:" "SELECT * FROM read_parquet('md:analytics.monitoring_log') ORDER BY check_time DESC LIMIT 10"
```

### Maintenance Tasks (Monthly)

- [ ] **Review SLA breaches** — Run `SELECT * FROM analytics.metric_statistics_by_borough WHERE pct_exceeding_risk_threshold > 50`
- [ ] **Check data anomalies** — Run `SELECT * FROM analytics.metric_statistics_by_borough WHERE outlier_count_3sd > n * 0.1`
- [ ] **Audit Slack alerts** — Review notification history for patterns
- [ ] **Update Metric benchmarks** (if needed) — Modify `analytics.metric_metadata` and re-run Dives
- [ ] **Backup monitoring logs** — Export `analytics.monitoring_log` for compliance

---

## Rollback Procedures

### If Metrics Computation Fails

1. **Check error message**
   ```bash
   duckdb -D ":memory:" "SELECT computation_status, message FROM analytics.metric_statistics_by_borough WHERE computation_status = 'FAILED' LIMIT 1"
   ```

2. **Diagnose root cause**
   - Check staging table: `SELECT COUNT(*) FROM analytics.metric_metrics_staged WHERE is_latest_record = TRUE`
   - Check raw table: `SELECT COUNT(*) FROM analytics.metric_metrics`
   - Check recent logs: `SELECT * FROM analytics.monitoring_log ORDER BY check_time DESC LIMIT 5`

3. **Rerun computation** (engine has retry logic)
   ```bash
   python -c "
   from src.socrata_toolkit.motherduck.metric_statistics_engine import MetricStatisticsEngine
   engine = MetricStatisticsEngine(motherduck_token='$MOTHERDUCK_TOKEN')
   engine.connect()
   result = engine.compute_all_metrics(max_retries=5)  # Retry up to 5 times
   print(f'Status: {result.status}')
   engine.close()
   "
   ```

### If Data Looks Wrong

1. **Validate data quality**
   ```bash
   python -c "
   import duckdb, os
   from src.socrata_toolkit.motherduck.metric_validation import MetricValidator
   conn = duckdb.connect('md:', config={'motherduck_token': os.getenv('MOTHERDUCK_TOKEN')})
   validator = MetricValidator(conn)
   report = validator.validate_all()
   # Review all checks
   conn.close()
   "
   ```

2. **If validation fails**
   - Contact data team to investigate source tables
   - Don't deploy new Dives until issue is resolved

3. **If advanced metrics are wrong**
   - They're optional; can skip them
   - Run nightly pipeline (core 60+ metrics are critical)
   - Rerun weekly advanced metrics later

---

## Success Criteria

Deployment is successful when:

- ✅ Nightly pipeline runs to completion (< 160 seconds total)
- ✅ 90 rows computed (18 Metrics × 5 boroughs)
- ✅ All validation checks pass (freshness, row count, NULLs, schema)
- ✅ 18 Metric Dives deployed and queryable
- ✅ Analysts can open Dives and see charts + statistics
- ✅ Slack alerts (if enabled) firing correctly
- ✅ Monitoring logs being written to `analytics.monitoring_log`

---

## Quick Reference

| Task | Command |
|------|---------|
| **Deploy schema** | `python deploy_schema.py` |
| **Seed metadata** | `python seed_metric_metadata.py` |
| **Run nightly pipeline** | `bash run_nightly_pipeline.sh` |
| **Run advanced metrics** | `bash run_weekly_advanced_metrics.sh` |
| **Run tests** | `pytest tests/test_metric_statistics_engine.py -v` |
| **Check status** | `duckdb -D ":memory:" "SELECT COUNT(*) FROM analytics.metric_statistics_by_borough"` |
| **View alerts** | `duckdb -D ":memory:" "SELECT * FROM analytics.monitoring_log ORDER BY check_time DESC LIMIT 10"` |
| **Query Dives** | Open `app_queries.v_metric_statistics` in MotherDuck |

