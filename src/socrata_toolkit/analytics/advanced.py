"""
Advanced Analytics skills for the SIM Mission Control workstation.
Implements TimeSeriesForecasting and Segmentation (Clustering).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from socrata_toolkit.analytics import AnalysisResult, BaseSkill

logger = logging.getLogger(__name__)

class TimeSeriesForecasting(BaseSkill):
    """
    Predicts future trends using Holt-Winters Exponential Smoothing.
    """
    
    def run(self, df: pd.DataFrame, date_col: str, value_col: str, periods: int = 30, **kwargs) -> AnalysisResult:
        """
        Args:
            df (pd.DataFrame): Input dataset.
            date_col (str): Column with datetime values.
            value_col (str): Column with values to forecast.
            periods (int): Number of periods to forecast.
        """
        self.logger.info("Starting TimeSeriesForecasting for %s", value_col)
        
        try:
            # 1. Prepare Data
            ts_df = df[[date_col, value_col]].copy()
            ts_df[date_col] = pd.to_datetime(ts_df[date_col])
            ts_df = ts_df.sort_values(date_col).set_index(date_col)
            
            # Resample if needed (assuming daily for now)
            ts_df = ts_df.resample("D").mean().ffill()
            
            # 2. Fit Model
            model = ExponentialSmoothing(ts_df[value_col], trend="add", seasonal=None)
            fit = model.fit()
            
            # 3. Forecast
            forecast = fit.forecast(periods)
            
            # 4. Calculate simple metrics (RMSE on train for now)
            residuals = ts_df[value_col] - fit.fittedvalues
            rmse = np.sqrt(np.mean(residuals**2))
            
            result_data = {
                "forecast": forecast.tolist(),
                "forecast_dates": [d.isoformat() for d in forecast.index],
                "metrics": {
                    "rmse": float(rmse),
                    "aic": float(fit.aic)
                }
            }
            
            self.logger.info("TimeSeriesForecasting complete. RMSE: %.2f", rmse)
            
            return AnalysisResult(
                skill_name="TimeSeriesForecasting",
                success=True,
                data=result_data,
                metadata={"periods": periods, "value_col": value_col}
            )
            
        except Exception as e:
            self.logger.error("TimeSeriesForecasting failed: %s", str(e), exc_info=True)
            return AnalysisResult("TimeSeriesForecasting", False, {"error": str(e)})

class Segmentation(BaseSkill):
    """
    Identifies distinct groups within the data using KMeans clustering.
    """
    
    def run(self, df: pd.DataFrame, n_clusters: int = 3, **kwargs) -> AnalysisResult:
        """
        Args:
            df (pd.DataFrame): Input dataset (numeric features only).
            n_clusters (int): Number of segments to identify.
        """
        self.logger.info("Starting Segmentation with n_clusters=%d", n_clusters)
        
        try:
            # 1. Preprocess
            numeric_df = df.select_dtypes(include=[np.number]).dropna()
            if numeric_df.empty:
                return AnalysisResult("Segmentation", False, {"error": "No numeric data available for clustering"})
                
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(numeric_df)
            
            # 2. Cluster
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
            clusters = kmeans.fit_predict(scaled_data)
            
            # 3. Aggregate results
            result_data = {
                "clusters": clusters.tolist(),
                "centroids": kmeans.cluster_centers_.tolist(),
                "inertia": float(kmeans.inertia_),
                "feature_names": numeric_df.columns.tolist()
            }
            
            self.logger.info("Segmentation complete. Inertia: %.2f", kmeans.inertia_)
            
            return AnalysisResult(
                skill_name="Segmentation",
                success=True,
                data=result_data,
                metadata={"n_clusters": n_clusters}
            )
            
        except Exception as e:
            self.logger.error("Segmentation failed: %s", str(e), exc_info=True)
            return AnalysisResult("Segmentation", False, {"error": str(e)})
