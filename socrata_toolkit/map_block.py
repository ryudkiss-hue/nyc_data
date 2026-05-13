import tempfile
import json
import asyncio
from pathlib import Path
from nicegui import ui
import pandas as pd

class InteractiveMapBlock:
    """
    A highly customizable, interactive OpenStreetMap block for the NiceGUI Workspace.
    Supports dynamic data plotting, popups, and exporting.
    """
    def __init__(self, workspace_state):
        self.state = workspace_state
        self.dataset_name = None
        self.lat_col = 'latitude'
        self.lon_col = 'longitude'
        self.color_col = None
        self.markers = []

    def render(self):
        """Renders the map and its configuration controls."""
        with ui.card().classes('w-full border border-gray-200 shadow-sm'):
            with ui.row().classes('w-full items-center justify-between mb-2'):
                ui.label('🌍 OpenStreetMap Explorer').classes('text-xl font-bold text-gray-800 dark:text-gray-200')
                
                # Export Options Dropdown
                with ui.dropdown_button('Export Data', icon='download', auto_close=True).classes('bg-green-600 text-white outline'):
                    ui.item('Export as CSV', on_click=self.export_csv)
                    ui.item('Export as GeoJSON', on_click=self.export_geojson)

            # Customization Controls
            with ui.row().classes('w-full items-end gap-4 mb-4 p-4 bg-gray-50 dark:bg-gray-800 rounded'):
                dataset_options = list(self.state.datasets.keys()) if self.state.datasets else []
                
                self.ds_select = ui.select(
                    dataset_options, 
                    label='1. Select Dataset', 
                    on_change=self.update_column_options
                ).classes('w-48')
                
                self.lat_select = ui.select([], label='2. Latitude').classes('w-32')
                self.lon_select = ui.select([], label='3. Longitude').classes('w-32')
                self.popup_select = ui.select([], label='4. Popup Label (Opt)').classes('w-40')
                
                ui.button('Plot Data', on_click=self.plot_map, icon='place').classes('bg-blue-600 text-white ml-auto')

            # OSM Base Layer via Leaflet
            self.map_view = ui.leaflet(center=(40.7128, -74.0060), zoom=11).classes('w-full h-[500px] z-0 rounded')

    def update_column_options(self):
        """Populate column dropdowns when a dataset is selected."""
        if not self.ds_select.value:
            return
            
        df = self.state.datasets[self.ds_select.value]
        columns = df.columns.tolist()
        
        self.lat_select.options = columns
        self.lon_select.options = columns
        self.popup_select.options = columns
        
        # Auto-guess lat/lon columns
        guess_lat = next((c for c in columns if c.lower() in ['lat', 'latitude', 'y']), None)
        guess_lon = next((c for c in columns if c.lower() in ['lon', 'long', 'longitude', 'x']), None)
        
        if guess_lat: self.lat_select.value = guess_lat
        if guess_lon: self.lon_select.value = guess_lon
        self.lat_select.update()
        self.lon_select.update()
        self.popup_select.update()

    async def plot_map(self):
        """Plots the selected data onto the OpenStreetMap layer asynchronously."""
        if not self.ds_select.value or not self.lat_select.value or not self.lon_select.value:
            ui.notify('Please select a dataset and coordinate columns.', type='warning')
            return
            
        df = self.state.datasets[self.ds_select.value]
        lat_col = self.lat_select.value
        lon_col = self.lon_select.value
        popup_col = self.popup_select.value

        # Clear existing markers immediately in the main thread
        self.map_view.clear_layers()
        self.markers.clear()

        # Provide immediate UI feedback
        notification = ui.notification('Processing spatial data in background...', type='info', timeout=None)

        # Offload heavy pandas operations to a background thread
        processed_data = await asyncio.to_thread(
            self._process_map_data, df, lat_col, lon_col, popup_col
        )

        total_points = processed_data.get('total_points', 0)
        
        if total_points == 0:
            notification.message = 'No valid coordinates found in selected columns.'
            notification.type = 'negative'
            notification.timeout = 3000
            return

        # Back in the main thread: safely add UI components
        if processed_data.get('markers'):
            for m in processed_data['markers']:
                marker = self.map_view.marker(latlng=(m['lat'], m['lon']))
                if m['popup']:
                    marker.bind_popup(m['popup'])
                    
        if processed_data.get('clusters'):
            for c in processed_data['clusters']:
                marker = self.map_view.marker(latlng=(c['lat'], c['lon']))
                if c['popup']:
                    marker.bind_popup(c['popup'])
                
        # Re-center map to the mean of the plotted points
        self.map_view.set_center((processed_data['avg_lat'], processed_data['avg_lon']))
        
        msg = f"Plotted {total_points:,} locations! "
        if processed_data.get('clusters'):
            msg += f"(Aggregated into {len(processed_data['clusters'])} high-density clusters)"
            
        notification.message = msg
        notification.type = 'positive'
        notification.timeout = 5000

    def _process_map_data(self, df: pd.DataFrame, lat_col: str, lon_col: str, popup_col: str | None) -> dict:
        """Runs in background thread: processes DataFrame and extracts marker properties."""
        plot_df = df.dropna(subset=[lat_col, lon_col]).copy()
        
        if plot_df.empty:
            return {'markers': [], 'clusters': []}

        # Convert to numeric to ensure math works properly
        plot_df['lat_num'] = pd.to_numeric(plot_df[lat_col], errors='coerce')
        plot_df['lon_num'] = pd.to_numeric(plot_df[lon_col], errors='coerce')
        plot_df = plot_df.dropna(subset=['lat_num', 'lon_num'])
        
        if plot_df.empty:
            return {'markers': [], 'clusters': []}

        total_points = len(plot_df)

        markers = []
        clusters = []

        if total_points <= 1000:
            for _, row in plot_df.iterrows():
                popup_text = f"<b>{popup_col}:</b> {row[popup_col]}<br>" if popup_col and pd.notna(row.get(popup_col)) else ""
                popup_text += f"<span class='text-xs text-gray-500'>Lat: {row['lat_num']:.4f}, Lon: {row['lon_num']:.4f}</span>"
                markers.append({'lat': row['lat_num'], 'lon': row['lon_num'], 'popup': popup_text})
        else:
            # Backend Grid Clustering for massive datasets
            # Rounding coordinates to 3 decimal places creates a geographic grid
            plot_df['lat_grid'] = plot_df['lat_num'].round(3)
            plot_df['lon_grid'] = plot_df['lon_num'].round(3)
            
            cluster_df = plot_df.groupby(['lat_grid', 'lon_grid']).size().reset_index(name='count')
            
            for _, row in cluster_df.iterrows():
                cluster_count = row['count']
                popup_text = (
                    f"<b>🛑 High-Density Cluster</b><br>"
                    f"<b>Contains:</b> {cluster_count:,} data points<br>"
                    f"<span class='text-xs text-gray-500'>Grid: {row['lat_grid']:.3f}, {row['lon_grid']:.3f}</span>"
                )
                clusters.append({
                    'lat': row['lat_grid'], 
                    'lon': row['lon_grid'], 
                    'count': cluster_count,
                    'popup': popup_text
                })
                
        avg_lat = plot_df['lat_num'].mean()
        avg_lon = plot_df['lon_num'].mean()
        
        return {
            'markers': markers,
            'clusters': clusters,
            'avg_lat': avg_lat,
            'avg_lon': avg_lon,
            'total_points': total_points
        }

    def export_csv(self):
        """Exports the active dataset to CSV."""
        if not self.ds_select.value:
            ui.notify('No dataset selected to export.', type='warning')
            return
        df = self.state.datasets[self.ds_select.value]
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
            df.to_csv(tmp.name, index=False)
            ui.download(tmp.name, f"{self.ds_select.value}_export.csv")

    def export_geojson(self):
        """Exports the active dataset to a GeoJSON feature collection."""
        if not self.ds_select.value or not self.lat_select.value or not self.lon_select.value:
            ui.notify('Please select dataset and coordinate columns first.', type='warning')
            return
            
        df = self.state.datasets[self.ds_select.value].dropna(subset=[self.lat_select.value, self.lon_select.value])
        
        features = []
        for _, row in df.iterrows():
            feature = {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(row[self.lon_select.value]), float(row[self.lat_select.value])]},
                "properties": row.drop([self.lat_select.value, self.lon_select.value]).fillna("").to_dict()
            }
            features.append(feature)
            
        geojson = {"type": "FeatureCollection", "features": features}
        with tempfile.NamedTemporaryFile(delete=False, suffix='.geojson', mode='w') as tmp:
            json.dump(geojson, tmp)
            ui.download(tmp.name, f"{self.ds_select.value}_spatial_export.geojson")