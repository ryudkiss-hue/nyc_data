import logging
import os
import pickle
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import diskcache
import numpy as np
import pandas as pd
import yaml
import zstandard as zstd

from socrata_toolkit import SocrataClient, SocrataConfig

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from socrata_toolkit.core.duckdb_store import DuckDBManager

# Item 108: FanoutCache for High-Concurrency Performance
cache_dir = Path(".cache/socrata_data")
cache_dir.mkdir(parents=True, exist_ok=True)
cache = diskcache.FanoutCache(str(cache_dir), shards=8, timeout=10)

class DataManager:
    """Industrial Data Manager for NYC DOT SIM Analytics."""

    def __init__(self, token=None, soda_version="3.0", db_path=None):
        self.token = token or os.getenv("SOCRATA_APP_TOKEN", "")
        self.soda_version = soda_version
        self.db_path = db_path or os.getenv("DUCKDB_PATH", "data/local_db/nyc_mission_control.duckdb")
        self.manager = DuckDBManager(self.db_path)
        self.client = SocrataClient(SocrataConfig(
            app_token=self.token,
            soda_version=self.soda_version
        ))
        self.datasets_config = self._load_config()
        self.progress = {"current": "", "completed": 0, "total": 0}
        self._lock = threading.Lock()

    def _load_config(self):
        config_path = Path("config/datasets.yaml")
        if not config_path.exists():
            config_path = Path("nyc_data/config/datasets.yaml")
        with open(config_path) as f:
            full_cfg = yaml.safe_load(f)
        return full_cfg

    def get_dataset_registry(self):
        return self.datasets_config.get("datasets", {})

    def _fetch_single_dataset(self, key, info, actual_limit, force_refresh, cctx, dctx):
        """Worker function for parallel fetching."""
        fourfour = info["fourfour"]
        limit_label = "unlimited" if actual_limit is None else str(actual_limit)
        cache_key = f"ds_{fourfour}_{limit_label}_v{self.soda_version}_zstd"

        if not force_refresh and cache_key in cache:
            logger.info(f"Loading {key} ({fourfour}) from compressed cache.")
            compressed_data = cache[cache_key]
            pickled_data = dctx.decompress(compressed_data)
            df = pickle.loads(pickled_data)
            # Item: Atomic progress update
            with self._lock:
                self.progress["completed"] += 1
            return key, df

        try:
            logger.info(f"Fetching {key} ({fourfour}) via SODA{self.soda_version} (Limit: {limit_label})...")

            rows = []
            for page in self.client.fetch_json(
                domain="data.cityofnewyork.us",
                fourfour=fourfour,
                max_rows=actual_limit
            ):
                rows.extend(page)
                # Item: Throttle progress updates to avoid lock contention
                if len(rows) % 1000 == 0:
                    self.progress["current"] = f"{key} ({len(rows):,} rows)"

            df = pd.DataFrame(rows)

            # Compress and Cache
            pickled_data = pickle.dumps(df)
            compressed_data = cctx.compress(pickled_data)
            cache[cache_key] = compressed_data

            with self._lock:
                self.progress["completed"] += 1
            return key, df
        except Exception as e:
            logger.error(f"Failed to fetch {key}: {e}")
            with self._lock:
                self.progress["completed"] += 1
            return key, pd.DataFrame()

    def fetch_all_datasets(self, limit=5000, force_refresh=False):
        """
        Fetch all 26 datasets in PARALLEL using ThreadPoolExecutor.
        Item 110: High-Throughput Network Concurrency.
        """
        registry = self.get_dataset_registry()
        actual_limit = None if int(limit) <= 0 else int(limit)

        self.progress["total"] = len(registry)
        self.progress["completed"] = 0

        data_bundle = {}
        cctx = zstd.ZstdCompressor()
        dctx = zstd.ZstdDecompressor()

        # Item 112: Optimal concurrency based on core count and network bandwidth
        max_workers = min(10, len(registry))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_key = {
                executor.submit(self._fetch_single_dataset, k, info, actual_limit, force_refresh, cctx, dctx): k
                for k, info in registry.items()
            }

            for future in as_completed(future_to_key):
                key, df = future.result()
                data_bundle[key] = df

        return data_bundle

    def get_cached_dataset(self, key, limit=5000):
        registry = self.get_dataset_registry()
        if key not in registry:
            return pd.DataFrame()

        fourfour = registry[key]["fourfour"]
        limit_label = "unlimited" if int(limit) <= 0 else str(limit)
        cache_key = f"ds_{fourfour}_{limit_label}_v{self.soda_version}_zstd"

        compressed_data = cache.get(cache_key)
        if compressed_data:
            dctx = zstd.ZstdDecompressor()
            pickled_data = dctx.decompress(compressed_data)
            return pickle.loads(pickled_data)

        return pd.DataFrame()

    def get_dataset_metadata(self):
        return self.get_dataset_registry()
