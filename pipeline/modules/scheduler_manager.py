"""
Scheduler Manager Module
Orchestrates pipeline execution with configurable schedules.
APScheduler-based nightly runs and triggered executions.
"""

import logging
from datetime import datetime
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class ScheduleConfig:
    """Configuration for pipeline scheduling."""

    def __init__(
        self,
        cron_schedule: str = "0 2 * * *",  # 2 AM daily
        timezone: str = "UTC",
        max_instances: int = 1,
        misfire_grace_time: int = 600,
        coalesce: bool = True
    ):
        """
        Initialize schedule configuration.

        Args:
            cron_schedule: Cron expression for schedule
            timezone: Timezone for schedule
            max_instances: Max concurrent jobs
            misfire_grace_time: Grace period for missed jobs
            coalesce: Merge missed executions
        """
        self.cron_schedule = cron_schedule
        self.timezone = timezone
        self.max_instances = max_instances
        self.misfire_grace_time = misfire_grace_time
        self.coalesce = coalesce


class PipelineScheduler:
    """
    Schedules and orchestrates pipeline execution.
    Supports both scheduled and triggered runs.
    """

    def __init__(self, schedule_config: Optional[ScheduleConfig] = None):
        """
        Initialize pipeline scheduler.

        Args:
            schedule_config: Schedule configuration (optional)
        """
        self.config = schedule_config or ScheduleConfig()
        self.jobs = {}
        self.execution_history = []
        logger.info(f"Scheduler initialized with cron: {self.config.cron_schedule}")

    def schedule_pipeline(
        self,
        job_name: str,
        pipeline_func: Callable,
        schedule_config: Optional[ScheduleConfig] = None
    ) -> bool:
        """
        Schedule a pipeline for regular execution.

        Args:
            job_name: Unique name for the job
            pipeline_func: Function to execute
            schedule_config: Override default config

        Returns:
            True if scheduled successfully
        """
        config = schedule_config or self.config

        try:
            job_info = {
                'name': job_name,
                'function': pipeline_func,
                'schedule': config.cron_schedule,
                'timezone': config.timezone,
                'status': 'scheduled',
                'created_at': datetime.now().isoformat(),
                'last_run': None,
                'next_run': None
            }

            self.jobs[job_name] = job_info
            logger.info(f"Scheduled job: {job_name} at {config.cron_schedule}")
            return True

        except Exception as e:
            logger.error(f"Failed to schedule {job_name}: {str(e)}")
            return False

    def trigger_execution(
        self,
        job_name: str,
        run_id: Optional[str] = None
    ) -> dict:
        """
        Trigger immediate execution of a job.

        Args:
            job_name: Job to execute
            run_id: Optional execution ID

        Returns:
            Execution result
        """
        if job_name not in self.jobs:
            logger.error(f"Job not found: {job_name}")
            return {'success': False, 'error': 'Job not found'}

        job = self.jobs[job_name]

        try:
            start_time = datetime.now()
            logger.info(f"Triggering execution: {job_name}")

            # Execute the pipeline function
            result = job['function']()

            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()

            execution = {
                'job_name': job_name,
                'run_id': run_id or f"{job_name}_{start_time.isoformat()}",
                'status': 'completed' if result else 'failed',
                'started_at': start_time.isoformat(),
                'completed_at': end_time.isoformat(),
                'elapsed_seconds': elapsed,
                'result': result
            }

            self.execution_history.append(execution)
            job['last_run'] = start_time.isoformat()

            logger.info(f"Execution completed: {job_name} in {elapsed}s")
            return execution

        except Exception as e:
            logger.error(f"Execution failed: {job_name} - {str(e)}")
            return {
                'job_name': job_name,
                'status': 'error',
                'error': str(e)
            }

    def get_job_status(self, job_name: str) -> dict:
        """Get status of a scheduled job."""
        if job_name not in self.jobs:
            return {'status': 'not_found'}

        job = self.jobs[job_name]
        return {
            'name': job['name'],
            'status': job['status'],
            'schedule': job['schedule'],
            'last_run': job['last_run'],
            'next_run': job['next_run'],
            'created_at': job['created_at']
        }

    def get_execution_history(
        self,
        job_name: Optional[str] = None,
        limit: int = 10
    ) -> list:
        """Get recent execution history."""
        if job_name:
            history = [e for e in self.execution_history if e['job_name'] == job_name]
        else:
            history = self.execution_history

        return sorted(
            history,
            key=lambda x: x.get('started_at', ''),
            reverse=True
        )[:limit]

    def get_scheduler_status(self) -> dict:
        """Get overall scheduler status."""
        return {
            'timestamp': datetime.now().isoformat(),
            'total_jobs': len(self.jobs),
            'active_jobs': sum(1 for j in self.jobs.values() if j['status'] == 'scheduled'),
            'total_executions': len(self.execution_history),
            'jobs': {name: self.get_job_status(name) for name in self.jobs.keys()}
        }

