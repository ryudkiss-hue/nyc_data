"""Clustering Diagnostics Engine — Optimal K Detection & Cluster Quality Metrics.

Addresses the problem of validating sidewalk segment clustering without manual assessment.
Provides elbow curve detection, silhouette analysis, and quality metrics (Davies-Bouldin,
Calinski-Harabasz) to help determine optimal cluster count (k).

Example::

    from socrata_toolkit.analysis.clustering_diagnostics import ClusteringDiagnostics
    import pandas as pd

    df = pd.DataFrame({
        'violation_count': [5, 12, 3, 8],
        'repair_cost': [1000, 4500, 800, 2200],
        'population_density': [100, 250, 80, 180],
    })

    diag = ClusteringDiagnostics(df)
    results = diag.diagnose(max_k=8)
    print(f"Optimal k: {results['optimal_k']}")  # {optimal_k: 4, ...}
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

__all__ = [
    "ClusteringDiagnostics",
    "ElbowAnalyzer",
    "SilhouetteAnalyzer",
]

def _get_sklearn():
    """Lazy import sklearn to handle optional dependency."""
    try:
        from sklearn.cluster import KMeans
        from sklearn.metrics import (
            calinski_harabasz_score,
            davies_bouldin_score,
            silhouette_samples,
            silhouette_score,
        )
        from sklearn.preprocessing import StandardScaler

        return {
            "KMeans": KMeans,
            "calinski_harabasz_score": calinski_harabasz_score,
            "davies_bouldin_score": davies_bouldin_score,
            "silhouette_samples": silhouette_samples,
            "silhouette_score": silhouette_score,
            "StandardScaler": StandardScaler,
        }
    except ImportError as exc:
        raise ImportError(
            "Install scikit-learn: pip install scikit-learn"
        ) from exc

class ElbowAnalyzer:
    """Detect elbow point in inertia curve using slope-based method."""

    @staticmethod
    def find_elbow(inertias: list[float], k_range: list[int]) -> int:
        """Find elbow (optimal k) using second derivative method.

        Args:
            inertias: List of inertia values (one per k)
            k_range: Corresponding k values (e.g., [2, 3, 4, ...])

        Returns:
            Optimal k (elbow point), or fallback to k=3 if detection fails.

        Algorithm:
            1. Compute first derivative (slope between points)
            2. Compute second derivative (change in slope)
            3. Elbow is where second derivative changes most sharply
        """
        if len(inertias) < 3:
            return k_range[0] if k_range else 2

        inertias = np.array(inertias)
        # First derivative
        d1 = np.diff(inertias)
        # Second derivative
        d2 = np.diff(d1)

        # Elbow is where second derivative is minimized (most negative slope change)
        if len(d2) > 0:
            elbow_idx = np.argmin(d2) + 1  # +1 because diff reduces length
            elbow_idx = min(elbow_idx, len(k_range) - 1)
            return k_range[elbow_idx]

        return k_range[1] if len(k_range) > 1 else k_range[0]

    @staticmethod
    def compute_inertias(
        X: np.ndarray, k_range: list[int], random_state: int = 42
    ) -> tuple[list[float], list[np.ndarray]]:
        """Fit KMeans for each k and return inertias + labels.

        Args:
            X: Feature matrix (n_samples, n_features)
            k_range: List of k values to test (e.g., [2, 3, 4, ...])
            random_state: Random seed for reproducibility

        Returns:
            Tuple of (inertias, labels_list) where:
            - inertias: Inertia value for each k
            - labels_list: Cluster labels for each k
        """
        sklearn_dict = _get_sklearn()
        KMeans = sklearn_dict["KMeans"]

        inertias = []
        labels_list = []

        for k in k_range:
            model = KMeans(n_clusters=k, n_init=10, random_state=random_state)
            labels = model.fit_predict(X)
            inertias.append(float(model.inertia_))
            labels_list.append(labels)

        return inertias, labels_list

class SilhouetteAnalyzer:
    """Compute silhouette coefficients and quality metrics."""

    @staticmethod
    def compute_silhouette_scores(
        X: np.ndarray, labels: np.ndarray
    ) -> tuple[float, np.ndarray]:
        """Compute per-sample and mean silhouette scores.

        Args:
            X: Feature matrix (n_samples, n_features)
            labels: Cluster assignments (n_samples,)

        Returns:
            Tuple of (mean_score, sample_scores) where:
            - mean_score: Average silhouette coefficient
            - sample_scores: Per-sample coefficients
        """
        sklearn_dict = _get_sklearn()
        silhouette_score = sklearn_dict["silhouette_score"]
        silhouette_samples = sklearn_dict["silhouette_samples"]

        mean_score = float(silhouette_score(X, labels))
        sample_scores = silhouette_samples(X, labels)

        return mean_score, sample_scores

    @staticmethod
    def compute_quality_metrics(
        X: np.ndarray, labels: np.ndarray
    ) -> dict[str, float]:
        """Compute Davies-Bouldin and Calinski-Harabasz indices.

        Args:
            X: Feature matrix (n_samples, n_features)
            labels: Cluster assignments (n_samples,)

        Returns:
            Dict with keys:
            - davies_bouldin: Davies-Bouldin Index (lower is better, 0-1 range ideal)
            - calinski_harabasz: Calinski-Harabasz Index (higher is better)
        """
        sklearn_dict = _get_sklearn()
        davies_bouldin_score = sklearn_dict["davies_bouldin_score"]
        calinski_harabasz_score = sklearn_dict["calinski_harabasz_score"]

        # Handle edge cases
        if len(np.unique(labels)) <= 1:
            return {"davies_bouldin": np.nan, "calinski_harabasz": np.nan}

        db = float(davies_bouldin_score(X, labels))
        ch = float(calinski_harabasz_score(X, labels))

        return {"davies_bouldin": db, "calinski_harabasz": ch}

class ClusteringDiagnostics:
    """Full clustering analysis pipeline: elbow detection + silhouette + quality metrics.

    Attributes:
        X: Scaled feature matrix
        X_orig: Original feature matrix (before scaling)
        feature_names: List of feature names
        optimal_k: Detected optimal cluster count
        results: Dict containing all diagnostic metrics
    """

    def __init__(
        self,
        df: pd.DataFrame,
        feature_cols: list[str] | None = None,
        random_state: int = 42,
    ):
        """Initialize clustering diagnostics with data.

        Args:
            df: Input DataFrame with features for clustering
            feature_cols: Columns to use for clustering. If None, uses all numeric columns.
            random_state: Random seed for reproducibility
        """
        self.df = df.copy()
        self.random_state = random_state
        self.optimal_k = None
        self.results = {}

        # Select features
        if feature_cols is None:
            feature_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        self.feature_cols = feature_cols

        # Extract and scale features
        sklearn_dict = _get_sklearn()
        StandardScaler = sklearn_dict["StandardScaler"]

        self.X_orig = df[feature_cols].values
        scaler = StandardScaler()
        self.X = scaler.fit_transform(self.X_orig)
        self.feature_names = feature_cols

    def diagnose(
        self,
        max_k: int = 10,
        min_k: int = 2,
    ) -> dict[str, Any]:
        """Run full clustering diagnosis.

        Args:
            max_k: Maximum k to test (default 10)
            min_k: Minimum k to test (default 2)

        Returns:
            Dict with keys:
            - optimal_k: Detected optimal cluster count
            - inertias: List of inertia values for each k
            - silhouette_scores: Mean silhouette score for each k
            - elbow_curve_data: {k, inertia} pairs for plotting
            - quality_metrics_by_k: {k: {davies_bouldin, calinski_harabasz}}
            - cluster_profiles: DataFrame with mean feature values per cluster
            - labels: Cluster assignments for optimal_k
        """
        k_range = list(range(min_k, max_k + 1))

        # Compute inertias
        inertias, labels_list = ElbowAnalyzer.compute_inertias(
            self.X, k_range, self.random_state
        )

        # Find elbow
        self.optimal_k = ElbowAnalyzer.find_elbow(inertias, k_range)

        # Compute silhouette scores and quality metrics
        silhouette_scores = []
        quality_metrics_by_k = {}

        for k, labels in zip(k_range, labels_list):
            mean_sil, _ = SilhouetteAnalyzer.compute_silhouette_scores(self.X, labels)
            silhouette_scores.append(mean_sil)

            quality = SilhouetteAnalyzer.compute_quality_metrics(self.X, labels)
            quality_metrics_by_k[k] = quality

        # Compute cluster profiles for optimal k
        optimal_idx = self.optimal_k - min_k
        optimal_labels = labels_list[optimal_idx]

        cluster_profiles = self._compute_cluster_profiles(optimal_labels)

        self.results = {
            "optimal_k": self.optimal_k,
            "inertias": inertias,
            "silhouette_scores": silhouette_scores,
            "elbow_curve_data": [
                {"k": k, "inertia": inertia}
                for k, inertia in zip(k_range, inertias)
            ],
            "quality_metrics_by_k": quality_metrics_by_k,
            "cluster_profiles": cluster_profiles,
            "labels": optimal_labels,
            "k_range": k_range,
        }

        return self.results

    def _compute_cluster_profiles(self, labels: np.ndarray) -> pd.DataFrame:
        """Compute mean feature values per cluster.

        Args:
            labels: Cluster assignments

        Returns:
            DataFrame with clusters as columns and features as rows
        """
        profiles = {}
        for cluster_id in np.unique(labels):
            mask = labels == cluster_id
            profiles[f"Cluster_{cluster_id}"] = (
                self.df[self.feature_cols].iloc[mask].mean()
            )

        return pd.DataFrame(profiles)

    def get_elbow_data(self) -> list[dict[str, float]]:
        """Get elbow curve data for visualization.

        Returns:
            List of {k, inertia} dicts
        """
        return self.results.get("elbow_curve_data", [])

    def get_silhouette_data(self, k: int | None = None) -> dict[str, Any]:
        """Get silhouette analysis data for a specific k.

        Args:
            k: Cluster count (default uses optimal_k)

        Returns:
            Dict with silhouette scores, cluster labels, and metrics
        """
        if k is None:
            k = self.optimal_k
        if k is None:
            return {}

        idx = k - min(self.results.get("k_range", [2]))
        labels = None
        if idx >= 0 and idx < len(self.results.get("labels", [])):
            _, labels_list = ElbowAnalyzer.compute_inertias(
                self.X, self.results.get("k_range", [2, 3, 4, 5, 6, 7, 8, 9, 10])
            )
            if idx < len(labels_list):
                labels = labels_list[idx]

        if labels is None:
            return {}

        mean_sil, sample_sils = SilhouetteAnalyzer.compute_silhouette_scores(
            self.X, labels
        )

        return {
            "labels": labels,
            "silhouette_samples": sample_sils,
            "silhouette_mean": mean_sil,
            "k": k,
        }
