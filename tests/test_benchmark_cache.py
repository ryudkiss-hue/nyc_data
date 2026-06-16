import pytest

import shutil
import time
from pathlib import Path

import pandas as pd
import pytest

from app.utils.cache_manager import CACHE_DIR, read_cache, write_cache
from src.socrata_toolkit.core.duckdb_store import DuckDBManager, DuckDBRepository

# Performance Thresholds (in seconds)
WRITE_THRESHOLD = 2.0
READ_THRESHOLD = 1.0

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup: Ensure cache directory exists
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # Teardown: Clean up
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)

def test_benchmark_parquet_cache():
    # Create sample data
    df = pd.DataFrame({'a': range(10000), 'b': range(10000)})
    key = 'test_dataset'

    # Measure write time
    start_write = time.perf_counter()
    write_cache(key, df)
    end_write = time.perf_counter()
    write_time = end_write - start_write
    print(f"Write time: {write_time:.4f}s")

    # Measure read time
    start_read = time.perf_counter()
    read_cache(key)
    end_read = time.perf_counter()
    read_time = end_read - start_read
    print(f"Read time: {read_time:.4f}s")

    # Assert thresholds (this will fail if thresholds are exceeded)
    assert write_time < WRITE_THRESHOLD, f"Write time {write_time:.4f}s exceeded threshold {WRITE_THRESHOLD}s"
    assert read_time < READ_THRESHOLD, f"Read time {read_time:.4f}s exceeded threshold {READ_THRESHOLD}s"
