import threading
import time
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.data_manager import DataManager

def test_progress_lock_contention():
    """Stress test the progress lock in DataManager."""
    dm = DataManager()
    dm.progress["total"] = 1000

    def simulate_updates():
        for i in range(100):
            with dm._lock:
                dm.progress["completed"] += 1
                dm.progress["current"] = f"Task {i}"
            time.sleep(0.001)

    threads = [threading.Thread(target=simulate_updates) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()

    # Total should be exactly 1000 (10 threads * 100 updates)
    assert dm.progress["completed"] == 1000

def test_redundant_ingestion_prevention():
    """Verify that multiple initialization calls don't spawn redundant threads."""
    from app.callbacks.ingestion import ingestion_status, initialize_pipeline

    # Mock dash components
    app = MagicMock()

    # 1. First trigger
    with patch("threading.Thread") as mock_thread:
        # initialize_pipeline(n_clicks, token_list, limit_list, version_list)
        initialize_pipeline([1], ["token"], ["5000"], ["3.0"])
        assert mock_thread.call_count == 1

        # Simulate ingestion status becomes active
        ingestion_status["active"] = True

        # 2. Second trigger while active
        initialize_pipeline([2], ["token"], ["5000"], ["3.0"])
        # Should NOT have called Thread() again
        assert mock_thread.call_count == 1

    # Reset for other tests
    ingestion_status["active"] = False
