import os
import pandas as pd
import numpy as np
from pathlib import Path
from socrata_toolkit import SocrataClient, SocrataConfig
import yaml
import diskcache
import logging
import zstandard as zstd
import pickle

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup Disk Cache
cache_dir = Path(".cache/socrata_data")
cache_dir.mkdir(parents=True, exist_ok=True)
cache = diskcache.Cache(str(cache_dir))

class DataManager:
    """Industrial Data Manager for NYC DOT SIM Analytics."""
    
    def __init__(self, token=None, soda_version="3.0"):
        self.token = token or os.getenv("SOCRATA_APP_TOKEN", "")
        self.soda_version = soda_version
        self.client = SocrataClient(SocrataConfig(
            app_token=self.token,
            soda_version=self.soda_version
        ))
        self.datasets_config = self._load_config()

    def _load_config(self):
        config_path = Path("config/datasets.yaml")
        if not config_path.exists():
            config_path = Path("nyc_data/config/datasets.yaml")
        with open(config_path, "r") as f:
            full_cfg = yaml.safe_load(f)
        return full_cfg

    def get_dataset_registry(self):
        return self.datasets_config.get("datasets", {})

    def fetch_all_datasets(self, limit=5000, force_refresh=False):
        """
        Fetch all 26 datasets from Socrata and cache them.
        Item 83: Zstandard (zstd) Compression for cache.
        """
        registry = self.get_dataset_registry()
        data_bundle = {}
        cctx = zstd.ZstdCompressor()
        dctx = zstd.ZstdDecompressor()
        
        for key, info in registry.items():
            fourfour = info["fourfour"]
            cache_key = f"ds_{fourfour}_{limit}_v{self.soda_version}_zstd"
            
            if not force_refresh and cache_key in cache:
                logger.info(f"Loading {key} ({fourfour}) from compressed cache.")
                compressed_data = cache[cache_key]
                pickled_data = dctx.decompress(compressed_data)
                df = pickle.loads(pickled_data)
                data_bundle[key] = df
                continue
            
            try:
                logger.info(f"Fetching {key} ({fourfour}) via SODA{self.soda_version}...")
                df = self.client.fetch_dataframe(
                    domain="data.cityofnewyork.us",
                    fourfour=fourfour,
                    max_rows=limit
                )
                
                # Compress and Cache
                pickled_data = pickle.dumps(df)
                compressed_data = cctx.compress(pickled_data)
                cache[cache_key] = compressed_data
                
                data_bundle[key] = df
            except Exception as e:
                logger.error(f"Failed to fetch {key}: {e}")
                data_bundle[key] = pd.DataFrame()
        
        return data_bundle

    def get_cached_dataset(self, key, limit=5000):
        registry = self.get_dataset_registry()
        if key not in registry:
            return pd.DataFrame()
        
        fourfour = registry[key]["fourfour"]
        cache_key = f"ds_{fourfour}_{limit}_v{self.soda_version}_zstd"
        
        compressed_data = cache.get(cache_key)
        if compressed_data:
            dctx = zstd.ZstdDecompressor()
            pickled_data = dctx.decompress(compressed_data)
            return pickle.loads(pickled_data)
            
        return pd.DataFrame()

    def get_dataset_metadata(self):
        return self.get_dataset_registry()
