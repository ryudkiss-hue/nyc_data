# Analytics Module: Advanced Analytics

## Overview
The `advanced` module within the `analytics` package provides high-fidelity forecasting and segmentation skills. These tools are designed to move beyond descriptive statistics into predictive and diagnostic analytics.

## Skills

### 1. TimeSeriesForecasting
Predicts future operational loads and asset deterioration trends.
- **Methodology**: Holt-Winters Exponential Smoothing (Additive Trend).
- **Logging**: Captures model RMSE and AIC for accuracy auditing.
- **Output**: Forecasted values with ISO timestamps.

**Usage:**
```python
from socrata_toolkit.analytics.advanced import TimeSeriesForecasting
skill = TimeSeriesForecasting()
result = skill.run(df=my_data, date_col="Inspection Date", value_col="Score", periods=30)
```

### 2. Segmentation
Identifies distinct cohorts within municipal datasets (e.g., grouping neighborhood lots by repair density).
- **Methodology**: KMeans Clustering with Standard Scaling.
- **Logging**: Reports cluster inertia to help validate the optimal number of segments.
- **Output**: Cluster assignments for each row and centroid coordinates.

## Integration
These skills utilize `statsmodels` and `scikit-learn` internally, ensuring that the SIM Mission Control workstation has access to production-grade statistical libraries without manual intervention.
