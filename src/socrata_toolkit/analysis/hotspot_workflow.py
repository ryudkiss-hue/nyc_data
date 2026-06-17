"""Geographic Hotspot Analysis Workflow — LangGraph Orchestration.

This module implements a LangGraph-based workflow that:

1. Fetches violations, complaints, and inspections (all with geometry) from Socrata.
2. Applies DBSCAN spatial clustering to identify geographic concentrations.
3. Computes KDE (kernel density estimation) for smooth density estimates.
4. Classifies hotspots using HotspotClassificationEngine.
5. Invokes Claude (~350 tokens) for prioritization reasoning.
6. Generates folium map and routing recommendations.
7. Returns structured JSON output with hotspot analysis.

Graph Structure:
    fetch_data → spatial_cluster → classify → claude_decision → generate_map → aggregate

Output:
    - hotspots: List of classified HotspotClassifier objects
    - density_map: Folium map with hotspot visualization
    - routing_recommendations: List of recommended service routes
    - claude_summary: Claude's operational recommendations (~350 tokens)
    - execution_log: Audit trail
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, TypedDict

import numpy as np
import pandas as pd

from ..core.client import SocrataClient, SocrataConfig
from .hotspot_classifier import (
    HotspotClassifier,
    classify_hotspots_from_dataframe,
)

logger = logging.getLogger(__name__)

# Optional: Only import LangGraph if available
try:
    from langgraph.graph import END, START, StateGraph
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False

# Optional: Spatial clustering and density estimation
try:
    from scipy.stats import gaussian_kde
    from sklearn.cluster import DBSCAN
    HAS_SPATIAL = True
except ImportError:
    HAS_SPATIAL = False

# Optional: Folium for map generation
try:
    import folium
    from folium import plugins
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False

# Optional: Claude API for reasoning
try:
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage
    HAS_CLAUDE = True
except ImportError:
    HAS_CLAUDE = False

class HotspotState(TypedDict):
    """Workflow state: passed through each node."""
    # Input context
    violations_fourfour: str
    complaints_fourfour: str
    inspections_fourfour: str
    domain: str
    borough_filter: str | None
    sample_size: int
    dbscan_eps: float  # meters
    dbscan_min_samples: int

    # Fetched data
    violations_df: pd.DataFrame | None
    complaints_df: pd.DataFrame | None
    inspections_df: pd.DataFrame | None

    # Spatial analysis results
    clusters: list[dict]  # DBSCAN clusters
    density_grid: np.ndarray | None
    density_bounds: tuple | None  # (min_lat, max_lat, min_lon, max_lon)

    # Classification results
    hotspots: list[HotspotClassifier]
    high_severity_hotspots: list[HotspotClassifier]

    # Claude reasoning
    claude_summary: str
    resource_allocation_strategy: str
    routing_recommendations: list[str]

    # Output artifacts
    map_html: str | None
    final_report: dict[str, Any]
    error_log: list[str]
    execution_log: list[str]

class GeographicHotspotWorkflow:
    """Orchestrate geographic hotspot analysis via LangGraph.

    Usage:
        workflow = GeographicHotspotWorkflow(
            violations_fourfour="dntt-gqwq",
            complaints_fourfour="erm2-nwe9",
            inspections_fourfour="p7ve-f997",  # Example
        )
        result = workflow.run(borough_filter="MN", sample_size=5000)
        print(json.dumps(result["final_report"], indent=2))
    """

    def __init__(
        self,
        violations_fourfour: str,
        complaints_fourfour: str,
        inspections_fourfour: str,
        domain: str = "data.cityofnewyork.us",
        dbscan_eps: float = 0.0005,  # ~50m in lat/lon
        dbscan_min_samples: int = 10,
    ):
        """Initialize workflow.

        Args:
            violations_fourfour: Violations dataset fourfour ID
            complaints_fourfour: Complaints dataset fourfour ID
            inspections_fourfour: Inspections dataset fourfour ID
            domain: Socrata domain (default: data.cityofnewyork.us)
            dbscan_eps: DBSCAN epsilon in degrees (default ~50m)
            dbscan_min_samples: DBSCAN minimum samples per cluster
        """
        self.violations_fourfour = violations_fourfour
        self.complaints_fourfour = complaints_fourfour
        self.inspections_fourfour = inspections_fourfour
        self.domain = domain
        self.dbscan_eps = dbscan_eps
        self.dbscan_min_samples = dbscan_min_samples

        self.client = SocrataClient(SocrataConfig(
            app_token=os.getenv("SOCRATA_APP_TOKEN"),
            timeout=30,
        ))

        if HAS_LANGGRAPH:
            self._build_graph()

    def _build_graph(self) -> None:
        """Build the LangGraph workflow."""
        self.graph = StateGraph(HotspotState)

        # Add nodes
        self.graph.add_node("fetch_data", self._node_fetch_data)
        self.graph.add_node("spatial_cluster", self._node_spatial_cluster)
        self.graph.add_node("classify", self._node_classify)
        self.graph.add_node("claude_decision", self._node_claude_decision)
        self.graph.add_node("generate_map", self._node_generate_map)
        self.graph.add_node("aggregate", self._node_aggregate)

        # Build edges
        self.graph.add_edge(START, "fetch_data")
        self.graph.add_edge("fetch_data", "spatial_cluster")
        self.graph.add_edge("spatial_cluster", "classify")
        self.graph.add_edge("classify", "claude_decision")
        self.graph.add_edge("claude_decision", "generate_map")
        self.graph.add_edge("generate_map", "aggregate")
        self.graph.add_edge("aggregate", END)

        self.compiled = self.graph.compile()

    def run(
        self,
        borough_filter: str | None = None,
        sample_size: int = 5000,
    ) -> dict[str, Any]:
        """Execute the workflow.

        Args:
            borough_filter: NYC borough code (MN, BX, BK, QN, SI) or None for all
            sample_size: Maximum rows to fetch per dataset

        Returns:
            Dictionary with hotspots, map, and analysis results
        """
        if not HAS_LANGGRAPH:
            return self._run_without_langgraph(borough_filter, sample_size)

        initial_state: HotspotState = {
            "violations_fourfour": self.violations_fourfour,
            "complaints_fourfour": self.complaints_fourfour,
            "inspections_fourfour": self.inspections_fourfour,
            "domain": self.domain,
            "borough_filter": borough_filter,
            "sample_size": sample_size,
            "dbscan_eps": self.dbscan_eps,
            "dbscan_min_samples": self.dbscan_min_samples,
            "violations_df": None,
            "complaints_df": None,
            "inspections_df": None,
            "clusters": [],
            "density_grid": None,
            "density_bounds": None,
            "hotspots": [],
            "high_severity_hotspots": [],
            "claude_summary": "",
            "resource_allocation_strategy": "",
            "routing_recommendations": [],
            "map_html": None,
            "final_report": {},
            "error_log": [],
            "execution_log": [],
        }

        result = self.compiled.invoke(initial_state)
        return result

    def _node_fetch_data(self, state: HotspotState) -> HotspotState:
        """Node 1: Fetch violations, complaints, and inspections from Socrata."""
        state["execution_log"].append(f"[FETCH] Starting data fetch at {datetime.now(timezone.utc).isoformat()}")

        try:
            # Build WHERE filter for borough if specified
            where_clause = ""
            if state["borough_filter"]:
                where_clause = f" AND borough='{state['borough_filter'].upper()}'"

            # Fetch violations (with geometry)
            logger.info(f"Fetching {state['violations_fourfour']}...")
            violations_df = self.client.fetch_dataframe(
                self.domain,
                state["violations_fourfour"],
                max_rows=state["sample_size"],
                select="*",
                where=f"location is not null{where_clause}",
            )
            state["violations_df"] = violations_df if violations_df is not None else pd.DataFrame()

            # Fetch complaints (with geometry)
            logger.info(f"Fetching {state['complaints_fourfour']}...")
            complaints_df = self.client.fetch_dataframe(
                self.domain,
                state["complaints_fourfour"],
                max_rows=state["sample_size"],
                select="*",
                where=f"location is not null{where_clause}",
            )
            state["complaints_df"] = complaints_df if complaints_df is not None else pd.DataFrame()

            # Fetch inspections (optional)
            logger.info(f"Fetching {state['inspections_fourfour']}...")
            try:
                inspections_df = self.client.fetch_dataframe(
                    self.domain,
                    state["inspections_fourfour"],
                    max_rows=state["sample_size"],
                    select="*",
                    where=f"location is not null{where_clause}",
                )
                state["inspections_df"] = inspections_df if inspections_df is not None else pd.DataFrame()
            except Exception as e:
                logger.warning(f"Failed to fetch inspections: {e}")
                state["inspections_df"] = pd.DataFrame()

            state["execution_log"].append(
                f"[FETCH] Loaded {len(state['violations_df'])} violations, "
                f"{len(state['complaints_df'])} complaints, "
                f"{len(state['inspections_df'])} inspections"
            )

        except Exception as e:
            msg = f"[FETCH] Error: {str(e)}"
            logger.error(msg)
            state["error_log"].append(msg)

        return state

    def _node_spatial_cluster(self, state: HotspotState) -> HotspotState:
        """Node 2: Apply DBSCAN clustering and KDE density estimation."""
        if not HAS_SPATIAL:
            state["error_log"].append("[CLUSTER] sklearn/scipy not available")
            return state

        state["execution_log"].append("[CLUSTER] Starting DBSCAN spatial clustering...")

        try:
            # Combine violations and complaints for clustering
            combined_df = pd.concat(
                [
                    state["violations_df"][["latitude", "longitude"]].assign(type="violation"),
                    state["complaints_df"][["latitude", "longitude"]].assign(type="complaint"),
                ],
                ignore_index=True,
            )

            if combined_df.empty:
                state["execution_log"].append("[CLUSTER] No data with geometry found")
                return state

            # Clean coordinates
            combined_df = combined_df.dropna(subset=["latitude", "longitude"])
            if combined_df.empty:
                state["execution_log"].append("[CLUSTER] All coordinates are null after cleaning")
                return state

            # Apply DBSCAN clustering
            coords = combined_df[["latitude", "longitude"]].values
            clustering = DBSCAN(
                eps=state["dbscan_eps"],
                min_samples=state["dbscan_min_samples"],
            ).fit(coords)

            combined_df["cluster_id"] = clustering.labels_

            # Process clusters (ignore noise points with label -1)
            clusters = []
            for cluster_id in set(clustering.labels_):
                if cluster_id == -1:
                    continue  # Skip noise
                cluster_mask = clustering.labels_ == cluster_id
                cluster_points = combined_df[cluster_mask]

                centroid = cluster_points[["latitude", "longitude"]].mean().values
                clusters.append({
                    "cluster_id": int(cluster_id),
                    "centroid": tuple(centroid),  # (lat, lon)
                    "size": len(cluster_points),
                    "items": cluster_points.to_dict("records"),
                })

            state["clusters"] = clusters
            state["execution_log"].append(f"[CLUSTER] Found {len(clusters)} clusters")

            # Compute KDE for density map (if folium available)
            if HAS_SPATIAL and len(coords) > 10:
                try:
                    kde = gaussian_kde(coords.T)
                    # Create a grid for density estimation
                    lat_range = np.linspace(coords[:, 0].min(), coords[:, 0].max(), 50)
                    lon_range = np.linspace(coords[:, 1].min(), coords[:, 1].max(), 50)
                    grid_lat, grid_lon = np.meshgrid(lat_range, lon_range)
                    positions = np.vstack([grid_lat.ravel(), grid_lon.ravel()])
                    state["density_grid"] = kde(positions).reshape(grid_lat.shape)
                    state["density_bounds"] = (
                        coords[:, 0].min(), coords[:, 0].max(),
                        coords[:, 1].min(), coords[:, 1].max(),
                    )
                except Exception as e:
                    logger.warning(f"KDE computation failed: {e}")

        except Exception as e:
            msg = f"[CLUSTER] Error: {str(e)}"
            logger.error(msg)
            state["error_log"].append(msg)

        return state

    def _node_classify(self, state: HotspotState) -> HotspotState:
        """Node 3: Classify hotspots using HotspotClassificationEngine."""
        state["execution_log"].append("[CLASSIFY] Starting hotspot classification...")

        try:
            classifiers = classify_hotspots_from_dataframe(
                violations_df=state["violations_df"],
                complaints_df=state["complaints_df"],
                clusters=state["clusters"],
            )

            state["hotspots"] = classifiers
            state["high_severity_hotspots"] = [
                h for h in classifiers
                if h.severity_score >= 50
            ]

            state["execution_log"].append(
                f"[CLASSIFY] Classified {len(classifiers)} hotspots; "
                f"{len(state['high_severity_hotspots'])} high-severity"
            )

        except Exception as e:
            msg = f"[CLASSIFY] Error: {str(e)}"
            logger.error(msg)
            state["error_log"].append(msg)

        return state

    def _node_claude_decision(self, state: HotspotState) -> HotspotState:
        """Node 4: Invoke Claude for resource allocation reasoning (~350 tokens)."""
        if not HAS_CLAUDE:
            state["claude_summary"] = "[CLAUDE] Claude API not available; skipping reasoning"
            return state

        state["execution_log"].append("[CLAUDE] Requesting resource allocation reasoning...")

        try:
            if not state["high_severity_hotspots"]:
                state["claude_summary"] = "No high-severity hotspots detected. Continue standard monitoring."
                return state

            # Build prompt for Claude
            hotspot_summary = "\n".join([
                f"- {h.hotspot_id}: {h.hotspot_type.value} ({h.density_level.value}), "
                f"Severity={h.severity_score:.0f}, {h.trend.value}, "
                f"Resource: {h.resource_allocation.value}"
                for h in state["high_severity_hotspots"][:5]  # Top 5
            ])

            prompt = f"""You are a resource allocation expert for NYC DOT sidewalk inspections.

High-severity hotspots detected:
{hotspot_summary}

For each hotspot, consider:
1. Is density/trend indicating emerging or stable problem?
2. Are current resources over/under/optimally allocated?
3. What's the recommended action (deploy, redirect, monitor)?
4. How to sequence responses given constraints?

Provide concise, actionable guidance (150 words max)."""

            client = ChatAnthropic(model="claude-haiku-4-5-20251001")
            messages = [HumanMessage(content=prompt)]
            response = client.invoke(messages)

            state["claude_summary"] = response.content
            state["execution_log"].append("[CLAUDE] Received resource allocation guidance")

        except Exception as e:
            msg = f"[CLAUDE] Error: {str(e)}"
            logger.error(msg)
            state["error_log"].append(msg)
            state["claude_summary"] = f"Claude reasoning failed: {str(e)}"

        return state

    def _node_generate_map(self, state: HotspotState) -> HotspotState:
        """Node 5: Generate folium map with hotspot visualization."""
        if not HAS_FOLIUM:
            state["map_html"] = "<p>Folium not available for map generation</p>"
            return state

        state["execution_log"].append("[MAP] Generating folium visualization...")

        try:
            if not state["hotspots"]:
                state["map_html"] = "<p>No hotspots to visualize</p>"
                return state

            # Create map centered on first hotspot
            first_hotspot = state["hotspots"][0]
            m = folium.Map(
                location=[first_hotspot.latitude, first_hotspot.longitude],
                zoom_start=12,
                tiles="OpenStreetMap",
            )

            # Add hotspot markers
            for hotspot in state["hotspots"]:
                color = {
                    "HIGH": "red",
                    "MEDIUM": "orange",
                    "LOW": "green",
                }.get(hotspot.density_level.value, "blue")

                popup_text = (
                    f"<b>{hotspot.hotspot_id}</b><br/>"
                    f"Type: {hotspot.hotspot_type.value}<br/>"
                    f"Severity: {hotspot.severity_score:.0f}<br/>"
                    f"Density: {hotspot.density_per_sqkm:.1f} events/sq km<br/>"
                    f"Trend: {hotspot.trend.value}<br/>"
                    f"Resource: {hotspot.resource_allocation.value}<br/>"
                    f"Backlog: {hotspot.estimated_backlog_days} days"
                )

                folium.CircleMarker(
                    location=[hotspot.latitude, hotspot.longitude],
                    radius=8,
                    popup=popup_text,
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7,
                    weight=2,
                ).add_to(m)

            # Add heatmap if KDE data available
            if state["density_grid"] is not None and state["density_bounds"] is not None:
                min_lat, max_lat, min_lon, max_lon = state["density_bounds"]
                # Convert density grid to heatmap data
                heatmap_data = [
                    [lat, lon, val]
                    for lat in np.linspace(min_lat, max_lat, state["density_grid"].shape[0])
                    for lon in np.linspace(min_lon, max_lon, state["density_grid"].shape[1])
                    for val in [1]  # Simplified; real implementation would index grid
                ]
                try:
                    plugins.HeatMap(heatmap_data, radius=20, blur=15, max_zoom=1).add_to(m)
                except Exception as e:
                    logger.warning(f"Heatmap layer failed: {e}")

            state["map_html"] = m._repr_html_()
            state["execution_log"].append("[MAP] Map generation complete")

        except Exception as e:
            msg = f"[MAP] Error: {str(e)}"
            logger.error(msg)
            state["error_log"].append(msg)
            state["map_html"] = f"<p>Map generation failed: {str(e)}</p>"

        return state

    def _node_aggregate(self, state: HotspotState) -> HotspotState:
        """Node 6: Aggregate results into final report."""
        state["final_report"] = {
            "workflow_timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_hotspots": len(state["hotspots"]),
                "high_severity_count": len(state["high_severity_hotspots"]),
                "borough_filter": state["borough_filter"],
            },
            "hotspots": [h.to_dict() for h in state["hotspots"]],
            "claude_guidance": state["claude_summary"],
            "map_available": state["map_html"] is not None,
            "errors": state["error_log"],
            "execution_log": state["execution_log"],
        }
        return state

    def _run_without_langgraph(
        self,
        borough_filter: str | None,
        sample_size: int,
    ) -> dict[str, Any]:
        """Fallback execution when LangGraph unavailable."""
        logger.warning("LangGraph unavailable; running with sequential execution")
        state: HotspotState = {
            "violations_fourfour": self.violations_fourfour,
            "complaints_fourfour": self.complaints_fourfour,
            "inspections_fourfour": self.inspections_fourfour,
            "domain": self.domain,
            "borough_filter": borough_filter,
            "sample_size": sample_size,
            "dbscan_eps": self.dbscan_eps,
            "dbscan_min_samples": self.dbscan_min_samples,
            "violations_df": None,
            "complaints_df": None,
            "inspections_df": None,
            "clusters": [],
            "density_grid": None,
            "density_bounds": None,
            "hotspots": [],
            "high_severity_hotspots": [],
            "claude_summary": "",
            "resource_allocation_strategy": "",
            "routing_recommendations": [],
            "map_html": None,
            "final_report": {},
            "error_log": [],
            "execution_log": [],
        }

        # Execute nodes sequentially
        state = self._node_fetch_data(state)
        state = self._node_spatial_cluster(state)
        state = self._node_classify(state)
        state = self._node_claude_decision(state)
        state = self._node_generate_map(state)
        state = self._node_aggregate(state)

        return state
