# Operations Management & Automation Guide

This document outlines the architecture and operational playbook for turning raw 311 and GIS data into proactive, prioritized actions for NYC DOT.

## Key concepts
- Early Warning System: Detect conflicts, SLA breaches, and resource overload before they impact delivery.
- Batch vs Streaming: Use streaming mode for low-memory runs; use bulk COPY for nightly large loads.
- PostGIS-first: Spatial joins and heavy lifting belong in the database for scale.

## Components
- Ingest: SocrataClient streaming fetch (page-by-page), transform to canonical schema.
- Store: Postgres/PostGIS for authoritative storage; Mongo for denormalized operational state.
- Analyze: Use Python modules (`ops`, `conflict`, `relevance`) to compute KPIs and rankings.
- Notify: `alerts.AlertManager` routes to CLI, email, and DB.

## Nightly job outline
1. Fetch deltas using `client.fetch_since()` with a stored high-watermark.
2. Load into staging tables using `PostgresExporter.copy_upsert_batches()`.
3. Refresh materialized `construction_lists` view.
4. Run `PostGISConflictResolver` against `permits` and `active_projects`.
5. Produce KPIs and push alerts through the `AlertManager`.

## Recommended Postgres schema additions
- `alerts` table: persistent store of issued alerts (see `docs/sop_faq.md`).
- `construction_lists` materialized view: pre-computed lists for each contractor.
- `permits` and `active_projects` partitioned by borough for scale.

## Example: Grace Period automation
Implement a scheduled job that reads from `violations`:

```sql
UPDATE violations
SET status = 'City-Initiated'
WHERE date_part('day', now() - issued_date) > COALESCE(grace_pd, 75)
  AND status = 'Pending Repair';
```

This SQL can be converted into a Python method with `psycopg` and scheduled in your orchestration layer.
