"""Advanced KPI expansion: SLA/turnaround, equity (HVI + demographics joins),
ratios, and time-series trends. Each KPI is a full SQL returning a scalar,
executed live — real values only, dropped if it fails. Appends to
serving.kpi_catalog + config/kpi_registry_real.json; builds serving.kpi_timeseries.
"""
import json
import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv

DB = "nyc_dot_analytics"
ROOT = Path(__file__).resolve().parents[2]
S = f"{DB}.staging"

# id, name, domain, unit, scalar_sql
ADV = [
    # --- SLA / turnaround (avg days, sane-bounded) -------------------------
    ("KPI-46", "Violation Resolution Days (avg)", "sla", "days",
     f"SELECT AVG(d) FROM (SELECT date_diff('day',TRY_CAST(vissuedate AS DATE),TRY_CAST(vdismissdate AS DATE)) d "
     f'FROM {S}."violations") WHERE d BETWEEN 0 AND 3650'),
    ("KPI-47", "Pothole Turnaround Days (avg)", "sla", "days",
     f"SELECT AVG(d) FROM (SELECT date_diff('day',TRY_CAST(rptdate AS DATE),TRY_CAST(rptclosed AS DATE)) d "
     f'FROM {S}."street_pothole_work_orders_closed_dataset") WHERE d BETWEEN 0 AND 3650'),
    ("KPI-48", "311 Sidewalk Complaint Turnaround Days (avg)", "sla", "days",
     f"SELECT AVG(d) FROM (SELECT date_diff('day',TRY_CAST(created_date AS DATE),TRY_CAST(closed_date AS DATE)) d "
     f'FROM {S}."complaints_311") WHERE d BETWEEN 0 AND 3650'),
    ("KPI-49", "Reinspection Turnaround Days (avg)", "sla", "days",
     f"SELECT AVG(d) FROM (SELECT date_diff('day',TRY_CAST(requestreinspectiondate AS DATE),TRY_CAST(actualreinspectdate AS DATE)) d "
     f'FROM {S}."reinspection") WHERE d BETWEEN 0 AND 3650'),
    # --- Equity: heat vulnerability (crashes.zip -> hvi.zcta20) ------------
    ("KPI-50", "Pedestrians Injured in High-Heat-Vuln Areas", "equity", "count",
     f"SELECT SUM(TRY_CAST(c.number_of_pedestrians_injured AS INTEGER)) "
     f'FROM {S}."motor_vehicle_collisions_crashes" c '
     f'JOIN {S}."heat_vulnerability_index" h ON CAST(c.zip_code AS VARCHAR)=CAST(h.zcta20 AS VARCHAR) '
     "WHERE TRY_CAST(h.hvi AS INTEGER) >= 4"),
    ("KPI-51", "% Pedestrian Injuries in High-Heat-Vuln Areas", "equity", "percent",
     f"SELECT 100.0 * SUM(CASE WHEN TRY_CAST(h.hvi AS INTEGER)>=4 THEN TRY_CAST(c.number_of_pedestrians_injured AS INTEGER) ELSE 0 END) "
     f"/ NULLIF(SUM(TRY_CAST(c.number_of_pedestrians_injured AS INTEGER)),0) "
     f'FROM {S}."motor_vehicle_collisions_crashes" c '
     f'JOIN {S}."heat_vulnerability_index" h ON CAST(c.zip_code AS VARCHAR)=CAST(h.zcta20 AS VARCHAR)'),
    # --- Equity: demographics (per-capita by NTA) -------------------------
    ("KPI-52", "311 Sidewalk Complaints per 1,000 Residents", "equity", "per_1k",
     f'SELECT 1000.0 * (SELECT COUNT(*) FROM {S}."complaints_311" WHERE geo_nta2020 IS NOT NULL) '
     f"/ NULLIF((SELECT SUM(TRY_CAST(total_population_2010_number AS DOUBLE)) "
     f'FROM {S}."census_demographics_nta"),0)'),
    ("KPI-53", "Violations per 1,000 Residents", "equity", "per_1k",
     f'SELECT 1000.0 * (SELECT COUNT(*) FROM {S}."violations" WHERE geo_nta2020 IS NOT NULL) '
     f"/ NULLIF((SELECT SUM(TRY_CAST(total_population_2010_number AS DOUBLE)) "
     f'FROM {S}."census_demographics_nta"),0)'),
    # --- Ratios ------------------------------------------------------------
    ("KPI-54", "Violations per Inspection", "ratio", "ratio",
     f'SELECT (SELECT COUNT(*) FROM {S}."violations")*1.0/NULLIF((SELECT COUNT(*) FROM {S}."inspection"),0)'),
    ("KPI-55", "Defect SqFt per Violation", "ratio", "sqft",
     f'SELECT (SELECT SUM(TRY_CAST(sq_feet AS DOUBLE)) FROM {S}."violations")/NULLIF((SELECT COUNT(*) FROM {S}."violations"),0)'),
    ("KPI-56", "Ramp Complaints per 1,000 Ramps", "ratio", "per_1k",
     f'SELECT 1000.0*(SELECT COUNT(*) FROM {S}."ramp_complaints")/NULLIF((SELECT COUNT(*) FROM {S}."ramp_progress"),0)'),
    ("KPI-57", "Pedestrian Fatality Rate (per 100 ped injuries)", "safety", "rate",
     f"SELECT 100.0*SUM(TRY_CAST(number_of_pedestrians_killed AS INTEGER))/NULLIF(SUM(TRY_CAST(number_of_pedestrians_injured AS INTEGER)),0) "
     f'FROM {S}."motor_vehicle_collisions_crashes"'),
    # --- Bike/ped sensor counts (ct66 daily aggregate) ---------------------
    ("KPI-58", "Bike+Ped Sensor Counts (all-time)", "walkability", "count",
     f'SELECT SUM(TRY_CAST(cnt AS DOUBLE)) FROM {DB}.raw."bicycle_pedestrian_counts_daily"'),
    ("KPI-59", "Pedestrian Sensor Counts (all-time)", "walkability", "count",
     f"SELECT SUM(TRY_CAST(cnt AS DOUBLE)) FROM {DB}.raw.\"bicycle_pedestrian_counts_daily\" "
     "WHERE lower(travelmode) LIKE '%ped%'"),
    # --- Gap-fill: composite condition index, per-capita safety, tree conflict ---
    ("KPI-67", "Defective Sidewalk Area % (SCI proxy)", "condition", "percent",
     f"SELECT 100.0 * (SELECT SUM(TRY_CAST(sq_feet AS DOUBLE))*0.092903 FROM {S}.\"violations\") "
     f"/ NULLIF((SELECT SUM(TRY_CAST(shape_area AS DOUBLE)) FROM {S}.\"sidewalk_planimetric\"),0)"),
    ("KPI-68", "Pedestrian Injuries per 100k Residents", "equity", "per_100k",
     f"SELECT 100000.0 * (SELECT SUM(TRY_CAST(number_of_pedestrians_injured AS INTEGER)) FROM {S}.\"motor_vehicle_collisions_crashes\") "
     f"/ NULLIF((SELECT SUM(TRY_CAST(total_population_2010_number AS DOUBLE)) FROM {S}.\"census_demographics_nta\"),0)"),
    ("KPI-69", "Tree-Related Violation %", "condition", "percent",
     f"SELECT 100.0 * (SELECT COUNT(DISTINCT violationid) FROM {S}.\"tree_damage\" WHERE violationid IS NOT NULL) "
     f"/ NULLIF((SELECT COUNT(*) FROM {S}.\"violations\"),0)"),
]

# time-series: label, metric_sql_select (returns yr,val), domain
TS = [
    ("Violations", "violations", "COUNT(*)"),
    ("Inspections", "inspection", "COUNT(*)"),
    ("Pedestrians Injured", "motor_vehicle_collisions_crashes", "SUM(TRY_CAST(number_of_pedestrians_injured AS INTEGER))"),
    ("Pedestrians Killed", "motor_vehicle_collisions_crashes", "SUM(TRY_CAST(number_of_pedestrians_killed AS INTEGER))"),
    ("311 Sidewalk Complaints", "complaints_311", "COUNT(*)"),
    ("Repair Dismissals", "dismissals", "COUNT(*)"),
]


def main():
    load_dotenv(ROOT / ".env")
    load_dotenv()
    _tok = None if os.getenv("NYC_FORCE_LOCAL") == "1" else os.getenv("MOTHERDUCK_TOKEN")
    con = duckdb.connect(f"md:{DB}?token={_tok}" if _tok else f"{DB}.duckdb")

    added, dropped = [], []
    for kid, name, dom, unit, sql in ADV:
        try:
            val = con.execute(sql).fetchone()[0]
            if val is None:
                dropped.append((kid, name, "NULL"))
                continue
            con.execute("INSERT INTO serving.kpi_catalog VALUES (?,?,?,?,?,?,?,current_date)",
                        [kid, name, dom, "(join)", unit, float(val), sql[:300]])
            added.append({"kpi_id": kid, "name": name, "domain": dom, "unit": unit,
                          "formula": sql, "value": float(val), "by_borough": False})
        except Exception as e:
            dropped.append((kid, name, str(e)[:70]))

    # time-series
    con.execute("DROP TABLE IF EXISTS serving.kpi_timeseries")
    con.execute("CREATE TABLE serving.kpi_timeseries (metric VARCHAR, year INTEGER, value DOUBLE)")
    ts_rows = 0
    for label, ds, agg in TS:
        try:
            rows = con.execute(
                f"SELECT year(geo_date_key) y, {agg} v FROM {S}.\"{ds}\" "
                f"WHERE geo_date_key IS NOT NULL AND year(geo_date_key) BETWEEN 2015 AND 2026 "
                f"GROUP BY y ORDER BY y").fetchall()
            for y, v in rows:
                if v is not None:
                    con.execute("INSERT INTO serving.kpi_timeseries VALUES (?,?,?)", [label, int(y), float(v)])
                    ts_rows += 1
        except Exception as e:
            dropped.append((f"TS:{label}", label, str(e)[:50]))
    con.close()

    # merge into registry
    reg_path = ROOT / "config" / "kpi_registry_real.json"
    reg = json.load(open(reg_path))
    reg["kpis"].extend(added)
    reg["total_kpis"] = len(reg["kpis"])
    json.dump(reg, open(reg_path, "w"), indent=2)

    print(f"advanced KPIs added: {len(added)} (catalog now {reg['total_kpis']})")
    print(f"time-series rows: {ts_rows}")
    if dropped:
        print("dropped:")
        for kid, nm, why in dropped:
            print(f"  {kid} {nm}: {why}")


if __name__ == "__main__":
    main()
