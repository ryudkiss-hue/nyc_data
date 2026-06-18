"""
Socrata API Data Loader
Fetches datasets from NYC Open Data Socrata API and loads to MotherDuck.
Implements pagination, batching, validation, and local caching.
"""

import os
import json
import logging
import time
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DatasetMetadata:
    """Metadata for a Socrata dataset."""
    id: int
    name: str
    socrata_id: str
    row_count: int
    primary_key: str
    source: str  # 'cache' or 'socrata'
    domain_schema: str


@dataclass
class LoadResult:
    """Result of dataset load operation."""
    dataset_name: str
    success: bool
    rows_loaded: int = 0
    rows_cached: int = 0
    error: Optional[str] = None
    load_time_ms: float = 0.0
    source: str = "unknown"  # 'cache', 'socrata', 'local'


class SocrataLoader:
    """
    Loads Socrata datasets with pagination, batching, and local caching.
    """

    def __init__(
        self,
        bridge,
        socrata_domain: str = "data.cityofnewyork.us",
        app_token: Optional[str] = None,
        cache_dir: str = "data/cache",
        batch_size: int = 200000,  # Rows per API request
        rate_limit_delay: float = 0.5  # Seconds between requests
    ):
        """
        Initialize Socrata loader.

        Args:
            bridge: MotherDuckBridge instance
            socrata_domain: Socrata domain URL
            app_token: Socrata app token (from env if not provided)
            cache_dir: Directory for cached Parquet files
            batch_size: Rows per API request
            rate_limit_delay: Delay between API calls
        """
        self.bridge = bridge
        self.socrata_domain = socrata_domain
        self.app_token = app_token or os.getenv("SOCRATA_APP_TOKEN", "")
        self.cache_dir = Path(cache_dir)
        self.batch_size = batch_size
        self.rate_limit_delay = rate_limit_delay

        # Create cache dir if needed
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Socrata loader initialized (cache: {self.cache_dir})")

    def load_config(self, config_path: str) -> List[DatasetMetadata]:
        """
        Load dataset config from JSON.

        Args:
            config_path: Path to socrata_datasets.json

        Returns:
            List of DatasetMetadata
        """
        try:
            with open(config_path, "r") as f:
                config = json.load(f)

            datasets = []

            # Load cached datasets
            for dataset_dict in config.get("cached_datasets", []):
                datasets.append(DatasetMetadata(**dataset_dict))

            # Load remaining Socrata datasets
            for dataset_dict in config.get("socrata_remaining", []):
                datasets.append(DatasetMetadata(**dataset_dict))

            logger.info(f"Loaded config with {len(datasets)} datasets")
            return datasets

        except FileNotFoundError:
            logger.error(f"Config file not found: {config_path}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config: {str(e)}")
            return []

    def load_from_cache(self, dataset_name: str, schema_name: str = "raw") -> LoadResult:
        """
        Load dataset from local Parquet cache.

        Args:
            dataset_name: Dataset name
            schema_name: Target schema in database

        Returns:
            LoadResult
        """
        cache_file = self.cache_dir / "raw" / f"{dataset_name}.parquet"

        if not cache_file.exists():
            return LoadResult(
                dataset_name=dataset_name,
                success=False,
                error=f"Cache file not found: {cache_file}",
                source="cache"
            )

        start_time = time.time()

        try:
            logger.info(f"Loading from cache: {dataset_name}")

            # Read Parquet file
            df = pd.read_parquet(cache_file)
            rows_loaded = len(df)

            # Create schema if needed
            self.bridge.create_schema(schema_name)

            # Create table from dataframe
            self.bridge.connection.register(f"{dataset_name}_temp", df)
            sql = f"CREATE TABLE IF NOT EXISTS {schema_name}.{dataset_name} AS SELECT * FROM {dataset_name}_temp"
            result = self.bridge.execute_sql(sql)

            if not result.success:
                return LoadResult(
                    dataset_name=dataset_name,
                    success=False,
                    error=result.error,
                    source="cache"
                )

            load_time_ms = (time.time() - start_time) * 1000

            logger.info(f"Loaded from cache: {dataset_name} ({rows_loaded} rows, {load_time_ms:.2f}ms)")

            return LoadResult(
                dataset_name=dataset_name,
                success=True,
                rows_loaded=rows_loaded,
                rows_cached=rows_loaded,
                load_time_ms=load_time_ms,
                source="cache"
            )

        except Exception as e:
            logger.error(f"Error loading from cache: {str(e)}")
            return LoadResult(
                dataset_name=dataset_name,
                success=False,
                error=str(e),
                source="cache"
            )

    def load_from_socrata(
        self,
        dataset_name: str,
        socrata_id: str,
        schema_name: str = "raw",
        limit: Optional[int] = None
    ) -> LoadResult:
        """
        Load dataset from Socrata API with pagination.

        Args:
            dataset_name: Dataset name
            socrata_id: Socrata dataset ID (4x4)
            schema_name: Target schema in database
            limit: Max rows to load (None = all)

        Returns:
            LoadResult
        """
        start_time = time.time()
        total_rows = 0

        try:
            logger.info(f"Loading from Socrata: {dataset_name} ({socrata_id})")

            # Fetch data with pagination using direct HTTP API
            offset = 0
            tables = []

            base_url = f"https://{self.socrata_domain}/api/views/{socrata_id}/rows.json"

            while True:
                # Rate limiting
                time.sleep(self.rate_limit_delay)

                logger.debug(f"Fetching batch at offset {offset}")

                try:
                    params = {
                        "$offset": offset,
                        "$limit": self.batch_size
                    }
                    if self.app_token:
                        params["$$app_token"] = self.app_token

                    response = requests.get(base_url, params=params, timeout=30)
                    response.raise_for_status()

                    rows = response.json()
                    if not rows:
                        logger.debug(f"No more rows at offset {offset}")
                        break

                    df = pd.DataFrame(rows)

                    if df is None or len(df) == 0:
                        logger.debug(f"No more rows at offset {offset}")
                        break

                    tables.append(df)
                    total_rows += len(df)
                    logger.debug(f"Fetched {len(df)} rows (total: {total_rows})")

                    if limit and total_rows >= limit:
                        logger.info(f"Reached limit of {limit} rows")
                        break

                    offset += self.batch_size

                except Exception as e:
                    logger.error(f"Error fetching batch at offset {offset}: {str(e)}")
                    if total_rows == 0:
                        return LoadResult(
                            dataset_name=dataset_name,
                            success=False,
                            error=f"Failed to fetch first batch: {str(e)}",
                            source="socrata"
                        )
                    else:
                        # Partial success
                        break

            # Combine tables and load to database
            if not tables:
                return LoadResult(
                    dataset_name=dataset_name,
                    success=False,
                    error="No data fetched from Socrata",
                    source="socrata"
                )

            combined_df = pd.concat(tables, ignore_index=True)
            logger.info(f"Combined {len(tables)} batches into {len(combined_df)} rows")

            # Create schema
            self.bridge.create_schema(schema_name)

            # Register dataframe and create table
            self.bridge.connection.register(f"{dataset_name}_temp", combined_df)
            sql = f"CREATE TABLE IF NOT EXISTS {schema_name}.{dataset_name} AS SELECT * FROM {dataset_name}_temp"
            result = self.bridge.execute_sql(sql)

            if not result.success:
                return LoadResult(
                    dataset_name=dataset_name,
                    success=False,
                    error=result.error,
                    source="socrata"
                )

            # Cache the data
            self._cache_dataframe(combined_df, dataset_name)

            load_time_ms = (time.time() - start_time) * 1000

            logger.info(f"Loaded from Socrata: {dataset_name} ({total_rows} rows, {load_time_ms:.2f}ms)")

            return LoadResult(
                dataset_name=dataset_name,
                success=True,
                rows_loaded=total_rows,
                rows_cached=0,
                load_time_ms=load_time_ms,
                source="socrata"
            )

        except Exception as e:
            logger.error(f"Error loading from Socrata: {str(e)}")
            return LoadResult(
                dataset_name=dataset_name,
                success=False,
                error=str(e),
                source="socrata"
            )

    def _cache_dataframe(self, df: pd.DataFrame, dataset_name: str):
        """
        Cache dataframe to local Parquet file.

        Args:
            df: DataFrame to cache
            dataset_name: Dataset name
        """
        try:
            cache_file = self.cache_dir / "raw" / f"{dataset_name}.parquet"
            cache_file.parent.mkdir(parents=True, exist_ok=True)

            df.to_parquet(cache_file, compression="snappy", index=False)
            logger.info(f"Cached to: {cache_file}")
        except Exception as e:
            logger.warning(f"Error caching dataframe: {str(e)}")

    def load_datasets_batch(
        self,
        datasets: List[DatasetMetadata],
        batch_size: int = 10,
        skip_socrata: bool = False
    ) -> Dict[str, LoadResult]:
        """
        Load multiple datasets in batches.

        Args:
            datasets: List of DatasetMetadata to load
            batch_size: Datasets per batch
            skip_socrata: Skip Socrata API calls (load cache only)

        Returns:
            Dictionary of {dataset_name: LoadResult}
        """
        results = {}

        for i, dataset in enumerate(datasets):
            logger.info(f"Loading dataset {i+1}/{len(datasets)}: {dataset.name}")

            # Try cache first
            if dataset.source == "cache" or Path(self.cache_dir / "raw" / f"{dataset.name}.parquet").exists():
                result = self.load_from_cache(dataset.name)
            elif not skip_socrata and dataset.source == "socrata":
                result = self.load_from_socrata(dataset.name, dataset.socrata_id)
            else:
                result = LoadResult(
                    dataset_name=dataset.name,
                    success=False,
                    error="Source unavailable and Socrata skipped",
                    source="unknown"
                )

            results[dataset.name] = result

            # Rate limiting between datasets
            if i < len(datasets) - 1:
                time.sleep(self.rate_limit_delay)

        return results

    def validate_load(self, dataset_name: str, schema_name: str = "raw") -> Tuple[bool, str]:
        """
        Validate that dataset was loaded correctly.

        Args:
            dataset_name: Dataset name
            schema_name: Schema name

        Returns:
            (is_valid, message)
        """
        try:
            # Check table exists
            tables = self.bridge.list_tables(schema_name)
            if dataset_name not in tables:
                return False, f"Table not found in schema {schema_name}"

            # Check row count
            count = self.bridge.get_table_count(schema_name, dataset_name)
            if count == 0:
                return False, "Table is empty"

            return True, f"Valid ({count} rows)"

        except Exception as e:
            return False, f"Validation error: {str(e)}"


# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test config loading
    loader = SocrataLoader(None)
    datasets = loader.load_config("pipeline/config/socrata_datasets.json")
    print(f"Loaded {len(datasets)} datasets from config")
