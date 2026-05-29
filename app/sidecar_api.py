"""Local-only FastAPI sidecar service for the NYC Data desktop SPA.

This service runs on 127.0.0.1:8000 and is invoked by the Electron desktop
front-end for heavy Python analytics (Bayesian inference, time-series
forecasting) and data-governance scoring (PII scanning, DMBOK, FAIR).

Design principles:

* **Local-only.** CORS is locked to localhost / 127.0.0.1 / file:// origins
  because the only client is the bundled Electron renderer running on the same
  machine. There is no authentication layer here, so the API must never be
  exposed to a network.
* **Graceful degradation.** Optional heavy dependencies (``pymc``,
  ``prophet``, ``pandas``) and sibling governance packages
  (``socrata_toolkit.privacy``, ``socrata_toolkit.fair``) may not be installed.
  All such imports are performed **lazily inside endpoint functions** so this
  module imports cleanly with only ``fastapi`` + ``pydantic`` present. When a
  capability is missing, endpoints return a clear JSON error (HTTP 503) or a
  pure-Python fallback rather than crashing.
"""

from __future__ import annotations

import importlib.util
import random
import time
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Lightweight in-process audit trail for governance operations (#50)
try:
    from socrata_toolkit.governance.audit import audit_op
    from socrata_toolkit.governance.audit import get_global_trail as _get_trail
    _AUDIT_OK = True
except ImportError:
    _AUDIT_OK = False
    def audit_op(op, **_):  # type: ignore[misc]
        import functools
        def d(fn): return fn
        return d

app = FastAPI(title="NYC Data Sidecar", version="1.0.0")

# CORS is intentionally restricted to local origins. This sidecar exposes
# unauthenticated heavy-compute and governance endpoints and is meant to be
# reachable ONLY by the Electron renderer on the same machine. The
# allow_origin_regex also permits the "file://" origin Electron uses when
# loading the SPA from disk (which arrives as the literal string "null" or
# "file://" depending on the platform).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
        "https://localhost",
        "https://127.0.0.1",
    ],
    allow_origin_regex=r"^(file://.*|null|https?://(localhost|127\.0\.0\.1)(:\d+)?)$",
    allow_methods=["*"],
    allow_headers=["*"],
)

_START_TIME = time.monotonic()


def _module_available(name: str) -> bool:
    """Return True if a module can be imported without importing it."""
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
@app.get("/health")
def health() -> dict[str, Any]:
    """Liveness probe reporting uptime and optional-capability availability."""
    return {
        "status": "ok",
        "uptime_s": round(time.monotonic() - _START_TIME, 3),
        "capabilities": {
            "pymc": _module_available("pymc"),
            "prophet": _module_available("prophet"),
            "privacy": _module_available("socrata_toolkit.privacy.pii_scanner"),
            "fair": _module_available("socrata_toolkit.fair.scoring"),
            "dmbok": _module_available("socrata_toolkit.privacy.dmbok"),
        },
    }


# --------------------------------------------------------------------------- #
# Bayesian yield-rate
# --------------------------------------------------------------------------- #
class YieldRateRequest(BaseModel):
    """Beta-Binomial yield-rate request.

    ``observations[i]`` successes out of ``totals[i]`` trials.
    """

    observations: list[int] = Field(..., min_length=1)
    totals: list[int] = Field(..., min_length=1)
    draws: int = Field(500, ge=10, le=5000)
    tune: int = Field(200, ge=10, le=5000)


@app.post("/api/bayesian/yield-rate")
def bayesian_yield_rate(req: YieldRateRequest) -> dict[str, Any]:
    """Estimate a pooled yield rate via a Beta-Binomial model.

    Attempts a PyMC ADVI fit; on any failure (incl. pymc not installed) it
    falls back to sampling directly from the conjugate Beta posterior using the
    standard-library ``random.betavariate``. Either way it returns posterior
    ``mean``, the 3%/97% HDI bounds, up to 200 ``samples`` and the ``method``.
    """
    if len(req.observations) != len(req.totals):
        raise HTTPException(400, "observations and totals must have equal length")
    if any(o < 0 for o in req.observations) or any(t <= 0 for t in req.totals):
        raise HTTPException(400, "totals must be > 0 and observations >= 0")
    if any(o > t for o, t in zip(req.observations, req.totals, strict=False)):
        raise HTTPException(400, "each observation must be <= its total")

    total_success = sum(req.observations)
    total_trials = sum(req.totals)

    # Try PyMC ADVI first.
    try:
        import numpy as np  # noqa: F401
        import pymc as pm  # type: ignore

        with pm.Model():
            theta = pm.Beta("theta", alpha=1.0, beta=1.0)
            pm.Binomial(
                "y",
                n=np.array(req.totals),
                p=theta,
                observed=np.array(req.observations),
            )
            approx = pm.fit(n=req.draws + req.tune, method="advi", progressbar=False)
            trace = approx.sample(req.draws)
        theta_samples = np.asarray(trace.posterior["theta"].values).reshape(-1)
        mean = float(theta_samples.mean())
        hdi_3 = float(np.percentile(theta_samples, 3))
        hdi_97 = float(np.percentile(theta_samples, 97))
        samples = [float(x) for x in theta_samples[:200]]
        return {
            "mean": mean,
            "hdi_3": hdi_3,
            "hdi_97": hdi_97,
            "samples": samples,
            "method": "advi",
        }
    except Exception:
        # Conjugate Beta(1,1) prior -> Beta(1 + successes, 1 + failures) posterior.
        alpha = 1.0 + total_success
        beta = 1.0 + (total_trials - total_success)
        draws = [random.betavariate(alpha, beta) for _ in range(req.draws)]
        draws.sort()
        n = len(draws)
        mean = sum(draws) / n

        def _pct(p: float) -> float:
            idx = min(n - 1, max(0, int(round(p / 100.0 * (n - 1)))))
            return draws[idx]

        return {
            "mean": mean,
            "hdi_3": _pct(3),
            "hdi_97": _pct(97),
            "samples": draws[:200],
            "method": "bootstrap",
        }


# --------------------------------------------------------------------------- #
# Prophet forecast
# --------------------------------------------------------------------------- #
class ProphetRequest(BaseModel):
    """Prophet forecast request. ``dates`` are ISO date strings."""

    dates: list[str] = Field(..., min_length=2)
    values: list[float] = Field(..., min_length=2)
    periods: int = Field(30, ge=1, le=3650)
    freq: str = "D"


@app.post("/api/forecast/prophet")
def forecast_prophet(req: ProphetRequest) -> dict[str, Any]:
    """Forecast a univariate series with Facebook Prophet.

    Returns future ``dates``/``yhat``/``yhat_lower``/``yhat_upper``/``trend``.
    400 on length mismatch or fewer than 2 points; 503 if prophet is absent.
    """
    if len(req.dates) != len(req.values):
        raise HTTPException(400, "dates and values must have equal length")
    if len(req.dates) < 2:
        raise HTTPException(400, "at least 2 data points are required")

    try:
        import pandas as pd
        from prophet import Prophet  # type: ignore
    except ImportError as exc:
        raise HTTPException(503, f"prophet is not installed: {exc}") from exc

    try:
        df = pd.DataFrame({"ds": pd.to_datetime(req.dates), "y": req.values})
        model = Prophet()
        model.fit(df)
        future = model.make_future_dataframe(periods=req.periods, freq=req.freq)
        fc = model.predict(future)
        return {
            "dates": [d.strftime("%Y-%m-%d") for d in fc["ds"]],
            "yhat": [float(v) for v in fc["yhat"]],
            "yhat_lower": [float(v) for v in fc["yhat_lower"]],
            "yhat_upper": [float(v) for v in fc["yhat_upper"]],
            "trend": [float(v) for v in fc["trend"]],
            "method": "prophet",
        }
    except Exception as exc:  # pragma: no cover - depends on prophet runtime
        raise HTTPException(500, f"prophet forecast failed: {exc}") from exc


# --------------------------------------------------------------------------- #
# Governance: PII scan
# --------------------------------------------------------------------------- #
class RowsRequest(BaseModel):
    """Generic tabular payload: a list of row dicts."""

    rows: list[dict[str, Any]] = Field(default_factory=list)


@app.post("/api/governance/pii-scan")
def governance_pii_scan(req: RowsRequest) -> dict[str, Any]:
    """Scan tabular rows for PII signals via socrata_toolkit privacy scanner."""
    try:
        import pandas as pd

        from socrata_toolkit.privacy.pii_scanner import scan_dataframe
    except ImportError as exc:
        raise HTTPException(503, f"pii scanner unavailable: {exc}") from exc

    df = pd.DataFrame(req.rows)
    signals = scan_dataframe(df)
    out = []
    for s in signals:
        if hasattr(s, "__dict__"):
            out.append(dict(s.__dict__))
        else:
            out.append(dict(s))
    return {"signals": out, "count": len(out)}


# --------------------------------------------------------------------------- #
# Governance: DMBOK
# --------------------------------------------------------------------------- #
class DmbokRequest(BaseModel):
    """DMBOK data-management scoring request."""

    rows: list[dict[str, Any]] = Field(default_factory=list)
    key_columns: list[str] | None = None
    date_column: str | None = None


@app.post("/api/governance/dmbok")
def governance_dmbok(req: DmbokRequest) -> dict[str, Any]:
    """Score tabular rows against a DMBOK rubric."""
    try:
        import pandas as pd

        from socrata_toolkit.privacy.dmbok import score_dataframe
    except ImportError as exc:
        raise HTTPException(503, f"dmbok scorer unavailable: {exc}") from exc

    df = pd.DataFrame(req.rows)
    kwargs: dict[str, Any] = {}
    if req.key_columns is not None:
        kwargs["key_columns"] = req.key_columns
    if req.date_column is not None:
        kwargs["date_column"] = req.date_column
    report = score_dataframe(df, **kwargs)
    if hasattr(report, "to_dict"):
        return report.to_dict()
    if hasattr(report, "__dict__"):
        return dict(report.__dict__)
    return dict(report)


# --------------------------------------------------------------------------- #
# Governance: FAIR
# --------------------------------------------------------------------------- #
# Known FairDataset public fields; only these are passed through defensively.
_FAIR_FIELDS = {
    "persistent_id",
    "title",
    "description",
    "keywords",
    "domain",
    "fourfour",
    "landing_page",
    "access_url",
    "access_protocol",
    "access_rights",
    "license",
    "format",
    "conforms_to",
    "vocabulary",
    "schema_fields",
    "provenance",
    "usage_rights",
    "citation",
}


class FairRequest(BaseModel):
    """FAIR dataset descriptor; extra/unknown fields are ignored."""

    model_config = {"extra": "allow"}


@app.post("/api/governance/fairness")
def governance_fairness(req: FairRequest) -> dict[str, Any]:
    """Score a dataset descriptor against the FAIR rubric."""
    try:
        from socrata_toolkit.fair.model import FairDataset
        from socrata_toolkit.fair.scoring import score_fairness
    except ImportError as exc:
        raise HTTPException(503, f"fair scorer unavailable: {exc}") from exc

    payload = req.model_dump()
    # Defensive: only forward known FairDataset fields.
    known = {k: v for k, v in payload.items() if k in _FAIR_FIELDS}
    if hasattr(FairDataset, "from_dict"):
        ds = FairDataset.from_dict(known)
    else:  # pragma: no cover - defensive
        ds = FairDataset(**known)
    score = score_fairness(ds)
    if hasattr(score, "to_dict"):
        return score.to_dict()
    if hasattr(score, "__dict__"):
        return dict(score.__dict__)
    return dict(score)


# --------------------------------------------------------------------------- #
# Quality: anomaly detection (pure numpy, always available)
# --------------------------------------------------------------------------- #
class AnomalyRequest(BaseModel):
    """Anomaly-detection request over a numeric series."""

    values: list[float] = Field(..., min_length=1)
    method: str = "zscore"
    period: int = Field(default=7, ge=2, le=365, description="Seasonal period for STL decomposition")


@app.post("/api/quality/anomalies")
def quality_anomalies(req: AnomalyRequest) -> dict[str, Any]:
    """Flag outliers via z-score or STL seasonal decomposition.

    * ``method="zscore"``  — global z-score, |z| > 3 (original behaviour).
    * ``method="seasonal"`` — STL-lite: remove trend (centered moving average)
      and seasonal component (mean-per-phase), then z-score residuals.
      Requires ``len(values) >= 2 * period``.
    """
    import numpy as np

    if req.method not in ("zscore", "seasonal"):
        raise HTTPException(400, f"unsupported method: {req.method!r}; use 'zscore' or 'seasonal'")

    arr = np.asarray(req.values, dtype=float)
    n = len(arr)

    if req.method == "zscore":
        mean = float(arr.mean())
        std = float(arr.std())
        zscores = np.zeros_like(arr) if std == 0.0 else (arr - mean) / std
        mask = np.abs(zscores) > 3.0
        indices = [int(i) for i in np.flatnonzero(mask)]
        return {
            "method": "zscore",
            "mean": mean,
            "std": std,
            "indices": indices,
            "scores": [float(zscores[i]) for i in indices],
            "all_scores": [float(z) for z in zscores],
        }

    # seasonal (STL-lite)
    period = req.period
    if n < period * 2:
        raise HTTPException(422, f"Need at least {period * 2} values for seasonal period={period}; got {n}")

    # 1. Trend: centered moving average
    half = period // 2
    trend = np.empty(n)
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        trend[i] = arr[lo:hi].mean()

    # 2. Seasonal: average detrended value per phase
    detrended = arr - trend
    seasonal = np.zeros(period)
    counts = np.zeros(period, dtype=int)
    for i, v in enumerate(detrended):
        seasonal[i % period] += v
        counts[i % period] += 1
    with np.errstate(invalid="ignore"):
        seasonal = np.where(counts > 0, seasonal / counts, 0.0)

    # 3. Residuals and z-score
    residuals = arr - trend - seasonal[np.arange(n) % period]
    r_mean = float(residuals.mean())
    r_std = float(residuals.std())
    zscores = np.zeros_like(residuals) if r_std == 0.0 else (residuals - r_mean) / r_std

    mask = np.abs(zscores) > 3.0
    indices = [int(i) for i in np.flatnonzero(mask)]
    return {
        "method": "seasonal",
        "period": period,
        "residual_mean": r_mean,
        "residual_std": r_std,
        "indices": indices,
        "scores": [float(zscores[i]) for i in indices],
        "all_scores": [float(z) for z in zscores],
        "trend": [float(t) for t in trend],
        "seasonal": [float(seasonal[i % period]) for i in range(n)],
    }


# --------------------------------------------------------------------------- #
# Governance: attach DMBOK quality score to FAIR catalog entry  (#47)
# --------------------------------------------------------------------------- #
class QualityCatalogRequest(BaseModel):
    """Attach a DMBOK quality assessment to an existing catalog entry."""

    dataset_id: str
    rows: list[dict[str, Any]] = Field(..., min_length=1)
    key_columns: list[str] = Field(default_factory=list)
    date_column: str | None = None
    catalog_path: str | None = None  # path to persist updated catalog JSON


@app.post("/api/governance/quality-catalog")
def governance_quality_catalog(req: QualityCatalogRequest) -> dict[str, Any]:
    """Score dataset with DMBOK and attach the report to the FAIR catalog entry."""
    try:
        import pandas as pd  # noqa: PLC0415

        from socrata_toolkit.fair.catalog import FairCatalog  # noqa: PLC0415
        from socrata_toolkit.privacy.dmbok import score_dataframe  # noqa: PLC0415
    except ImportError as exc:
        raise HTTPException(503, f"Required library missing: {exc}") from exc

    df = pd.DataFrame(req.rows)
    report = score_dataframe(df, key_columns=req.key_columns, date_column=req.date_column)
    dims = {d.dimension: d.score for d in report.dimensions}

    catalog_updated = False
    if req.catalog_path:
        import pathlib  # noqa: PLC0415
        p = pathlib.Path(req.catalog_path)
        if p.exists():
            try:
                catalog = FairCatalog.from_json(p.read_text(encoding="utf-8"))
                ds = catalog.get(req.dataset_id)
                if ds is not None:
                    ds.extra_metadata = getattr(ds, "extra_metadata", None) or {}
                    ds.extra_metadata["dmbok_overall"] = report.overall
                    ds.extra_metadata["dmbok_dimensions"] = dims
                    p.write_text(catalog.to_json(), encoding="utf-8")
                    catalog_updated = True
            except Exception:
                pass

    return {
        "dataset_id": req.dataset_id,
        "dmbok_overall": report.overall,
        "dimensions": dims,
        "catalog_updated": catalog_updated,
    }


# --------------------------------------------------------------------------- #
# Audit trail endpoint  (#50)
# --------------------------------------------------------------------------- #
@app.get("/api/audit/trail")
def audit_trail_get(limit: int = 100) -> dict[str, Any]:
    """Return recent in-process audit entries."""
    if not _AUDIT_OK:
        return {"entries": [], "note": "audit module not available"}
    entries = _get_trail().entries()[-limit:]
    return {"entries": [e.__dict__ for e in reversed(entries)], "total": len(_get_trail().entries())}


@app.delete("/api/audit/trail")
def audit_trail_clear() -> dict[str, Any]:
    """Clear in-process audit entries."""
    if not _AUDIT_OK:
        return {"cleared": False}
    _get_trail().clear()
    return {"cleared": True}
