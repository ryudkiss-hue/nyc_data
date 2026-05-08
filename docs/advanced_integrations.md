# Advanced Integrations & Data Sources

This file lists recommended external datasets, integration notes, and short SQL samples to connect them with your PostGIS-backed operational DB.

## High-Precision Asset Layers (priority)

- DEP Green Infrastructure (porous pavement, bioswales)
  - Use: prevent paving over sensitive environmental assets
  - Key columns: `gi_id`, `geom`, `type`, `installation_date`

- Parks: Trees & Sidewalks program
  - Use: identify tree-caused sidewalk damage and route to tree-removal workflows
  - Key columns: `tree_id`, `geom`, `species`, `ownership` (city vs private)

## Permits & Licensing

- DCWP Contractor Licenses
  - Use: validate contractor eligibility automatically prior to list approval

- Parks Permits
  - Use: ensure contractors have both DCWP and Parks permits for works near street trees

## Example SQL: join proposed locations with green infrastructure
```sql
SELECT p.*, g.gi_id
FROM proposed_work p
LEFT JOIN dep_green_infra g
  ON ST_DWithin(p.geom::geography, g.geom::geography, 10)
WHERE g.gi_id IS NOT NULL;
```

## 3D City Twin integration (overview)

- PostGIS can be exported to 3D formats (CityGML / 3D Tiles). For ramp calculations, export cross-sections with elevation attributes and compute localized slopes.
- This is typically an offline step and can be implemented via a small ETL: PostGIS -> GeoPackage -> external 3D toolchain.

## Integration checklist
1. Map fields and define canonical names (`id`, `geom`, `effective_date`, `source`)
2. Decide storage schema (partitioning by borough is recommended)
3. Add ingestion jobs and metadata entries to `_socrata_metadata`
