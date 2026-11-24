# Business Rules Reference — NYC DOT SIM Datasets

Authoritative constraints used by the data-quality-audit skill to validate field values.
Update this file whenever DOT business logic changes.

---

## Required Fields by Dataset

| Dataset Key | Required Columns |
|---|---|
| `inspection` | objectid, borough, status, inspection_date |
| `violations` | objectid, borough, status, created_date |
| `ramp_progress` | objectid, borough, status |
| `dismissals` | objectid, borough |
| `street_permits` | permit_si_no, borough, work_type |
| `ramp_complaints` | unique_key, borough |

---

## Valid Categorical Values

### `borough`
Accepted values (case-insensitive):

| Code | Full Name |
|---|---|
| MN | MANHATTAN |
| BX | BRONX |
| BK | BROOKLYN |
| QN | QUEENS |
| SI | STATEN ISLAND |

Any other value is a validity violation. Mixed-case variants (e.g. `Manhattan`, `manhattan`) are acceptable — normalize with `.str.upper()` before comparison.

### `status` — inspection dataset
- `OPEN`, `CLOSED`, `PENDING`, `DISMISSED`, `IN PROGRESS`
- Blank status on records older than 90 days = **major** violation.

### `status` — ramp_progress dataset
- `COMPLETED`, `PENDING`, `SCHEDULED`, `CANCELLED`
- COMPLETED records must have a non-null `completion_date`.

---

## Date Range Rules

All date columns must satisfy:

| Column | Dataset | Min | Max |
|---|---|---|---|
| `inspection_date` | inspection | 2000-01-01 | today |
| `created_date` | violations | 2000-01-01 | today |
| `created_date` | dismissals | 2000-01-01 | today |
| `completion_date` | ramp_progress | 2000-01-01 | today |
| `startdate` | street_permits | 1990-01-01 | today + 5 years |
| `enddate` | street_permits | startdate | today + 10 years |

Future `inspection_date` values (> today) are always **critical** violations.

---

## Numeric Range Rules

| Column | Dataset | Min | Max | Notes |
|---|---|---|---|---|
| `house_number` | inspection | 1 | 99999 | Must be positive integer |
| `latitude` | any geo | 40.4 | 40.95 | NYC bounding box |
| `longitude` | any geo | -74.26 | -73.7 | NYC bounding box |

---

## Null Rate Thresholds

| Severity | Required Field Null % | Optional Field Null % |
|---|---|---|
| critical | > 5% | — |
| major | > 1% | > 25% |
| minor | > 0% | > 10% |
| ok | 0% | ≤ 10% |

---

## Duplicate Thresholds

| Severity | Duplicate Rate on Primary Key |
|---|---|
| critical | > 1% |
| major | > 0.1% |
| minor | > 0.01% |
| ok | ≤ 0.01% |

Primary key is `objectid` for most SIM datasets. For `street_permits` use `permit_si_no`.

---

## Freshness SLA

| SLA Tier | Max Age (days) | Datasets |
|---|---|---|
| HIGH | 14 | inspection, violations, dismissals, ramp_complaints, ramp_progress |
| MEDIUM | 30 | street_permits, ramp_locations |
| LOW | 60 | tree_damage, curb_metal_protruding |

Source: `data/sla_config.json` (overrides these defaults when present).
