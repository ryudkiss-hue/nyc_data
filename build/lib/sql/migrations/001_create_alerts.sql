-- Migration: create alerts table used by the toolkit
-- Run this on your Postgres/PostGIS database before enabling DB-based alert persistence.

CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now(),
    severity TEXT,
    message TEXT,
    payload JSONB
);

-- Optional: create a simple smart_spine table used by trigger templates.
CREATE TABLE IF NOT EXISTS smart_spine (
    id SERIAL PRIMARY KEY,
    name TEXT,
    geom GEOMETRY(Geometry, 4326)
);
