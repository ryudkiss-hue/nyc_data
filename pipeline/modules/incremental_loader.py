"""
Incremental Loader Module
Handles delta loading using watermarks and checkpoints.
Supports resumable loads with state persistence.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class LoadWatermark:
    """Tracks the high-water mark for incremental loads."""
    dataset_name: str
    last_load_date: Optional[str] = None
    last_load_id: Optional[str] = None
    rows_loaded: int = 0
    load_duration_seconds: float = 0.0
    status: str = 'pending'  # pending, in_progress, completed, failed
    last_error: Optional[str] = None
    next_load_time: Optional[str] = None


class IncrementalLoader:
    """
    Handles incremental/delta loading of datasets.
    Uses watermarks to track progress and support resumable loads.
    """

    def __init__(self, bridge, state_dir: str = None):
        """
        Initialize incremental loader.

        Args:
            bridge: MotherDuckBridge instance
            state_dir: Directory for watermark state files
        """
        self.bridge = bridge
        if state_dir is None:
            state_dir = str(Path(__file__).parent.parent / "state")
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.watermarks: Dict[str, LoadWatermark] = {}
        self._load_watermarks()

    def _load_watermarks(self):
        """Load watermarks from state file."""
        watermark_file = self.state_dir / "watermarks.json"

        if watermark_file.exists():
            try:
                with open(watermark_file) as f:
                    data = json.load(f)

                for dataset_name, watermark_data in data.items():
                    self.watermarks[dataset_name] = LoadWatermark(**watermark_data)

                logger.info(f"Loaded watermarks for {len(self.watermarks)} datasets")
            except Exception as e:
                logger.warning(f"Failed to load watermarks: {str(e)}")

    def _save_watermarks(self):
        """Persist watermarks to state file."""
        watermark_file = self.state_dir / "watermarks.json"

        try:
            data = {name: asdict(wm) for name, wm in self.watermarks.items()}

            with open(watermark_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Saved watermarks for {len(self.watermarks)} datasets")
        except Exception as e:
            logger.error(f"Failed to save watermarks: {str(e)}")

    def get_watermark(self, dataset_name: str) -> LoadWatermark:
        """Get watermark for a dataset."""
        if dataset_name not in self.watermarks:
            self.watermarks[dataset_name] = LoadWatermark(dataset_name=dataset_name)

        return self.watermarks[dataset_name]

    def update_watermark(self, dataset_name: str, **kwargs):
        """Update watermark for a dataset."""
        wm = self.get_watermark(dataset_name)

        for key, value in kwargs.items():
            if hasattr(wm, key):
                setattr(wm, key, value)

        self._save_watermarks()

    def should_load(self, dataset_name: str, force: bool = False) -> bool:
        """
        Determine if dataset should be loaded.

        Returns True if:
        - Never loaded before
        - Last load failed
        - Force flag set
        - Scheduled load time reached
        """
        if force:
            return True

        wm = self.get_watermark(dataset_name)

        if wm.status == 'pending' or wm.status == 'failed':
            return True

        if wm.last_load_date is None:
            return True

        # Check if next_load_time has passed
        if wm.next_load_time:
            try:
                next_time = datetime.fromisoformat(wm.next_load_time)
                if datetime.now() >= next_time:
                    return True
            except:
                pass

        return False

    def build_incremental_query(
        self,
        dataset_name: str,
        base_query: str,
        date_column: Optional[str] = None,
        id_column: Optional[str] = None
    ) -> str:
        """
        Build incremental query using watermark.

        Adds WHERE clause to only fetch new/updated records.
        """
        wm = self.get_watermark(dataset_name)

        if wm.status == 'completed' and wm.last_load_date and date_column:
            # Load only records after last load date
            query = f"{base_query} WHERE {date_column} > '{wm.last_load_date}'"
            logger.info(f"Incremental query for {dataset_name}: {query[:80]}...")
            return query

        # Full load if no watermark
        logger.info(f"Full load for {dataset_name} (no prior watermark)")
        return base_query

    def calculate_load_summary(self, dataset_name: str, row_count: int, elapsed_seconds: float):
        """Calculate and log load summary."""
        rate = row_count / elapsed_seconds if elapsed_seconds > 0 else 0

        summary = {
            'dataset': dataset_name,
            'rows_loaded': row_count,
            'load_time_seconds': elapsed_seconds,
            'rows_per_second': round(rate, 2)
        }

        logger.info(f"Load summary: {summary}")
        return summary

    def get_load_status_report(self) -> Dict[str, Any]:
        """Generate load status report for all datasets."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_datasets': len(self.watermarks),
            'completed_loads': sum(1 for wm in self.watermarks.values() if wm.status == 'completed'),
            'failed_loads': sum(1 for wm in self.watermarks.values() if wm.status == 'failed'),
            'total_rows_loaded': sum(wm.rows_loaded for wm in self.watermarks.values()),
            'datasets': {}
        }

        for dataset_name, wm in self.watermarks.items():
            report['datasets'][dataset_name] = {
                'status': wm.status,
                'rows_loaded': wm.rows_loaded,
                'last_load_date': wm.last_load_date,
                'load_duration': wm.load_duration_seconds
            }

        return report


class IncrementalStrategy:
    """Strategies for different load patterns."""

    @staticmethod
    def full_load(loader: IncrementalLoader, dataset_name: str) -> str:
        """Full load strategy - fetch all data."""
        return f"SELECT * FROM raw.{dataset_name}"

    @staticmethod
    def date_based_incremental(
        loader: IncrementalLoader,
        dataset_name: str,
        date_column: str
    ) -> str:
        """Date-based incremental - fetch records after last load date."""
        wm = loader.get_watermark(dataset_name)

        if wm.last_load_date:
            return f"SELECT * FROM raw.{dataset_name} WHERE {date_column} > '{wm.last_load_date}'"

        return f"SELECT * FROM raw.{dataset_name}"

    @staticmethod
    def id_based_incremental(
        loader: IncrementalLoader,
        dataset_name: str,
        id_column: str
    ) -> str:
        """ID-based incremental - fetch records after last load ID."""
        wm = loader.get_watermark(dataset_name)

        if wm.last_load_id:
            return f"SELECT * FROM raw.{dataset_name} WHERE {id_column} > '{wm.last_load_id}'"

        return f"SELECT * FROM raw.{dataset_name}"

