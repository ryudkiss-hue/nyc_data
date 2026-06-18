"""
State Manager Module
Persists pipeline state for resumable/restartable execution.
Handles checkpoints, lineage tracking, and recovery.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PipelineCheckpoint:
    """Checkpoint for resumable pipeline execution."""
    checkpoint_id: str
    stage_name: str
    status: str  # started, completed, failed
    timestamp: str
    rows_processed: int = 0
    rows_failed: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None


class StateManager:
    """
    Manages pipeline state and checkpoints.
    Enables resumable execution and failure recovery.
    """

    def __init__(self, state_dir: str = "pipeline/state"):
        """Initialize state manager."""
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints: List[PipelineCheckpoint] = []
        self.metadata: Dict = {}
        self._load_state()

    def _load_state(self):
        """Load state from files."""
        checkpoints_file = self.state_dir / "checkpoints.json"
        metadata_file = self.state_dir / "metadata.json"

        try:
            if checkpoints_file.exists():
                with open(checkpoints_file) as f:
                    data = json.load(f)
                    self.checkpoints = [PipelineCheckpoint(**cp) for cp in data]
                logger.info(f"Loaded {len(self.checkpoints)} checkpoints")

            if metadata_file.exists():
                with open(metadata_file) as f:
                    self.metadata = json.load(f)
                logger.info(f"Loaded metadata: {self.metadata}")
        except Exception as e:
            logger.warning(f"Failed to load state: {str(e)}")

    def save_state(self):
        """Persist state to files."""
        try:
            checkpoints_file = self.state_dir / "checkpoints.json"
            with open(checkpoints_file, 'w') as f:
                json.dump([asdict(cp) for cp in self.checkpoints], f, indent=2)

            metadata_file = self.state_dir / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2, default=str)

            logger.info("Persisted pipeline state")
        except Exception as e:
            logger.error(f"Failed to save state: {str(e)}")

    def create_checkpoint(
        self,
        stage_name: str,
        checkpoint_id: Optional[str] = None
    ) -> PipelineCheckpoint:
        """Create a new checkpoint."""
        if checkpoint_id is None:
            checkpoint_id = f"{stage_name}_{datetime.now().isoformat()}"

        cp = PipelineCheckpoint(
            checkpoint_id=checkpoint_id,
            stage_name=stage_name,
            status='started',
            timestamp=datetime.now().isoformat()
        )

        self.checkpoints.append(cp)
        self.save_state()

        logger.info(f"Created checkpoint: {checkpoint_id}")
        return cp

    def complete_checkpoint(
        self,
        checkpoint_id: str,
        rows_processed: int = 0,
        duration_seconds: float = 0.0
    ) -> bool:
        """Mark checkpoint as completed."""
        for cp in self.checkpoints:
            if cp.checkpoint_id == checkpoint_id:
                cp.status = 'completed'
                cp.rows_processed = rows_processed
                cp.duration_seconds = duration_seconds
                self.save_state()
                logger.info(f"Checkpoint completed: {checkpoint_id} ({rows_processed} rows in {duration_seconds}s)")
                return True

        return False

    def fail_checkpoint(self, checkpoint_id: str, error_message: str) -> bool:
        """Mark checkpoint as failed."""
        for cp in self.checkpoints:
            if cp.checkpoint_id == checkpoint_id:
                cp.status = 'failed'
                cp.error_message = error_message
                self.save_state()
                logger.error(f"Checkpoint failed: {checkpoint_id} - {error_message}")
                return True

        return False

    def get_last_checkpoint(self, stage_name: Optional[str] = None) -> Optional[PipelineCheckpoint]:
        """Get the most recent checkpoint, optionally filtered by stage."""
        if not self.checkpoints:
            return None

        matching = [cp for cp in self.checkpoints if stage_name is None or cp.stage_name == stage_name]
        return matching[-1] if matching else None

    def can_resume_from(self, stage_name: str) -> bool:
        """Check if we can resume from a specific stage."""
        cp = self.get_last_checkpoint(stage_name)
        return cp is not None and cp.status == 'completed'

    def get_resume_point(self) -> Optional[str]:
        """Get the stage to resume from."""
        # Find the last completed checkpoint
        completed = [cp for cp in self.checkpoints if cp.status == 'completed']

        if completed:
            return completed[-1].stage_name

        return None

    def get_state_report(self) -> Dict:
        """Generate state report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_checkpoints': len(self.checkpoints),
            'completed': sum(1 for cp in self.checkpoints if cp.status == 'completed'),
            'failed': sum(1 for cp in self.checkpoints if cp.status == 'failed'),
            'total_rows': sum(cp.rows_processed for cp in self.checkpoints),
            'total_duration': sum(cp.duration_seconds for cp in self.checkpoints),
            'checkpoints': [asdict(cp) for cp in self.checkpoints[-10:]]  # Last 10
        }

        logger.info(f"State report: {len(report['checkpoints'])} checkpoints")
        return report


class ExecutionContext:
    """Tracks execution context across pipeline stages."""

    def __init__(self, state_manager: StateManager, pipeline_id: str):
        """Initialize execution context."""
        self.state_manager = state_manager
        self.pipeline_id = pipeline_id
        self.current_stage = None
        self.current_checkpoint = None
        self.metrics = {}

    def start_stage(self, stage_name: str):
        """Start execution of a stage."""
        self.current_stage = stage_name
        self.current_checkpoint = self.state_manager.create_checkpoint(stage_name)
        logger.info(f"Starting stage: {stage_name}")

    def complete_stage(self, rows_processed: int = 0, duration: float = 0.0):
        """Complete execution of current stage."""
        if self.current_checkpoint:
            self.state_manager.complete_checkpoint(
                self.current_checkpoint.checkpoint_id,
                rows_processed=rows_processed,
                duration_seconds=duration
            )
            logger.info(f"Completed stage: {self.current_stage}")

    def fail_stage(self, error: str):
        """Record stage failure."""
        if self.current_checkpoint:
            self.state_manager.fail_checkpoint(
                self.current_checkpoint.checkpoint_id,
                error
            )
            logger.error(f"Failed stage: {self.current_stage} - {error}")

