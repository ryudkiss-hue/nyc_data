"""
Socrata API Data Loader
Fetches datasets from NYC Open Data Socrata API and loads to MotherDuck.
Implements pagination, batching, validation, and local caching.
"""

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

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
    soql_where: Optional[str] = None   # optional server-side row filter (e.g. 311)
    ll251_name: Optional[str] = None   # original Local Law 251 dataset name


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
            with open(config_path) as f:
                config = json.load(f)

            datasets = []

            # Tolerate unknown keys so config schema can evolve without breaking
            # ingestion (the registry-driven regenerator may add new metadata).
            known = {f.name for f in fields(DatasetMetadata)}

            def _coerce(d):
                return DatasetMetadata(**{k: v for k, v in d.items() if k in known})

            for dataset_dict in config.get("cached_datasets", []):
                datasets.append(_coerce(dataset_dict))

            for dataset_dict in config.get("socrata_remaining", []):
                datasets.append(_coerce(dataset_dict))

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
            self.bridge.connection.register("_cache_temp", df)
            sql = f'CREATE OR REPLACE TABLE {schema_name}."{dataset_name}" AS SELECT * FROM _cache_temp'
            result = self.bridge.execute_sql(sql)
            self.bridge.connection.unregister("_cache_temp")

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
        limit: Optional[int] = None,
        soql_where: Optional[str] = None,
    ) -> LoadResult:
        """
        Load dataset from Socrata API with pagination.

        Args:
            dataset_name: Dataset name
            socrata_id: Socrata dataset ID (4x4)
            schema_name: Target schema in database
            limit: Max rows to load (None = all)
            soql_where: Optional SoQL $where filter (server-side row filtering,
                e.g. for large datasets like 311 where only sidewalk/curb
                complaint types are in scope). May be given as a bare predicate
                or prefixed with "$where=".

        Returns:
            LoadResult
        """
        start_time = time.time()
        total_rows = 0
        # Quoted, fully-qualified target — handles names that start with a digit
        # (e.g. 9_11_authorized_bus_parking_permit) or contain reserved words.
        qualified = f'{schema_name}."{dataset_name}"'

        try:
            logger.info(f"Loading from Socrata: {dataset_name} ({socrata_id})")

            # Create schema up front; stream batches straight into the table so a
            # single huge CTAS never has to materialize the whole dataset in
            # memory (root cause of the prior DuckDB Out-of-Memory failures).
            self.bridge.create_schema(schema_name)
            # Lower the insert memory footprint; best-effort (ignore if unsupported).
            self.bridge.execute_sql("SET preserve_insertion_order=false")

            # Use the SODA resource endpoint, which returns proper named-column
            # JSON records (list of dicts). The /api/views/{id}/rows.json
            # endpoint returns positional arrays wrapped in {meta, data} and
            # yields unnamed columns — do not use it for ingestion.
            base_url = f"https://{self.socrata_domain}/resource/{socrata_id}.json"

            offset = 0
            last_id = None
            table_created = False
            cache_batches = []
            cache_capped = False  # stop accumulating in-memory cache for huge sets

            where_base = soql_where
            if where_base and where_base.startswith("$where="):
                where_base = where_base[len("$where="):]

            # Keyset pagination on the universal ":id" system field is robust at
            # any depth (no offset degradation, survives long-running loads, no
            # lease/timeouts from deep skips). ":id" can't be combined with "*"
            # in $select, so probe the column list once to build an explicit
            # projection. Falls back to offset paging if the probe fails.
            select_cols = None
            try:
                # Use the FULL column schema from the views-metadata API — NOT a
                # 1-row data probe. Socrata omits null fields per-row, so a sample
                # drops sparse columns (e.g. tree_damage.inspectionid), corrupting
                # the table. Backtick-quote names so reserved words (from/to) are
                # valid in $select.
                meta = requests.get(
                    f"https://{self.socrata_domain}/api/views/{socrata_id}.json",
                    headers={"X-App-Token": self.app_token} if self.app_token else {},
                    timeout=60)
                meta.raise_for_status()
                fields = [c.get("fieldName") for c in meta.json().get("columns", [])
                          if c.get("fieldName") and not c["fieldName"].startswith(":@")]
                if fields:
                    select_cols = ",".join(f"`{c}`" for c in fields)
            except Exception as e:
                logger.warning(f"Column schema fetch failed for {dataset_name}: {e!r}; using offset paging")
            use_keyset = bool(select_cols)
            logger.info(f"{dataset_name}: {'keyset(:id)' if use_keyset else 'offset'} pagination")

            while True:
                # Rate limiting
                time.sleep(self.rate_limit_delay)

                # Fetch one page with retry + backoff (transient network errors).
                rows = None
                last_err = None
                for attempt in range(4):
                    try:
                        if use_keyset:
                            where = where_base
                            if last_id is not None:
                                kw = f":id > '{last_id}'"
                                where = f"({where_base}) AND {kw}" if where_base else kw
                            params = {"$select": f":id,{select_cols}", "$order": ":id",
                                      "$limit": self.batch_size}
                            if where:
                                params["$where"] = where
                        else:
                            params = {"$offset": offset, "$limit": self.batch_size}
                            if where_base:
                                params["$where"] = where_base
                        if self.app_token:
                            params["$$app_token"] = self.app_token

                        response = requests.get(base_url, params=params, timeout=120)
                        response.raise_for_status()
                        rows = response.json()
                        break
                    except Exception as e:
                        last_err = e
                        wait = 2 ** attempt
                        logger.warning(
                            f"Fetch attempt {attempt+1} failed for {dataset_name}: "
                            f"{e!r}; retrying in {wait}s"
                        )
                        time.sleep(wait)

                if rows is None:
                    msg = f"{type(last_err).__name__}: {last_err}"
                    logger.error(f"Error fetching page for {dataset_name}: {msg}")
                    if total_rows == 0:
                        return LoadResult(
                            dataset_name=dataset_name,
                            success=False,
                            error=f"Failed to fetch first batch: {msg}",
                            source="socrata",
                        )
                    break  # partial success: keep what we ingested

                if not rows:
                    break

                page_n = len(rows)
                df = pd.DataFrame(rows)
                if df is None or len(df) == 0:
                    break

                # Keyset cursor: remember the last :id, then drop it (not a data col).
                if use_keyset:
                    last_id = rows[-1].get(":id")
                    if ":id" in df.columns:
                        df = df.drop(columns=[":id"])

                # Stream this batch into the DB immediately, then free it.
                self.bridge.connection.register("_ingest_temp", df)
                if not table_created:
                    sql = f"CREATE OR REPLACE TABLE {qualified} AS SELECT * FROM _ingest_temp"
                    table_created = True
                else:
                    # Reconcile schema drift: sparse datasets (e.g. 311) introduce
                    # new columns in later pages. INSERT ... BY NAME rejects source
                    # columns absent from the target, so add them first (NULLs for
                    # prior rows). BY NAME also tolerates missing columns.
                    self._reconcile_columns(qualified, df)
                    sql = f"INSERT INTO {qualified} BY NAME SELECT * FROM _ingest_temp"
                result = self.bridge.execute_sql(sql)
                self.bridge.connection.unregister("_ingest_temp")

                if not result.success:
                    if total_rows == 0:
                        return LoadResult(
                            dataset_name=dataset_name,
                            success=False,
                            error=result.error,
                            source="socrata",
                        )
                    logger.error(f"Insert failed at offset {offset}: {result.error}")
                    break

                total_rows += len(df)
                if not cache_capped:
                    cache_batches.append(df)
                    # Cap in-memory cache accumulation to avoid pandas OOM on
                    # multi-million-row datasets; the DB already has all rows.
                    if total_rows > 1_500_000:
                        cache_batches = []
                        cache_capped = True
                logger.debug(f"Ingested {len(df)} rows (total: {total_rows})")

                if limit and total_rows >= limit:
                    logger.info(f"Reached limit of {limit} rows")
                    break

                # A short page means we've reached the end (both paging modes).
                if page_n < self.batch_size:
                    break
                offset += self.batch_size

            if total_rows == 0:
                return LoadResult(
                    dataset_name=dataset_name,
                    success=False,
                    error="No data fetched from Socrata",
                    source="socrata",
                )

            # Cache the data (skipped for very large datasets to bound memory).
            if cache_batches and not cache_capped:
                self._cache_dataframe(pd.concat(cache_batches, ignore_index=True), dataset_name)

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

    def _reconcile_columns(self, qualified: str, df: pd.DataFrame):
        """Add any DataFrame columns missing from the target table.

        Socrata records are sparse: a column may first appear in a later page
        (e.g. 311 'facility_type'). New columns are added as VARCHAR (all
        Socrata JSON values arrive as strings); existing rows get NULL.
        """
        try:
            existing = {
                c[0] for c in self.bridge.connection.execute(
                    f"SELECT * FROM {qualified} LIMIT 0"
                ).description
            }
        except Exception as e:
            logger.debug(f"Could not introspect {qualified} for reconcile: {e}")
            return
        for col in df.columns:
            if col not in existing:
                alter = f'ALTER TABLE {qualified} ADD COLUMN "{col}" VARCHAR'
                res = self.bridge.execute_sql(alter)
                if res.success:
                    logger.info(f"Schema drift: added column '{col}' to {qualified}")
                else:
                    logger.warning(f"Failed to add column '{col}' to {qualified}: {res.error}")

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
