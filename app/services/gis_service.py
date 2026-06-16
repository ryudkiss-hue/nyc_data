"""
Geographic Information Systems (GIS) service.
Handles spatial queries, clustering, conflict detection, and visualization.
Optimized for Dash callback-based architecture with caching.
"""

from __future__ import annotations

import logging
import math

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

# NYC Bounds for filtering
NYC_BOUNDS = {
    "lat_min": 40.477,
    "lat_max": 40.917,
    "lon_min": -74.259,
    "lon_max": -73.700,
}

# Haversine distance calculation
def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in kilometres between two WGS84 points."""
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

class GISService:
    """Unified GIS operations for Dash callbacks."""

    @staticmethod
    def flag_in_bounds(df: pd.DataFrame) -> pd.DataFrame:
        """Filter DataFrame to points within NYC bounds."""
        if "latitude" not in df.columns or "longitude" not in df.columns:
            return df
        mask = (
            df["latitude"].between(NYC_BOUNDS["lat_min"], NYC_BOUNDS["lat_max"])
            & df["longitude"].between(NYC_BOUNDS["lon_min"], NYC_BOUNDS["lon_max"])
        )
        return df[mask].copy()

    @staticmethod
    def create_condition_map(
        df: pd.DataFrame,
        title: str = "Inspection Condition Map",
        color_col: str | None = "condition_score",
    ) -> go.Figure:
        """
        Create Plotly scatter mapbox visualization of inspection locations.
        Item 1: Condition map with Scatter Mapbox.

        Args:
            df: DataFrame with latitude, longitude columns
            title: Chart title
            color_col: Column to color by (e.g., condition_score, severity)

        Returns:
            Plotly Figure object
        """
        if df.empty:
            return go.Figure().add_annotation(
                text="No data available",
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
            )

        if "latitude" not in df.columns or "longitude" not in df.columns:
            return go.Figure().add_annotation(
                text="Missing coordinate columns",
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
            )

        df_valid = GISService.flag_in_bounds(
            df.dropna(subset=["latitude", "longitude"])
        )
        if df_valid.empty:
            return go.Figure().add_annotation(
                text="No points within NYC bounds",
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
            )

        # Determine color column
        available_color_cols = [
            c for c in ["condition_score", "result", "status", "severity"]
            if c in df_valid.columns
        ]
        if not available_color_cols:
            color_col = None
        elif color_col not in df_valid.columns:
            color_col = available_color_cols[0]

        hover_data = [
            c
            for c in [
                "borough",
                "defect_type",
                "result",
                "status",
                "street_name",
                "condition_score",
            ]
            if c in df_valid.columns
        ]

        fig = px.scatter_mapbox(
            df_valid,
            lat="latitude",
            lon="longitude",
            color=color_col,
            color_continuous_scale=(
                "RdYlGn" if color_col == "condition_score" else None
            ),
            hover_data=hover_data,
            zoom=10,
            title=title,
            height=550,
            mapbox_style="carto-positron",
        )

        fig.update_layout(
            margin={"r": 0, "t": 40, "l": 0, "b": 50},
            hovermode="closest",
        )

        # Add data source annotation
        fig.add_annotation(
            text="Data: NYC Open Data (Socrata) | Map: OpenStreetMap contributors",
            xref="paper",
            yref="paper",
            x=0.01,
            y=-0.08,
            showarrow=False,
            font=dict(size=8, color="gray"),
            xanchor="left",
        )

        return fig

    @staticmethod
    def create_kde_heatmap(
        df: pd.DataFrame,
        title: str = "Hotspot Analysis (Kernel Density)",
    ) -> go.Figure:
        """
        Create KDE-based heatmap for hotspot analysis.
        Item 2: Hotspot analysis with KDE + density visualization.

        Args:
            df: DataFrame with latitude, longitude columns
            title: Chart title

        Returns:
            Plotly Figure object (density heatmap)
        """
        if df.empty:
            return go.Figure().add_annotation(
                text="No data available",
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
            )

        df_valid = GISService.flag_in_bounds(
            df.dropna(subset=["latitude", "longitude"])
        )
        if df_valid.empty:
            return go.Figure().add_annotation(
                text="No points within NYC bounds",
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
            )

        # Use Plotly's density_heatmap for KDE visualization
        fig = px.density_heatmap(
            df_valid,
            x="longitude",
            y="latitude",
            nbinsx=30,
            nbinsy=30,
            title=title,
            height=550,
            color_continuous_scale="Viridis",
        )
        fig.update_layout(
            margin={"r": 0, "t": 40, "l": 0, "b": 50},
            hovermode="closest",
        )

        # Add data source annotation
        fig.add_annotation(
            text="Data: Socrata API | Map: OpenStreetMap contributors",
            xref="paper",
            yref="paper",
            x=0.01,
            y=-0.08,
            showarrow=False,
            font=dict(size=8, color="gray"),
            xanchor="left",
        )

        return fig

    @staticmethod
    def detect_conflicts(
        inspections: pd.DataFrame,
        permits: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Flag permits that temporally overlap with inspections.
        Item 3: Conflict detection (attribute-based fallback).

        Uses block_id, _bbl, or borough join with date-based severity.

        Args:
            inspections: Inspection DataFrame with spatial/temporal columns
            permits: Permit DataFrame with spatial/temporal columns

        Returns:
            DataFrame of conflict pairs with severity
        """
        if inspections.empty or permits.empty:
            return pd.DataFrame()

        insp = inspections.copy()
        perm = permits.copy()

        # Find common join column
        join_col = None
        for col in ["block_id", "_bbl", "borough"]:
            if col in insp.columns and col in perm.columns:
                join_col = col
                break

        if join_col is None:
            return pd.DataFrame()

        common = set(insp[join_col].dropna()) & set(perm[join_col].dropna())
        if not common:
            return pd.DataFrame()

        insp_sub = insp[insp[join_col].isin(common)].copy()
        perm_sub = perm[perm[join_col].isin(common)].copy()

        today = pd.Timestamp.today()
        conflicts = []

        for _, permit in perm_sub.iterrows():
            bid = permit[join_col]
            matching = insp_sub[insp_sub[join_col] == bid]

            for _, insp_row in matching.iterrows():
                insp_date = insp_row.get("inspection_date") or insp_row.get(
                    "inspectiondate"
                )
                days_gap = 999

                if insp_date:
                    try:
                        days_gap = abs((today - pd.Timestamp(insp_date)).days)
                    except Exception:
                        pass

                # Classify severity by temporal proximity
                if days_gap <= 30:
                    severity = "HIGH"
                elif days_gap <= 90:
                    severity = "MEDIUM"
                else:
                    severity = "LOW"

                conflicts.append(
                    {
                        join_col: bid,
                        "borough": insp_row.get(
                            "borough", permit.get("borough", "")
                        ),
                        "permit_type": permit.get(
                            "permit_type", permit.get("worktype", "")
                        ),
                        "applicant": permit.get("applicant", ""),
                        "severity": severity,
                        "inspection_date": insp_date,
                        "permit_start": permit.get("start_date", ""),
                        "permit_end": permit.get("end_date", ""),
                        "insp_lat": insp_row.get("latitude"),
                        "insp_lon": insp_row.get("longitude"),
                        "perm_lat": permit.get("latitude"),
                        "perm_lon": permit.get("longitude"),
                    }
                )

        if not conflicts:
            return pd.DataFrame()

        df_conflicts = pd.DataFrame(conflicts)
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        df_conflicts["_sort"] = df_conflicts["severity"].map(order)
        return df_conflicts.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)

    @staticmethod
    def create_conflict_map(
        conflicts: pd.DataFrame,
        title: str = "Spatial Conflict Detection",
    ) -> go.Figure:
        """
        Visualize conflicts on a map with severity coloring.

        Args:
            conflicts: DataFrame from detect_conflicts()
            title: Chart title

        Returns:
            Plotly Figure
        """
        if conflicts.empty:
            return go.Figure().add_annotation(
                text="No conflicts detected",
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
            )

        # Filter to rows with coordinates
        df_valid = conflicts.dropna(subset=["insp_lat", "insp_lon"]).copy()
        if df_valid.empty:
            return go.Figure().add_annotation(
                text="No conflict coordinates available",
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
            )

        # Map severity to color
        color_map = {"HIGH": "red", "MEDIUM": "orange", "LOW": "green"}
        df_valid["_color"] = df_valid["severity"].map(color_map).fillna("blue")

        fig = px.scatter_mapbox(
            df_valid,
            lat="insp_lat",
            lon="insp_lon",
            color="severity",
            color_discrete_map={"HIGH": "red", "MEDIUM": "orange", "LOW": "green"},
            hover_data=["severity", "permit_type", "applicant"],
            zoom=10,
            title=title,
            height=550,
            mapbox_style="carto-positron",
        )

        fig.update_layout(
            margin={"r": 0, "t": 40, "l": 0, "b": 0},
            hovermode="closest",
        )
        return fig

    @staticmethod
    def aggregate_by_borough(
        df: pd.DataFrame,
        value_col: str | None = None,
        title: str = "Records by Borough",
    ) -> go.Figure:
        """
        Create bar chart aggregated by borough.

        Args:
            df: DataFrame with borough column
            value_col: Column to aggregate (default: count)
            title: Chart title

        Returns:
            Plotly Figure
        """
        if df.empty or "borough" not in df.columns:
            return go.Figure().add_annotation(
                text="No borough data available",
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
            )

        if value_col and value_col not in df.columns:
            value_col = None

        if value_col:
            agg_df = (
                df.groupby("borough")[value_col]
                .agg(["count", "mean"])
                .reset_index()
            )
            agg_df.columns = ["borough", "count", "mean"]

            fig = px.bar(
                agg_df,
                x="borough",
                y="count",
                color="mean",
                color_continuous_scale="RdYlGn"
                if value_col == "condition_score"
                else "Viridis",
                title=title,
                height=400,
            )
        else:
            agg_df = df["borough"].value_counts().reset_index()
            agg_df.columns = ["borough", "count"]

            fig = px.bar(
                agg_df,
                x="borough",
                y="count",
                color="count",
                color_continuous_scale="Blues",
                title=title,
                height=400,
            )

        fig.update_layout(
            xaxis_tickangle=-45,
            margin={"r": 0, "t": 40, "l": 0, "b": 80},
        )
        return fig

    @staticmethod
    def compute_dbscan_clusters(
        df: pd.DataFrame,
        eps: float = 0.01,
        min_samples: int = 5,
    ) -> tuple[np.ndarray, int]:
        """
        DBSCAN spatial clustering on lat/lon coordinates.

        Args:
            df: DataFrame with latitude, longitude columns
            eps: DBSCAN epsilon in degrees (~1.1 km per 0.01 degrees)
            min_samples: Minimum points per cluster

        Returns:
            (cluster_labels, n_clusters)
        """
        if df.empty or len(df) < min_samples:
            return np.array([]), 0

        try:
            from sklearn.cluster import DBSCAN

            coords = df[["latitude", "longitude"]].dropna().values
            if len(coords) == 0:
                return np.array([]), 0

            clusterer = DBSCAN(eps=eps, min_samples=min_samples)
            labels = clusterer.fit_predict(coords)
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)

            logger.info(f"DBSCAN: {n_clusters} clusters from {len(coords)} points")
            return labels, n_clusters

        except ImportError:
            logger.warning("sklearn not available for DBSCAN clustering")
            return np.array([]), 0

    @staticmethod
    def create_cluster_map(
        df: pd.DataFrame,
        clusters: np.ndarray | None = None,
        title: str = "Spatial Clustering (DBSCAN)",
    ) -> go.Figure:
        """
        Visualize DBSCAN clusters on a map.

        Args:
            df: DataFrame with latitude, longitude
            clusters: Array of cluster labels from compute_dbscan_clusters
            title: Chart title

        Returns:
            Plotly Figure
        """
        if df.empty:
            return go.Figure().add_annotation(
                text="No data available",
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
            )

        df_valid = GISService.flag_in_bounds(
            df.dropna(subset=["latitude", "longitude"]).copy()
        )
        if df_valid.empty:
            return go.Figure().add_annotation(
                text="No points within NYC bounds",
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
            )

        if clusters is not None and len(clusters) == len(df_valid):
            df_valid["_cluster"] = clusters
            color_col = "_cluster"
        else:
            color_col = None

        fig = px.scatter_mapbox(
            df_valid,
            lat="latitude",
            lon="longitude",
            color=color_col,
            color_continuous_scale="Viridis" if color_col else None,
            hover_data=["borough"] if "borough" in df_valid.columns else None,
            zoom=10,
            title=title,
            height=550,
            mapbox_style="carto-positron",
        )

        fig.update_layout(
            margin={"r": 0, "t": 40, "l": 0, "b": 0},
            hovermode="closest",
        )
        return fig

# Global instance
gis_service = GISService()
