"""FastAPI sidecar for the Manhattan Mission Control Electron app.

Exposes heavy Python analytics (PyMC Bayesian ADVI, Prophet forecasting)
to the SPA via a local HTTP API on 127.0.0.1:8000.

Launch:
    python -m uvicorn app.sidecar_api:app --host 127.0.0.1 --port 8000

Or via Electron:
    MMC_SIDECAR=1 npm start   (inside desktop/)
"""
from __future__ import annotations

import os
import time
from typing import Any

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover
    raise ImportError("Install fastapi and uvicorn: pip install fastapi uvicorn") from exc

app = FastAPI(title="MMC Sidecar", version="1.0.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # renderer is same machine
    allow_methods=["*"],
    allow_headers=["*"],
)

_start_time = time.time()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "uptime_s": round(time.time() - _start_time, 1),
        "pymc": _pymc_available(),
        "prophet": _prophet_available(),
    }


def _pymc_available() -> bool:
    try:
        import pymc  # noqa: F401
        return True
    except ImportError:
        return False


def _prophet_available() -> bool:
    try:
        from prophet import Prophet  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Bayesian yield-rate model  (PyMC ADVI)
# ---------------------------------------------------------------------------

class YieldRateRequest(BaseModel):
    observations: list[int]   # numerator counts (successes)
    totals: list[int]         # denominator counts (trials)
    draws: int = 500
    tune: int = 200


class YieldRateResponse(BaseModel):
    mean: float
    hdi_3: float               # 3rd-percentile HDI lower
    hdi_97: float              # 97th-percentile HDI upper
    samples: list[float]
    method: str                # "advi" | "bootstrap"


@app.post("/api/bayesian/yield-rate", response_model=YieldRateResponse)
def bayesian_yield_rate(req: YieldRateRequest):
    """Fit a Beta-Binomial Bayesian model via ADVI and return the posterior."""
    if len(req.observations) != len(req.totals):
        raise HTTPException(400, "observations and totals must have equal length")
    if not req.totals or sum(req.totals) == 0:
        raise HTTPException(400, "totals must be non-empty and non-zero")

    try:
        return _advi_yield_rate(req)
    except Exception:
        return _bootstrap_yield_rate(req)


def _advi_yield_rate(req: YieldRateRequest) -> dict[str, Any]:
    import numpy as np
    import pymc as pm

    obs = np.array(req.observations, dtype=np.int32)
    totals = np.array(req.totals, dtype=np.int32)

    with pm.Model():
        alpha = pm.HalfNormal("alpha", sigma=5)
        beta_p = pm.HalfNormal("beta", sigma=5)
        p = pm.Beta("p", alpha=alpha, beta=beta_p)
        pm.Binomial("y", n=totals, p=p, observed=obs)

        approx = pm.fit(
            n=req.draws + req.tune,
            method="advi",
            progressbar=False,
            random_seed=42,
        )
        trace = approx.sample(req.draws, random_seed=42)

    samples = trace.posterior["p"].values.flatten().tolist()
    arr = np.array(samples)
    hdi = pm.stats.hdi(arr, hdi_prob=0.94)

    return {
        "mean": float(arr.mean()),
        "hdi_3": float(hdi[0]),
        "hdi_97": float(hdi[1]),
        "samples": samples[:200],   # send a subset for the chart
        "method": "advi",
    }


def _bootstrap_yield_rate(req: YieldRateRequest) -> dict[str, Any]:
    import random

    obs = req.observations
    tot = req.totals
    total_s = sum(obs)
    total_t = sum(tot)
    p_hat = total_s / total_t if total_t else 0.0
    rng = random.Random(42)
    samples = [rng.betavariate(total_s + 1, total_t - total_s + 1) for _ in range(req.draws)]
    samples_sorted = sorted(samples)
    lo = samples_sorted[int(0.03 * len(samples_sorted))]
    hi = samples_sorted[int(0.97 * len(samples_sorted))]

    return {
        "mean": p_hat,
        "hdi_3": lo,
        "hdi_97": hi,
        "samples": samples[:200],
        "method": "bootstrap",
    }


# ---------------------------------------------------------------------------
# Prophet time-series forecast
# ---------------------------------------------------------------------------

class ForecastRequest(BaseModel):
    dates: list[str]           # ISO date strings "YYYY-MM-DD"
    values: list[float]
    periods: int = 30
    freq: str = "D"            # pandas freq: D, W, MS, etc.


class ForecastResponse(BaseModel):
    dates: list[str]
    yhat: list[float]
    yhat_lower: list[float]
    yhat_upper: list[float]
    trend: list[float]
    method: str


@app.post("/api/forecast/prophet", response_model=ForecastResponse)
def prophet_forecast(req: ForecastRequest):
    """Fit a Prophet model and return an extended forecast."""
    if len(req.dates) != len(req.values):
        raise HTTPException(400, "dates and values must have equal length")
    if len(req.dates) < 2:
        raise HTTPException(400, "need at least 2 data points")

    try:
        return _prophet_forecast(req)
    except Exception as exc:
        raise HTTPException(500, f"Forecast failed: {exc}") from exc


def _prophet_forecast(req: ForecastRequest) -> dict[str, Any]:
    import pandas as pd
    from prophet import Prophet

    df = pd.DataFrame({"ds": pd.to_datetime(req.dates), "y": req.values})
    m = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=True)
    m.fit(df)

    future = m.make_future_dataframe(periods=req.periods, freq=req.freq)
    fc = m.predict(future)

    return {
        "dates": fc["ds"].dt.strftime("%Y-%m-%d").tolist(),
        "yhat": fc["yhat"].round(4).tolist(),
        "yhat_lower": fc["yhat_lower"].round(4).tolist(),
        "yhat_upper": fc["yhat_upper"].round(4).tolist(),
        "trend": fc["trend"].round(4).tolist(),
        "method": "prophet",
    }
