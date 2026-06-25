"""Split geometry layers by dimension (borough / NTA) and measure each piece.

Uses duckdb-spatial (github.com/duckdb/duckdb-spatial): ST_Intersection to clip
a feature to a dimension polygon, then ST_Length_Spheroid / ST_Area_Spheroid for
real-world meters (the_geom is WGS84 degrees). Produces serving.spatial_metrics:
per (layer, granularity, dim_value) length_m for lines, area_m2 for polygons.

Borough granularity uses 5 dissolved borough polygons (cheap); NTA granularity
uses the 262 NTA polygons (only for smaller layers, to bound compute).
"""
import os

import duckdb
from dotenv import load_dotenv

DB = "nyc_dot_analytics"
R = f"{DB}.raw"
S = f"{DB}.staging"

# (table, kind) — kind drives length vs area
LINE_LAYERS = [
    "new_york_city_bike_routes", "bus_lanes_local_streets", "vzv_priority_corridors",
    "open_streets_locations", "vzv_arterial_slow_zones", "protected_streets_block_dataset",
]
POLY_LAYERS = [
    "sidewalk_planimetric", "public_plazas_planimetric", "nyc_dot_pedestrian_plazas_polygon",
    "median_planimetric", "roadbed_planimetric",
]
# layers small enough for NTA-granularity (262 polygons)
NTA_OK = {"new_york_city_bike_routes", "bus_lanes_local_streets", "vzv_priority_corridors",
          "open_streets_locations", "vzv_arterial_slow_zones", "public_plazas_planimetric",
          "nyc_dot_pedestrian_plazas_polygon", "median_planimetric"}


def geom(expr):
    return f"ST_MakeValid(ST_GeomFromGeoJSON({expr}))"


def main():
    load_dotenv("C:/Users/ryudk/Desktop/nyc_data/.env")
    load_dotenv()
    _tok = None if os.getenv("NYC_FORCE_LOCAL") == "1" else os.getenv("MOTHERDUCK_TOKEN")
    con = duckdb.connect(f"md:{DB}?token={_tok}" if _tok else f"{DB}.duckdb")
    con.execute("LOAD spatial")
    con.execute("CREATE SCHEMA IF NOT EXISTS serving")

    # Dissolve NTAs -> 5 borough polygons (cheap dimension for big layers).
    con.execute(f"""CREATE OR REPLACE TABLE serving.dim_borough_geom AS
        SELECT boroname AS borough, ST_Union_Agg({geom('the_geom')}) AS g
        FROM {R}."nta_2020" WHERE the_geom IS NOT NULL GROUP BY boroname""")
    con.execute(f"""CREATE OR REPLACE TABLE serving.dim_nta_geom AS
        SELECT boroname AS borough, nta2020, {geom('the_geom')} AS g
        FROM {R}."nta_2020" WHERE the_geom IS NOT NULL""")

    con.execute("DROP TABLE IF EXISTS serving.spatial_metrics")
    con.execute("CREATE TABLE serving.spatial_metrics (layer VARCHAR, kind VARCHAR, "
                "granularity VARCHAR, borough VARCHAR, nta2020 VARCHAR, features BIGINT, "
                "length_m DOUBLE, area_m2 DOUBLE)")

    def run(layer, kind, dim_tbl, gran):
        measure = ("SUM(ST_Length_Spheroid(ST_Intersection(s.g, d.g)))" if kind == "line"
                   else "SUM(ST_Area_Spheroid(ST_Intersection(s.g, d.g)))")
        ncol = "d.nta2020" if gran == "nta" else "NULL"
        col = "length_m" if kind == "line" else "area_m2"
        other = "area_m2" if kind == "line" else "length_m"
        con.execute(f"""INSERT INTO serving.spatial_metrics
            (layer, kind, granularity, borough, nta2020, features, {col}, {other})
            SELECT '{layer}','{kind}','{gran}', d.borough, {ncol}, COUNT(*), {measure}, NULL
            FROM (SELECT {geom('the_geom')} AS g FROM {S}."{layer}" WHERE the_geom IS NOT NULL) s
            JOIN serving.{dim_tbl} d ON ST_Intersects(s.g, d.g)
            GROUP BY d.borough{', d.nta2020' if gran=='nta' else ''}""")

    done = []
    for layer in LINE_LAYERS + POLY_LAYERS:
        kind = "line" if layer in LINE_LAYERS else "polygon"
        try:
            run(layer, kind, "dim_borough_geom", "borough")
            if layer in NTA_OK:
                run(layer, kind, "dim_nta_geom", "nta")
            done.append(layer)
            print(f"  split {layer} ({kind})", flush=True)
        except Exception as e:
            print(f"  ERR {layer}: {str(e)[:70]}", flush=True)
    con.close()
    print(f"\nspatial_metrics built for {len(done)} layers")


if __name__ == "__main__":
    main()
