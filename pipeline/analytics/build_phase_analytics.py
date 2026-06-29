"""Compute REAL Phase B–F analytics from the warehouse (no synthetic data).

Replaces the stale/seeded analytics.phase_* tables (which contained statistically
impossible values, e.g. bootstrap CIs with lower>upper) with statistics computed
from the real serving/geo data each run:

  Phase B  Moran's I spatial autocorrelation of NTA infrastructure-feature density
           per borough (pure-numpy KNN weights + permutation p-value; no PySAL dep).
  Phase C  Distribution classification (skewness/kurtosis → type) of that same
           per-NTA density, per borough.
  Phase D  Anomaly detection (z-score) on serving.metric_timeseries, per metric.
  Phase E  Trend/residual decomposition of serving.metric_timeseries (annual data
           has no sub-annual seasonality, so the seasonal component is omitted
           rather than fabricated).
  Phase F  Bootstrap confidence intervals of per-NTA density, per borough, plus a
           real SLA-breach probability (share of bootstrap means above target).

Writes analytics.phase_b…f, then app_queries.v_phase_b…f views the Dash app reads.
Validity gates fail the build on empty output or invalid CIs (lower>upper or
point outside [lower, upper]).

Run:  python pipeline/analytics/build_phase_analytics.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB = str(ROOT / "nyc_dot_analytics.duckdb")
RNG = np.random.default_rng(42)  # deterministic (Math.random-free); reproducible runs

# Warehouse-wide borough convention is the 2-letter code (matches the dashboard
# filters and serving.metric_by_borough); geo.dim_nta carries full names.
BORO_CODE = {"Manhattan": "MN", "Brooklyn": "BK", "Bronx": "BX",
             "Queens": "QN", "Staten Island": "SI"}


def morans_i(values: np.ndarray, coords: np.ndarray, k: int = 8, perms: int = 199):
    """Global Moran's I with row-standardized KNN weights + permutation p-value."""
    n = len(values)
    if n < 10:
        return None
    k = min(k, n - 1)
    # pairwise distances, k nearest neighbours per row (exclude self)
    d = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=2)
    np.fill_diagonal(d, np.inf)
    nn = np.argsort(d, axis=1)[:, :k]
    W = np.zeros((n, n))
    for i in range(n):
        W[i, nn[i]] = 1.0 / k  # row-standardized
    z = values - values.mean()
    denom = (z * z).sum()
    if denom == 0:
        return None

    def _i(zv):
        return (zv @ (W @ zv)) / denom  # S0 = n for row-standardized W → cancels

    obs = _i(z)
    perm = np.array([_i(RNG.permutation(z)) for _ in range(perms)])
    p = (1 + (np.abs(perm) >= abs(obs)).sum()) / (perms + 1)
    return float(obs), float(p), n


def _classify(skew: float, kurt: float) -> str:
    if abs(skew) < 0.5 and abs(kurt) < 1:
        return "NORMAL"
    if skew > 1:
        return "RIGHT-SKEWED"
    if skew < -1:
        return "LEFT-SKEWED"
    if kurt > 3:
        return "HEAVY-TAILED"
    return "MODERATE-SKEW"


def build(con: duckdb.DuckDBPyConnection) -> int:
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute("CREATE SCHEMA IF NOT EXISTS analytics")
    con.execute("CREATE SCHEMA IF NOT EXISTS app_queries")

    # Per-NTA infrastructure-feature density + borough + centroid (real spatial data).
    nta = con.execute(
        """
        SELECT s.nta2020, dn.borough,
               sum(s.features) AS features,
               ST_X(ST_Centroid(p.geom)) AS lon,
               ST_Y(ST_Centroid(p.geom)) AS lat
        FROM serving.spatial_metrics s
        JOIN geo.dim_nta dn ON dn.nta2020 = s.nta2020
        JOIN geo._nta_poly p ON p.nta2020 = s.nta2020
        WHERE s.granularity = 'nta' AND s.nta2020 IS NOT NULL
        GROUP BY s.nta2020, dn.borough, p.geom
        """
    ).fetchdf()

    # ---------- Phase B (Moran's I) + Phase C (distribution) per borough ----------
    b_rows, c_rows, f_rows = [], [], []
    for boro, g in nta.groupby("borough"):
        vals = g["features"].to_numpy(dtype=float)
        coords = g[["lat", "lon"]].to_numpy(dtype=float)
        code = BORO_CODE.get(boro, boro)
        res = morans_i(vals, coords)
        if res:
            i_val, p_val, n = res
            b_rows.append({"borough": code, "morans_i": round(i_val, 4),
                           "significance": round(p_val, 4), "n_units": n,
                           "cluster_count": int((vals > vals.mean()).sum())})
        s = pd.Series(vals)
        skew, kurt = float(s.skew()), float(s.kurtosis())
        c_rows.append({"borough": code, "metric_name": "NTA Infrastructure Density",
                       "distribution_type": _classify(skew, kurt),
                       "skewness": round(skew, 3), "kurtosis": round(kurt, 3),
                       "value": round(float(s.mean()), 2)})
        # ---------- Phase F (bootstrap CI of mean density) ----------
        if len(vals) >= 10:
            boot = np.array([RNG.choice(vals, size=len(vals), replace=True).mean()
                             for _ in range(2000)])
            lo, hi = np.percentile(boot, [2.5, 97.5])
            target = float(np.median(nta["features"]))  # citywide median density as SLA target
            f_rows.append({"borough": code, "metric_name": "NTA Infrastructure Density",
                           "point_estimate": round(float(vals.mean()), 2),
                           "ci_lower": round(float(lo), 2), "ci_upper": round(float(hi), 2),
                           "prob_sla_breach": round(float((boot < target).mean()), 4)})

    # ---------- Phase D (anomalies) + Phase E (decomposition) on time series ----------
    ts = con.execute(
        "SELECT metric, year, value FROM serving.metric_timeseries ORDER BY metric, year"
    ).fetchdf()
    d_rows, e_rows = [], []
    for metric, g in ts.groupby("metric"):
        v = g["value"].to_numpy(dtype=float)
        years = g["year"].to_numpy()
        if len(v) < 4:
            continue
        mu, sd = v.mean(), v.std(ddof=1)
        if sd > 0:
            for yr, val in zip(years, v):
                z = (val - mu) / sd
                if abs(z) >= 2:
                    d_rows.append({"metric_name": metric, "year": int(yr),
                                   "anomaly_type": "spike" if z > 0 else "drop",
                                   "severity": "HIGH" if abs(z) >= 3 else "MEDIUM",
                                   "zscore": round(float(z), 2)})
        # linear trend + residual (annual series → no seasonal component)
        x = np.arange(len(v), dtype=float)
        slope, intercept = np.polyfit(x, v, 1)
        trend = slope * x + intercept
        resid = v - trend
        for yr, tr, re in zip(years, trend, resid):
            e_rows.append({"metric_name": metric, "year": int(yr),
                           "trend": round(float(tr), 2), "residual": round(float(re), 2)})

    # ---------- persist real tables ----------
    def _write(name: str, rows: list[dict]):
        df = pd.DataFrame(rows)  # noqa: F841 (referenced by DuckDB)
        con.execute(f"CREATE OR REPLACE TABLE analytics.{name} AS SELECT * FROM df")

    _write("phase_b_morans", b_rows)
    _write("phase_c_distribution", c_rows)
    _write("phase_d_anomalies_real", d_rows)
    _write("phase_e_decomposition_real", e_rows)
    _write("phase_f_bootstrap_real", f_rows)

    # ---------- app-facing views (columns the Dash callbacks consume) ----------
    con.execute("CREATE OR REPLACE VIEW app_queries.v_phase_b_results AS "
                "SELECT borough, morans_i, significance, cluster_count, n_units FROM analytics.phase_b_morans")
    con.execute("CREATE OR REPLACE VIEW app_queries.v_phase_c_results AS "
                "SELECT borough, metric_name, distribution_type, skewness, kurtosis, value FROM analytics.phase_c_distribution")
    # D/E are citywide (per metric, not per borough); tag borough='ALL' so the
    # dashboard's borough filter keeps them, and carry metric_name for labelling.
    con.execute("CREATE OR REPLACE VIEW app_queries.v_phase_d_results AS "
                "SELECT 'ALL' AS borough, metric_name, anomaly_type AS outlier_type, severity, year, zscore FROM analytics.phase_d_anomalies_real")
    con.execute("CREATE OR REPLACE VIEW app_queries.v_phase_e_decomposition AS "
                "SELECT 'ALL' AS borough, metric_name, year AS date_key, trend, residual FROM analytics.phase_e_decomposition_real")
    con.execute("CREATE OR REPLACE VIEW app_queries.v_phase_f_bootstrap_ci AS "
                "SELECT borough, metric_name, point_estimate, ci_lower, ci_upper, prob_sla_breach FROM analytics.phase_f_bootstrap_real")

    # ---------- validity gates ----------
    for v in ("v_phase_b_results", "v_phase_c_results", "v_phase_d_results",
              "v_phase_e_decomposition", "v_phase_f_bootstrap_ci"):
        n = con.execute(f"SELECT count(*) FROM app_queries.{v}").fetchone()[0]
        if n == 0:
            print(f"FAIL: {v} is empty", file=sys.stderr)
            return 2
    bad = con.execute(
        "SELECT count(*) FROM app_queries.v_phase_f_bootstrap_ci "
        "WHERE ci_lower > ci_upper OR point_estimate < ci_lower OR point_estimate > ci_upper"
    ).fetchone()[0]
    if bad:
        print(f"FAIL: {bad} invalid bootstrap CIs (lower>upper or point outside)", file=sys.stderr)
        return 2

    print(f"OK: real Phase B–F computed — B:{len(b_rows)} boroughs, C:{len(c_rows)}, "
          f"D:{len(d_rows)} anomalies, E:{len(e_rows)} points, F:{len(f_rows)} CIs")
    return 0


def main() -> int:
    if not Path(DB).exists():
        print(f"FAIL: warehouse not found at {DB}", file=sys.stderr)
        return 2
    con = duckdb.connect(DB)
    try:
        return build(con)
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
