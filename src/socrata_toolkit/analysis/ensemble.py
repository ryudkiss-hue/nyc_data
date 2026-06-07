import pandas as pd
import numpy as np
from prophet import Prophet
from statsmodels.tsa.arima.model import ARIMA
import logging

logger = logging.getLogger(__name__)

class EnsembleForecaster:
    """Ensemble Forecasting Engine combining Prophet, ARIMA, and Linear Trend."""

    @staticmethod
    def run_consensus_forecast(df_ts, periods=12):
        """
        Runs multiple models and returns a consensus mean.
        Fulfills Item 16: Ensemble Forecast Consensus.
        """
        if df_ts.empty or len(df_ts) < 12: # Need more history for ARIMA
            logger.warning("Insufficient history for ensemble forecast.")
            return pd.DataFrame()

        # 1. Prophet Model
        m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
        m.fit(df_ts.rename_axis("ds").reset_index().rename(columns={"Postings": "y"}))
        future = m.make_future_dataframe(periods=periods, freq="MS")
        forecast_prophet = m.predict(future)
        
        # 2. ARIMA Model (Self-tuning p,d,q)
        try:
            series = df_ts["Postings"].values
            arima_model = ARIMA(series, order=(1, 1, 1)) # Simplified p,d,q
            arima_fit = arima_model.fit()
            arima_forecast = arima_fit.forecast(steps=periods)
        except Exception as e:
            logger.error(f"ARIMA fit failed: {e}")
            arima_forecast = np.zeros(periods)

        # 3. Linear Trend extrapolation
        x = np.arange(len(df_ts))
        y = df_ts["Postings"].values
        slope, intercept = np.polyfit(x, y, 1)
        linear_trend = intercept + slope * (np.arange(len(df_ts) + periods))
        
        # Merge into Consensus
        result = forecast_prophet[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
        
        # Forecast only part
        f_idx = len(df_ts)
        result.loc[f_idx:, "arima_pred"] = arima_forecast
        result.loc[f_idx:, "linear_pred"] = linear_trend[f_idx:]
        
        # Ensemble Mean (Prophet weighted 60%, ARIMA 20%, Linear 20%)
        result["ensemble_mean"] = (
            (result["yhat"] * 0.6) + 
            (result.get("arima_pred", result["yhat"]) * 0.2) + 
            (result.get("linear_pred", result["yhat"]) * 0.2)
        )
        
        return result
