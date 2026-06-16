# Dataset Registry

Catalog of 26 NYC Open Data datasets integrated with this toolkit.

## Core SIM Data (Inspection & Violations)

| Key | Dataset | Fourfour | Rows | Freshness | Notes |
|-----|---------|----------|------|-----------|-------|
| `inspection` | Sidewalk Inspection Data | dntt-gqwq | ~398K | Daily | Primary inspection records |
| `violations` | Violation Data | 6kbp-uz6m | ~312K | Daily | Violation details by inspection |
| `dismissals` | Dismissed Complaints | p4u2-3jgx | ~85K | Daily | Closed/dismissed cases |
| `reinspection` | Reinspection Results | gx72-kirf | ~36K | Weekly | Follow-up inspection data |
| `correspondences` | Communication Records | bheb-sjfi | ~30K | Monthly | Agency correspondence |
| `tree_damage` | Tree Damage Assessments | j6v2-6uxq | ~17K | Monthly | Sidewalk tree damage |
| `curb_metal_protruding` | Curb Hazards | i2y3-sx2e | ~23K | Monthly | Metal protruding hazards |
| `built` | Construction Data | ugc8-s3f6 | ~105K | Quarterly | Projects with cost/budget |
| `lot_info` | Property Info | i642-2fxq | ~1.2M | Rarely | Property values, assessed data |

## Accessibility (Ramps)

| Key | Dataset | Fourfour | Rows | Freshness | Notes |
|-----|---------|----------|------|-----------|-------|
| `ramp_progress` | Ramp Installation Progress | e7gc-ub6z | ~187K | Daily | Active ramp entries (current) |
| `ramp_complaints` | Ramp Complaints | jagj-gttd | ~6K | Daily | ADA ramp complaints |
| `ramp_locations` | Ramp Locations | ufzp-rrqu | ~217K | ⚠️ Stale | Last updated 2021 (archived) |

## Coordination (Permits & Construction)

| Key | Dataset | Fourfour | Rows | Freshness | Notes |
|-----|---------|----------|------|-----------|-------|
| `street_permits` | Street Permits | tqtj-sjs8 | ~3.6M | Daily | All street work permits |
| `street_construction_inspections` | Construction Inspections | ydkf-mpxb | ~11.5M | Daily | Inspection records for construction |
| `capital_intersections` | Capital Program Intersections | 97nd-ff3i | ~7.8K | Quarterly | Capital improvement locations |
| `street_closures_block` | Street Closures | i6b5-j7bu | ~4.3K | Monthly | Temporary closure permits |
| `street_resurfacing_schedule` | Resurfacing Schedule | xnfm-u3k5 | ~309K | Quarterly | Planned paving projects |
| `street_resurfacing_inhouse` | In-House Resurfacing | ffaf-8mrv | ~602K | Quarterly | Completed paving (budget actuals) |
| `weekly_construction` | Weekly Construction | r528-jcks | 0 | ⚠️ Stale | Last updated 2017 (archived) |
| `capital_blocks` | Capital Blocks | jvk9-k4re | 0 | ⚠️ Empty | No data available |

## Context Layers (Overlays)

| Key | Dataset | Fourfour | Rows | Freshness | Notes |
|-----|---------|----------|------|-----------|-------|
| `complaints_311` | 311 Complaints | erm2-nwe9 | ~21.3M | Daily | All 311 complaints by category |
| `pedestrian_demand` | Pedestrian Demand | fwpa-qxaf | ~127K | Quarterly | Pedestrian activity hotspots |
| `mappluto` | MapPLUTO | 64uk-42ks | ~858K | Annually | NYC property parcels |
| `sidewalk_planimetric` | Sidewalk Network | vfx9-tbb6 | ~50K | Annually | NYC sidewalk geometry |
| `step_streets` | Step Streets | u9au-h79y | ~110 | Rarely | Historic step street locations |

---

## Data Availability Status

### 🟢 Healthy (Updated within SLA)
- inspection, violations, dismissals, reinspection
- ramp_progress, ramp_complaints
- street_permits, street_construction_inspections
- complaints_311

### 🟡 Caution (Near SLA threshold)
- built, correspondences, tree_damage, curb_metal_protruding
- capital_intersections, street_closures_block
- street_resurfacing_schedule, street_resurfacing_inhouse
- pedestrian_demand, mappluto

### 🔴 Issues (Stale or empty)
- ramp_locations (⚠️ Stale since 2021 — use ramp_progress instead)
- weekly_construction (⚠️ Stale since 2017 — use street_permits instead)
- capital_blocks (⚠️ Empty — 0 rows)
- permit_stipulations (🚫 API 403 error — permissions issue)

---

## Quick Access

### Fetch data via CLI
```bash
socrata fetch data.cityofnewyork.us dntt-gqwq --format csv --out inspections.csv

# With filters
socrata fetch data.cityofnewyork.us dntt-gqwq --format csv \
  --where "borough='MANHATTAN'" \
  --out manhattan_inspections.csv
```

### Fetch via Python API
```python
from socrata_toolkit.core.client import SocrataClient, SocrataConfig

client = SocrataClient(SocrataConfig())
df = client.fetch_dataframe('data.cityofnewyork.us', 'dntt-gqwq', max_rows=50000)
```

### Check dataset health
```bash
socrata dataset health --all
socrata dataset health --key inspection
socrata dataset health --key ramp_progress
```

---

## Tips

**Before using a dataset:**
1. Check its status above (🟢 = use freely, 🟡 = check freshness, 🔴 = find alternative)
2. If stale, find a recommended alternative
3. Set `SOCRATA_APP_TOKEN` for high-volume requests (>2K rows)

**For spatial analysis:**
- Most datasets have `the_geom` (GeoJSON) or lat/lon columns
- Use `street_permits`, `street_construction_inspections` for spatial joins
- Refer to GIS Overview dashboard for conflict detection

**For SLA tracking:**
- HIGH SLA = 14 days (inspection, violations, ramp_progress)
- MEDIUM SLA = 30 days (most coordination datasets)
- LOW SLA = 60 days (context layers, historical data)

