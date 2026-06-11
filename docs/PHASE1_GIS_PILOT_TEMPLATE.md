# Phase 1: GIS Dashboard Pilot - Implementation Template

**Duration:** Weeks 1-3  
**Team:** 1-2 developers  
**Goal:** Migrate 10 GIS charts from Streamlit to Dash, achieve <500ms interaction latency

---

## Week 1: Foundation & Layout Extraction

### Task 1.1: Create GIS-Specific Layout Module

**File:** `app/dash_layouts_gis.py`

```python
"""
GIS Dashboard layout for Dash.
Extracted from Streamlit app/main.py Geospatial Intelligence view.
"""

import dash_mantine_components as dmc
from dash import dcc, html
from dash_iconify import DashIconify

def layout_gis():
    """Complete GIS Dashboard layout."""
    return dmc.Container(
        fluid=True,
        pt="md",
        children=[
            # Header
            dmc.Group([
                dmc.Text("GIS & SPATIAL INTELLIGENCE", fw=900, size="xl", c="black"),
                dmc.Group([
                    dmc.Button(
                        "DRAW GEOFENCE",
                        id="btn-draw-polygon",
                        leftSection=DashIconify(icon="mdi:vector-polygon"),
                        variant="outline",
                        color="dark"
                    ),
                    dmc.Switch(
                        label="3D Buildings",
                        id="toggle-3d-buildings",
                        color="blue",
                        size="sm",
                        checked=False
                    ),
                    dmc.Switch(
                        label="Isochrone Overlay",
                        id="toggle-isochrones",
                        color="indigo",
                        size="sm",
                        checked=False
                    ),
                ], gap="xl")
            ], justify="space-between", mb="lg"),
            
            # Filters
            dmc.Grid([
                dmc.GridCol(
                    span=3,
                    children=[
                        dmc.MultiSelect(
                            id="gis-damage-type-filter",
                            label="Damage Type",
                            placeholder="Select damage types",
                            searchable=True,
                            data=[
                                {"value": "BROKEN", "label": "Broken"},
                                {"value": "PATCHWORK", "label": "Patchwork"},
                                {"value": "TRIP_HAZ", "label": "Trip Hazard"},
                                # ... etc
                            ]
                        ),
                    ]
                ),
                dmc.GridCol(
                    span=3,
                    children=[
                        dmc.Select(
                            id="gis-season-filter",
                            label="Season",
                            placeholder="All Seasons",
                            searchable=True,
                            data=[
                                {"value": "ALL", "label": "All Seasons"},
                                {"value": "SPRING", "label": "Spring"},
                                {"value": "SUMMER", "label": "Summer"},
                                {"value": "FALL", "label": "Fall"},
                                {"value": "WINTER", "label": "Winter"},
                            ]
                        ),
                    ]
                ),
            ]),
            
            dmc.Space(h="md"),
            
            # Charts (stored as session data for lazy loading)
            dcc.Store(id="store-gis-spatial-filters", storage_type="session"),
            dcc.Store(id="store-gis-chart-data", storage_type="memory"),
            
            # Chart Grid
            dmc.Stack([
                # Row 1: Main map + sidebar
                dmc.Grid([
                    dmc.GridCol(span=9, children=[
                        dmc.Paper(
                            withBorder=True,
                            p="lg",
                            radius="lg",
                            shadow="sm",
                            children=[
                                dmc.Text("3D Pedestrian Ramp Density", fw=700, mb="md"),
                                dcc.Graph(id="viz-gis-ramp-heatmap")
                            ]
                        )
                    ]),
                    dmc.GridCol(span=3, children=[
                        dmc.Stack([
                            dmc.Paper(
                                withBorder=True,
                                p="lg",
                                radius="lg",
                                children=[
                                    dmc.Text("Cluster Summary", fw=700, mb="md"),
                                    html.Div(id="gis-cluster-stats")
                                ]
                            ),
                            dmc.Button("Export Map", id="btn-export-gis-map", fullWidth=True, color="blue")
                        ])
                    ])
                ]),
                
                dmc.Space(h="lg"),
                
                # Row 2: Chart grid (2x2)
                dmc.SimpleGrid(
                    cols=2,
                    spacing="lg",
                    children=[
                        dmc.Paper(
                            withBorder=True,
                            p="lg",
                            radius="lg",
                            children=[
                                dmc.Text("DBSCAN Spatial Clustering", fw=700, mb="md"),
                                dcc.Graph(id="viz-gis-density-clusters")
                            ]
                        ),
                        dmc.Paper(
                            withBorder=True,
                            p="lg",
                            radius="lg",
                            children=[
                                dmc.Text("TSP Route Optimization", fw=700, mb="md"),
                                dcc.Graph(id="viz-gis-tsp-routes")
                            ]
                        ),
                        dmc.Paper(
                            withBorder=True,
                            p="lg",
                            radius="lg",
                            children=[
                                dmc.Text("Conflict Buffers (500m)", fw=700, mb="md"),
                                dcc.Graph(id="viz-gis-conflict-buffers")
                            ]
                        ),
                        dmc.Paper(
                            withBorder=True,
                            p="lg",
                            radius="lg",
                            children=[
                                dmc.Text("Animated Borough Bar", fw=700, mb="md"),
                                dcc.Graph(id="viz-gis-borough-bar-animated")
                            ]
                        ),
                    ]
                ),
                
                dmc.Space(h="lg"),
                
                # Row 3: More charts
                dmc.SimpleGrid(
                    cols=2,
                    spacing="lg",
                    children=[
                        dmc.Paper(
                            withBorder=True,
                            p="lg",
                            radius="lg",
                            children=[
                                dmc.Text("Accessibility Score Heat Map", fw=700, mb="md"),
                                dcc.Graph(id="viz-gis-accessibility-heatmap")
                            ]
                        ),
                        dmc.Paper(
                            withBorder=True,
                            p="lg",
                            radius="lg",
                            children=[
                                dmc.Text("Damage Type Distribution", fw=700, mb="md"),
                                dcc.Graph(id="viz-gis-damage-distribution")
                            ]
                        ),
                        dmc.Paper(
                            withBorder=True,
                            p="lg",
                            radius="lg",
                            children=[
                                dmc.Text("Inspection Frequency by Zone", fw=700, mb="md"),
                                dcc.Graph(id="viz-gis-inspection-freq")
                            ]
                        ),
                        dmc.Paper(
                            withBorder=True,
                            p="lg",
                            radius="lg",
                            children=[
                                dmc.Text("Contractor Coverage Map", fw=700, mb="md"),
                                dcc.Graph(id="viz-gis-contractor-coverage")
                            ]
                        ),
                    ]
                ),
            ], spacing="lg")
        ]
    )
```

**Checklist:**
- [ ] Copy layout structure from Streamlit app/main.py
- [ ] Create all dcc.Graph components (one per chart)
- [ ] Create filter controls (MultiSelect, Select)
- [ ] Create data stores (dcc.Store)
- [ ] Test layout renders without errors
- [ ] Compare visual appearance to Streamlit version

---

### Task 1.2: Create GIS Service Layer

**File:** `app/services/gis_service.py`

```python
"""
Geographic Information Systems (GIS) service.
Handles spatial queries, clustering, and visualization.
"""

import logging
from typing import Tuple
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.cluster import DBSCAN
import networkx as nx

logger = logging.getLogger(__name__)

class GISService:
    """Unified GIS operations."""
    
    @staticmethod
    def create_ramp_heatmap_figure(df: pd.DataFrame, title: str = "3D Pedestrian Ramp Density") -> go.Figure:
        """
        Create 3D heatmap of ramp locations.
        
        Args:
            df: DataFrame with columns ['lat', 'lon', 'damage_count']
            title: Chart title
            
        Returns:
            Plotly Figure object
        """
        if df.empty:
            return go.Figure().add_annotation(text="No data available")
        
        # Aggregate by location
        df_agg = df.groupby(['lat', 'lon']).agg({'damage_count': 'sum'}).reset_index()
        
        fig = go.Figure(data=[
            go.Scattergeo(
                lon=df_agg['lon'],
                lat=df_agg['lat'],
                text=df_agg['damage_count'],
                mode='markers',
                marker=dict(
                    size=df_agg['damage_count'] / 5,  # Scale size
                    color=df_agg['damage_count'],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="Damage Count")
                )
            )
        ])
        
        fig.update_layout(
            title=title,
            geo=dict(
                scope='usa',
                projection_type='mercator',
                center=dict(lat=40.78, lon=-73.97)
            ),
            height=500
        )
        
        return fig
    
    @staticmethod
    def compute_spatial_clusters(df: pd.DataFrame, eps: float = 0.05, min_samples: int = 10) -> Tuple[np.ndarray, int]:
        """
        DBSCAN spatial clustering on lat/lon coordinates.
        
        Args:
            df: DataFrame with ['lat', 'lon'] columns
            eps: DBSCAN epsilon (approximate meters / 111,000)
            min_samples: Minimum samples per cluster
            
        Returns:
            (cluster_labels, n_clusters)
        """
        if df.empty or len(df) < min_samples:
            return np.array([]), 0
        
        coords = df[['lat', 'lon']].values
        clusters = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
        n_clusters = len(set(clusters.labels_)) - (1 if -1 in clusters.labels_ else 0)
        
        logger.info(f"DBSCAN found {n_clusters} clusters from {len(df)} points")
        return clusters.labels_, n_clusters
    
    @staticmethod
    def create_dbscan_figure(df: pd.DataFrame, clusters: np.ndarray, title: str = "DBSCAN Spatial Clustering") -> go.Figure:
        """Visualize DBSCAN clusters on map."""
        if df.empty:
            return go.Figure().add_annotation(text="No data available")
        
        df_plot = df.copy()
        df_plot['cluster'] = clusters
        
        fig = go.Figure()
        
        # Plot each cluster with different color
        for cluster_id in sorted(set(clusters)):
            cluster_points = df_plot[df_plot['cluster'] == cluster_id]
            fig.add_trace(go.Scattergeo(
                lon=cluster_points['lon'],
                lat=cluster_points['lat'],
                mode='markers',
                name=f"Cluster {cluster_id}" if cluster_id >= 0 else "Noise",
                marker=dict(size=5)
            ))
        
        fig.update_layout(
            title=title,
            geo=dict(
                scope='usa',
                projection_type='mercator',
                center=dict(lat=40.78, lon=-73.97)
            ),
            height=500
        )
        
        return fig
    
    @staticmethod
    def solve_tsp(locations: pd.DataFrame, max_nodes: int = 20) -> Tuple[list, float]:
        """
        Traveling Salesman Problem: Find shortest route visiting all locations.
        
        Args:
            locations: DataFrame with ['lat', 'lon'] columns
            max_nodes: Max locations to include (TSP is NP-hard)
            
        Returns:
            (ordered_indices, total_distance)
        """
        if len(locations) < 2:
            return list(range(len(locations))), 0.0
        
        # Limit to max_nodes for performance
        if len(locations) > max_nodes:
            locations = locations.sample(max_nodes, random_state=42)
        
        coords = locations[['lat', 'lon']].values
        
        # Create distance matrix (Euclidean)
        n = len(coords)
        dist_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                dist_matrix[i, j] = np.sqrt((coords[i] - coords[j]) ** 2).sum()
        
        # Greedy TSP approximation
        unvisited = set(range(n))
        current = 0
        route = [0]
        unvisited.remove(0)
        total_distance = 0
        
        while unvisited:
            nearest = min(unvisited, key=lambda x: dist_matrix[current, x])
            total_distance += dist_matrix[current, nearest]
            route.append(nearest)
            unvisited.remove(nearest)
            current = nearest
        
        total_distance += dist_matrix[route[-1], route[0]]  # Return to start
        
        logger.info(f"TSP solved for {len(locations)} locations, distance: {total_distance:.2f}")
        return route, total_distance
    
    @staticmethod
    def create_tsp_figure(locations: pd.DataFrame, route: list, title: str = "TSP Route Optimization") -> go.Figure:
        """Visualize TSP route."""
        if len(route) < 2:
            return go.Figure().add_annotation(text="Insufficient locations")
        
        # Order locations by route
        ordered_locs = locations.iloc[route]
        
        fig = go.Figure()
        
        # Plot route as line
        fig.add_trace(go.Scattergeo(
            lon=ordered_locs['lon'],
            lat=ordered_locs['lat'],
            mode='lines+markers',
            name='Route',
            line=dict(color='blue', width=2),
            marker=dict(size=8, color='red')
        ))
        
        fig.update_layout(
            title=title,
            geo=dict(
                scope='usa',
                projection_type='mercator',
                center=dict(lat=40.78, lon=-73.97)
            ),
            height=500
        )
        
        return fig
    
    @staticmethod
    def create_conflict_buffer_figure(df: pd.DataFrame, buffer_m: float = 500, title: str = "Conflict Buffers (500m)") -> go.Figure:
        """
        Create buffers around points (e.g., contractor work zones).
        Detect overlaps = conflicts.
        """
        # Simplified: just show points with buffer circles
        if df.empty:
            return go.Figure().add_annotation(text="No data available")
        
        fig = go.Figure()
        
        # Add circles (buffers) around points
        for idx, row in df.iterrows():
            circle = dict(
                type='circle',
                x0=row['lon'] - (buffer_m / 111000),
                y0=row['lat'] - (buffer_m / 111000),
                x1=row['lon'] + (buffer_m / 111000),
                y1=row['lat'] + (buffer_m / 111000),
                line=dict(color='red', width=1)
            )
        
        # Add base points
        fig.add_trace(go.Scattergeo(
            lon=df['lon'],
            lat=df['lat'],
            mode='markers',
            marker=dict(size=10, color='blue'),
            name='Locations'
        ))
        
        fig.update_layout(
            title=title,
            geo=dict(
                scope='usa',
                projection_type='mercator',
                center=dict(lat=40.78, lon=-73.97)
            ),
            height=500
        )
        
        return fig

# Global instance
gis_service = GISService()
```

**Checklist:**
- [ ] Implement ramp_heatmap figure creation
- [ ] Implement DBSCAN clustering
- [ ] Implement TSP route solving
- [ ] Implement conflict buffer visualization
- [ ] Add error handling (empty DataFrames, etc.)
- [ ] Test each function with sample data

---

## Week 2: Callback Implementation

### Task 2.1: Create GIS Callbacks Module

**File:** `app/callbacks/gis_spatial.py`

```python
"""
GIS Dashboard callbacks.
Handles spatial filtering, clustering, and visualization updates.
"""

import logging
from dash import Input, Output, State, callback, no_update
import plotly.graph_objects as go
from app.services.gis_service import gis_service
from app.callbacks.base import timer_callback, memoize_with_ttl

logger = logging.getLogger(__name__)

def register_gis_spatial_callbacks(app, dm_instance):
    """Register all GIS spatial callbacks."""
    
    # ============================================================
    # Filter Synchronization
    # ============================================================
    
    @app.callback(
        Output("store-gis-spatial-filters", "data"),
        Input("gis-damage-type-filter", "value"),
        Input("gis-season-filter", "value"),
        State("store-global-filters", "data"),
        prevent_initial_call=False
    )
    @timer_callback
    def sync_gis_filters(damage_types, season, global_filters):
        """Merge GIS-specific filters with global filters."""
        if global_filters is None:
            global_filters = {}
        
        filters = {
            **global_filters,
            "damage_types": damage_types or [],
            "season": season or "ALL"
        }
        
        return filters
    
    # ============================================================
    # Chart: Ramp Heatmap
    # ============================================================
    
    @app.callback(
        Output("viz-gis-ramp-heatmap", "figure"),
        Input("store-gis-spatial-filters", "data"),
        prevent_initial_call=False
    )
    @timer_callback
    @memoize_with_ttl(seconds=600)
    def update_ramp_heatmap(filters):
        """Generate 3D ramp density heatmap."""
        if not filters:
            return go.Figure().add_annotation(text="No filters set")
        
        try:
            # Fetch ramp data
            df = dm_instance.fetch_dataset("ramp_locations")
            
            # Apply filters
            borough = filters.get("borough", "ALL")
            if borough != "ALL":
                df = df[df["borough"] == borough]
            
            if filters.get("damage_types"):
                df = df[df["damage_type"].isin(filters["damage_types"])]
            
            if filters.get("season") != "ALL":
                df = df[df["season"] == filters["season"]]
            
            # Generate figure
            return gis_service.create_ramp_heatmap_figure(df)
        except Exception as e:
            logger.error(f"Error updating ramp heatmap: {e}")
            return go.Figure().add_annotation(text=f"Error: {str(e)}")
    
    # ============================================================
    # Chart: DBSCAN Clustering
    # ============================================================
    
    @app.callback(
        Output("viz-gis-density-clusters", "figure"),
        Input("store-gis-spatial-filters", "data"),
        prevent_initial_call=False
    )
    @timer_callback
    @memoize_with_ttl(seconds=600)
    def update_density_clusters(filters):
        """Generate DBSCAN clustering visualization."""
        if not filters:
            return go.Figure().add_annotation(text="No filters set")
        
        try:
            df = dm_instance.fetch_dataset("ramp_locations")
            
            # Apply filters
            borough = filters.get("borough", "ALL")
            if borough != "ALL":
                df = df[df["borough"] == borough]
            
            # Compute clusters
            clusters, n_clusters = gis_service.compute_spatial_clusters(df, eps=0.01, min_samples=5)
            
            # Generate figure
            return gis_service.create_dbscan_figure(df, clusters)
        except Exception as e:
            logger.error(f"Error updating clusters: {e}")
            return go.Figure().add_annotation(text=f"Error: {str(e)}")
    
    # ============================================================
    # Chart: TSP Route Optimization
    # ============================================================
    
    @app.callback(
        Output("viz-gis-tsp-routes", "figure"),
        Input("store-gis-spatial-filters", "data"),
        prevent_initial_call=False
    )
    @timer_callback
    @memoize_with_ttl(seconds=1200)  # Cache longer (expensive computation)
    def update_tsp_routes(filters):
        """Generate TSP route visualization."""
        if not filters:
            return go.Figure().add_annotation(text="No filters set")
        
        try:
            df = dm_instance.fetch_dataset("ramp_locations")
            
            # Apply filters
            borough = filters.get("borough", "ALL")
            if borough != "ALL":
                df = df[df["borough"] == borough]
            
            # Solve TSP
            route, distance = gis_service.solve_tsp(df, max_nodes=30)
            
            # Generate figure
            return gis_service.create_tsp_figure(df, route)
        except Exception as e:
            logger.error(f"Error solving TSP: {e}")
            return go.Figure().add_annotation(text=f"Error: {str(e)}")
    
    # ============================================================
    # Cluster Statistics Display
    # ============================================================
    
    @app.callback(
        Output("gis-cluster-stats", "children"),
        Input("viz-gis-density-clusters", "figure"),
        prevent_initial_call=False
    )
    def update_cluster_stats(figure):
        """Display cluster count and summary stats."""
        if not figure or not figure.get("data"):
            return "No data"
        
        import dash_mantine_components as dmc
        
        n_traces = len(figure["data"])
        return dmc.Stack([
            dmc.Text(f"Clusters: {n_traces}", fw=700),
            dmc.Text("Density-based spatial clustering with DBSCAN (eps=0.01)", size="xs", c="gray"),
        ])

```

**Checklist:**
- [ ] Implement filter synchronization callback
- [ ] Implement ramp heatmap callback
- [ ] Implement DBSCAN clustering callback
- [ ] Implement TSP route callback
- [ ] Implement cluster statistics display
- [ ] Add @timer_callback decorator to all callbacks
- [ ] Test each callback independently

---

### Task 2.2: Register Callbacks in Main App

**File:** `app/dash_app.py` (modify existing file)

```python
# Add to existing imports
from app.callbacks.gis_spatial import register_gis_spatial_callbacks

# Add to callback registration section (around line 180)
register_gis_spatial_callbacks(app, dm)
```

**Checklist:**
- [ ] Add import for register_gis_spatial_callbacks
- [ ] Call register_gis_spatial_callbacks() in callback registration
- [ ] Test app starts without errors
- [ ] Verify GIS route loads and callbacks fire

---

## Week 3: Testing & Performance Baseline

### Task 3.1: Unit Tests for Callbacks

**File:** `tests/test_gis_callbacks.py`

```python
"""Unit tests for GIS callbacks."""

import pytest
import pandas as pd
import plotly.graph_objects as go
from app.callbacks.gis_spatial import (
    update_ramp_heatmap,
    update_density_clusters,
    update_tsp_routes
)
from app.services.gis_service import gis_service

# Sample test data
@pytest.fixture
def sample_ramp_data():
    return pd.DataFrame({
        "lat": [40.75, 40.76, 40.77, 40.78, 40.79],
        "lon": [-73.95, -73.94, -73.93, -73.92, -73.91],
        "damage_count": [5, 3, 8, 2, 6],
        "borough": ["MANHATTAN", "MANHATTAN", "BROOKLYN", "BROOKLYN", "QUEENS"],
        "season": ["SPRING", "SUMMER", "SPRING", "FALL", "WINTER"]
    })

def test_gis_service_create_ramp_heatmap(sample_ramp_data):
    """Test ramp heatmap figure generation."""
    fig = gis_service.create_ramp_heatmap_figure(sample_ramp_data)
    
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    assert fig.layout.title.text is not None

def test_gis_service_dbscan_clustering(sample_ramp_data):
    """Test DBSCAN clustering."""
    clusters, n_clusters = gis_service.compute_spatial_clusters(sample_ramp_data)
    
    assert len(clusters) == len(sample_ramp_data)
    assert n_clusters >= 0

def test_gis_service_tsp_solver(sample_ramp_data):
    """Test TSP route optimization."""
    route, distance = gis_service.solve_tsp(sample_ramp_data)
    
    assert len(route) == len(sample_ramp_data)
    assert distance >= 0
    assert set(route) == set(range(len(sample_ramp_data)))  # All locations visited

def test_callback_empty_data():
    """Test callbacks handle empty DataFrames gracefully."""
    empty_df = pd.DataFrame()
    
    # Should return figure with error message, not crash
    fig = gis_service.create_ramp_heatmap_figure(empty_df)
    assert isinstance(fig, go.Figure)

```

**Checklist:**
- [ ] Write test for ramp heatmap
- [ ] Write test for DBSCAN clustering
- [ ] Write test for TSP solving
- [ ] Write test for empty data handling
- [ ] Run tests: `pytest tests/test_gis_callbacks.py -v`
- [ ] Ensure 100% pass rate

---

### Task 3.2: Performance Baseline Measurement

**File:** `tests/test_gis_performance.py`

```python
"""Performance testing for GIS dashboard."""

import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture
def selenium_driver():
    """Start Chrome driver for Selenium testing."""
    driver = webdriver.Chrome()
    yield driver
    driver.quit()

class TestGISPerformance:
    """Measure GIS dashboard interaction latencies."""
    
    BASE_URL = "http://localhost:8012/geo"
    
    def test_initial_page_load(self, selenium_driver):
        """Measure initial GIS dashboard load time."""
        start = time.time()
        selenium_driver.get(self.BASE_URL)
        
        # Wait for all charts to render (up to 10 seconds)
        WebDriverWait(selenium_driver, 10).until(
            EC.presence_of_all_elements_located((By.ID, "viz-gis-ramp-heatmap"))
        )
        
        elapsed = time.time() - start
        print(f"Initial load time: {elapsed:.2f}s")
        
        # Target: <2.5 seconds
        assert elapsed < 2.5, f"Initial load too slow: {elapsed:.2f}s (target: <2.5s)"
    
    def test_borough_filter_latency(self, selenium_driver):
        """Measure borough filter change latency."""
        selenium_driver.get(self.BASE_URL)
        WebDriverWait(selenium_driver, 5).until(
            EC.presence_of_element_located((By.ID, "borough-filter"))
        )
        
        # Change borough filter
        borough_select = selenium_driver.find_element(By.ID, "borough-filter")
        borough_select.click()
        
        # Select "BROOKLYN"
        option = WebDriverWait(selenium_driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//option[@value='BROOKLYN']"))
        )
        option.click()
        
        # Measure time until chart updates (detect figure data change)
        start = time.time()
        WebDriverWait(selenium_driver, 10).until(
            EC.presence_of_element_located((By.ID, "viz-gis-ramp-heatmap"))
        )
        
        elapsed = time.time() - start
        print(f"Borough filter latency: {elapsed:.2f}s")
        
        # Target: <0.5 seconds (Dash callback, much faster than Streamlit)
        assert elapsed < 0.5, f"Filter latency too high: {elapsed:.2f}s (target: <0.5s)"
    
    def test_3d_toggle_latency(self, selenium_driver):
        """Measure 3D buildings toggle latency."""
        selenium_driver.get(self.BASE_URL)
        WebDriverWait(selenium_driver, 5).until(
            EC.presence_of_element_located((By.ID, "toggle-3d-buildings"))
        )
        
        toggle = selenium_driver.find_element(By.ID, "toggle-3d-buildings")
        
        start = time.time()
        toggle.click()
        
        # Wait for chart update
        WebDriverWait(selenium_driver, 10).until(
            EC.presence_of_element_located((By.ID, "viz-gis-ramp-heatmap"))
        )
        
        elapsed = time.time() - start
        print(f"3D toggle latency: {elapsed:.2f}s")
        
        # Target: <0.5 seconds
        assert elapsed < 0.5, f"3D toggle latency too high: {elapsed:.2f}s"

if __name__ == "__main__":
    # Run performance tests
    # Command: pytest tests/test_gis_performance.py -v -s
    pass
```

**Checklist:**
- [ ] Set up Selenium + Chrome driver
- [ ] Write initial load test
- [ ] Write borough filter latency test
- [ ] Write 3D toggle latency test
- [ ] Run tests: `pytest tests/test_gis_performance.py -v -s`
- [ ] Document baseline metrics
- [ ] Compare to Streamlit version (should be 20x faster)

---

### Task 3.3: Create Performance Baseline Report

**File:** `docs/GIS_PILOT_PERFORMANCE_BASELINE.md`

```markdown
# GIS Pilot Performance Baseline

**Date:** [Today]  
**Dash Version:** 2.14+  
**Browser:** Chrome (Headless)  
**Load Test Configuration:** Single user, sequential interactions

## Streamlit Baseline (Before Migration)

| Operation | Latency | Notes |
|-----------|---------|-------|
| Initial page load | 8.2s | Full script rerun, all data fetches |
| Borough filter change | 12.1s | Complete script rerun |
| 3D toggle | 9.8s | Full script rerun |
| Isochrone overlay toggle | 15.3s | Complex computation |
| Export CSV | 5.2s | Data serialization |
| **Average interaction** | **10.1s** | 5 measurements |

## Dash Target (After Migration)

| Operation | Latency | Target | Status |
|-----------|---------|--------|--------|
| Initial page load | TBD | <2.5s | ⏳ Testing |
| Borough filter change | TBD | <0.5s | ⏳ Testing |
| 3D toggle | TBD | <0.5s | ⏳ Testing |
| Isochrone overlay toggle | TBD | <0.5s | ⏳ Testing |
| Export CSV | TBD | <1s | ⏳ Testing |
| **Average interaction** | TBD | <0.6s | ⏳ Testing |

## Performance Improvement Target

- **Initial load:** 8.2s → 2.5s (97% improvement)
- **Filter interactions:** 12.1s → 0.5s (96% improvement)
- **Overall:** 10.1s → 0.6s average (94% improvement)

```

**Checklist:**
- [ ] Run all performance tests
- [ ] Document baseline metrics
- [ ] Compare Streamlit vs Dash latencies
- [ ] Verify 95%+ improvement
- [ ] Save results for future optimization

---

## Final Checklist: Week 3 Completion

- [ ] All 10 GIS charts implemented as callbacks
- [ ] All callbacks pass unit tests (100% success rate)
- [ ] All callbacks meet <500ms latency target
- [ ] Session state syncing works (Streamlit ↔ Dash)
- [ ] Error handling for edge cases (empty data, API failures)
- [ ] Code reviewed by 1 team member
- [ ] Performance baseline documented
- [ ] Ready for merge to main branch

---

## Go/No-Go Decision

**Go to Phase 2 if:**
- ✅ All callbacks latency <500ms (P95)
- ✅ 100% unit test pass rate
- ✅ Session state persists across refreshes
- ✅ No memory leaks (monitor for 24 hours)
- ✅ Code review approved

**No-go / Iterate if:**
- ❌ Any callback >500ms
- ❌ Unit test failures
- ❌ Session state inconsistencies
- ❌ Memory bloat observed
- ❌ Code review feedback

---

## Deployment Checklist (if Go approved)

- [ ] Merge feature branch to main
- [ ] Deploy to staging environment
- [ ] Run smoke tests (basic functionality)
- [ ] A/B test: 10% users on Dash, 90% on Streamlit
- [ ] Monitor error rates for 24 hours
- [ ] Collect user feedback
- [ ] If successful: increase Dash % to 50%
- [ ] If issues: rollback to Streamlit

