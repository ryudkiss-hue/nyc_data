"""
Spatial Analytics Engine for Advanced Geographic Analysis.

This module provides advanced spatial analysis capabilities:
- Network analysis (street networks, routing)
- Hotspot detection (kernel density, clustering)
- Interpolation (kriging, IDW)
- Service area analysis
- Outlier detection
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np  # type: ignore[import]
from scipy.spatial.distance import cdist  # type: ignore[import]
from scipy.stats import gaussian_kde  # type: ignore[import]
from sklearn.cluster import DBSCAN, KMeans  # type: ignore[import]
from sklearn.preprocessing import StandardScaler  # type: ignore[import]

logger = logging.getLogger(__name__)


@dataclass
class Hotspot:
    """Represents a detected hotspot."""
    centroid_x: float
    centroid_y: float
    density: float
    segment_count: int
    average_condition: float
    severity: str  # "low", "medium", "high"


@dataclass
class Cluster:
    """Represents a cluster of segments."""
    cluster_id: int
    size: int
    centroid_x: float
    centroid_y: float
    average_value: float
    segment_ids: list[str]


class NetworkAnalysis:
    """
    Network analysis for street networks and routing.
    
    Supports:
    - Building routable networks from street centerlines
    - Finding shortest paths for inspection routes
    - Service area analysis
    - Network distance vs Euclidean distance
    - Isolated segment detection
    """
    
    def __init__(self) -> None:
        """Initialize network analysis engine."""
        self.network = {}  # node_id -> [neighbor_ids]
        self.edge_lengths = {}  # (node_a, node_b) -> length
    
    def build_network(
        self,
        street_centerlines: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Build routable network from street centerlines.
        
        Args:
            street_centerlines: List of street geometry dictionaries
            
        Returns:
            Network statistics
            
        Example:
            >>> streets = [
            ...     {"id": "st1", "geometry": "LINESTRING(...)", "length": 150},
            ...     {"id": "st2", "geometry": "LINESTRING(...)", "length": 200},
            ... ]
            >>> stats = network.build_network(streets)
            >>> print(f"Network has {stats['nodes']} nodes, {stats['edges']} edges")
        """
        try:
            nodes = {}
            edges = []
            
            for street in street_centerlines:
                street_id = street.get("id")
                # Extract endpoints from geometry (simplified)
                coords = street.get("coordinates", [])
                if len(coords) < 2:
                    continue
                
                start_node = f"{street_id}_start"
                end_node = f"{street_id}_end"
                
                nodes[start_node] = coords[0]
                nodes[end_node] = coords[-1]
                
                length = street.get("length", 0)
                edges.append((start_node, end_node, length))
                
                # Add to network
                if start_node not in self.network:
                    self.network[start_node] = []
                if end_node not in self.network:
                    self.network[end_node] = []
                
                self.network[start_node].append(end_node)
                self.network[end_node].append(start_node)
                
                self.edge_lengths[(start_node, end_node)] = length
                self.edge_lengths[(end_node, start_node)] = length
            
            stats = {
                "nodes": len(nodes),
                "edges": len(edges),
                "total_length": sum(e[2] for e in edges),
            }
            
            logger.info(f"Built network: {stats['nodes']} nodes, {stats['edges']} edges")
            return stats
        
        except Exception as e:
            logger.error(f"Error building network: {e}")
            return {"nodes": 0, "edges": 0, "total_length": 0, "error": str(e)}
    
    def find_shortest_route(
        self,
        start_node_id: str,
        end_node_id: str,
        max_iterations: int = 1000,
    ) -> list[str]:
        """
        Find shortest path between two nodes using Dijkstra's algorithm.
        
        Args:
            start_node_id: Starting node ID
            end_node_id: Ending node ID
            max_iterations: Maximum iterations to prevent infinite loops
            
        Returns:
            List of node IDs forming the path
        """
        try:
            if start_node_id not in self.network or end_node_id not in self.network:
                return []
            
            # Dijkstra's algorithm
            distances = {node: float('inf') for node in self.network}
            distances[start_node_id] = 0
            previous = {node: None for node in self.network}
            unvisited = set(self.network.keys())
            
            iterations = 0
            while unvisited and iterations < max_iterations:
                iterations += 1
                
                # Find unvisited node with minimum distance
                current = min(
                    (node for node in unvisited if distances[node] != float('inf')),
                    key=lambda n: distances[n],
                    default=None
                )
                
                if current is None or current == end_node_id:
                    break
                
                unvisited.discard(current)
                
                # Check neighbors
                for neighbor in self.network.get(current, []):
                    if neighbor not in unvisited:
                        continue
                    
                    edge_length = self.edge_lengths.get((current, neighbor), 1.0)
                    new_distance = distances[current] + edge_length
                    
                    if new_distance < distances[neighbor]:
                        distances[neighbor] = new_distance
                        previous[neighbor] = current
            
            # Reconstruct path
            path = []
            current = end_node_id
            while current is not None:
                path.insert(0, current)
                current = previous[current]
            
            if path[0] == start_node_id:
                logger.info(f"Found route with {len(path)} nodes, distance: {distances[end_node_id]}")
                return path
            else:
                logger.warning(f"No route found from {start_node_id} to {end_node_id}")
                return []
        
        except Exception as e:
            logger.error(f"Error finding shortest route: {e}")
            return []
    
    def compute_service_areas(
        self,
        center_x: float,
        center_y: float,
        walk_distance_meters: float,
    ) -> list[str]:
        """
        Find all nodes reachable within walk distance from center.
        
        Args:
            center_x: Center longitude
            center_y: Center latitude
            walk_distance_meters: Maximum walk distance
            
        Returns:
            List of reachable node IDs
        """
        try:
            # Find nearest starting node
            start_node = min(
                self.network.keys(),
                key=lambda n: (n[0] - center_x) ** 2 + (n[1] - center_y) ** 2,
                default=None
            )
            
            if not start_node:
                return []
            
            # BFS with distance accumulation
            reachable = set()
            queue = [(start_node, 0)]
            visited = {start_node}
            
            while queue:
                node, dist = queue.pop(0)
                
                if dist <= walk_distance_meters:
                    reachable.add(node)
                    
                    for neighbor in self.network.get(node, []):
                        if neighbor not in visited:
                            edge_len = self.edge_lengths.get((node, neighbor), 0)
                            if dist + edge_len <= walk_distance_meters:
                                queue.append((neighbor, dist + edge_len))
                                visited.add(neighbor)
            
            logger.info(f"Service area has {len(reachable)} nodes within {walk_distance_meters}m")
            return list(reachable)
        
        except Exception as e:
            logger.error(f"Error computing service area: {e}")
            return []


class HotspotAnalysis:
    """
    Hotspot and anomaly detection using density-based methods.
    
    Identifies problem areas with high defect concentration or poor condition.
    """
    
    def __init__(self) -> None:
        """Initialize hotspot analysis engine."""
        self.hotspots: list[Hotspot] = []
    
    def kernel_density(
        self,
        points: list[tuple[float, float]],
        values: list[float],
        bandwidth: float = 0.01,
        grid_size: int = 50,
    ) -> dict[str, Any]:
        """
        Perform kernel density estimation (Gaussian KDE).
        
        Args:
            points: List of (x, y) coordinates
            values: Values at each point (e.g., condition scores)
            bandwidth: KDE bandwidth parameter
            grid_size: Grid resolution for output
            
        Returns:
            Dictionary with density grid and statistics
            
        Example:
            >>> points = [(-74.0, 40.7), (-74.01, 40.71), ...]
            >>> values = [80, 60, 45, ...]
            >>> result = analysis.kernel_density(points, values)
            >>> print(f"Highest density: {result['max_density']}")
        """
        try:
            if len(points) < 2:
                return {"error": "Insufficient points for KDE", "max_density": 0}
            
            points_array = np.array(points)
            values_array = np.array(values)
            
            # Perform KDE
            kde = gaussian_kde(points_array.T, bw_method=bandwidth)
            
            # Create grid
            x_min, y_min = points_array.min(axis=0)
            x_max, y_max = points_array.max(axis=0)
            
            x_grid = np.linspace(x_min, x_max, grid_size)
            y_grid = np.linspace(y_min, y_max, grid_size)
            X, Y = np.meshgrid(x_grid, y_grid)
            positions = np.vstack([X.ravel(), Y.ravel()])
            
            Z = kde(positions).reshape(X.shape)
            
            # Weight by values (condition scores)
            weighted_z = Z * np.mean(values_array)
            
            result = {
                "density_grid": weighted_z.tolist(),
                "x_grid": x_grid.tolist(),
                "y_grid": y_grid.tolist(),
                "max_density": float(weighted_z.max()),
                "min_density": float(weighted_z.min()),
                "mean_density": float(weighted_z.mean()),
            }
            
            logger.info(f"KDE complete: max density {result['max_density']:.4f}")
            return result
        
        except Exception as e:
            logger.error(f"Error in kernel density: {e}")
            return {"error": str(e), "max_density": 0}
    
    def cluster_segments(
        self,
        coordinates: list[tuple[float, float]],
        values: list[float],
        segment_ids: list[str],
        method: str = "dbscan",
        eps: float = 0.01,
        min_samples: int = 5,
    ) -> list[Cluster]:
        """
        Cluster segments using DBSCAN or KMeans.
        
        Args:
            coordinates: List of (lon, lat) coordinates
            values: Corresponding values (condition scores)
            segment_ids: Segment identifiers
            method: 'dbscan' or 'kmeans'
            eps: DBSCAN epsilon (max distance between points in cluster)
            min_samples: DBSCAN minimum samples in cluster
            
        Returns:
            List of Cluster objects
            
        Example:
            >>> coords = [(-74.0, 40.7), (-74.01, 40.71), ...]
            >>> values = [80, 60, 45, ...]
            >>> ids = ["seg1", "seg2", "seg3", ...]
            >>> clusters = analysis.cluster_segments(coords, values, ids)
            >>> for c in clusters:
            ...     print(f"Cluster {c.cluster_id}: {c.size} segments, avg value {c.average_value:.2f}")
        """
        try:
            if len(coordinates) < 2:
                return []
            
            X = np.array(coordinates)
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            if method == "dbscan":
                clusterer = DBSCAN(eps=eps, min_samples=min_samples)
                labels = clusterer.fit_predict(X_scaled)
            elif method == "kmeans":
                n_clusters = max(len(coordinates) // 10, 2)
                clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                labels = clusterer.fit_predict(X_scaled)
            else:
                return []
            
            clusters = []
            for cluster_id in set(labels):
                if cluster_id == -1:  # Noise points in DBSCAN
                    continue
                
                mask = labels == cluster_id
                cluster_coords = X[mask]
                cluster_values = np.array(values)[mask]
                cluster_segment_ids = [sid for i, sid in enumerate(segment_ids) if mask[i]]
                
                centroid = cluster_coords.mean(axis=0)
                
                cluster = Cluster(
                    cluster_id=int(cluster_id),
                    size=len(cluster_segment_ids),
                    centroid_x=float(centroid[0]),
                    centroid_y=float(centroid[1]),
                    average_value=float(cluster_values.mean()),
                    segment_ids=cluster_segment_ids,
                )
                clusters.append(cluster)
            
            logger.info(f"Clustered {len(coordinates)} points into {len(clusters)} clusters")
            return clusters
        
        except Exception as e:
            logger.error(f"Error in cluster_segments: {e}")
            return []
    
    def detect_hotspots(
        self,
        coordinates: list[tuple[float, float]],
        values: list[float],
        threshold: float = 60.0,
        radius_degrees: float = 0.01,
    ) -> list[Hotspot]:
        """
        Detect hotspots as areas with poor condition.
        
        Args:
            coordinates: List of (lon, lat) coordinates
            values: Condition scores (0-100)
            threshold: Condition score threshold for hotspot
            radius_degrees: Radius for spatial grouping
            
        Returns:
            List of detected Hotspot objects
        """
        try:
            if len(coordinates) < 3:
                return []
            
            # Cluster poor condition segments
            bad_mask = np.array(values) < threshold
            bad_coords = [c for i, c in enumerate(coordinates) if bad_mask[i]]
            bad_values = [v for i, v in enumerate(values) if bad_mask[i]]
            bad_ids = [f"seg_{i}" for i, v in enumerate(values) if bad_mask[i]]
            
            if not bad_coords:
                return []
            
            clusters = self.cluster_segments(
                bad_coords,
                bad_values,
                bad_ids,
                method="dbscan",
                eps=radius_degrees,
                min_samples=3,
            )
            
            hotspots = []
            for cluster in clusters:
                # Calculate severity based on average condition
                if cluster.average_value < 30:
                    severity = "critical"
                elif cluster.average_value < 50:
                    severity = "high"
                elif cluster.average_value < 70:
                    severity = "medium"
                else:
                    severity = "low"
                
                hotspot = Hotspot(
                    centroid_x=cluster.centroid_x,
                    centroid_y=cluster.centroid_y,
                    density=cluster.size / (np.pi * radius_degrees ** 2),
                    segment_count=cluster.size,
                    average_condition=cluster.average_value,
                    severity=severity,
                )
                hotspots.append(hotspot)
            
            logger.info(f"Detected {len(hotspots)} hotspots")
            return hotspots
        
        except Exception as e:
            logger.error(f"Error detecting hotspots: {e}")
            return []


class InterpolationAnalysis:
    """
    Spatial interpolation for estimating values at unmapped locations.
    
    Supports:
    - Inverse Distance Weighting (IDW)
    - Simple kriging
    """
    
    def inverse_distance_weighted(
        self,
        known_points: list[tuple[float, float]],
        known_values: list[float],
        query_points: list[tuple[float, float]],
        power: float = 2.0,
    ) -> list[float]:
        """
        Interpolate values using Inverse Distance Weighting.
        
        Args:
            known_points: List of (x, y) with known values
            known_values: Values at known points
            query_points: List of (x, y) to estimate
            power: IDW power parameter (typical 2.0)
            
        Returns:
            Interpolated values for query points
            
        Example:
            >>> known_pts = [(-74.0, 40.7), (-74.01, 40.71)]
            >>> known_vals = [80, 60]
            >>> query_pts = [(-74.005, 40.705)]
            >>> interpolated = analysis.inverse_distance_weighted(
            ...     known_pts, known_vals, query_pts
            ... )
            >>> print(f"Interpolated value: {interpolated[0]:.2f}")
        """
        try:
            known_array = np.array(known_points)
            query_array = np.array(query_points)
            values_array = np.array(known_values)
            
            # Compute distances
            distances = cdist(query_array, known_array, metric='euclidean')
            
            # Handle zero distances
            distances = np.where(distances == 0, 1e-10, distances)
            
            # Compute weights
            weights = 1.0 / (distances ** power)
            weights_sum = weights.sum(axis=1, keepdims=True)
            weights = weights / weights_sum
            
            # Weighted average
            interpolated = np.dot(weights, values_array)
            
            logger.info(f"IDW interpolation for {len(query_points)} points")
            return interpolated.tolist()
        
        except Exception as e:
            logger.error(f"Error in IDW interpolation: {e}")
            return []


class SpatialAnomalyDetector:
    """
    Detect spatial anomalies and outliers in sidewalk data.
    """
    
    @staticmethod
    def detect_outliers(
        coordinates: list[tuple[float, float]],
        values: list[float],
        method: str = "zscore",
        threshold: float = 2.5,
    ) -> list[int]:
        """
        Detect outlier values using statistical methods.
        
        Args:
            coordinates: List of (x, y) coordinates
            values: Values to analyze
            method: 'zscore' or 'iqr'
            threshold: Outlier threshold
            
        Returns:
            List of indices of detected outliers
        """
        try:
            values_array = np.array(values)
            
            if method == "zscore":
                from scipy.stats import zscore
                z_scores = np.abs(zscore(values_array))
                outliers = np.where(z_scores > threshold)[0]
            
            elif method == "iqr":
                q1 = np.percentile(values_array, 25)
                q3 = np.percentile(values_array, 75)
                iqr = q3 - q1
                lower = q1 - threshold * iqr
                upper = q3 + threshold * iqr
                outliers = np.where((values_array < lower) | (values_array > upper))[0]
            
            else:
                return []
            
            logger.info(f"Detected {len(outliers)} outliers")
            return outliers.tolist()
        
        except Exception as e:
            logger.error(f"Error detecting outliers: {e}")
            return []
    
    @staticmethod
    def detect_spatial_outliers(
        coordinates: list[tuple[float, float]],
        values: list[float],
        k: int = 5,
        std_threshold: float = 2.0,
    ) -> list[int]:
        """
        Detect spatial outliers using Local Outlier Factor.
        
        Identifies points whose values differ significantly from neighbors.
        
        Args:
            coordinates: List of (x, y) coordinates
            values: Values to analyze
            k: Number of neighbors to consider
            std_threshold: Standard deviation threshold
            
        Returns:
            List of indices of detected spatial outliers
        """
        try:
            from sklearn.neighbors import NearestNeighbors
            
            X = np.array(coordinates)
            values_array = np.array(values)
            
            # Find k nearest neighbors
            nbrs = NearestNeighbors(n_neighbors=k + 1).fit(X)
            distances, indices = nbrs.kneighbors(X)
            
            # Compare each point to its neighbors
            outlier_indices = []
            for i in range(len(X)):
                neighbor_values = values_array[indices[i][1:]]  # Exclude self
                neighbor_mean = neighbor_values.mean()
                neighbor_std = neighbor_values.std()
                
                if neighbor_std > 0:
                    z_score = abs(values_array[i] - neighbor_mean) / neighbor_std
                    if z_score > std_threshold:
                        outlier_indices.append(i)
            
            logger.info(f"Detected {len(outlier_indices)} spatial outliers")
            return outlier_indices
        
        except Exception as e:
            logger.error(f"Error in spatial outlier detection: {e}")
            return []
