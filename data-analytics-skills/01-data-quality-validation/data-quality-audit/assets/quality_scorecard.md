# Data Quality Scorecard — {{dataset_key}}

**Dataset:** {{dataset_name}}
**Fourfour:** {{fourfour}}
**Audit date:** {{audit_date}}
**Rows sampled:** {{row_count}}
**Analyst:** {{analyst_name}}

---

## Overall Score: {{overall_score}}/100

| Dimension | Score | Weight | Weighted |
|---|---|---|---|
| Completeness | {{completeness_score}}/100 | 35% | {{completeness_weighted}} |
| Validity | {{validity_score}}/100 | 25% | {{validity_weighted}} |
| Consistency | {{consistency_score}}/100 | 25% | {{consistency_weighted}} |
| Freshness | {{freshness_score}}/100 | 15% | {{freshness_weighted}} |
| **Overall** | **{{overall_score}}/100** | 100% | — |

---

## Findings Summary

### Critical (must fix before production use)
<!-- List critical findings here -->
- {{critical_finding_1}}
- {{critical_finding_2}}

### Major (fix before next release)
<!-- List major findings here -->
- {{major_finding_1}}

### Minor (address in backlog)
<!-- List minor findings here -->
- {{minor_finding_1}}

---

## Completeness Detail

| Column | Null Count | Null % | Required | Severity |
|---|---|---|---|---|
| objectid | {{objectid_null_count}} | {{objectid_null_pct}}% | yes | {{objectid_severity}} |
| borough | {{borough_null_count}} | {{borough_null_pct}}% | yes | {{borough_severity}} |
| status | {{status_null_count}} | {{status_null_pct}}% | yes | {{status_severity}} |
| inspection_date | {{date_null_count}} | {{date_null_pct}}% | yes | {{date_severity}} |
| house_number | {{house_null_count}} | {{house_null_pct}}% | no | {{house_severity}} |
| street_name | {{street_null_count}} | {{street_null_pct}}% | no | {{street_severity}} |
| latitude | {{lat_null_count}} | {{lat_null_pct}}% | no | {{lat_severity}} |
| longitude | {{lon_null_count}} | {{lon_null_pct}}% | no | {{lon_severity}} |

---

## Validity Detail

| Check | Pass/Fail | Count | Notes |
|---|---|---|---|
| Valid borough codes | {{borough_valid}} | {{borough_invalid_count}} invalid | {{borough_notes}} |
| Dates not in future | {{future_date_valid}} | {{future_date_count}} violations | |
| Dates not before 2000 | {{old_date_valid}} | {{old_date_count}} violations | |
| Lat/lon in NYC bbox | {{geo_valid}} | {{geo_invalid_count}} outside bbox | |

---

## Consistency (Duplicate Check)

| Key Column | Total Rows | Duplicate Rows | Duplicate % | Severity |
|---|---|---|---|---|
| objectid | {{total_rows}} | {{dup_count}} | {{dup_pct}}% | {{dup_severity}} |

---

## Freshness

- **Last modified:** {{last_modified}}
- **SLA tier:** {{sla_tier}} (max {{sla_days}} days)
- **Age:** {{age_days}} days
- **Status:** {{freshness_status}}

---

## Recommended Actions

1. {{action_1}}
2. {{action_2}}
3. {{action_3}}

---

## Sign-off

| Role | Name | Date | Signature |
|---|---|---|---|
| Analyst | | | |
| Data Steward | | | |
| Manager | | | |
