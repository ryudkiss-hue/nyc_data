# SOP, FAQ, and Operational Playbook

This document provides Standard Operating Procedures (SOPs), Frequently Asked Questions (FAQ), and step-by-step guides for the core operational workflows supported by the Socrata Toolkit deploy for NYC DOT analysts.

---

## Table of contents
- SOP: Daily Morning Brief (email + CLI)
- SOP: Running a conflict detection sweep (90-day permit look-ahead)
- SOP: Generating and approving a construction list
- FAQ: Common issues and troubleshooting
- SOP: Triggering High-Priority flags and audit logs
- Operational checklist for integrating external datasets

---

## SOP: Daily Morning Brief (email + CLI)

Purpose: Produce a short, prioritized digest of operational items for program managers and field leads.

Steps:
1. Run the nightly batch job (Postgres) which materializes `construction_lists` and `alerts` tables.
2. Generate the burndown and KPI summary using `socrata_toolkit.ops.generate_burndown()`.
3. Use `socrata_toolkit.alerts.AlertManager` to assemble alerts into a single email and CLI summary.
4. Email recipients (configurable) receive attachments: `daily_construction_list.csv`, `kpi_summary.json`.

CLI example (local run):
```bash
# preview summary
python -m socrata_toolkit.cli alerts --preview

# send email (requires SMTP config in env or config yaml)
python -m socrata_toolkit.cli alerts --send --recipients ops@dot.nyc.gov
```

Notes:
- The email uses batched alerts to avoid spamming staff with one-alert-per-incident.
- Use `--filter-borough=Manhattan` to focus the digest.

---

## SOP: Running a conflict detection sweep (90-day permit look-ahead)

Purpose: Ensure upcoming permits and active projects do not collide with proposed repairs.

Recommended frequency: nightly (batch) + ad-hoc before producing a construction list.

Workflow:
1. Materialize the latest `permits` and `active_projects` tables in Postgres with geometry columns populated.
2. Run a permit look-ahead to identify permits starting within the next 90 days:
   - Use `socrata_toolkit.ops.permit_lookahead(conn, days=90, permit_table='permits', target_table='construction_lists')`.
3. Re-run `PostGISConflictResolver.resolve_conflicts()` on the proposed list but include `permits` as a reference layer.
4. Move rows with conflicts into the `Pending Review - Permits` queue and notify relevant parties.

Practical tips:
- Use spatial indexes (`GIST`) on geometry columns for performance.
- If you cannot run PostGIS jobs, run the streaming `socrata_toolkit.stream_pipeline` for an approximate, low-memory check.

---

## SOP: Generating and approving a construction list

Purpose: Produce an actionable list for contractor assignment.

Steps:
1. Derive the candidate list via `PostGISConflictResolver` or `ConflictResolver` (Shapely) depending on dataset size.
2. Run `socrata_toolkit.compliance.validate_contractor_for_list()` to ensure the contractor assigned holds the necessary DCWP license and Parks permits.
3. Use `socrata_toolkit.ops.generate_burndown()` to simulate schedule pressure and contractor capacity.
4. Approve the list and export via `XLSXExporter` or `Contractor Portal` CSV.

Approval checklist (manual):
- [ ] Contractor license verified
- [ ] No permit conflicts within 90 days for this block
- [ ] High-priority items flagged and assigned

---

## FAQ: Common issues and troubleshooting

Q: The Postgres upsert fails with `duplicate key` errors.
A: Ensure the `conflict_column` is present and indexed. Use `PostgresExporter.copy_upsert_batches()` for large loads; it stages into a temp table then performs an `INSERT ... ON CONFLICT`.

Q: Streamlit dashboard runs out of memory on large datasets.
A: Enable streaming mode in the Workbench (checkbox) which processes rows page-by-page instead of loading them all.

Q: My GeoJSON export is missing geometries.
A: Ensure the dataset has a valid GeoJSON geometry column or run `client.fetch_geojson()` instead of `fetch_json()`.

---

## SOP: Triggering High-Priority flags and audit logs

When a 311 complaint occurs on a high-pedestrian 'Smart Spine' corridor, it's useful to escalate automatically. Use the sample SQL template in `docs/sql_templates.md` (or inlined in this repo) to create a Postgres trigger that sets `is_high_priority = TRUE` when `ST_Intersects(geom, smart_spine.geom)`.

Minimal SQL (sample):
```sql
CREATE TABLE IF NOT EXISTS alerts (
  id SERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT now(),
  severity TEXT,
  message TEXT,
  payload JSONB
);

CREATE OR REPLACE FUNCTION flag_high_priority()
RETURNS trigger AS $$
BEGIN
  IF (NEW.geom IS NOT NULL AND
      EXISTS(SELECT 1 FROM smart_spine s WHERE ST_Intersects(NEW.geom, s.geom))) THEN
    NEW.is_high_priority := TRUE;
    INSERT INTO alerts (severity, message, payload) VALUES ('critical', 'SmartSpine conflict', to_jsonb(NEW));
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_flag_high_priority
BEFORE INSERT OR UPDATE ON sidewalk_complaints
FOR EACH ROW EXECUTE FUNCTION flag_high_priority();
```

---

## Data sources and integration checklist

For the highest-fidelity early-warning system, add the following datasets to your nightly ETL:
- DEP Green Infrastructure (porous pavement and bioswales)
- Parks: Tree inventories and Trees & Sidewalk program
- DCWP License database and Parks Permits
- Sidewalk Management Database (violations + re-inspections)
- Street Opening Permits and Pavement Ratings

When integrating each dataset:
1. Confirm column mapping (unique id, geometry column, effective date)
2. Add a materialized table in Postgres with proper indexes (GIST for geometry, BTree for IDs)
3. Annotate the dataset in the metadata table (`_socrata_metadata`) for observability

---

## Contact / Change log
- Authors: Socrata Toolkit enhancements team
- For operational changes, increment the `alerts` schema and notify the DBAs before production changes.
