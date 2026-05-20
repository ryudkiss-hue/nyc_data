import asyncio
import json
import tempfile
from typing import Any

import pandas as pd
from nicegui import ui


class InteractiveMapBlock:
    """
    A highly customizable, interactive OpenStreetMap block for the NiceGUI Workspace.
    Supports dynamic data plotting, popups, and exporting.
    """

    def __init__(self, workspace_state: Any) -> None:
        self.state = workspace_state
        self.dataset_name: str | None = None
        self.lat_col: str = "latitude"
        self.lon_col: str = "longitude"
        self.color_col: str | None = None
        self.markers: list[Any] = []
        self.ds_select: ui.select | None = None
        self.lat_select: ui.select | None = None
        self.lon_select: ui.select | None = None
        self.popup_select: ui.select | None = None
        self.map_view: ui.leaflet | None = None

    def render(self) -> None:
        """Renders the map and its configuration controls."""
        with ui.card().classes("w-full border border-gray-200 shadow-sm"):
            with ui.row().classes("w-full items-center justify-between mb-2"):
                _ = ui.label("🌍 OpenStreetMap Explorer").classes(
                    "text-xl font-bold text-gray-800 dark:text-gray-200"
                )

                # Export Options Dropdown
                with ui.dropdown_button("Export Data", icon="download", auto_close=True).classes(
                    "bg-green-600 text-white outline"
                ):
                    ui.item("Export as CSV", on_click=self.export_csv)
                    ui.item("Export as GeoJSON", on_click=self.export_geojson)

            # Customization Controls
            with ui.row().classes(
                "w-full items-end gap-4 mb-4 p-4 bg-gray-50 dark:bg-gray-800 rounded"
            ):
                dataset_options = list(self.state.datasets.keys()) if self.state.datasets else []

                self.ds_select = ui.select(
                    dataset_options, label="1. Select Dataset", on_change=self.update_column_options
                ).classes("w-48")

                self.lat_select = ui.select([], label="2. Latitude").classes("w-32")
                self.lon_select = ui.select([], label="3. Longitude").classes("w-32")
                self.popup_select = ui.select([], label="4. Popup Label (Opt)").classes("w-40")

                _ = ui.button("Plot Data", on_click=self.plot_map, icon="place").classes(
                    "bg-blue-600 text-white ml-auto"
                )

            # OSM Base Layer via Leaflet
            self.map_view = ui.leaflet(center=(40.7128, -74.0060), zoom=11).classes(
                "w-full h-[500px] z-0 rounded"
            )

    def update_column_options(self) -> None:
        """Populate column dropdowns when a dataset is selected."""
        if not self.ds_select or not self.ds_select.value:
            return

        ds_name = str(self.ds_select.value)
        if ds_name not in self.state.datasets:
            return

        df = self.state.datasets[ds_name]
        columns = df.columns.tolist()

        if self.lat_select and self.lon_select and self.popup_select:
            self.lat_select.options = columns
            self.lon_select.options = columns
            self.popup_select.options = columns

            # Auto-guess lat/lon columns
            guess_lat = next((c for c in columns if c.lower() in ["lat", "latitude", "y"]), None)
            guess_lon = next((c for c in columns if c.lower() in ["lon", "long", "longitude", "x"]), None)

            if guess_lat:
                self.lat_select.value = guess_lat
            if guess_lon:
                self.lon_select.value = guess_lon
            self.lat_select.update()
            self.lon_select.update()
            self.popup_select.update()

    async def plot_map(self) -> None:
        """Plots the selected data onto the OpenStreetMap layer asynchronously."""
        if (
            not self.ds_select
            or not self.lat_select
            or not self.lon_select
            or not self.popup_select
            or not self.map_view
        ):
            return

        if not self.ds_select.value or not self.lat_select.value or not self.lon_select.value:
            ui.notify("Please select a dataset and coordinate columns.", type="warning")
            return

        ds_name = str(self.ds_select.value)
        lat_col = str(self.lat_select.value)
        lon_col = str(self.lon_select.value)
        popup_col = str(self.popup_select.value) if self.popup_select.value else None

        df = self.state.datasets[ds_name]

        # Clear existing markers immediately in the main thread
        self.map_view.clear_layers()
        self.markers.clear()

        # Provide immediate UI feedback
        notification = ui.notification(
            "Processing spatial data in background...", type="info", timeout=None
        )

        # Offload heavy pandas operations to a background thread
        processed_data = await asyncio.to_thread(self._process_map_data, df, lat_col, lon_col, popup_col)

        total_points = processed_data.get("total_points", 0)

        if total_points == 0:
            notification.message = "No valid coordinates found in selected columns."
            notification.type = "negative"
            notification.timeout = 3000
            return

        # Back in the main thread: safely add UI components
        if processed_data.get("markers"):
            for m in processed_data["markers"]:
                marker = self.map_view.marker(latlng=(m["lat"], m["lon"]))
                if m["popup"]:
                    marker.bind_popup(m["popup"])

        if processed_data.get("clusters"):
            for c in processed_data["clusters"]:
                marker = self.map_view.marker(latlng=(c["lat"], c["lon"]))
                if c["popup"]:
                    marker.bind_popup(c["popup"])

        # Re-center map to the mean of the plotted points
        self.map_view.set_center((processed_data["avg_lat"], processed_data["avg_lon"]))

        msg = f"Plotted {total_points:,} locations! "
        if processed_data.get("clusters"):
            msg += f"(Aggregated into {len(processed_data['clusters'])} high-density clusters)"

        notification.message = msg
        notification.type = "positive"
        notification.timeout = 5000

    def _process_map_data(
        self, df: pd.DataFrame, lat_col: str, lon_col: str, popup_col: str | None
    ) -> dict[str, Any]:
        """Runs in background thread: processes DataFrame and extracts marker properties."""
        plot_df = df.dropna(subset=[lat_col, lon_col]).copy()

        if plot_df.empty:
            return {"markers": [], "clusters": [], "avg_lat": 0, "avg_lon": 0, "total_points": 0}

        # Convert to numeric to ensure math works properly
        plot_df["lat_num"] = pd.to_numeric(plot_df[lat_col], errors="coerce")
        plot_df["lon_num"] = pd.to_numeric(plot_df[lon_col], errors="coerce")
        plot_df = plot_df.dropna(subset=["lat_num", "lon_num"])

        if plot_df.empty:
            return {"markers": [], "clusters": [], "avg_lat": 0, "avg_lon": 0, "total_points": 0}

        total_points = len(plot_df)

        markers: list[dict[str, Any]] = []
        clusters: list[dict[str, Any]] = []

        if total_points <= 1000:
            for _, row in plot_df.iterrows():
                popup_text = (
                    f"<b>{popup_col}:</b> {row[popup_col]}<br>"
                    if popup_col and pd.notna(row.get(popup_col))
                    else ""
                )
                popup_text += (
                    "<span class='text-xs text-gray-500'>"
                    f"Lat: {row['lat_num']:.4f}, Lon: {row['lon_num']:.4f}"
                    "</span>"
                )
                markers.append({"lat": row["lat_num"], "lon": row["lon_num"], "popup": popup_text})
        else:
            # Backend Grid Clustering for massive datasets
            plot_df["lat_grid"] = plot_df["lat_num"].round(3)
            plot_df["lon_grid"] = plot_df["lon_num"].round(3)

            cluster_df = plot_df.groupby(["lat_grid", "lon_grid"]).size().reset_index(name="count")

            for _, row in cluster_df.iterrows():
                cluster_count = int(row["count"])
                popup_text = (
                    "<b>🛑 High-Density Cluster</b><br>"
                    f"<b>Contains:</b> {cluster_count:,} data points<br>"
                    f"<span class='text-xs text-gray-500'>Grid: {row['lat_grid']:.3f}, {row['lon_grid']:.3f}</span>"
                )
                clusters.append(
                    {
                        "lat": float(row["lat_grid"]),
                        "lon": float(row["lon_grid"]),
                        "count": cluster_count,
                        "popup": popup_text,
                    }
                )

        avg_lat = float(plot_df["lat_num"].mean())
        avg_lon = float(plot_df["lon_num"].mean())

        return {
            "markers": markers,
            "clusters": clusters,
            "avg_lat": avg_lat,
            "avg_lon": avg_lon,
            "total_points": total_points,
        }

    def export_csv(self) -> None:
        """Exports the active dataset to CSV."""
        if not self.ds_select or not self.ds_select.value:
            ui.notify("No dataset selected to export.", type="warning")
            return
        ds_name = str(self.ds_select.value)
        df = self.state.datasets[ds_name]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            df.to_csv(tmp.name, index=False)
            ui.download(tmp.name, f"{ds_name}_export.csv")

    def export_geojson(self) -> None:
        """Exports the active dataset to a GeoJSON feature collection."""
        if (
            not self.ds_select
            or not self.ds_select.value
            or not self.lat_select
            or not self.lat_select.value
            or not self.lon_select
            or not self.lon_select.value
        ):
            ui.notify("Please select dataset and coordinate columns first.", type="warning")
            return

        ds_name = str(self.ds_select.value)
        lat_c = str(self.lat_select.value)
        lon_c = str(self.lon_select.value)
        df = self.state.datasets[ds_name].dropna(subset=[lat_c, lon_c])

        features = []
        for _, row in df.iterrows():
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row[lon_c]), float(row[lat_c])],
                },
                "properties": row.drop([lat_c, lon_c]).fillna("").to_dict(),
            }
            features.append(feature)

        geojson = {"type": "FeatureCollection", "features": features}
        with tempfile.NamedTemporaryFile(delete=False, suffix=".geojson", mode="w") as tmp:
            json.dump(geojson, tmp)
            ui.download(tmp.name, f"{ds_name}_spatial_export.geojson")

