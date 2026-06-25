"""Geographic conform transform — unify every staging table on shared geo keys.

Stamps a standard key set onto each staging table so all tables join to the geo
dimensions (geo.dim_nta / dim_segment / dim_parcel / dim_zcta / dim_date):

    geo_borough, geo_nta2020, geo_bbl, geo_segment_id, geo_date_key, geo_tier

Three tiers, cheapest first (a table uses the best it can reach):
  Tier 1 DIRECT  - derive from columns already present (borough / BBL / NTA /
                   community district / boro_cb / BBL components / physicalid).
  Tier 2 SPATIAL - tables with the_geom or lat/long but no admin key: point-in-
                   polygon into raw.nta_2020 (GeoJSON) -> nta2020 + borough.
  Tier 3 GEOCODE - address-only tables: Geosupport (pipeline/geo/geocode.py).

Run:  python pipeline/geo/conform.py            (all staging tables)
      python pipeline/geo/conform.py <table>... (specific tables)
"""
from __future__ import annotations

import os
import sys

import duckdb
from dotenv import load_dotenv

DB = "nyc_dot_analytics"
BORO_FROM_DIGIT = {"1": "MANHATTAN", "2": "BRONX", "3": "BROOKLYN", "4": "QUEENS", "5": "STATEN ISLAND"}
NTA_PREFIX = {"MN": "MANHATTAN", "BX": "BRONX", "BK": "BROOKLYN", "QN": "QUEENS", "SI": "STATEN ISLAND"}

# the_geom/geom first; 'location'/'geometry' are point columns on some feeds
# (e.g. forestry). The GeoJSON guard in the spatial branch skips non-JSON text.
GEOM_COLS = ("the_geom", "geom", "location", "geometry", "geom2", "wkt", "locationgeometry")
LAT = ("latitude", "lat", "y_sp", "y_coord")
LON = ("longitude", "lon", "x_sp", "x_coord")
BORO_COLS = ("borough", "boroname", "borough_name", "boroughname", "boroughnam",
             "borocode", "boro", "boro_name", "propertyborough")
NTA_COLS = ("nta2020", "nta", "ntacode", "nta_code",
            "geographic_area_neighborhood_tabulation_area_nta_code")
CD_COLS = ("community_district", "communityboard", "community_board", "cb",
           "commboard", "boro_cb", "communitydistrict")
DATE_HINTS = ("date", "_dt", "issued", "created", "inspection", "crash", "complaint", "year")


def connect():
    load_dotenv("C:/Users/ryudk/Desktop/nyc_data/.env")
    load_dotenv()
    _tok = None if os.getenv("NYC_FORCE_LOCAL") == "1" else os.getenv("MOTHERDUCK_TOKEN")
    con = duckdb.connect(f"md:{DB}?token={_tok}" if _tok else f"{DB}.duckdb")
    con.execute("LOAD spatial")
    con.execute("SET preserve_insertion_order=false")
    return con


def staging_tables(con):
    return [r[0] for r in con.execute(
        f"SELECT table_name FROM information_schema.tables "
        f"WHERE table_catalog='{DB}' AND table_schema='staging' ORDER BY table_name").fetchall()]


def cols_of(con, t):
    return [c[0] for c in con.execute(f'SELECT * FROM {DB}.staging."{t}" LIMIT 0').description]


def _first(cols, candidates):
    low = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand in low:
            return low[cand]
    return None


def _find_boro(cols):
    """Borough column, in preference order: exact name -> coded -> loose.
    Excludes flags ('borough_indicator') and community-district columns, which
    are not borough values."""
    names = ("boroname", "boro_name", "borough", "borough_name", "boroughname",
             "boroughnam", "propertyborough")
    codes = ("boroughcode", "borocode", "borocd", "boro", "boro_code", "borough_code")

    def bad(cl):
        return "communit" in cl or "indicator" in cl or "flag" in cl

    for c in cols:  # pass 1: exact clean borough-name columns
        if not bad(c.lower()) and c.lower() in names:
            return c
    for c in cols:  # pass 2: coded borough columns
        if not bad(c.lower()) and c.lower() in codes:
            return c
    for c in cols:  # pass 3: loose 'borough' substring (last resort)
        cl = c.lower()
        if not bad(cl) and "borough" in cl and "code" not in cl and "cd" not in cl:
            return c
    return None


def _find_cd(cols):
    """Community district / boro_cb column (any prefix)."""
    for c in cols:
        cl = c.lower()
        if "communit" in cl or cl in ("cb", "cd", "boro_cb", "commboard", "comm_dist"):
            return c
    return None


def _find_seg(cols):
    """LION segment id column (physicalid / *segment_id)."""
    for c in cols:
        cl = c.lower()
        if cl == "physicalid" or "segmentid" in cl or "segment_id" in cl:
            return c
    return None


def _boro_norm(expr):
    # Normalize any borough text/code expression to a standard name.
    # Clean: strip parens/commas/periods and a trailing ' NY', uppercase, trim.
    c = f"trim(upper(regexp_replace(CAST({expr} AS VARCHAR), '[(),.]| NY$', '', 'g')))"
    # NYC single-letter codes: M/X/B/Q/R (std), plus K(ings), S(taten) seen in feeds.
    return (f"CASE WHEN {c} IN ('1','M','MN','MANHATTAN','NEW YORK','NEWYORK') THEN 'MANHATTAN' "
            f"WHEN {c} IN ('2','X','BX','BRONX') THEN 'BRONX' "
            f"WHEN {c} IN ('3','B','K','BK','BROOKLYN','KINGS') THEN 'BROOKLYN' "
            f"WHEN {c} IN ('4','Q','QN','QUEENS') THEN 'QUEENS' "
            f"WHEN {c} IN ('5','R','S','SI','STATEN ISLAND','STATENISLAND','RICHMOND') THEN 'STATEN ISLAND' "
            f"WHEN {c} LIKE '%MANHATTAN%' THEN 'MANHATTAN' WHEN {c} LIKE '%BRONX%' THEN 'BRONX' "
            f"WHEN {c} LIKE '%BROOKLYN%' THEN 'BROOKLYN' WHEN {c} LIKE '%QUEENS%' THEN 'QUEENS' "
            f"WHEN {c} LIKE '%STATEN%' THEN 'STATEN ISLAND' END")


def build_plan(cols, q="s."):
    """Return (bbl, boro, nta, seg, date_expr, has_geom, has_ll).
    Column refs are prefixed with alias `q` so exprs stay unambiguous when the
    staging table is joined to nta_2020 (which shares names like nta2020)."""
    low = {c.lower(): c for c in cols}

    def col(name):
        return f'{q}"{name}"'

    # BBL
    bbl = None
    if "bblid" in low:
        bbl = f"NULLIF(regexp_replace(CAST({col(low['bblid'])} AS VARCHAR),'[^0-9]','','g'),'')"
    elif "bbl" in low:
        bbl = f"NULLIF(regexp_replace(CAST({col(low['bbl'])} AS VARCHAR),'[^0-9]','','g'),'')"
    elif {"propertyborough", "propertyblock", "propertylot"} <= set(low):
        bbl = (f"CAST({col(low['propertyborough'])} AS VARCHAR) || "
               f"lpad(CAST({col(low['propertyblock'])} AS VARCHAR),5,'0') || "
               f"lpad(CAST({col(low['propertylot'])} AS VARCHAR),4,'0')")

    # NTA
    nta_col = _first(cols, NTA_COLS)
    nta = f"CAST({col(nta_col)} AS VARCHAR)" if nta_col else None

    # Borough (cheapest first)
    boro_col = _find_boro(cols)
    cd_col = _find_cd(cols)
    if boro_col:
        boro = _boro_norm(col(boro_col))
    elif bbl:
        boro = f"CASE substr({bbl},1,1) " + " ".join(
            f"WHEN '{k}' THEN '{v}'" for k, v in BORO_FROM_DIGIT.items()) + " END"
    elif nta_col:
        boro = f"CASE substr(upper(CAST({col(nta_col)} AS VARCHAR)),1,2) " + " ".join(
            f"WHEN '{k}' THEN '{v}'" for k, v in NTA_PREFIX.items()) + " END"
    elif cd_col:
        boro = (f"CASE substr(regexp_replace(CAST({col(cd_col)} AS VARCHAR),'[^0-9]','','g'),1,1) "
                + " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in BORO_FROM_DIGIT.items()) + " END")
    else:
        boro = None

    # Segment
    seg_col = _find_seg(cols)
    seg = f"CAST({col(seg_col)} AS VARCHAR)" if seg_col else None

    # Date key: first date-like column
    date_col = None
    for c in cols:
        if any(h in c.lower() for h in DATE_HINTS):
            date_col = c
            break
    date_expr = f"TRY_CAST({col(date_col)} AS DATE)" if date_col else None

    has_geom = _first(cols, GEOM_COLS)
    has_ll = _first(cols, LAT) and _first(cols, LON)
    return bbl, boro, nta, seg, date_expr, has_geom, has_ll


def conform_table(con, t):
    cols = cols_of(con, t)
    # idempotent: rebuild from base columns (drop any prior geo_* columns)
    base = [c for c in cols if not c.lower().startswith("geo_")]
    bbl, boro, nta, seg, date_expr, has_geom, has_ll = build_plan(base, "s.")
    sel_s = ", ".join('s."' + c + '"' for c in base)
    src = f'{DB}.staging."{t}"'
    do_spatial = bool(has_geom or has_ll)

    if do_spatial:
        # Representative point: lat/long if present, else a point guaranteed ON
        # the geometry (ST_PointOnSurface) — avoids ST_Centroid dangling off
        # lines/concave polygons into the void. ST_MakeValid repairs bad geom.
        if has_ll:
            lat = _first(base, LAT)
            lon = _first(base, LON)
            pt = f'ST_Point(TRY_CAST(s."{lon}" AS DOUBLE), TRY_CAST(s."{lat}" AS DOUBLE))'
        else:
            g = f's."{has_geom}"'
            pt = (f"CASE WHEN starts_with(trim(CAST({g} AS VARCHAR)), '{{') "
                  f"THEN ST_PointOnSurface(ST_MakeValid(ST_GeomFromGeoJSON({g}))) END")
        # Direct column wins for borough/nta; spatial NTA enriches the rest.
        boro_expr = f"COALESCE({boro}, n.boroname)" if boro else "n.boroname"
        nta_expr = f"COALESCE({nta}, n.nta2020)" if nta else "n.nta2020"
        tier = "1+spatial" if boro else "2-spatial"
        # Compute each row's representative point ONCE (MATERIALIZED CTE) and join
        # to PRE-PARSED polygons (geo._nta_poly). The old form re-parsed the NTA
        # GeoJSON inside the ON clause for every row-pair (~131M times on the 502K
        # line table) -> native segfault. This parses each polygon once.
        q = (f'CREATE OR REPLACE TABLE {src} AS '
             f'WITH s AS MATERIALIZED (SELECT {sel_s}, {pt} AS _geo_pt FROM {src} s) '
             f'SELECT {sel_s}, '
             f"{boro_expr} AS geo_borough, {nta_expr} AS geo_nta2020, "
             f"{bbl or 'NULL'} AS geo_bbl, {seg or 'NULL'} AS geo_segment_id, "
             f"{date_expr or 'NULL'} AS geo_date_key, '{tier}' AS geo_tier "
             f'FROM s LEFT JOIN {DB}.geo."_nta_poly" n '
             f"ON s._geo_pt IS NOT NULL AND ST_Contains(n.geom, s._geo_pt)")
    else:
        tier = "1-direct" if boro else "0-none"
        q = (f'CREATE OR REPLACE TABLE {src} AS SELECT {sel_s}, '
             f"{boro or 'NULL'} AS geo_borough, {nta or 'NULL'} AS geo_nta2020, "
             f"{bbl or 'NULL'} AS geo_bbl, {seg or 'NULL'} AS geo_segment_id, "
             f"{date_expr or 'NULL'} AS geo_date_key, '{tier}' AS geo_tier "
             f'FROM {src} s')
    con.execute(q)
    n, b = con.execute(f'SELECT COUNT(*), COUNT(geo_borough) FROM {src}').fetchone()
    return tier, n, b


def _config_names():
    import json
    cfg = json.load(open("pipeline/config/socrata_datasets.json"))
    return {d["name"] for d in cfg["socrata_remaining"]}, cfg["socrata_remaining"]


# Tables whose borough comes from an entity FK to an already-conformed table.
FK_BOROUGH = {
    "motor_vehicle_collisions_person": ("motor_vehicle_collisions_crashes", "collision_id"),
    "street_construction_permits_cranes": ("street_construction_permits", "permitnumber"),
}


def fk_borough_pass(con):
    """Fill geo_borough via entity FK for tables that join to a conformed table."""
    filled = []
    for t, (parent, key) in FK_BOROUGH.items():
        src = f'{DB}.staging."{t}"'
        par = f'{DB}.staging."{parent}"'
        try:
            cols = [c for c in cols_of(con, t)]
            if key not in cols:
                continue
            base = [c for c in cols if not c.lower().startswith("geo_")]
            keep = [c for c in cols if c.lower().startswith("geo_") and c != "geo_borough"]
            sel = ", ".join('s."' + c + '"' for c in base + keep)
            con.execute(
                f'CREATE OR REPLACE TABLE {src} AS SELECT {sel}, '
                f"p.geo_borough AS geo_borough "
                f'FROM {src} s LEFT JOIN (SELECT DISTINCT "{key}", geo_borough FROM {par} '
                f'WHERE geo_borough IS NOT NULL) p ON s."{key}"=p."{key}"')
            n, b = con.execute(f'SELECT COUNT(*), COUNT(geo_borough) FROM {src}').fetchone()
            filled.append((t, n, b))
        except Exception as e:
            filled.append((t, -1, str(e)[:60]))
    return filled


def main():
    con = connect()
    # Resource guards: bound threads/memory so heavy spatial joins spill instead
    # of crashing the spatial extension on giant line tables.
    for pragma in ("SET threads=4", "SET preserve_insertion_order=false"):
        try:
            con.execute(pragma)
        except Exception:
            pass
    # Pre-parse NTA polygons ONCE (262 rows) so the per-table spatial join never
    # re-parses GeoJSON in its ON clause (the segfault cause).
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {DB}.geo")
    con.execute(
        f'CREATE OR REPLACE TABLE {DB}.geo."_nta_poly" AS '
        f"SELECT boroname, nta2020, ST_MakeValid(ST_GeomFromGeoJSON(the_geom)) AS geom "
        f'FROM {DB}.raw."nta_2020" WHERE the_geom IS NOT NULL')
    names, _ = _config_names()
    targets = sys.argv[1:] or [t for t in staging_tables(con) if t in names]
    print(f"conforming {len(targets)} staging tables (config-backed; junk skipped)")
    summary = {"1-direct": 0, "2-spatial": 0, "0-none": 0}
    for t in targets:
        try:
            tier, n, b = conform_table(con, t)
            summary[tier] = summary.get(tier, 0) + 1
            pct = (100 * b / n) if n else 0
            print(f"  [{tier}] {t:46s} borough {b:>9,}/{n:<9,} ({pct:5.1f}%)")
        except Exception as e:
            print(f"  [ERR] {t}: {str(e)[:80]}")
    print("tier counts:", summary)
    print("FK-borough pass:")
    for t, n, b in fk_borough_pass(con):
        print(f"  {t}: borough {b}/{n}" if n >= 0 else f"  {t}: ERR {b}")
    con.close()


if __name__ == "__main__":
    main()
