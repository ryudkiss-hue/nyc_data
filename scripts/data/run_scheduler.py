#!/usr/bin/env python
"""
Run the automated pipeline scheduler in the foreground.

This script starts the APScheduler-based routine orchestration for:
- Nightly raw data loads from Socrata
- Staging transformations
- Analytics materialization
- Data validation and reconciliation
- Domain business rule checks
- Spatial conflict detection
- Continuous monitoring alerts

To enable Slack/email notifications:
1. Edit data/scheduler_config.json
2. Set notification settings
3. Restart the scheduler

To modify job schedules:
1. Edit data/scheduler_config.json
2. Change cron expressions (uses UTC timezone)
3. Restart the scheduler

Usage:
    python scripts/run_scheduler.py          # Run with config from data/scheduler_config.json
    SCHEDULER_CONFIG=custom.json python scripts/run_scheduler.py  # Use custom config

To run in background (Linux/macOS):
    nohup python scripts/run_scheduler.py > logs/scheduler.log 2>&1 &

To run as systemd service (Linux):
    See docs/SCHEDULER_SERVICE_SETUP.md for systemd configuration
"""

import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from socrata_toolkit.core.scheduler import PipelineScheduler, ScheduleRunner


def setup_logging(config: dict):
    """Configure logging based on scheduler config."""
    logging_config = config.get("logging", {})
    log_level = getattr(logging, logging_config.get("level", "INFO"))
    log_file = logging_config.get("file", "logs/scheduler.log")

    # Create logs directory
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger(__name__)

def main():
    """Initialize and run the scheduler."""
    logger = logging.getLogger(__name__)

    try:
        logger.info("=" * 70)
        logger.info("NYC DOT Sidewalk Data Pipeline Scheduler Starting")
        logger.info("=" * 70)

        # Initialize scheduler
        scheduler = PipelineScheduler()
        logger.info(f"Scheduler initialized with DuckDB: {scheduler.duckdb_path}")

        # Create job runner
        runner = ScheduleRunner()

        # Job registry - maps job IDs to callable functions
        job_registry = {
            "load_raw_data": runner.run_load_raw_data,
            "stage_data": runner.run_stage_data,
            "materialize_analytics": runner.run_materialize_analytics,
            "validate_all": runner.run_validate_all,
            "reconciliation_check": runner.run_reconciliation_check,
            "domain_validation": runner.run_domain_validation,
            "conflict_detection": runner.run_conflict_detection,
            "alert_check": runner.run_alert_check,
        }

        # Schedule all jobs from configuration
        scheduler.schedule_jobs_from_config(job_registry)

        # Print scheduled jobs
        logger.info("Scheduled Jobs:")
        for job in scheduler.get_jobs():
            logger.info(f"  - {job['id']}: {job['trigger']} (next: {job['next_run_time']})")

        # Start the scheduler
        logger.info("Starting scheduler...")
        scheduler.start()

        logger.info("Scheduler is running. Press Ctrl+C to stop.")
        logger.info("=" * 70)

        # Keep the scheduler running
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            scheduler.stop()
            logger.info("Scheduler stopped successfully")
            sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # Setup logging
    logger = setup_logging({
        "logging": {
            "level": "INFO",
            "file": "logs/scheduler.log"
        }
    })

    main()
