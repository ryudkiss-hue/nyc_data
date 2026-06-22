-- Staging Schema - promotion + dedup on REAL keys (auto-generated 2026-06-22)
-- Generated from live MotherDuck raw schema column introspection.
-- Datasets with a natural key are deduped; geometry/keyless tables promoted as-is.

CREATE SCHEMA IF NOT EXISTS staging;

CREATE OR REPLACE TABLE staging."inspection" AS
SELECT * FROM raw."inspection"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "inspectionid" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."violations" AS
SELECT * FROM raw."violations"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "swv_number" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."reinspection" AS
SELECT * FROM raw."reinspection"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "reinspectionid" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."lot_info" AS
SELECT * FROM raw."lot_info"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "bblid" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."built" AS
SELECT * FROM raw."built"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "bblid" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."dismissals" AS
SELECT * FROM raw."dismissals"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "sr" ORDER BY 1 DESC) = 1;

CREATE OR REPLACE TABLE staging."tree_damage" AS
SELECT * FROM raw."tree_damage"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "atdid" ORDER BY 1 DESC) = 1;

-- correspondences: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."correspondences" AS SELECT * FROM raw."correspondences";

-- ramp_progress: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."ramp_progress" AS SELECT * FROM raw."ramp_progress";

CREATE OR REPLACE TABLE staging."ramp_complaints" AS
SELECT * FROM raw."ramp_complaints"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "cmt_corner_id" ORDER BY 1 DESC) = 1;

-- ramp_locations: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."ramp_locations" AS SELECT * FROM raw."ramp_locations";

CREATE OR REPLACE TABLE staging."curb_metal_protruding" AS
SELECT * FROM raw."curb_metal_protruding"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "sr" ORDER BY 1 DESC) = 1;

-- step_streets: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."step_streets" AS SELECT * FROM raw."step_streets";

CREATE OR REPLACE TABLE staging."street_resurfacing_schedule" AS
SELECT * FROM raw."street_resurfacing_schedule"
QUALIFY ROW_NUMBER() OVER (PARTITION BY "workscheduleprojectlocationid" ORDER BY 1 DESC) = 1;

-- weekly_construction: no natural key -> promote as-is
CREATE OR REPLACE TABLE staging."weekly_construction" AS SELECT * FROM raw."weekly_construction";

-- pedestrian_demand: geometry table -> promote as-is
CREATE OR REPLACE TABLE staging."pedestrian_demand" AS SELECT * FROM raw."pedestrian_demand";
