# NYC DOT Data Governance Policy Reference

## Legal Framework

All datasets registered in this toolkit are published under the **NYC Open Data Law
(Local Law 11 of 2012)**. Key obligations:

- All public datasets must be published on the NYC Open Data portal
- Datasets must have a designated agency data coordinator
- Agencies must maintain a data inventory and publish an annual open data compliance plan
- PII must be redacted or aggregated before publication

---

## Sensitivity Classification

| Level | Definition | Examples in this toolkit |
|---|---|---|
| **Public** | Published on NYC Open Data; no access restrictions | inspection, violations, ramp_progress, all 26 registered datasets |
| **Internal** | Agency-internal only; not on Open Data | Inspector routing sheets, budget line items |
| **Restricted** | Limited access within agency | Individual complaint filer identities (pre-aggregation) |
| **Confidential** | Legal hold or under investigation | None in this toolkit |

All 26 datasets in this toolkit are classified **Public**.

---

## Data Ownership

| Dataset group | Data owner | Data steward | Contact channel |
|---|---|---|---|
| core_smd (inspection, violations, etc.) | NYC DOT SIM Unit Director | SIM Data Coordinator | data311@dot.nyc.gov |
| accessibility (ramp_*) | NYC DOT Accessibility Programs | Ramp Program Manager | accessibility@dot.nyc.gov |
| coordination (street_permits, etc.) | NYC DOT Permits Division | Permits Data Coordinator | permits@dot.nyc.gov |
| overlays (mappluto, pedestrian_demand) | NYC DOITT / DCP | Agency data coordinators | opendata@nyc.gov |

---

## Access Policy

### Public access (no authentication)

- Up to 1,000 rows per Socrata API call without authentication
- Rate-limited to 60 calls/hour per IP without token

### App token access (`SOCRATA_APP_TOKEN`)

- Required for full-corpus fetches (>2,000 rows effective limit without token)
- Register at: https://data.cityofnewyork.us/profile/edit/developer_settings
- Store as environment variable; never commit to version control

### Restricted datasets

`permit_stipulations` (gsgx-6efw) currently returns HTTP 403. This may indicate:
1. Dataset was made private after a policy change
2. API endpoint migrated and fourfour is stale
3. Temporary access restriction under legal review

Resolution: contact opendata@nyc.gov with the fourfour and the error response.

---

## PII Handling

None of the 26 registered datasets contain direct PII as published. However:

- `complaints_311` (erm2-nwe9): Contains street-level address of complaint. Treat
  address fields as quasi-PII; do not join with voter or DMV records.
- `ramp_complaints`: May contain filer-provided location descriptions. Do not republish
  verbatim complaint text without review.

When computing analysis outputs that aggregate to borough or block level, PII risk is
negligible. Flag any analysis that produces individual-level outputs.

---

## Audit Trail Requirements

Per DOT data governance policy, all programmatic data access to core_smd datasets
must be logged via `AuditLogger` when processing records in a production context:

```python
from socrata_toolkit.governance import AuditLogger

logger = AuditLogger()
logger.log_event(
    actor="analyst_email@dot.nyc.gov",
    action="fetch",
    resource="inspection:dntt-gqwq",
    details={"max_rows": 10000, "where": "borough='MN'"},
)
```

Audit logs are stored in the DuckDB governance store (`data/local_db/`).

---

## Data Retention

| Dataset | Retention obligation | Notes |
|---|---|---|
| All Open Data datasets | Indefinite (public record) | Governed by NYC record retention schedule |
| DuckDB L2 cache | Configurable; default 30 days of Parquet | See `SOCRATA_CACHE_DIR` |
| Audit logs | 7 years (NYC records schedule Series 800) | Stored in DuckDB governance store |
| Analysis outputs (Excel/PDF/PPTX) | Per project; label with date and version | |

---

## Catalog Entry Lifecycle

| Stage | Trigger | Owner |
|---|---|---|
| Draft | New dataset added to registry | Analyst |
| Review | Before sharing entry with other teams | Data steward |
| Published | Approved entry in data catalog | Data steward |
| Stale review | Dataset last_modified > 90 days without catalog update | Automated alert |
| Deprecated | Dataset removed from Open Data or replaced | Data owner |

---

## NYC Open Data API Conventions

```
Base URL:  https://data.cityofnewyork.us/resource/{fourfour}.json
Metadata:  https://data.cityofnewyork.us/api/views/{fourfour}.json
SOQL docs: https://dev.socrata.com/docs/queries/
```

Key SOQL patterns for governance queries:

```soql
-- Row count
SELECT count(*) AS total

-- Most recent record
SELECT max(created_date) AS latest

-- Null rate for a column
SELECT count(*) AS null_count WHERE borough IS NULL
```
