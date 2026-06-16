# Data Catalog Entry: `{dataset_key}`

**Fourfour:** `{fourfour}`
**Domain:** data.cityofnewyork.us
**Owner:** {owner}
**Data steward:** {data_steward}
**Update frequency:** {update_frequency}
**SLA tier:** {sla_tier} (HIGH=14d / MEDIUM=30d / LOW=60d)
**Sensitivity:** Public
**Generated:** {generated_at} UTC
**Entry version:** 1.0

---

## Description

{description}

<!-- One paragraph covering: what program generates this data, what real-world events
     it records, how it is used operationally, and what analytical questions it answers. -->

**Example:** The `inspection` dataset (dntt-gqwq) records the outcome of physical
sidewalk inspections conducted by NYC DOT SIM unit inspectors. Each row represents one
inspection event. Used operationally to trigger violation notices and analytically to
measure borough-level sidewalk condition trends.

---

## Business Context

| Field | Value |
|---|---|
| Business purpose | {business_purpose} |
| Primary users | DOT SIM analysts, borough program managers |
| Key decisions informed | Sidewalk repair prioritisation, SLA compliance reporting |
| Update trigger | {update_trigger} |
| Retention policy | Indefinite (public record) |

---

## Technical Metadata

| Field | Value |
|---|---|
| Approximate row count | {row_count} |
| Last modified | {last_modified} |
| API endpoint | `https://data.cityofnewyork.us/resource/{fourfour}.json` |
| Geo-enabled | {is_geo} |
| Primary key | `objectid` |

---

## Schema

| Field | Type | Nullable | Null rate | Description | Valid values / Business rules |
|---|---|---|---|---|---|
| `objectid` | Number | No | 0% | Unique record identifier. System-assigned. | Positive integer |
| `borough` | Text | Yes | ~0.2% | Borough code where inspection occurred | MN, BX, BK, QN, SI |
| `status` | Text | Yes | {status_null_rate} | Current record status | PASS, FAIL, PENDING, CLOSED |
| `inspection_date` | Calendar date | Yes | {inspection_date_null_rate} | Date physical inspection was conducted. Prefer over `created_date` for time-series. | ISO 8601 |
| `created_date` | Calendar date | Yes | {created_date_null_rate} | Date record entered the Socrata system. Lags `inspection_date` by 0–45 days. | ISO 8601 |
| `unit_id` | Text | Yes | {unit_id_null_rate} | SIM unit identifier. Foreign key to `violations.unit_id` and `dismissals.unit_id`. | Alphanumeric |
| `defect_type` | Text | Yes | {defect_type_null_rate} | Classification of defect observed | CRACK, UNEVEN, OBSTRUCTION, TREE_DAMAGE, OTHER |
| `material_type` | Text | Yes | {material_type_null_rate} | Sidewalk material at inspection site | CONCRETE, BRICK, ASPHALT, BLUESTONE, OTHER |
| `the_geom` | Point | Yes | ~8% | WGS84 point geometry. ~92% coverage. | GeoJSON Point |

---

## Data Quality

| Dimension | Score | Notes |
|---|---|---|
| **Overall** | **{overall_quality}** | Composite: 35% completeness / 25% validity / 25% consistency / 15% freshness |
| Completeness | {completeness} | Key columns: objectid, borough, status |
| Validity | {validity} | Format checks on dates and geometry |
| Consistency | {consistency} | Cross-field rules (e.g. status vs defect_type) |
| Freshness | {freshness} | Based on SLA tier: HIGH = 14-day threshold |

**Known quality issues:**

- `the_geom` is null for ~8% of records — likely data entry gaps in legacy records pre-2018.
- `defect_type` has an `OTHER` catch-all that represents ~15% of violations; not useful for defect classification analysis.
- `borough` nulls (<0.2%) correlate with records entered via legacy paper submission workflow.

---

## Sample Queries

```python
# Fetch 1,000 inspections from Manhattan, most recent first
from socrata_toolkit.core.client import SocrataClient, SocrataConfig
client = SocrataClient(SocrataConfig())
df = client.fetch_dataframe(
    "data.cityofnewyork.us", "{fourfour}",
    max_rows=1000,
    where="upper(borough)='MN' AND inspection_date > '2026-01-01T00:00:00'",
    order="inspection_date DESC",
)
```

```soql
-- Count by borough for current year
SELECT borough, count(*) AS total
WHERE inspection_date >= '2026-01-01T00:00:00'
GROUP BY borough
ORDER BY total DESC
```

---

## Lineage

```
NYC DOT SIM Inspector → SIM Field System → Socrata Open Data API → socrata_toolkit
```

| Step | Description |
|---|---|
| Upstream source | NYC DOT SIM field inspection system |
| Ingestion method | Socrata API (nightly push from SIM system) |
| Transformations | None — raw open data |
| Downstream consumers | SIM analytics dashboards, borough reports, conflict detection |

---

## Governance

| Field | Value |
|---|---|
| Sensitivity classification | Public |
| PII present | No |
| Access policy | Open — no auth for <2K rows; `SOCRATA_APP_TOKEN` for full corpus |
| Data owner | {owner} |
| Data steward | {data_steward} |
| Entry review cycle | Annual |
| Compliance notes | Subject to NYC Open Data Law (Local Law 11 of 2012) |

---

## Related Datasets

| Key | Fourfour | Relationship |
|---|---|---|
| violations | 6kbp-uz6m | Join on `unit_id` — violations generated by inspections |
| dismissals | p4u2-3jgx | Join on `unit_id` — dismissed violations |
| ramp_progress | e7gc-ub6z | Spatial join — ramps near inspection sites |
| street_permits | tqtj-sjs8 | Spatial join — construction near inspection sites |

---

*Generated by `scripts/catalog_extractor.py`. Validate null rates with live data before publishing.*
