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

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np  # type: ignore[import]
from scipy.spatial.distance import cdist  # type: ignore[import]
from scipy.stats import gaussian_kde  # type: ignore[import]
from sklearn.cluster import DBSCAN, KMeans  # type: ignore[import]
from sklearn.preprocessing import StandardScaler  # type: ignore[import]

logger = logging.getLogger(__name__)

# Optional-dependency guards for the conflict engine. ``numpy``, ``scipy`` and
# ``sklearn`` are required to import this module today, but we still expose the
# HAS_* flags so callers can branch defensively and so the conflict helpers
# below degrade gracefully if the import surface ever changes.
try:
    import numpy as _np  # noqa: F401

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from sklearn.cluster import DBSCAN as _DBSCAN  # noqa: F401

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import geopandas as gpd  # type: ignore[import]
    from shapely.geometry import Point  # type: ignore[import]

    HAS_GEOPANDAS = True
except ImportError:
    gpd = None  # type: ignore[assignment]
    Point = None  # type: ignore[assignment,misc]
    HAS_GEOPANDAS = False

# Metric CRS for NYC: NY State Plane Long Island zone (US survey feet).
# Buffering/distance in this CRS yields feet; we convert metres accordingly.
METRIC_CRS = "EPSG:2263"
_FEET_PER_METER = 3.28084


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

from ..governance.equity import EquityScorer

    def detect_hotspots(
        self,
        coordinates: list[tuple[float, float]],
        values: list[float],
        threshold: float = 60.0,
        radius_degrees: float = 0.01,
        apply_equity: bool = True
    ) -> list[Hotspot]:
        """
        Detect hotspots as areas with poor condition, weighted by equity impact.
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

            equity_scorer = EquityScorer() if apply_equity else None
            hotspots = []
            for cluster in clusters:
                # Calculate base severity
                avg_val = cluster.average_value
                
                # Apply equity multiplier if enabled
                multiplier = 1.0
                if equity_scorer:
                    # heuristic: use centroid to check for priority zones
                    impact = equity_scorer.calculate_impact(pd.Series({"lat": cluster.centroid_y, "lon": cluster.centroid_x}), 1.0)
                    multiplier = impact.equity_multiplier
                
                weighted_severity_score = (100 - avg_val) * multiplier

                if weighted_severity_score > 80: severity = "critical"
                elif weighted_severity_score > 60: severity = "high"
                elif weighted_severity_score > 40: severity = "medium"
                else: severity = "low"

                hotspot = Hotspot(
                    centroid_x=cluster.centroid_x,
                    centroid_y=cluster.centroid_y,
                    density=cluster.size / (np.pi * radius_degrees ** 2),
                    segment_count=cluster.size,
                    average_condition=avg_val,
                    severity=severity,
                )
                hotspots.append(hotspot)

            logger.info(f"Detected {len(hotspots)} hotspots (Equity-Weighting: {apply_equity})")
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


# ── Spatial Conflict Engine ─────────────────────────────────────────────────
#
# GeoPandas-backed helpers used by NYC DOT analysts to flag conflicts between
# sidewalk inspections and active permits, score their severity, find missing
# accessible-route ramps, and surface conflict hotspots. All functions guard
# their optional dependencies and degrade gracefully when they are absent.

# Default permit-type severity weights (0-1). Construction/excavation work
# poses the greatest conflict risk to a sidewalk inspection.
_PERMIT_TYPE_WEIGHTS = {
    "excavation": 1.0,
    "construction": 0.9,
    "demolition": 0.9,
    "building": 0.7,
    "street opening": 0.8,
    "sidewalk": 0.6,
    "occupancy": 0.4,
    "event": 0.3,
}

# Inspection-priority weights (0-1).
_PRIORITY_WEIGHTS = {
    "critical": 1.0,
    "emergency": 1.0,
    "high": 0.8,
    "medium": 0.5,
    "low": 0.2,
    "routine": 0.2,
}


def _empty_geodataframe():
    """Return an empty GeoDataFrame (WGS84) or None if geopandas is missing."""
    if not HAS_GEOPANDAS:
        return None
    return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")


def detect_conflicts(gdf_inspections, gdf_permits, buffer_m: float = 100):
    """Find inspections whose buffered footprint overlaps permit areas.

    Geometries are reprojected to a metric CRS (``EPSG:2263`` NY State Plane,
    feet), each inspection is buffered by ``buffer_m`` metres, and the buffers
    are spatially joined against the permits. A ``dist`` column holds the
    centroid-to-centroid distance in metres between each matched pair.

    Args:
        gdf_inspections: GeoDataFrame of inspection geometries.
        gdf_permits: GeoDataFrame of permit geometries.
        buffer_m: Buffer radius around each inspection, in metres.

    Returns:
        GeoDataFrame of conflicting pairs in WGS84 with a ``dist`` column, or
        an empty GeoDataFrame when there are no matches. Returns ``None`` if
        geopandas is unavailable.
    """
    if not HAS_GEOPANDAS:
        logger.warning("detect_conflicts: geopandas not installed")
        return None
    if gdf_inspections is None or gdf_permits is None:
        return _empty_geodataframe()
    if len(gdf_inspections) == 0 or len(gdf_permits) == 0:
        return _empty_geodataframe()

    try:
        insp = gdf_inspections.copy()
        perm = gdf_permits.copy()
        if insp.crs is None:
            insp = insp.set_crs("EPSG:4326")
        if perm.crs is None:
            perm = perm.set_crs("EPSG:4326")

        insp_m = insp.to_crs(METRIC_CRS)
        perm_m = perm.to_crs(METRIC_CRS)

        # Keep original (point) centroids before buffering to compute distance.
        insp_centroids = insp_m.geometry.centroid
        buffer_ft = buffer_m * _FEET_PER_METER
        insp_m = insp_m.assign(geometry=insp_m.geometry.buffer(buffer_ft))

        matches = gpd.sjoin(
            insp_m, perm_m, how="inner", predicate="intersects"
        )
        if len(matches) == 0:
            return _empty_geodataframe()

        # Distance (metres) from inspection centroid to matched permit centroid.
        right_index = matches["index_right"].to_numpy()
        perm_centroids = perm_m.geometry.centroid
        left_centroids = insp_centroids.loc[matches.index]
        right_centroids = perm_centroids.iloc[
            perm_m.index.get_indexer(right_index)
        ]
        dist_ft = left_centroids.reset_index(drop=True).distance(
            right_centroids.reset_index(drop=True)
        )
        matches = matches.assign(dist=(dist_ft.to_numpy() / _FEET_PER_METER))

        return matches.to_crs("EPSG:4326")
    except Exception as exc:  # noqa: BLE001 - degrade gracefully for analysts
        logger.error("detect_conflicts failed: %s", exc)
        return _empty_geodataframe()


def spatial_conflict_score(
    gdf,
    *,
    dist_col: str = "dist",
    permit_type_col: str = "permit_type",
    priority_col: str = "priority",
    buffer_m: float = 100,
):
    """Add a composite ``conflict_score`` (0-100) severity column.

    The score blends three weighted components:

    * distance — closer conflicts score higher (linearly within ``buffer_m``);
    * permit type — heavier construction/excavation work scores higher;
    * inspection priority — higher-priority inspections score higher.

    Missing columns contribute a neutral mid-weight so the function never
    fails on partial data.

    Args:
        gdf: Conflict GeoDataFrame (typically from :func:`detect_conflicts`).
        dist_col: Column with conflict distance in metres.
        permit_type_col: Column with the permit type label.
        priority_col: Column with the inspection priority label.
        buffer_m: Distance at which the distance weight reaches zero.

    Returns:
        A copy of ``gdf`` with a ``conflict_score`` column, or the input
        unchanged when dependencies are missing or the frame is empty.
    """
    if not HAS_GEOPANDAS or not HAS_NUMPY:
        logger.warning("spatial_conflict_score: numpy/geopandas not installed")
        return gdf
    if gdf is None or len(gdf) == 0:
        return gdf

    try:
        out = gdf.copy()
        n = len(out)

        # Distance weight: 1.0 at zero distance, 0.0 at >= buffer_m.
        if dist_col in out.columns:
            dist = np.asarray(out[dist_col], dtype="float64")
            dist = np.nan_to_num(dist, nan=buffer_m)
            dist_w = np.clip(1.0 - (dist / float(buffer_m)), 0.0, 1.0)
        else:
            dist_w = np.full(n, 0.5)

        # Permit-type weight.
        if permit_type_col in out.columns:
            perm_w = np.array(
                [
                    _PERMIT_TYPE_WEIGHTS.get(str(v).strip().lower(), 0.5)
                    for v in out[permit_type_col]
                ],
                dtype="float64",
            )
        else:
            perm_w = np.full(n, 0.5)

        # Priority weight.
        if priority_col in out.columns:
            prio_w = np.array(
                [
                    _PRIORITY_WEIGHTS.get(str(v).strip().lower(), 0.5)
                    for v in out[priority_col]
                ],
                dtype="float64",
            )
        else:
            prio_w = np.full(n, 0.5)

        # Weighted blend: distance 50%, permit type 30%, priority 20%.
        score = (0.5 * dist_w + 0.3 * perm_w + 0.2 * prio_w) * 100.0
        out["conflict_score"] = np.clip(score, 0.0, 100.0).round(1)
        return out
    except Exception as exc:  # noqa: BLE001
        logger.error("spatial_conflict_score failed: %s", exc)
        return gdf


def find_ramp_gaps(gdf_ramps, gdf_inspections, threshold_m: float = 50):
    """Identify inspections with no accessible ramp within ``threshold_m``.

    Uses a nearest-neighbour spatial join in a metric CRS to measure the
    distance from each inspection to its closest ramp, then flags those whose
    nearest ramp is farther than ``threshold_m`` metres (accessible-route
    gaps).

    Args:
        gdf_ramps: GeoDataFrame of pedestrian-ramp geometries.
        gdf_inspections: GeoDataFrame of inspection geometries.
        threshold_m: Maximum acceptable distance to a ramp, in metres.

    Returns:
        GeoDataFrame (WGS84) of gap inspections with a ``ramp_dist`` column
        (metres to nearest ramp), or an empty GeoDataFrame. ``None`` if
        geopandas is unavailable.
    """
    if not HAS_GEOPANDAS:
        logger.warning("find_ramp_gaps: geopandas not installed")
        return None
    if gdf_inspections is None or len(gdf_inspections) == 0:
        return _empty_geodataframe()

    try:
        insp = gdf_inspections.copy()
        if insp.crs is None:
            insp = insp.set_crs("EPSG:4326")
        insp_m = insp.to_crs(METRIC_CRS)

        # No ramps at all → every inspection is a gap.
        if gdf_ramps is None or len(gdf_ramps) == 0:
            gaps = insp_m.assign(ramp_dist=float("inf"))
            return gaps.to_crs("EPSG:4326")

        ramps = gdf_ramps.copy()
        if ramps.crs is None:
            ramps = ramps.set_crs("EPSG:4326")
        ramps_m = ramps.to_crs(METRIC_CRS)

        joined = gpd.sjoin_nearest(
            insp_m, ramps_m, how="left", distance_col="_ramp_dist_ft"
        )
        # sjoin_nearest can yield duplicate rows on ties; keep the closest.
        joined = joined.sort_values("_ramp_dist_ft").groupby(
            level=0, sort=False
        ).first()
        joined = insp_m.join(joined[["_ramp_dist_ft"]], how="left")
        joined["ramp_dist"] = joined["_ramp_dist_ft"] / _FEET_PER_METER

        threshold_ft = threshold_m * _FEET_PER_METER
        gaps = joined[
            joined["_ramp_dist_ft"].isna()
            | (joined["_ramp_dist_ft"] > threshold_ft)
        ].copy()
        gaps = gaps.drop(columns=["_ramp_dist_ft"])
        return gaps.to_crs("EPSG:4326")
    except Exception as exc:  # noqa: BLE001
        logger.error("find_ramp_gaps failed: %s", exc)
        return _empty_geodataframe()


def moran_i(gdf, col: str, *, max_neighbors: int = 8):
    """Compute global Moran's I spatial autocorrelation for a numeric column.

    Builds a k-nearest-neighbour, row-standardised weights matrix from feature
    centroids using only numpy (no ``esda``/``libpysal`` dependency), then
    evaluates the classic Moran's I statistic. Values near ``+1`` indicate
    clustering, near ``-1`` dispersion, and near the expected value
    ``-1/(n-1)`` randomness.

    Args:
        gdf: GeoDataFrame with point or polygon geometries.
        col: Name of the numeric column to test.
        max_neighbors: Number of nearest neighbours per feature.

    Returns:
        The Moran's I value as a float, or ``None`` when dependencies are
        missing, the column is absent, or there are too few features.
    """
    if not HAS_GEOPANDAS or not HAS_NUMPY:
        logger.warning("moran_i: numpy/geopandas not installed")
        return None
    if gdf is None or col not in getattr(gdf, "columns", []):
        return None
    if len(gdf) < 3:
        return None

    try:
        values = np.asarray(gdf[col], dtype="float64")
        mask = ~np.isnan(values)
        if mask.sum() < 3:
            return None

        sub = gdf.loc[mask]
        values = values[mask]
        centroids = (
            sub.geometry.to_crs(epsg=3857).centroid.to_crs(sub.crs)
            if sub.crs is not None and sub.crs.is_geographic
            else sub.geometry.centroid
        )
        coords = np.column_stack(
            [centroids.x.to_numpy(), centroids.y.to_numpy()]
        )
        n = len(values)

        # Pairwise distances → k-nearest-neighbour binary contiguity.
        diff = coords[:, None, :] - coords[None, :, :]
        dist = np.sqrt((diff ** 2).sum(axis=2))
        np.fill_diagonal(dist, np.inf)

        k = int(min(max_neighbors, n - 1))
        if k < 1:
            return None
        neighbor_idx = np.argsort(dist, axis=1)[:, :k]

        weights = np.zeros((n, n), dtype="float64")
        rows = np.repeat(np.arange(n), k)
        weights[rows, neighbor_idx.ravel()] = 1.0

        # Row-standardise.
        row_sums = weights.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        weights = weights / row_sums

        z = values - values.mean()
        denom = (z ** 2).sum()
        if denom == 0:
            return 0.0
        s0 = weights.sum()
        if s0 == 0:
            return 0.0
        numer = float(z @ weights @ z)
        return (n / s0) * (numer / denom)
    except Exception as exc:  # noqa: BLE001
        logger.error("moran_i failed: %s", exc)
        return None


def cluster_conflict_hotspots(gdf, eps_deg: float = 0.005, min_samples: int = 5):
    """Label conflict-point clusters with DBSCAN on lon/lat coordinates.

    Reduces each feature to its centroid and runs DBSCAN (great-circle
    neighbourhoods approximated in degrees via ``eps_deg``). Noise points are
    labelled ``-1``.

    Args:
        gdf: Conflict GeoDataFrame.
        eps_deg: DBSCAN neighbourhood radius in degrees (~0.005 ≈ 550m).
        min_samples: Minimum points to form a dense cluster.

    Returns:
        A copy of ``gdf`` with an integer ``cluster`` column, or the input
        unchanged when dependencies are missing. Empty inputs gain an empty
        ``cluster`` column.
    """
    if not HAS_GEOPANDAS or not HAS_SKLEARN or not HAS_NUMPY:
        logger.warning("cluster_conflict_hotspots: numpy/sklearn/geopandas not installed")
        return gdf
    if gdf is None:
        return gdf
    if len(gdf) == 0:
        out = gdf.copy()
        out["cluster"] = []
        return out

    try:
        out = gdf.copy()
        work = out
        if work.crs is not None and str(work.crs).upper() not in (
            "EPSG:4326",
            "WGS84",
        ):
            work = work.to_crs("EPSG:4326")
        centroids = (
            work.geometry.to_crs(epsg=3857).centroid.to_crs(work.crs)
            if work.crs is not None and work.crs.is_geographic
            else work.geometry.centroid
        )
        coords = np.column_stack(
            [centroids.x.to_numpy(), centroids.y.to_numpy()]
        )
        labels = DBSCAN(eps=eps_deg, min_samples=min_samples).fit_predict(coords)
        out["cluster"] = labels.astype(int)
        return out
    except Exception as exc:  # noqa: BLE001
        logger.error("cluster_conflict_hotspots failed: %s", exc)
        return gdf
