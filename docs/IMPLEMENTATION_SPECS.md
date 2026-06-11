# Implementation Specifications: Phase 1 Analytics Capabilities

---

## OVERVIEW

This document provides detailed implementation templates for the three Phase 1 (Pareto zone) capabilities. Each section includes:
- Module architecture
- Function signatures
- Test harness skeleton
- Integration checkpoints
- Edge case handling

---

## 1. CLUSTERING DIAGNOSTICS ENGINE

### Module Structure

```
src/socrata_toolkit/analysis/clustering.py
  ├── class ClusteringDiagnostics
  │   ├── __init__(df, feature_cols, random_state=42)
  │   ├── fit_range(max_k=10) → (inertias, silhouette_scores, optimal_k)
  │   ├── explain_clusters(k) → cluster_profiles_df, feature_importance
  │   └── diagnose(k=None) → detailed_diagnostics_dict
  └── utility functions
      ├── detect_elbow(inertias, curve='convex') → k_optimal
      ├── validate_inputs(df, feature_cols) → bool
      └── compute_quality_metrics(data, labels) → metrics_dict

src/socrata_toolkit/viz/clustering_viz.py
  ├── plot_elbow_curve(inertias, optimal_k, silhouette_scores) → plotly.Figure
  ├── plot_silhouette(data, labels, k) → plotly.Figure
  ├── plot_quality_heatmap(metrics_dict, max_k) → plotly.Figure
  └── plot_cluster_scatter(data_2d, labels) → plotly.Figure
```

### Core Implementation

```python
# src/socrata_toolkit/analysis/clustering.py

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import (
    davies_bouldin_score,
    silhouette_samples,
    silhouette_score,
    calinski_harabasz_score,
)
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


@dataclass
class ClusteringResult:
    """Immutable result container."""
    optimal_k: int
    inertias: list[float]
    silhouette_scores: list[float]
    quality_metrics: dict[str, float]
    labels: np.ndarray
    cluster_centers: np.ndarray
    cluster_profiles: pd.DataFrame


class ClusteringDiagnostics:
    """
    Comprehensive K-means diagnostics for sidewalk segmentation.
    
    Usage:
        cd = ClusteringDiagnostics(violations_df, feature_cols=['violations', 'cost'])
        result = cd.diagnose(max_k=10)
        print(result.optimal_k)  # e.g., 5
    """
    
    def __init__(
        self,
        df: pd.DataFrame,
        feature_cols: list[str],
        random_state: int = 42,
        verbose: bool = True,
    ):
        """
        Initialize clustering engine.
        
        Args:
            df: Input DataFrame
            feature_cols: Columns to use for clustering (numeric only)
            random_state: Seed for reproducibility
            verbose: Log diagnostic messages
        """
        self.df_orig = df.copy()
        self.feature_cols = feature_cols
        self.random_state = random_state
        self.verbose = verbose
        
        # Validate inputs
        if not self._validate_inputs():
            raise ValueError("Invalid feature columns or data type")
        
        # Preprocess
        self.X = self.df_orig[feature_cols].copy()
        self.X_scaled = self._scale_features()
        
        logger.info(f"ClusteringDiagnostics initialized: n_samples={len(self.X)}, n_features={len(feature_cols)}")
    
    def _validate_inputs(self) -> bool:
        """Check feature columns exist and are numeric."""
        for col in self.feature_cols:
            if col not in self.df_orig.columns:
                logger.error(f"Column '{col}' not found in DataFrame")
                return False
            if not pd.api.types.is_numeric_dtype(self.df_orig[col]):
                logger.error(f"Column '{col}' is not numeric")
                return False
        
        if self.X.isna().any().any():
            logger.warning(f"Dropping {self.X.isna().sum().sum()} NaN values")
            self.X = self.X.dropna()
        
        return len(self.X) > 0
    
    def _scale_features(self) -> np.ndarray:
        """Standardize features to mean=0, std=1."""
        scaler = StandardScaler()
        return scaler.fit_transform(self.X)
    
    def fit_range(self, max_k: int = 10) -> tuple[list, list, int]:
        """
        Fit K-means for k=1..max_k, compute metrics.
        
        Returns:
            (inertias, silhouette_scores, optimal_k)
        """
        inertias = []
        silhouette_scores = []
        
        for k in range(1, max_k + 1):
            kmeans = KMeans(n_clusters=k, n_init=10, random_state=self.random_state)
            kmeans.fit(self.X_scaled)
            inertias.append(kmeans.inertia_)
            
            # Silhouette score only meaningful for k >= 2
            if k >= 2:
                sil_score = silhouette_score(self.X_scaled, kmeans.labels_)
                silhouette_scores.append(sil_score)
            else:
                silhouette_scores.append(0.0)
            
            if self.verbose:
                logger.info(f"k={k}: inertia={inertias[-1]:.2f}, silhouette={silhouette_scores[-1]:.3f}")
        
        # Detect optimal k using elbow method
        optimal_k = self._detect_elbow(inertias, default=3)
        
        return inertias, silhouette_scores, optimal_k
    
    def _detect_elbow(self, inertias: list[float], default: int = 3) -> int:
        """
        Knee detection using simple algorithm (look for max 2nd derivative).
        
        For now, use heuristic: k where inertia reduction < 10% of prior.
        """
        if len(inertias) < 3:
            return default
        
        inertias_arr = np.array(inertias)
        
        # Compute differences
        diffs = np.diff(inertias_arr)
        pct_diffs = np.abs(diffs[1:] / diffs[:-1])  # ratio of consecutive diffs
        
        # Find first k where ratio < 0.1 (diminishing returns)
        for i, ratio in enumerate(pct_diffs):
            if ratio < 0.1:
                optimal_k = i + 2
                if self.verbose:
                    logger.info(f"Elbow detected at k={optimal_k}")
                return optimal_k
        
        # Fallback: use silhouette score if no clear elbow
        logger.warning("No clear elbow detected; using default k")
        return default
    
    def diagnose(self, k: int | None = None, max_k: int = 10) -> ClusteringResult:
        """
        Full diagnostic run: fit range, detect optimal k, return comprehensive result.
        
        Args:
            k: If specified, use this k instead of auto-detection
            max_k: Maximum k to evaluate in range
        
        Returns:
            ClusteringResult with all diagnostics
        """
        inertias, silhouette_scores, optimal_k = self.fit_range(max_k)
        
        # Use provided k if specified
        if k is not None:
            optimal_k = k
        
        # Fit final model
        kmeans = KMeans(n_clusters=optimal_k, n_init=10, random_state=self.random_state)
        labels = kmeans.fit_predict(self.X_scaled)
        
        # Compute quality metrics
        quality_metrics = {
            "davies_bouldin": davies_bouldin_score(self.X_scaled, labels),
            "calinski_harabasz": calinski_harabasz_score(self.X_scaled, labels),
            "silhouette_mean": silhouette_score(self.X_scaled, labels),
        }
        
        # Cluster profiles (mean feature values per cluster)
        cluster_profiles = self._compute_profiles(labels, optimal_k)
        
        result = ClusteringResult(
            optimal_k=optimal_k,
            inertias=inertias,
            silhouette_scores=silhouette_scores,
            quality_metrics=quality_metrics,
            labels=labels,
            cluster_centers=kmeans.cluster_centers_,
            cluster_profiles=cluster_profiles,
        )
        
        logger.info(f"Clustering complete: k={optimal_k}, silhouette={quality_metrics['silhouette_mean']:.3f}")
        
        return result
    
    def _compute_profiles(self, labels: np.ndarray, k: int) -> pd.DataFrame:
        """Compute cluster profiles: mean feature values per cluster."""
        profiles = pd.DataFrame(index=self.feature_cols)
        
        for cluster_id in range(k):
            mask = labels == cluster_id
            cluster_mean = self.X[mask].mean()
            profiles[f"Cluster_{cluster_id}"] = cluster_mean
        
        return profiles
    
    def get_silhouette_per_sample(self, labels: np.ndarray) -> np.ndarray:
        """Compute per-sample silhouette coefficients for visualization."""
        return silhouette_samples(self.X_scaled, labels)
```

### Visualization Implementation

```python
# src/socrata_toolkit/viz/clustering_viz.py

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_elbow_curve(
    inertias: list[float],
    silhouette_scores: list[float],
    optimal_k: int,
    title: str | None = None,
) -> go.Figure:
    """
    Interactive elbow curve with silhouette overlay.
    
    Returns Plotly Figure with dual y-axes:
    - Left: inertia (decreasing)
    - Right: silhouette score
    """
    k_values = list(range(1, len(inertias) + 1))
    
    fig = make_subplots(
        rows=1, cols=1,
        specs=[[{"secondary_y": True}]]
    )
    
    # Inertia trace (primary y-axis)
    fig.add_trace(
        go.Scatter(
            x=k_values,
            y=inertias,
            mode="lines+markers",
            name="Inertia",
            line=dict(color="#0066cc", width=2),
            marker=dict(size=8),
            hovertemplate="<b>k=%{x}</b><br>Inertia=%{y:.0f}<extra></extra>",
        ),
        secondary_y=False,
    )
    
    # Silhouette trace (secondary y-axis, skip k=1)
    fig.add_trace(
        go.Scatter(
            x=k_values[1:],
            y=silhouette_scores[1:],
            mode="lines+markers",
            name="Silhouette",
            line=dict(color="#ff6600", width=2),
            marker=dict(size=8, symbol="diamond"),
            hovertemplate="<b>k=%{x}</b><br>Silhouette=%{y:.3f}<extra></extra>",
        ),
        secondary_y=True,
    )
    
    # Vertical line at optimal_k
    fig.add_vline(
        x=optimal_k,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Optimal k={optimal_k}",
        annotation_position="top right",
        secondary_y=False,
    )
    
    fig.update_xaxes(title_text="Number of Clusters (k)", secondary_y=False)
    fig.update_yaxes(title_text="Inertia", secondary_y=False)
    fig.update_yaxes(title_text="Silhouette Score", secondary_y=True)
    
    fig.update_layout(
        title=title or "Elbow Curve: Optimal Cluster Selection",
        template="plotly_white",
        height=500,
        hovermode="x unified",
        legend=dict(x=0.65, y=0.95),
    )
    
    return fig


def plot_silhouette(
    data: np.ndarray,
    labels: np.ndarray,
    k: int,
    title: str | None = None,
) -> go.Figure:
    """
    Horizontal silhouette plot by cluster.
    
    Shows per-sample silhouette coefficients grouped by cluster.
    Negative values indicate poor cluster assignment.
    """
    from sklearn.metrics import silhouette_samples
    
    silhouette_vals = silhouette_samples(data, labels)
    silhouette_mean = silhouette_vals.mean()
    
    # Sort by cluster and silhouette value for visual clarity
    sorted_indices = np.argsort(silhouette_vals)
    sorted_labels = labels[sorted_indices]
    sorted_vals = silhouette_vals[sorted_indices]
    
    # Assign colors by cluster
    color_map = {i: f"hsl({i*360//k}, 70%, 50%)" for i in range(k)}
    colors = [color_map[label] for label in sorted_labels]
    
    fig = go.Figure(
        data=[
            go.Bar(
                y=np.arange(len(sorted_vals)),
                x=sorted_vals,
                orientation="h",
                marker=dict(color=colors),
                hovertemplate="<b>Sample %{y}</b><br>Silhouette=%{x:.3f}<extra></extra>",
                showlegend=False,
            )
        ]
    )
    
    # Add mean line
    fig.add_vline(
        x=silhouette_mean,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Mean={silhouette_mean:.3f}",
        annotation_position="top right",
    )
    
    fig.update_xaxes(title_text="Silhouette Coefficient")
    fig.update_yaxes(title_text="Sample (ordered by cluster & silhouette)")
    
    fig.update_layout(
        title=title or f"Silhouette Plot (k={k})",
        template="plotly_white",
        height=600,
        showlegend=False,
        hovermode="closest",
    )
    
    return fig


def plot_quality_metrics_heatmap(
    inertias: list[float],
    silhouette_scores: list[float],
    davies_bouldin_scores: list[float] | None = None,
    title: str | None = None,
) -> go.Figure:
    """
    Heatmap of quality metrics across k values.
    
    Normalize metrics to [0, 1] for visual comparison.
    """
    k_values = list(range(1, len(inertias) + 1))
    
    # Normalize inertia (lower is better → flip sign)
    inertia_norm = 1 - (np.array(inertias) / np.max(inertias))
    
    # Silhouette already in [-1, 1], normalize to [0, 1]
    sil_norm = (np.array(silhouette_scores) + 1) / 2
    
    # Build heatmap data
    metrics_data = [inertia_norm, sil_norm]
    metric_names = ["Inertia (inverted)", "Silhouette"]
    
    if davies_bouldin_scores:
        # Lower DB is better → invert
        db_norm = 1 - (np.array(davies_bouldin_scores) / np.max(davies_bouldin_scores))
        metrics_data.append(db_norm)
        metric_names.append("Davies-Bouldin (inverted)")
    
    fig = go.Figure(
        data=[
            go.Heatmap(
                z=metrics_data,
                x=k_values,
                y=metric_names,
                colorscale="RdYlGn",
                zmin=0,
                zmax=1,
                hovertemplate="<b>%{y}</b><br>k=%{x}<br>Score=%{z:.3f}<extra></extra>",
            )
        ]
    )
    
    fig.update_xaxes(title_text="Number of Clusters (k)")
    fig.update_layout(
        title=title or "Quality Metrics Heatmap",
        template="plotly_white",
        height=300,
        yaxis=dict(tickangle=-45),
    )
    
    return fig
```

### Test Harness

```python
# tests/test_clustering_diagnostics.py

import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import make_blobs

from socrata_toolkit.analysis.clustering import ClusteringDiagnostics
from socrata_toolkit.viz.clustering_viz import (
    plot_elbow_curve,
    plot_silhouette,
)


@pytest.fixture
def synthetic_data():
    """Generate synthetic 2D data with 4 well-separated clusters."""
    X, y = make_blobs(n_samples=300, centers=4, n_features=2, random_state=42)
    df = pd.DataFrame(X, columns=["feature_1", "feature_2"])
    df["true_cluster"] = y
    return df, y


def test_clustering_diagnostics_init(synthetic_data):
    """Test initialization with valid data."""
    df, _ = synthetic_data
    cd = ClusteringDiagnostics(df, feature_cols=["feature_1", "feature_2"])
    assert cd.X.shape == (300, 2)
    assert len(cd.feature_cols) == 2


def test_clustering_diagnostics_fit_range(synthetic_data):
    """Test fit_range produces correct output shape."""
    df, _ = synthetic_data
    cd = ClusteringDiagnostics(df, feature_cols=["feature_1", "feature_2"])
    inertias, sil_scores, optimal_k = cd.fit_range(max_k=10)
    
    assert len(inertias) == 10
    assert len(sil_scores) == 10
    assert 2 <= optimal_k <= 10


def test_clustering_diagnostics_diagnose_returns_correct_k(synthetic_data):
    """Test diagnose correctly identifies k=4 for synthetic data."""
    df, _ = synthetic_data
    cd = ClusteringDiagnostics(df, feature_cols=["feature_1", "feature_2"])
    result = cd.diagnose(max_k=10)
    
    # Expect k=3, 4, or 5 for 4 true clusters
    assert result.optimal_k in [3, 4, 5], f"Expected k~4, got {result.optimal_k}"
    assert len(result.labels) == 300
    assert len(set(result.labels)) == result.optimal_k


def test_plot_elbow_curve_produces_figure():
    """Test elbow plot returns valid Plotly figure."""
    inertias = [1000, 600, 400, 300, 280, 270, 265, 263, 262, 261]
    sil_scores = [0.0, 0.45, 0.52, 0.55, 0.54, 0.51, 0.48, 0.45, 0.42, 0.40]
    
    fig = plot_elbow_curve(inertias, sil_scores, optimal_k=4)
    
    assert fig is not None
    assert len(fig.data) >= 2  # At least inertia + silhouette traces


def test_invalid_feature_column_raises_error():
    """Test error handling for missing columns."""
    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    
    with pytest.raises(ValueError):
        ClusteringDiagnostics(df, feature_cols=["A", "C"])  # C doesn't exist


def test_nonnumeric_column_raises_error():
    """Test error handling for non-numeric columns."""
    df = pd.DataFrame({"A": [1, 2, 3], "B": ["x", "y", "z"]})
    
    with pytest.raises(ValueError):
        ClusteringDiagnostics(df, feature_cols=["A", "B"])
```

### Integration Checkpoint

```python
# In app/callbacks/analytics.py or similar

from socrata_toolkit.analysis.clustering import ClusteringDiagnostics
from socrata_toolkit.viz.clustering_viz import plot_elbow_curve, plot_silhouette

def analyze_violations_clustering(violations_df):
    """
    User requests clustering analysis for violations.
    
    Feature set: violation_count, repair_cost, inspection_frequency
    """
    feature_cols = ["violation_count", "repair_cost", "inspection_frequency"]
    
    # Ensure numeric
    for col in feature_cols:
        violations_df[col] = pd.to_numeric(violations_df[col], errors="coerce")
    
    violations_df = violations_df.dropna(subset=feature_cols)
    
    # Run analysis
    cd = ClusteringDiagnostics(
        violations_df,
        feature_cols=feature_cols,
        random_state=42,
    )
    result = cd.diagnose(max_k=10)
    
    # Generate visualizations
    fig_elbow = plot_elbow_curve(
        result.inertias,
        result.silhouette_scores,
        result.optimal_k,
    )
    
    # Add cluster assignments back to original data
    violations_df["cluster"] = result.labels
    
    return {
        "optimal_k": result.optimal_k,
        "fig_elbow": fig_elbow,
        "cluster_assignments": violations_df[["BBLID", "cluster"]],
        "quality_metrics": result.quality_metrics,
    }
```

---

## 2. SIDEWALK MATERIAL DEGRADATION PATHWAY ANALYSIS

### Module Structure

```
src/socrata_toolkit/analysis/survival.py
  ├── class SurvivalDataPrep
  │   ├── __init__(inspections_df, violations_df, cutoff_date)
  │   ├── prepare() → survival_df (time-to-event format)
  │   └── validate_censoring() → (n_events, n_censored)
  ├── class KaplanMeierAnalysis
  │   ├── __init__(survival_df)
  │   ├── fit() → km_results_dict
  │   ├── compare_materials() → log_rank_test_results
  │   └── median_survival_times() → dict
  └── class CoxRegressionModel
      ├── __init__(survival_df)
      ├── fit(formula) → cph
      └── summary() → pd.DataFrame

src/socrata_toolkit/viz/survival_viz.py
  ├── plot_km_curves(km_results) → plotly.Figure
  ├── plot_cumulative_hazard(naf_results) → plotly.Figure
  ├── plot_material_economics(km_results, costs_dict) → plotly.Figure
  └── plot_logrank_heatmap(logrank_results) → plotly.Figure
```

### Core Implementation (Skeleton)

```python
# src/socrata_toolkit/analysis/survival.py

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class SurvivalEvent:
    """Single time-to-event observation."""
    block_id: str
    material_type: str
    time_months: float
    event: bool  # 1 if violation, 0 if censored
    borough: str
    volume: int


class SurvivalDataPrep:
    """Prepare time-to-event data from inspections + violations."""
    
    def __init__(
        self,
        inspections_df: pd.DataFrame,
        violations_df: pd.DataFrame,
        cutoff_date: str | None = None,
    ):
        """
        Args:
            inspections_df: Must have columns: [BBLID, materialid, inspectiondate, ...]
            violations_df: Must have columns: [BBLID, vissuedate, ...]
            cutoff_date: Data end date (default: today)
        """
        self.df_ins = inspections_df.copy()
        self.df_vio = violations_df.copy()
        self.cutoff_date = pd.to_datetime(cutoff_date or pd.Timestamp.today())
        
        logger.info(f"SurvivalDataPrep initialized: {len(self.df_ins)} inspections, {len(self.df_vio)} violations")
    
    def prepare(self) -> pd.DataFrame:
        """
        Transform into time-to-event format.
        
        Returns:
            DataFrame with columns: [material_type, time_months, event, borough, volume, BBLID]
        """
        # Merge inspection + violation history
        df = self.df_ins.merge(
            self.df_vio[["BBLID", "vissuedate"]],
            on="BBLID",
            how="left",
        )
        
        # Compute time-to-event
        df["time_months"] = (df["vissuedate"] - df["inspectiondate"]).dt.days / 30.44
        df["event"] = (~df["vissuedate"].isna()).astype(int)
        
        # Censor observations with insufficient follow-up (<6 months)
        df.loc[df["time_months"] < 6, "event"] = 0
        df["time_months"] = df["time_months"].clip(lower=6)
        
        # Select output columns
        result = df[[
            "material_type", "time_months", "event", "borough", "BBLID"
        ]].copy()
        
        result["volume"] = 1  # Placeholder
        
        # Validate
        n_events = result["event"].sum()
        n_censored = len(result) - n_events
        logger.info(f"Survival data: {n_events} events, {n_censored} censored")
        
        return result.dropna()
    
    def validate_censoring(self) -> tuple[int, int]:
        """Return (n_events, n_censored)."""
        survival_df = self.prepare()
        n_events = survival_df["event"].sum()
        n_censored = len(survival_df) - n_events
        return n_events, n_censored


class KaplanMeierAnalysis:
    """Kaplan-Meier survival curves by material."""
    
    def __init__(self, survival_df: pd.DataFrame):
        self.survival_df = survival_df.copy()
        self.kmf = None  # Will import lifelines
        self.results = {}
    
    def fit(self) -> dict[str, dict[str, Any]]:
        """
        Fit K-M curves for each material.
        
        Returns dict with structure:
        {
            'concrete': {
                'survival_function': pd.Series,
                'confidence_interval': pd.DataFrame,
                'median_survival_time': float,
                'event_count': int,
                'n_at_risk': int,
            },
            ...
        }
        """
        try:
            from lifelines import KaplanMeierFitter
        except ImportError:
            logger.error("lifelines not installed; install via: pip install lifelines")
            raise
        
        kmf = KaplanMeierFitter()
        results = {}
        
        for material in self.survival_df["material_type"].unique():
            material_data = self.survival_df[
                self.survival_df["material_type"] == material
            ]
            
            kmf.fit(
                material_data["time_months"],
                material_data["event"],
                label=material
            )
            
            results[material] = {
                "survival_function": kmf.survival_function_,
                "confidence_interval": kmf.confidence_interval_survival_function_,
                "median_survival_time": kmf.median_survival_time_,
                "event_count": material_data["event"].sum(),
                "n_at_risk": len(material_data),
            }
        
        self.results = results
        return results
    
    def compare_materials(self) -> dict[tuple, dict]:
        """
        Pairwise log-rank tests between materials.
        
        Returns:
        {
            ('concrete', 'asphalt'): {
                'test_statistic': float,
                'p_value': float,
                'significant': bool,
            },
            ...
        }
        """
        try:
            from lifelines.statistics import logrank_test
        except ImportError:
            logger.error("lifelines not installed")
            raise
        
        materials = self.survival_df["material_type"].unique()
        n_comparisons = len(materials) * (len(materials) - 1) / 2
        alpha_corrected = 0.05 / max(1, n_comparisons)
        
        results = {}
        
        for i, mat1 in enumerate(materials):
            for mat2 in materials[i+1:]:
                data1 = self.survival_df[self.survival_df["material_type"] == mat1]
                data2 = self.survival_df[self.survival_df["material_type"] == mat2]
                
                test = logrank_test(
                    data1["time_months"],
                    data2["time_months"],
                    data1["event"],
                    data2["event"]
                )
                
                results[(mat1, mat2)] = {
                    "test_statistic": test.test_statistic,
                    "p_value": test.p_value,
                    "significant": test.p_value < alpha_corrected,
                }
        
        return results


class CoxRegressionModel:
    """Cox proportional hazards regression."""
    
    def __init__(self, survival_df: pd.DataFrame):
        self.survival_df = survival_df.copy()
        self.cph = None
    
    def fit(self) -> Any:
        """
        Fit Cox model: log_hazard ~ material_type + borough + log(volume)
        
        Returns CoxPHFitter instance.
        """
        try:
            from lifelines import CoxPHFitter
        except ImportError:
            logger.error("lifelines not installed")
            raise
        
        # One-hot encode categorical features
        df_encoded = pd.get_dummies(
            self.survival_df,
            columns=["material_type", "borough"],
            drop_first=True
        )
        
        df_encoded["log_volume"] = np.log1p(df_encoded["volume"])
        
        # Prepare feature matrix
        feature_cols = [c for c in df_encoded.columns if c not in ["BBLID"]]
        
        self.cph = CoxPHFitter()
        self.cph.fit(
            df_encoded,
            duration_col="time_months",
            event_col="event"
        )
        
        return self.cph
    
    def summary(self) -> pd.DataFrame:
        """Return Cox model summary table."""
        if self.cph is None:
            raise ValueError("Model not fitted; call fit() first")
        
        return self.cph.summary
```

### Test Harness (Skeleton)

```python
# tests/test_survival_analysis.py

import pandas as pd
import pytest


@pytest.fixture
def survival_test_data():
    """Generate synthetic survival data."""
    np.random.seed(42)
    
    data = {
        "BBLID": [f"{i:010d}" for i in range(100)],
        "material_type": np.random.choice(["concrete", "asphalt", "stone"], 100),
        "time_months": np.random.exponential(scale=120, size=100),
        "event": np.random.binomial(1, 0.4, 100),
        "borough": np.random.choice(["MANHATTAN", "BROOKLYN"], 100),
        "volume": np.random.randint(1, 100, 100),
    }
    
    return pd.DataFrame(data)


def test_km_analysis_fit(survival_test_data):
    """Test K-M fitting produces results for each material."""
    km = KaplanMeierAnalysis(survival_test_data)
    results = km.fit()
    
    assert len(results) == 3  # 3 materials
    assert "concrete" in results
    assert "median_survival_time" in results["concrete"]


def test_cox_regression_fit(survival_test_data):
    """Test Cox model fitting completes."""
    cox = CoxRegressionModel(survival_test_data)
    cph = cox.fit()
    
    assert cph is not None
    summary = cox.summary()
    assert isinstance(summary, pd.DataFrame)
```

---

## 3. GEOSPATIAL HEATMAP WITH TEMPORAL ANIMATION

### Module Structure

```
src/socrata_toolkit/viz/temporal_geospatial.py
  ├── class TemporalGeospatialDashboard
  │   ├── __init__(violations_df, cb_geometries)
  │   ├── aggregate_by_month() → monthly_agg_df
  │   ├── compute_month_over_month_change() → change_df
  │   └── get_hot_blocks(month, top_k=10) → list
  ├── plot_animated_choropleth(monthly_df) → plotly.Figure
  ├── plot_hot_blocks_timeline(monthly_df) → plotly.Figure
  └── plot_month_over_month_heatmap(change_df) → plotly.Figure
```

### Core Implementation (Skeleton)

```python
# src/socrata_toolkit/viz/temporal_geospatial.py

from __future__ import annotations

import logging
from collections import defaultdict

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)

# NYC Community Board centroids (lat/lon for label placement)
CB_CENTROIDS = {
    101: (40.774, -73.990),  # Manhattan 1
    102: (40.714, -74.010),  # Manhattan 2
    # ... (full mapping in actual code)
}


class TemporalGeospatialDashboard:
    """Temporal aggregation + visualization for violation heatmaps."""
    
    def __init__(
        self,
        violations_df: pd.DataFrame,
        cb_areas_km2: dict[int, float] | None = None,
    ):
        """
        Args:
            violations_df: Must have columns [date, community_board, borough, violation_count]
            cb_areas_km2: Dict mapping CB ID -> area in km^2
        """
        self.df_vio = violations_df.copy()
        self.df_vio["date"] = pd.to_datetime(self.df_vio["date"])
        
        # Default CB areas (approximate for NYC)
        self.cb_areas = cb_areas_km2 or defaultdict(lambda: 15.0)
        
        logger.info(f"TemporalGeospatialDashboard initialized: {len(self.df_vio)} records")
    
    def aggregate_by_month(self) -> pd.DataFrame:
        """
        Aggregate violations by community_board + month.
        
        Returns:
            DataFrame with columns:
            [year_month, community_board, borough, violation_count, violation_density, ...]
        """
        df = self.df_vio.copy()
        df["year_month"] = df["date"].dt.to_period("M").astype(str)
        
        # Group and aggregate
        agg_df = df.groupby(["year_month", "community_board", "borough"]).agg({
            "violation_count": "sum",
            "latitude": "mean",
            "longitude": "mean",
        }).reset_index()
        
        # Compute density
        agg_df["cb_area"] = agg_df["community_board"].map(self.cb_areas)
        agg_df["violation_density"] = agg_df["violation_count"] / agg_df["cb_area"]
        
        # Sort
        agg_df = agg_df.sort_values(["year_month", "violation_density"], ascending=[True, False])
        
        return agg_df
    
    def compute_month_over_month_change(self, monthly_agg_df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute % change in violation_density month-to-month.
        
        Returns:
            DataFrame with column "density_pct_change"
        """
        df = monthly_agg_df.sort_values(["community_board", "year_month"])
        df["density_pct_change"] = (
            df.groupby("community_board")["violation_density"]
            .pct_change() * 100
        )
        
        return df
    
    def get_hot_blocks(self, month: str, top_k: int = 10) -> list[dict]:
        """Get top-k community boards by violation density for a given month."""
        monthly_agg = self.aggregate_by_month()
        month_data = monthly_agg[monthly_agg["year_month"] == month].head(top_k)
        
        return month_data[
            ["community_board", "violation_density", "borough"]
        ].to_dict("records")


def plot_animated_choropleth_by_borough(
    monthly_agg_df: pd.DataFrame,
    title: str | None = None,
) -> go.Figure:
    """
    Create animated borough subplots showing violation density over time.
    
    Each frame corresponds to a month.
    """
    months = sorted(monthly_agg_df["year_month"].unique())
    boroughs = ["MANHATTAN", "BRONX", "BROOKLYN", "QUEENS", "STATEN ISLAND"]
    
    # Create initial frame (first month)
    first_month = months[0]
    initial_data = monthly_agg_df[monthly_agg_df["year_month"] == first_month]
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=boroughs,
        specs=[[{"type": "geo"}, {"type": "geo"}, {"type": "geo"}],
               [{"type": "geo"}, {"type": "geo"}, {"type": "geo"}]],
    )
    
    # For simplicity, show bar chart per borough (alternative to full choropleth)
    for idx, borough in enumerate(boroughs):
        row, col = (idx // 3) + 1, (idx % 3) + 1
        
        borough_data = initial_data[initial_data["borough"] == borough]
        
        fig.add_trace(
            go.Bar(
                x=borough_data["community_board"],
                y=borough_data["violation_density"],
                name=borough,
                showlegend=(idx == 0),
                hovertemplate="<b>CB %{x}</b><br>Density: %{y:.2f}<extra></extra>",
            ),
            row=row, col=col,
        )
    
    # Create frames for animation
    frames = []
    for month in months:
        month_data = monthly_agg_df[monthly_agg_df["year_month"] == month]
        
        frame_data = []
        for idx, borough in enumerate(boroughs):
            borough_data = month_data[month_data["borough"] == borough]
            frame_data.append(
                go.Bar(
                    x=borough_data["community_board"],
                    y=borough_data["violation_density"],
                )
            )
        
        frames.append(go.Frame(data=frame_data, name=str(month)))
    
    fig.frames = frames
    
    # Add play/pause buttons
    fig.update_layout(
        updatemenus=[
            {
                "type": "buttons",
                "showactive": False,
                "buttons": [
                    {
                        "label": "Play",
                        "method": "animate",
                        "args": [None, {
                            "frame": {"duration": 500, "redraw": True},
                            "fromcurrent": True,
                        }],
                    },
                    {
                        "label": "Pause",
                        "method": "animate",
                        "args": [[None], {
                            "frame": {"duration": 0, "redraw": False},
                            "mode": "immediate",
                            "transition": {"duration": 0},
                        }],
                    },
                ],
            }
        ],
    )
    
    fig.update_layout(
        title=title or "Violation Density by Borough (Animated)",
        template="plotly_white",
        height=700,
    )
    
    return fig


def plot_hot_blocks_timeline(
    monthly_agg_df: pd.DataFrame,
    top_k: int = 10,
    title: str | None = None,
) -> go.Figure:
    """
    Animated bar chart of top-k community boards by violation density.
    
    Bars change color based on trend (increasing = red, decreasing = green).
    """
    months = sorted(monthly_agg_df["year_month"].unique())
    
    # Get top-k for first month
    first_month = months[0]
    first_data = monthly_agg_df[monthly_agg_df["year_month"] == first_month].head(top_k)
    
    # Create initial figure
    fig = go.Figure(
        data=[
            go.Bar(
                x=first_data["violation_density"],
                y=first_data["community_board"].astype(str),
                orientation="h",
                text=first_data["violation_density"].round(2),
                textposition="auto",
            )
        ]
    )
    
    # Create frames
    frames = []
    for month in months:
        month_data = monthly_agg_df[monthly_agg_df["year_month"] == month].head(top_k)
        
        frames.append(
            go.Frame(
                data=[
                    go.Bar(
                        x=month_data["violation_density"],
                        y=month_data["community_board"].astype(str),
                        orientation="h",
                    )
                ],
                name=str(month),
            )
        )
    
    fig.frames = frames
    
    # Add animation controls
    fig.update_layout(
        updatemenus=[
            {
                "type": "buttons",
                "buttons": [
                    {"label": "Play", "method": "animate", "args": [None]},
                    {"label": "Pause", "method": "animate", "args": [[None], {"frame": {"duration": 0}}]},
                ],
            }
        ],
    )
    
    fig.update_layout(
        title=title or f"Top-{top_k} Hot Blocks by Violation Density (Animated)",
        template="plotly_white",
        height=600,
        xaxis_title="Violation Density (violations/km²)",
        yaxis_title="Community Board",
    )
    
    return fig


def plot_month_over_month_heatmap(
    change_df: pd.DataFrame,
    title: str | None = None,
) -> go.Figure:
    """
    Heatmap: rows = CBs, cols = months, values = % change.
    
    Red = worsening, green = improving.
    """
    # Pivot for heatmap
    heatmap_data = change_df.pivot_table(
        index="community_board",
        columns="year_month",
        values="density_pct_change",
    )
    
    fig = go.Figure(
        data=[
            go.Heatmap(
                z=heatmap_data.values,
                x=heatmap_data.columns,
                y=heatmap_data.index.astype(str),
                colorscale="RdYlGn_r",
                zmid=0,
                hovertemplate="<b>CB %{y}</b><br>%{x}<br>Change: %{z:.1f}%<extra></extra>",
            )
        ]
    )
    
    fig.update_layout(
        title=title or "Month-over-Month Violation Density Change (%)",
        template="plotly_white",
        height=800,
        xaxis_title="Month",
        yaxis_title="Community Board",
    )
    
    return fig
```

---

## SUMMARY: INTEGRATION CHECKLIST

### Clustering Diagnostics
- [ ] Implement `ClusteringDiagnostics` class in `src/socrata_toolkit/analysis/clustering.py`
- [ ] Implement viz functions in `src/socrata_toolkit/viz/clustering_viz.py`
- [ ] Add unit tests in `tests/test_clustering_diagnostics.py`
- [ ] Integration test with real violations dataset
- [ ] Add Dash callback in `app/callbacks/analytics.py`
- [ ] Document in API docs

### Material Degradation
- [ ] Add `lifelines` to dependencies (or use statsmodels alternative)
- [ ] Implement survival data prep in `src/socrata_toolkit/analysis/survival.py`
- [ ] Implement K-M + Cox models in same module
- [ ] Implement viz functions in `src/socrata_toolkit/viz/survival_viz.py`
- [ ] Unit + integration tests
- [ ] Dash integration

### Geospatial Animation
- [ ] Implement temporal aggregation in `src/socrata_toolkit/viz/temporal_geospatial.py`
- [ ] Implement animated choropleths / bar charts
- [ ] Performance testing (caching strategy for 24+ months)
- [ ] Unit + integration tests
- [ ] Dash integration with slider widget

### Cross-Cutting
- [ ] Add dependencies to `pyproject.toml` if needed
- [ ] Create shared test fixtures for violations/inspections data
- [ ] Set up CI/CD to run tests on each commit
- [ ] Document expected data schemas (DATASETS.md updates)

---

## NEXT STEPS

1. **Data validation:** Confirm availability of required columns in current datasets
2. **Team kickoff:** Assign ownership (analysis, viz, QA)
3. **Dependency review:** Confirm lifelines or alternative survival analysis library
4. **Sprint planning:** Map to development calendar
5. **Stakeholder alignment:** Socialize designs with Operations, Planning teams

