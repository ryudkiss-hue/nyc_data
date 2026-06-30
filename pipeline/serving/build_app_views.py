"""Build the app-facing `app_queries.*` views from REAL warehouse data.

Replaces the retired scripts/init_local_duckdb.py, which fabricated hardcoded
synthetic values (Total Inspections=12543, Moran's I=0.45, …). Everything here is
derived from the real serving/kpi/analytics layers the pipeline produces, so the
Dash Mission Control dashboard reflects the actual ingested data.

Builds:
  app_queries.v_metric_dashboard  -- KPI cards, from serving.metric_by_borough
                                     (per-borough + an 'ALL' rollup) with real
                                     period-over-period change_pct.

Phase B–F views (v_phase_b…f) are built by pipeline/analytics/build_phase_analytics.py
(real computed statistics), not here.

Run:  python pipeline/serving/build_app_views.py
Exit 0 on success; non-zero if a validity gate fails (empty view, synthetic
sentinel value, or a configured KPI slot missing a real source).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]

# Curated KPI card slots → the REAL serving.metric_by_borough metric_name each maps to.
# (slug, real_metric_name, category, agg). `agg` is how the citywide 'ALL' rollup is
# computed: "sum" for counts/budgets, "avg" for rates/percentages/ages (summing a
# percentage across boroughs is meaningless). Slugs are the stable ids the Dash
# METRIC_CONFIG references; they must stay in sync with app/components/metric_cards.py.
KPI_SLOTS: list[tuple[str, str, str, str]] = [
    # Inspection & Violations
    ("total_violations", "Total Violations", "Inspection & Violations", "sum"),
    ("open_violations", "Open Violations", "Inspection & Violations", "sum"),
    ("open_violation_avg_age_days", "Open Violation Avg Age (days)", "Inspection & Violations", "avg"),
    ("repair_pass_rate_pct", "Repair Pass Rate %", "Inspection & Violations", "avg"),
    ("trip_hazard_violations_pct", "Trip-Hazard Violations %", "Inspection & Violations", "avg"),
    # Accessibility & Ramps
    ("total_ramps_tracked", "Total Ramps Tracked", "Accessibility & Ramps", "sum"),
    ("ramp_complaints", "Ramp Complaints", "Accessibility & Ramps", "sum"),
    ("accessible_pedestrian_signals", "Accessible Pedestrian Signals", "Accessibility & Ramps", "sum"),
    ("sidewalk_curb_311_complaints", "Sidewalk/Curb 311 Complaints", "Accessibility & Ramps", "sum"),
    # Vision Zero Safety
    ("pedestrian_crashes", "Pedestrian-Involved Crashes", "Vision Zero Safety", "sum"),
    ("pedestrians_injured", "Pedestrians Injured (crashes)", "Vision Zero Safety", "sum"),
    ("pedestrians_killed", "Pedestrians Killed (crashes)", "Vision Zero Safety", "sum"),
    # Capital & Construction
    ("street_construction_permits", "Street Construction Permits", "Capital & Construction", "sum"),
    ("capital_reconstruction_projects", "Capital Reconstruction Projects", "Capital & Construction", "sum"),
    ("total_capital_budget", "Total Capital Budget", "Capital & Construction", "sum"),
    ("pothole_work_orders_closed", "Pothole Work Orders (closed)", "Capital & Construction", "sum"),
]

SYNTHETIC_SENTINELS = (12543.0, 11288.70)  # values that betrayed the old fake view


def _local_db_path() -> str:
    load_dotenv(ROOT / ".env")
    p = os.getenv("DUCKDB_PATH")
    if not p:
        p = str(ROOT / "nyc_dot_analytics.duckdb")
    # DUCKDB_PATH may be relative (./nyc_dot_analytics.duckdb) in .env
    return str((ROOT / p).resolve()) if not os.path.isabs(p) else p


def build(con: duckdb.DuckDBPyConnection) -> int:
    con.execute("CREATE SCHEMA IF NOT EXISTS app_queries")
    # The object may pre-exist as a VIEW (legacy synthetic) or a TABLE (prior run of
    # this builder); DuckDB's typed DROP ... IF EXISTS errors on the wrong type, so
    # attempt both forms and ignore the type-mismatch.
    for stmt in ("DROP VIEW IF EXISTS app_queries.v_metric_dashboard",
                 "DROP TABLE IF EXISTS app_queries.v_metric_dashboard"):
        try:
            con.execute(stmt)
        except duckdb.CatalogException:
            pass

    # Map each curated slot to its real metric_name via a VALUES table.
    slot_rows = ",\n        ".join(
        f"('{slug}', '{name.replace(chr(39), chr(39) * 2)}', '{cat}', '{agg}')"
        for slug, name, cat, agg in KPI_SLOTS
    )

    # Per (metric, borough): latest value + prior value (for change_pct), from the
    # two most recent measurement_dates. ALL rollup = SUM for counts, AVG for %/age.
    con.execute(
        f"""
        CREATE OR REPLACE TABLE app_queries.v_metric_dashboard AS
        WITH slots(metric_id, metric_name, category, agg) AS (
            VALUES
        {slot_rows}
        ),
        ranked AS (
            SELECT mb.metric_name, mb.borough, mb.unit, mb.value,
                   ROW_NUMBER() OVER (PARTITION BY mb.metric_name, mb.borough
                                      ORDER BY mb.measurement_date DESC) AS rn
            FROM serving.metric_by_borough mb
        ),
        latest AS (SELECT metric_name, borough, unit, value FROM ranked WHERE rn = 1),
        prior  AS (SELECT metric_name, borough, value AS prev FROM ranked WHERE rn = 2),
        per_boro AS (
            SELECT s.metric_id, s.metric_name, l.borough,
                   round(l.value, 2) AS value,
                   CASE WHEN p.prev IS NOT NULL AND p.prev <> 0
                        THEN round(100.0 * (l.value - p.prev) / abs(p.prev), 1) ELSE 0 END AS change_pct,
                   s.category, l.unit
            FROM slots s
            JOIN latest l ON l.metric_name = s.metric_name
            LEFT JOIN prior p ON p.metric_name = s.metric_name AND p.borough = l.borough
        ),
        all_roll AS (
            -- Citywide rollup: SUM for counts, AVG for rates/percentages/ages,
            -- driven by the curated per-slot agg (never sum a percentage).
            SELECT s.metric_id, s.metric_name, 'ALL' AS borough,
                   round(CASE WHEN max(s.agg) = 'avg' THEN avg(l.value) ELSE sum(l.value) END, 2) AS value,
                   0 AS change_pct, s.category, max(l.unit) AS unit
            FROM slots s JOIN latest l ON l.metric_name = s.metric_name
            GROUP BY s.metric_id, s.metric_name, s.category
        )
        SELECT metric_id, metric_name, borough, value, change_pct, category, unit FROM per_boro
        UNION ALL
        SELECT metric_id, metric_name, borough, value, change_pct, category, unit FROM all_roll
        """
    )

    # ---- validity gates ----
    n = con.execute("SELECT count(*) FROM app_queries.v_metric_dashboard").fetchone()[0]
    if n == 0:
        print("FAIL: v_metric_dashboard is empty", file=sys.stderr)
        return 2

    bad = con.execute(
        "SELECT count(*) FROM app_queries.v_metric_dashboard WHERE value IN "
        f"({','.join(str(v) for v in SYNTHETIC_SENTINELS)})"
    ).fetchone()[0]
    if bad:
        print(f"FAIL: {bad} synthetic-sentinel values present", file=sys.stderr)
        return 2

    present = {r[0] for r in con.execute(
        "SELECT DISTINCT metric_id FROM app_queries.v_metric_dashboard").fetchall()}
    missing = [slug for slug, _, _, _ in KPI_SLOTS if slug not in present]
    if missing:
        print(f"FAIL: KPI slots with no real source: {missing}", file=sys.stderr)
        return 2

    print(f"OK: app_queries.v_metric_dashboard rebuilt from real data — {n} rows, "
          f"{len(present)} metrics across boroughs+ALL")
    return 0


def main() -> int:
    db = _local_db_path()
    if not Path(db).exists():
        print(f"FAIL: local warehouse not found at {db}", file=sys.stderr)
        return 2
    con = duckdb.connect(db)
    try:
        return build(con)
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
