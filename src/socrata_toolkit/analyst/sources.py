"""Data source adapters for Analyst Autopilot."""

from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import Protocol

import pandas as pd

from .config import SourceConfig


class DataSource(Protocol):
    """Load a canonical DataFrame from a configured source."""

    def load(self) -> pd.DataFrame: ...

def _apply_column_map(df: pd.DataFrame, column_map: dict[str, str]) -> pd.DataFrame:
    if not column_map:
        return df
    rename = {k: v for k, v in column_map.items() if k in df.columns}
    return df.rename(columns=rename)

class ExcelSource:
    def __init__(self, config: SourceConfig):
        self.config = config

    def load(self) -> pd.DataFrame:
        """Load one or more Excel files matching the configured path glob and return a combined DataFrame."""
        path_pattern = self.config.path
        if not path_pattern:
            return pd.DataFrame()
        paths = sorted(glob.glob(path_pattern))
        if not paths and Path(path_pattern).exists():
            paths = [path_pattern]
        if not paths:
            return pd.DataFrame()
        frames = []
        for p in paths:
            df = pd.read_excel(p, sheet_name=self.config.sheet, engine="openpyxl")
            frames.append(df)
        out = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
        return _apply_column_map(out, self.config.column_map)

class SocrataSource:
    def __init__(self, config: SourceConfig):
        self.config = config

    def load(self) -> pd.DataFrame:
        """Fetch data from a Socrata dataset and return it as a DataFrame."""
        from ..core import SocrataClient

        if not self.config.domain or not self.config.fourfour:
            return pd.DataFrame()
        client = SocrataClient()
        df = client.fetch_dataframe(
            self.config.domain,
            self.config.fourfour,
            max_rows=self.config.max_rows,
        )
        return _apply_column_map(df, self.config.column_map)

class PostgresSource:
    def __init__(self, config: SourceConfig):
        self.config = config

    def load(self) -> pd.DataFrame:
        """Query the configured Postgres table via DSN env var and return a DataFrame."""
        dsn = os.getenv(self.config.dsn_env, "")
        table = self.config.table
        if not dsn or not table:
            return pd.DataFrame()
        import psycopg

        with psycopg.connect(dsn) as conn:
            df = pd.read_sql(f'SELECT * FROM "{table}"', conn)
        return _apply_column_map(df, self.config.column_map)

class GeoSource:
    """Optional geospatial file loader (requires geo extra for some formats)."""

    def __init__(self, config: SourceConfig):
        self.config = config

    def load(self) -> pd.DataFrame:
        """Load geospatial files matching the configured path glob and return a flat DataFrame."""
        path_pattern = self.config.path
        if not path_pattern:
            return pd.DataFrame()
        paths = sorted(glob.glob(path_pattern))
        if not paths and Path(path_pattern).exists():
            paths = [path_pattern]
        if not paths:
            return pd.DataFrame()
        try:
            import geopandas as gpd

            frames = [gpd.read_file(p) for p in paths]
            gdf = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
            return _apply_column_map(pd.DataFrame(gdf), self.config.column_map)
        except ImportError:
            p = paths[0]
            if p.lower().endswith(".geojson") or p.lower().endswith(".json"):
                import json

                data = json.loads(Path(p).read_text(encoding="utf-8"))
                rows = data.get("features", [])
                records = [f.get("properties", {}) for f in rows]
                return _apply_column_map(pd.DataFrame(records), self.config.column_map)
            return pd.DataFrame()

def build_source(config: SourceConfig) -> DataSource:
    """Instantiate and return the appropriate DataSource subclass for the given config type."""
    kind = config.type.lower()
    if kind == "excel":
        return ExcelSource(config)
    if kind == "socrata":
        return SocrataSource(config)
    if kind == "postgres":
        return PostgresSource(config)
    if kind in ("geo", "geopackage", "geojson"):
        return GeoSource(config)
    raise ValueError(f"Unknown source type: {config.type}")
