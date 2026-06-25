"""Build the exhaustive, REAL KPI set from the unified staging layer.

Every KPI is a SQL aggregate over a staging table — executed against live data,
so the value is real (no synthetic placeholders). KPIs that fail to compute are
dropped and reported, never faked. Borough-flagged KPIs also emit a per-borough
breakdown using the conformed geo_borough key.

Outputs:
  serving.kpi_catalog       — one row per (kpi, citywide)
  serving.kpi_by_borough    — one row per (kpi, borough) for borough-flagged KPIs
  config/kpi_registry_real.json — registry w/ id, name, domain, dataset, formula, unit, value
"""
import json
import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv

DB = "nyc_dot_analytics"
ROOT = Path(__file__).resolve().parents[2]

# id, name, domain, dataset, unit, expr, where, by_borough
KPIS = [
    # --- SIM core: inspections / violations / repairs ----------------------
    ("KPI-01", "Total Inspections", "sim_core", "inspection", "count", "COUNT(*)", None, False),
    ("KPI-02", "Inspections No-Violation %", "sim_core", "inspection", "percent",
     "100.0*AVG(CASE WHEN lower(CAST(noviolationfound AS VARCHAR)) IN ('1','true','yes','y') THEN 1 ELSE 0 END)", None, False),
    ("KPI-03", "311-Driven Inspection %", "sim_core", "inspection", "percent",
     "100.0*AVG(CASE WHEN lower(CAST(is_311_inspection AS VARCHAR)) IN ('1','true','yes','y') THEN 1 ELSE 0 END)", None, False),
    ("KPI-04", "Total Violations", "sim_core", "violations", "count", "COUNT(*)", None, True),
    ("KPI-05", "Open Violations", "sim_core", "violations", "count",
     "SUM(CASE WHEN vdismissdate IS NULL OR CAST(vdismissdate AS VARCHAR)='' THEN 1 ELSE 0 END)", None, True),
    ("KPI-06", "Violation Resolution Rate", "sim_core", "violations", "percent",
     "100.0*AVG(CASE WHEN vdismissdate IS NOT NULL AND CAST(vdismissdate AS VARCHAR)<>'' THEN 1 ELSE 0 END)", None, False),
    ("KPI-07", "Total Defect SqFt", "sim_core", "violations", "sqft", "SUM(TRY_CAST(sq_feet AS DOUBLE))", None, False),
    ("KPI-08", "Total Reinspections", "sim_core", "reinspection", "count", "COUNT(*)", None, False),
    ("KPI-09", "Repair Dismissals", "sim_core", "dismissals", "count", "COUNT(*)", None, True),
    # --- Accessibility -----------------------------------------------------
    ("KPI-10", "Total Ramps Tracked", "accessibility", "ramp_progress", "count", "COUNT(*)", None, True),
    ("KPI-11", "Ramp Complaints", "accessibility", "ramp_complaints", "count", "COUNT(*)", None, True),
    ("KPI-12", "Accessible Pedestrian Signals", "accessibility", "accessible_pedestrian_signal_locations", "count", "COUNT(*)", None, True),
    ("KPI-13", "Pedestrian Ramp Audit Records", "accessibility", "mbpo_pedestrian_ramp_report", "count", "COUNT(*)", None, False),
    # --- Vision Zero / pedestrian safety ----------------------------------
    ("KPI-14", "Pedestrians Injured (crashes)", "safety", "motor_vehicle_collisions_crashes", "count",
     "SUM(TRY_CAST(number_of_pedestrians_injured AS INTEGER))", None, True),
    ("KPI-15", "Pedestrians Killed (crashes)", "safety", "motor_vehicle_collisions_crashes", "count",
     "SUM(TRY_CAST(number_of_pedestrians_killed AS INTEGER))", None, True),
    ("KPI-16", "Pedestrian-Involved Crashes", "safety", "motor_vehicle_collisions_crashes", "count", "COUNT(*)", None, True),
    ("KPI-17", "Speed Humps", "safety", "vzv_speed_humps", "count", "COUNT(*)", None, True),
    ("KPI-18", "Raised Crosswalks", "safety", "raised_crosswalk_locations", "count", "COUNT(*)", None, True),
    ("KPI-19", "Leading Pedestrian Interval Signals", "safety", "vzv_leading_pedestrian_interval_signals", "count", "COUNT(*)", None, True),
    ("KPI-20", "Arterial Slow Zones", "safety", "vzv_arterial_slow_zones", "count", "COUNT(*)", None, False),
    ("KPI-21", "Neighborhood Slow Zones", "safety", "vzv_neighborhood_slow_zones", "count", "COUNT(*)", None, False),
    ("KPI-22", "Turn Traffic Calming Treatments", "safety", "vzv_turn_traffic_calming", "count", "COUNT(*)", None, True),
    ("KPI-23", "Safe Streets for Seniors Areas", "safety", "vzv_safe_streets_for_seniors", "count", "COUNT(*)", None, False),
    ("KPI-24", "Enhanced Crossings", "safety", "vzv_enhanced_crossings", "count", "COUNT(*)", None, True),
    # --- Condition ---------------------------------------------------------
    ("KPI-25", "Avg Street Pavement Rating", "condition", "street_pavement_ratings", "rating",
     "AVG(TRY_CAST(systemrating AS DOUBLE))", "systemrating IS NOT NULL", True),
    ("KPI-26", "Pothole Work Orders (closed)", "condition", "street_pothole_work_orders_closed_dataset", "count", "COUNT(*)", None, True),
    ("KPI-27", "Tree Damage Reports", "condition", "tree_damage", "count", "COUNT(*)", None, True),
    ("KPI-28", "Forestry Inspections", "condition", "forestry_inspections", "count", "COUNT(*)", None, True),
    # --- Demand / 311 ------------------------------------------------------
    ("KPI-29", "Sidewalk/Curb 311 Complaints", "demand", "complaints_311", "count", "COUNT(*)", None, True),
    ("KPI-30", "311 Closed Rate", "demand", "complaints_311", "percent",
     "100.0*AVG(CASE WHEN lower(CAST(status AS VARCHAR))='closed' THEN 1 ELSE 0 END)", None, False),
    # --- Capital / budget --------------------------------------------------
    ("KPI-31", "Total Capital Budget", "capital", "capital_projects_dashboard", "usd",
     "SUM(TRY_CAST(total_budget AS DOUBLE))", None, True),
    ("KPI-32", "Capital Spend To Date", "capital", "capital_projects_dashboard", "usd",
     "SUM(TRY_CAST(spend_to_date AS DOUBLE))", None, True),
    ("KPI-33", "Capital Projects (count)", "capital", "capital_projects_dashboard", "count", "COUNT(DISTINCT fms_id)", None, False),
    ("KPI-34", "State of Good Repair Needs", "capital", "state_of_good_repair_needs", "count", "COUNT(*)", None, False),
    ("KPI-35", "Capital Reconstruction Projects", "capital", "street_and_highway_capital_reconstruction_projec", "count", "COUNT(*)", None, True),
    # --- Pedestrianization / walkability ----------------------------------
    ("KPI-36", "Open Streets Locations", "walkability", "open_streets_locations", "count", "COUNT(*)", None, True),
    ("KPI-37", "Pedestrian Plazas", "walkability", "nyc_dot_pedestrian_plazas_polygon", "count", "COUNT(*)", None, True),
    ("KPI-38", "Public Plazas (planimetric)", "walkability", "public_plazas_planimetric", "count", "COUNT(*)", None, False),
    ("KPI-39", "Seating Locations", "walkability", "seating_locations", "count", "COUNT(*)", None, True),
    ("KPI-40", "Bus Stop Shelters", "walkability", "bus_stop_shelters", "count", "COUNT(*)", None, True),
    ("KPI-41", "Bicycle Parking", "walkability", "bicycle_parking", "count", "COUNT(*)", None, True),
    # --- Sidewalk inventory (planimetric) ---------------------------------
    ("KPI-42", "Sidewalk Polygons", "inventory", "sidewalk_planimetric", "count", "COUNT(*)", None, False),
    ("KPI-43", "Sidewalk Area (sqft)", "inventory", "sidewalk_planimetric", "sqft", "SUM(TRY_CAST(shape_area AS DOUBLE))", None, False),
    ("KPI-44", "Curb Features", "inventory", "curbs_planimetric", "count", "COUNT(*)", None, False),
    ("KPI-45", "Street Construction Permits", "coordination", "street_construction_permits", "count", "COUNT(*)", None, True),
]
BOROS = ("MANHATTAN", "BRONX", "BROOKLYN", "QUEENS", "STATEN ISLAND")


def main():
    load_dotenv(ROOT / ".env")
    load_dotenv()
    _tok = None if os.getenv("NYC_FORCE_LOCAL") == "1" else os.getenv("MOTHERDUCK_TOKEN")
    con = duckdb.connect(f"md:{DB}?token={_tok}" if _tok else f"{DB}.duckdb")
    con.execute("CREATE SCHEMA IF NOT EXISTS serving")

    catalog, byboro, registry, dropped = [], [], [], []
    for kid, name, dom, ds, unit, expr, where, byb in KPIS:
        src = f'{DB}.staging."{ds}"'
        w = f" WHERE {where}" if where else ""
        try:
            val = con.execute(f"SELECT {expr} FROM {src}{w}").fetchone()[0]
            if val is None:
                dropped.append((kid, name, "NULL result"))
                continue
            catalog.append((kid, name, dom, ds, unit, float(val), expr))
            registry.append({"kpi_id": kid, "name": name, "domain": dom, "dataset": ds,
                             "unit": unit, "formula": expr, "where": where,
                             "value": float(val), "by_borough": byb})
            if byb:
                wb = (where + " AND " if where else "") + "geo_borough IS NOT NULL"
                rows = con.execute(
                    f"SELECT geo_borough, {expr} FROM {src} WHERE {wb} GROUP BY geo_borough").fetchall()
                for b, v in rows:
                    if b in BOROS and v is not None:
                        byboro.append((kid, name, b, unit, float(v)))
        except Exception as e:
            dropped.append((kid, name, str(e)[:60]))

    # write serving tables
    con.execute("DROP TABLE IF EXISTS serving.kpi_catalog")
    con.execute("CREATE TABLE serving.kpi_catalog (kpi_id VARCHAR, kpi_name VARCHAR, domain VARCHAR, "
                "dataset VARCHAR, unit VARCHAR, value DOUBLE, formula VARCHAR, measurement_date DATE)")
    con.executemany("INSERT INTO serving.kpi_catalog VALUES (?,?,?,?,?,?,?,current_date)", catalog)
    con.execute("DROP TABLE IF EXISTS serving.kpi_by_borough")
    con.execute("CREATE TABLE serving.kpi_by_borough (kpi_id VARCHAR, kpi_name VARCHAR, borough VARCHAR, "
                "unit VARCHAR, value DOUBLE, measurement_date DATE)")
    con.executemany("INSERT INTO serving.kpi_by_borough VALUES (?,?,?,?,?,current_date)", byboro)
    con.close()

    out = ROOT / "config" / "kpi_registry_real.json"
    json.dump({"generated": "staging-computed", "total_kpis": len(registry),
               "kpis": registry}, open(out, "w"), indent=2)

    print(f"KPI catalog: {len(catalog)} citywide KPIs computed")
    print(f"Borough breakdown rows: {len(byboro)}")
    print(f"Registry written: {out} ({len(registry)} KPIs)")
    if dropped:
        print(f"\nDropped ({len(dropped)}):")
        for kid, nm, why in dropped:
            print(f"  {kid} {nm}: {why}")


if __name__ == "__main__":
    main()
