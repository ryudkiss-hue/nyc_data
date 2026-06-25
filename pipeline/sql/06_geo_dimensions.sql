-- ============================================================================
-- Geo + Date Conformed Dimensions  (geographic unification backbone)
-- ============================================================================
-- Conformed dimensions every operational table links to after the geo-conform
-- transform stamps borough/nta2020/segment_id/bbl/date_key onto staging tables.
--   dim_nta     <- nta_2020            (NTA + borough; polygons in raw for PIP)
--   dim_segment <- street_centerline   (LION physicalid + b5sc; lines in raw)
--   dim_parcel  <- lot_info            (BBL; ZOLA-grade parcel key)
--   dim_zcta    <- heat_vulnerability_index (ZIP/ZCTA + HVI)
--   dim_date    <- generated spine
-- Geometry stays in raw (GeoJSON); spatial joins parse it inline via
-- ST_GeomFromGeoJSON during the conform step.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS nyc_dot_analytics.geo;

CREATE OR REPLACE TABLE nyc_dot_analytics.geo.dim_date AS
SELECT d AS date_key,
       year(d)    AS year,
       month(d)   AS month,
       quarter(d) AS quarter,
       strftime(d, '%Y-%m') AS year_month,
       dayofweek(d) AS day_of_week
FROM (SELECT unnest(generate_series(DATE '2010-01-01', DATE '2027-12-31',
                                    INTERVAL 1 DAY)) AS d);

CREATE OR REPLACE TABLE nyc_dot_analytics.geo.dim_nta AS
SELECT nta2020, ntaname, boroname AS borough, borocode, cdta2020, cdtaname
FROM nyc_dot_analytics.raw."nta_2020"
WHERE nta2020 IS NOT NULL;

CREATE OR REPLACE TABLE nyc_dot_analytics.geo.dim_segment AS
SELECT * FROM (
  SELECT physicalid, b5sc, full_street_name AS street_name, stname_label, rw_type,
         CASE substr(CAST(boroughcode AS VARCHAR), 1, 1)
              WHEN '1' THEN 'MANHATTAN' WHEN '2' THEN 'BRONX'
              WHEN '3' THEN 'BROOKLYN'  WHEN '4' THEN 'QUEENS'
              WHEN '5' THEN 'STATEN ISLAND' END AS borough
  FROM nyc_dot_analytics.raw."street_centerline"
  WHERE physicalid IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (PARTITION BY physicalid ORDER BY 1) = 1
);

CREATE OR REPLACE TABLE nyc_dot_analytics.geo.dim_parcel AS
SELECT * FROM (
  SELECT bblid AS bbl, boro, block, lot, zipcode,
         CASE substr(CAST(bblid AS VARCHAR), 1, 1)
              WHEN '1' THEN 'MANHATTAN' WHEN '2' THEN 'BRONX'
              WHEN '3' THEN 'BROOKLYN'  WHEN '4' THEN 'QUEENS'
              WHEN '5' THEN 'STATEN ISLAND' END AS borough
  FROM nyc_dot_analytics.raw."lot_info"
  WHERE bblid IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (PARTITION BY bblid ORDER BY 1) = 1
);

CREATE OR REPLACE TABLE nyc_dot_analytics.geo.dim_zcta AS
SELECT zcta20, TRY_CAST(hvi AS INTEGER) AS hvi
FROM nyc_dot_analytics.raw."heat_vulnerability_index"
WHERE zcta20 IS NOT NULL;
