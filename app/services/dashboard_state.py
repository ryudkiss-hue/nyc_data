"""
Dashboard State Adapter

This module provides the DashboardStateAdapter, a centralized interface for
Dash callbacks to retrieve fully materialized and filtered DataFrames.
It encapsulates global filter parsing, dataset routing, and data caching,
providing a clean seam between the UI triggers and the data/analytics logic.
"""

import logging
from typing import Any, Dict, List, Optional

import geopandas as gpd
import pandas as pd

from app.data_manager import DataManager
from app.services.analytics_service import (
    get_dataset,
    get_metric_metrics,
    get_spatial_data,
    get_timeseries_data,
)

logger = logging.getLogger(__name__)

class DashboardStateAdapter:
    """
    Adapter to encapsulate state retrieval and data filtering for the dashboard.

    Provides a unified interface for callbacks to request filtered datasets
    without needing to manually concatenate, cache, or parse global filters.
    """

    def __init__(self, data_manager: DataManager, filters: Optional[Dict[str, Any]] = None):
        """
        Initialize the adapter with a DataManager instance and the current global filters.

        Args:
            data_manager: The singleton DataManager instance to fetch cached data.
            filters: The current global filters from the Dash store.
        """
        self.dm = data_manager
        self.filters = filters or {}

    def get_boroughs(self) -> List[str]:
        """Get the selected boroughs from the global filter."""
        boroughs = self.filters.get("boroughs", ["MN", "BK", "BX", "QN", "SI"])
        if isinstance(boroughs, str):
            return [boroughs]
        return boroughs

    def get_limit(self) -> Optional[int]:
        """Get the data limit from the global filter."""
        limit_str = self.filters.get("data_limit", "none")
        return None if limit_str == "none" else int(limit_str)

    def get_selected_datasets(self) -> List[str]:
        """Get the list of selected datasets."""
        return self.filters.get("datasets", ["inspection", "built", "violations", "lot_info"])

    def get_combined_dataset(self) -> pd.DataFrame:
        """
        Get a fully materialized and filtered DataFrame containing all selected datasets.

        Returns:
            pd.DataFrame: Concatenated DataFrame with a '_source_dataset' identifier column.
        """
        datasets = self.get_selected_datasets()
        limit = self.get_limit()

        combined_df = pd.DataFrame()

        for ds in datasets:
            try:
                ds_key = "inspection" if "311" in ds else "built" if "capital" in ds else ds
                df_part = self.dm.get_cached_dataset(ds_key)

                if df_part is not None and not df_part.empty:
                    if limit is not None:
                        df_part = df_part.head(limit)
                    # Create a copy to avoid SettingWithCopyWarning
                    df_part = df_part.copy()
                    df_part["_source_dataset"] = ds
                    combined_df = pd.concat([combined_df, df_part], ignore_index=True)
            except Exception as e:
                logger.warning(f"Error fetching dataset {ds}: {e}")

        return combined_df

    def get_dataset_by_key(self, dataset_key: str) -> pd.DataFrame:
        """Get a specific cached dataset by key, properly filtered."""
        df = self.dm.get_cached_dataset(dataset_key)
        if df is None or df.empty:
            return pd.DataFrame()

        boroughs = self.get_boroughs()
        if boroughs and "ALL" not in boroughs:
            boro_cols = [c for c in df.columns if "boro" in c.lower()]
            if boro_cols:
                df = df[df[boro_cols[0]].str.upper().isin([b.upper() for b in boroughs])]

        limit = self.get_limit()
        if limit is not None:
            df = df.head(limit)
        return df

    def get_analytics_dataset(self) -> pd.DataFrame:
        """Get the base dataset for analytics (Phase C) properly filtered."""
        df = get_dataset(self.filters)
        limit = self.get_limit()
        if not df.empty and limit is not None:
            df = df.head(limit)
        return df

    def get_spatial_dataset(self) -> gpd.GeoDataFrame:
        """Get the spatial dataset for mapping (Phase B/D) properly filtered."""
        gdf = get_spatial_data(self.filters)
        limit = self.get_limit()
        if not gdf.empty and limit is not None:
            gdf = gdf.head(limit)
        return gdf

    def get_timeseries_dataset(self) -> pd.DataFrame:
        """Get the timeseries dataset (Phase E) properly filtered."""
        df = get_timeseries_data("built", "approved_date", "project_id", self.filters)
        limit = self.get_limit()
        if not df.empty and limit is not None:
            df = df.head(limit)
        return df

    def get_metrics_dataset(self) -> pd.DataFrame:
        """Get the KPIs dataset properly filtered."""
        df = get_metric_metrics(self.filters)
        limit = self.get_limit()
        if not df.empty and limit is not None:
            df = df.head(limit)
        return df
