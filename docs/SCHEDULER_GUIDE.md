# NYC DOT Sidewalk Data Pipeline Scheduler Guide

## Overview

The scheduler automatically runs all pipeline routines on a fixed schedule:
- **Nightly (2am-8am UTC):** Raw load → stage → materialize → validate → reconcile → domain rules → conflicts
- **Continuous (every 30 min):** Alert checks & monitoring

All jobs run serially to prevent resource contention. Configuration is version-controlled in `data/scheduler_config.json`.

## Quick Start

### Run the Scheduler

```bash
python scripts/run_scheduler.py
```

This starts the scheduler in the foreground. It will:
1. Load configuration from `data/scheduler_config.json`
2. Schedule all enabled jobs
3. Run jobs on their configured schedules
4. Log all activity to `logs/scheduler.log`

### Modify Job Schedules

Edit `data/scheduler_config.json`:

```json
{
  "jobs": {
    "load_raw_data": {
      "enabled": true,
      "cron": "0 2 * * *",
      "timezone": "UTC",
      "description": "Load raw data from Socrata (nightly at 2am UTC)"
    }
  }
}
```

**Cron Expression Format:** `minute hour day_of_month month day_of_week`

Examples:
- `0 2 * * *` — Daily at 2:00 AM UTC
- `0 */6 * * *` — Every 6 hours
- `*/30 * * * *` — Every 30 minutes
- `0 0 * * 1` — Weekly on Monday at midnight

### Enable/Disable Jobs

Set `"enabled": true` or `"enabled": false` for each job:

```json
{
  "jobs": {
    "load_raw_data": {"enabled": true},
    "validate_all": {"enabled": false}
  }
}
```

## Job Schedule (Default)

All times in UTC (adjust as needed):

| Time | Job | Purpose |
|------|-----|---------|
| 2:00 AM | `load_raw_data` | Fetch 3.6M+ rows from Socrata |
| 3:00 AM | `stage_data` | Deduplicate, join, transform |
| 4:00 AM | `materialize_analytics` | Pre-compute 5 analytics views |
| 5:00 AM | `validate_all` | Run 15+ data quality checks |
| 6:00 AM | `reconciliation_check` | Compare expected vs actual counts |
| 7:00 AM | `domain_validation` | NYC business rule validation |
| 8:00 AM | `conflict_detection` | Detect permit/inspection conflicts |
| Every 30 min | `alert_check` | Check thresholds & trigger alerts |

**Total Time:** ~6 hours for full pipeline (load + stage + materialize + validate)

## Monitoring

### View Job Status

```bash
# Check logs
tail -f logs/scheduler.log

# Search for job runs
grep "Starting.*routine" logs/scheduler.log

# Check for failures
grep "FAILED\|ERROR" logs/scheduler.log
```

### Job Store

Job state persists in `data/scheduler_jobs.db` (SQLite):
- Job history
- Next run times
- Execution details

This survives scheduler restarts.

## Notifications

### Enable Slack Alerts

1. Create a Slack webhook: https://api.slack.com/messaging/webhooks
2. Edit `data/scheduler_config.json`:

```json
{
  "notifications": {
    "slack_enabled": true,
    "slack_webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  }
}
```

3. Restart scheduler

Alerts trigger on:
- HIGH severity: Load failure, validation failure (>5% checks fail)
- MEDIUM severity: Reconciliation discrepancy, domain rule breach
- LOW severity: Performance warnings

### Enable Email Alerts

```json
{
  "notifications": {
    "email_enabled": true,
    "email_recipients": ["ops@nycdot.gov", "analytics@nycdot.gov"]
  }
}
```

Requires `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` environment variables.

## Background Operation

### macOS / Linux

Run scheduler in background with output to log:

```bash
nohup python scripts/run_scheduler.py > logs/scheduler.log 2>&1 &
```

Monitor:

```bash
tail -f logs/scheduler.log
```

Kill:

```bash
pkill -f "python scripts/run_scheduler.py"
```

### systemd Service (Linux)

Create `/etc/systemd/system/nyc-scheduler.service`:

```ini
[Unit]
Description=NYC DOT Sidewalk Data Pipeline Scheduler
After=network.target

[Service]
Type=simple
User=appuser
WorkingDirectory=/opt/nyc_data
ExecStart=/usr/bin/python3 scripts/run_scheduler.py
Restart=on-failure
RestartSec=60
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable nyc-scheduler
sudo systemctl start nyc-scheduler
sudo systemctl status nyc-scheduler
sudo journalctl -fu nyc-scheduler
```

### Docker

Add to Dockerfile:

```dockerfile
CMD ["python", "scripts/run_scheduler.py"]
```

Then:

```bash
docker run -v data:/app/data -v logs:/app/logs nyc-scheduler:latest
```

## Troubleshooting

### Job Not Running

Check:
1. Is the job enabled in `scheduler_config.json`?
2. Is the cron expression valid?
3. Are there errors in `logs/scheduler.log`?
4. Check SQLite job store: `sqlite3 data/scheduler_jobs.db`.tables`

### Performance Issues

If jobs overlap or take too long:
1. Increase `max_workers` in config (default 4)
2. Stagger job times (spread across more hours)
3. Reduce materialization complexity (fewer analytics views)

### High Memory Usage

- Reduce `max_workers` (fewer concurrent threads)
- Lower `permit` dataset fetch size (if > 3.6M rows)
- Enable periodic job cleanup in scheduler config

## Configuration Reference

### Main Settings

```json
{
  "jobs": {
    "<job_id>": {
      "enabled": true,
      "cron": "0 2 * * *",
      "timezone": "UTC",
      "description": "Human-readable description"
    }
  },
  "executors": {
    "default": {"type": "threadpool", "max_workers": 4},
    "processpool": {"type": "processpool", "max_workers": 2}
  },
  "notifications": {
    "slack_enabled": false,
    "email_enabled": false
  },
  "logging": {
    "level": "INFO",
    "file": "logs/scheduler.log"
  },
  "performance": {
    "max_concurrent_jobs": 4,
    "job_timeout_seconds": 3600,
    "retry_count": 3,
    "retry_delay_seconds": 300
  }
}
```

### Job IDs Available

- `load_raw_data` — Socrata fetch
- `stage_data` — Transformations
- `materialize_analytics` — View creation
- `validate_all` — Validation checks
- `reconciliation_check` — Count reconciliation
- `domain_validation` — Business rules
- `conflict_detection` — Spatial conflicts
- `alert_check` — Monitoring

## Editing Schedule (Live)

1. Edit `data/scheduler_config.json`
2. Restart scheduler: `pkill -f "python scripts/run_scheduler.py"`
3. Restart: `python scripts/run_scheduler.py`

**No data loss** — SQLite job store persists state across restarts.

## Git Workflow

Scheduler config is version-controlled:

```bash
# After editing scheduler_config.json
git add data/scheduler_config.json
git commit -m "ops(scheduler): Update job schedule - shift load to 3am UTC"
git push origin main
```

This ensures all deployments use the same schedule.

---

**Last Updated:** 2026-06-10  
**Status:** Active  
**Maintenance:** Weekly log review recommended
