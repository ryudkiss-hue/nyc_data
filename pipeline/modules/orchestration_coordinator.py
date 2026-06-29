"""
Orchestration Coordinator Module
Coordinates multi-module pipeline execution with error handling.
Manages dependencies, retries, and alerting.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecutionPlan:
    """Execution plan for coordinated pipeline stages."""

    plan_id: str
    stages: List[str]
    dependencies: Dict[str, List[str]]
    retry_policy: Dict
    timeout_seconds: int = 3600
    allow_partial_failure: bool = False


class PipelineOrchestrator:
    """
    Orchestrates multi-stage pipeline execution.
    Manages stage dependencies, retries, and error handling.
    """

    def __init__(self, state_manager=None):
        """
        Initialize orchestrator.

        Args:
            state_manager: Optional StateManager for tracking
        """
        self.state_manager = state_manager
        self.stages = {}
        self.stage_results = {}
        logger.info("Pipeline orchestrator initialized")

    def register_stage(
        self,
        stage_name: str,
        execute_fn,
        dependencies: List[str] = None,
        retry_count: int = 1,
        timeout: int = 300
    ) -> bool:
        """
        Register a pipeline stage.

        Args:
            stage_name: Unique stage identifier
            execute_fn: Function to execute
            dependencies: List of stage dependencies
            retry_count: Number of retries on failure
            timeout: Stage timeout in seconds

        Returns:
            True if registered successfully
        """
        stage = {
            'name': stage_name,
            'execute': execute_fn,
            'dependencies': dependencies or [],
            'retry_count': retry_count,
            'timeout': timeout,
            'status': 'pending'
        }

        self.stages[stage_name] = stage
        logger.info(f"Registered stage: {stage_name} with dependencies: {stage['dependencies']}")
        return True

    def execute_plan(self, plan: ExecutionPlan) -> Dict:
        """
        Execute coordinated pipeline plan.

        Args:
            plan: ExecutionPlan with stages and dependencies

        Returns:
            Execution results
        """
        logger.info(f"Starting execution plan: {plan.plan_id}")

        results = {
            'plan_id': plan.plan_id,
            'status': 'completed',
            'started_at': datetime.now().isoformat(),
            'stages': {}
        }

        executed = set()
        failed = set()

        # Topological execution based on dependencies
        while len(executed) < len(plan.stages):
            ready_stages = [
                s for s in plan.stages
                if s not in executed
                and all(dep in executed for dep in plan.dependencies.get(s, []))
            ]

            if not ready_stages:
                logger.error("Circular dependency or blocked stages")
                results['status'] = 'failed'
                break

            for stage_name in ready_stages:
                result = self._execute_stage(stage_name, plan.retry_policy)
                self.stage_results[stage_name] = result
                results['stages'][stage_name] = result

                if result['status'] == 'failed':
                    failed.add(stage_name)
                    if not plan.allow_partial_failure:
                        results['status'] = 'failed'
                        logger.error(f"Stage failed, aborting: {stage_name}")
                        break
                else:
                    executed.add(stage_name)

        results['completed_at'] = datetime.now().isoformat()
        results['failed_stages'] = list(failed)
        results['executed_stages'] = list(executed)

        logger.info(f"Plan execution completed: {results['status']}")
        return results

    def _execute_stage(self, stage_name: str, retry_policy: Dict) -> Dict:
        """
        Execute a single stage with retry logic.

        Args:
            stage_name: Stage to execute
            retry_policy: Retry configuration

        Returns:
            Stage execution result
        """
        if stage_name not in self.stages:
            return {'status': 'failed', 'error': 'Stage not found'}

        stage = self.stages[stage_name]
        retry_count = retry_policy.get('max_retries', 1)
        retry_delay = retry_policy.get('delay_seconds', 5)

        for attempt in range(1, retry_count + 1):
            try:
                logger.info(f"Executing stage: {stage_name} (attempt {attempt}/{retry_count})")

                start_time = datetime.now()
                result = stage['execute']()
                elapsed = (datetime.now() - start_time).total_seconds()

                if result:
                    logger.info(f"Stage succeeded: {stage_name} in {elapsed}s")
                    return {
                        'status': 'succeeded',
                        'stage': stage_name,
                        'elapsed_seconds': elapsed,
                        'attempts': attempt
                    }
                else:
                    logger.warning(f"Stage returned False: {stage_name}")

            except Exception as e:
                logger.error(f"Stage execution error: {stage_name} - {str(e)}")

                if attempt < retry_count:
                    logger.info(f"Retrying {stage_name} after {retry_delay}s")
                    import time
                    time.sleep(retry_delay)
                else:
                    return {
                        'status': 'failed',
                        'stage': stage_name,
                        'error': str(e),
                        'attempts': attempt
                    }

        return {
            'status': 'failed',
            'stage': stage_name,
            'error': 'Max retries exceeded'
        }

    def get_stage_status(self, stage_name: str) -> Dict:
        """Get status of a stage."""
        if stage_name in self.stages:
            return {
                'name': stage_name,
                'status': self.stages[stage_name]['status'],
                'dependencies': self.stages[stage_name]['dependencies']
            }
        return {'status': 'not_found'}

    def get_execution_summary(self) -> Dict:
        """Get summary of all stage executions."""
        total = len(self.stage_results)
        succeeded = sum(1 for r in self.stage_results.values() if r.get('status') == 'succeeded')
        failed = total - succeeded

        return {
            'timestamp': datetime.now().isoformat(),
            'total_stages': total,
            'succeeded': succeeded,
            'failed': failed,
            'stages': self.stage_results
        }

