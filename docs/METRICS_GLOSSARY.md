# NYC Data Toolkit - Metrics Glossary

Complete definitions of all platform metrics, their business context, and interpretation guidelines.

---

## Data Quality Metrics

### Completeness
**Definition**: Percentage of non-null values across all required fields in a dataset.

**Calculation**: `(Non-null records / Total records) × 100`

**Business Context**: 
- Incomplete data impacts downstream analytics and decision-making
- Target: 99%+ (most operational datasets)
- Alert threshold: <95%

**Current Value**: 99.2%

**Trend**: ↑ Improving (+0.2% MoM)

**Example**:
```
Sidewalk Inspections: 10,000 total records
- Missing material_type: 75 records
- Missing ada_compliant: 5 records
Completeness = (10,000 - 75 - 5) / 10,000 = 99.2%
```

---

### Validity
**Definition**: Percentage of records that conform to defined schema and business rules.

**Calculation**: `(Valid records / Total records) × 100`

**Business Context**:
- Invalid data causes processing failures and downstream errors
- Includes schema type checks, range validation, format validation
- Target: 98%+
- Alert threshold: <90%

**Current Value**: 98.8%

**Trend**: ↑ Stable/Improving

**Validation Rules**:
- Type matching (e.g., date fields must be valid dates)
- Range checks (e.g., ADA compliance as boolean)
- Format validation (e.g., ZIP codes as 5 digits)
- Business rule enforcement

---

### Consistency
**Definition**: Percentage of records with no contradictions across related fields or datasets.

**Calculation**: `(Consistent records / Total records) × 100`

**Business Context**:
- Inconsistency indicates duplicate records, data corruption, or ETL failures
- Includes cross-field and cross-dataset consistency checks
- Target: 99%+
- Alert threshold: <95%

**Current Value**: 99.5%

**Trend**: ↑ Improving

**Examples**:
- Sum of parts equals whole (detail vs summary tables)
- Date logic (closed_date > created_date)
- Foreign key relationships maintained
- Duplicate detection and resolution

---

### Uniqueness
**Definition**: Percentage of records with unique primary/natural keys.

**Calculation**: `(Unique records / Total records) × 100`

**Business Context**:
- Duplicate records skew analytics and KPIs
- Entity resolution identifies logical duplicates
- Target: 99.98%+
- Alert threshold: >0.1% duplicates

**Current Value**: 99.98% (0.02% duplicates)

**Trend**: ↓ Decreasing duplicates

**Example**:
```
10,000 inspection records
- 19 exact duplicates (same inspection_id)
- 1 logical duplicate (same location, date, inspector)
Uniqueness = (10,000 - 20) / 10,000 = 99.8%
```

---

### Freshness
**Definition**: Time elapsed since last successful data ingestion/refresh.

**Measurement**: Minutes since last update

**Business Context**:
- Stale data leads to outdated decisions
- Freshness SLA: <60 minutes for most datasets
- Critical datasets: <15 minutes
- Alert threshold: Exceeds SLA by >10 minutes

**Current Value**: <1 hour average across all datasets

**Trend**: → Consistent

**Target**:
- Sidewalk Inspections: <1 hour
- 311 Complaints: <1 hour
- Contractor Data: <4 hours
- Reference Data: <24 hours

---

## Performance Metrics

### Query Latency (p95)
**Definition**: 95th percentile response time for database queries at peak load.

**Measurement**: Milliseconds

**Business Context**:
- Slow queries impact user experience and system responsiveness
- p95 = 95% of queries faster than this threshold
- Target: <500ms
- Alert threshold: >750ms sustained

**Current Value**: 245ms

**Trend**: ↓ Improving (-30ms YoY)

**Monitoring Points**:
- API response time (includes network)
- Database query execution time
- Cache hit rate impact

**Example**:
```
If p95 = 245ms:
- 95% of queries complete in <245ms
- 5% of queries take >245ms
- Max observed: ~2 seconds
```

---

### Ingestion Throughput
**Definition**: Average volume of records processed per unit time during ingestion.

**Measurement**: Records per day / minute

**Business Context**:
- Throughput determines capacity and scaling needs
- Enables SLA planning for new datasets
- Target: 1M+ records/day
- Affects: Query latency, infrastructure costs

**Current Value**: 1.2M records/day

**Trend**: ↑ Growing (+15% YoY)

**Capacity Planning**:
```
Current throughput: 1.2M/day = 50k/hour = 833/min
Growth rate: 15% YoY
Projected (12 months): 1.38M/day
```

---

### System Uptime
**Definition**: Percentage of time system is available and responding to requests.

**Calculation**: `((Total minutes - Downtime) / Total minutes) × 100`

**Business Context**:
- Uptime SLA: 99.9% (8.7 hours/month allowed)
- Production target: 99.95%+
- Alert threshold: <99% measured over 1 hour

**Current Value**: 99.97% (30-day rolling)

**Trend**: ↑ Exceeds target

**Recent Downtime** (30 days):
- Planned maintenance: 18 minutes
- Incident resolution: 0 minutes
- Unplanned: 0 minutes
- **Total**: 18 minutes (~0.03%)

---

### Mean Time to Resolution (MTTR)
**Definition**: Average time from incident detection to full resolution.

**Measurement**: Minutes

**Business Context**:
- Lower MTTR = faster recovery = less business impact
- Target: <30 minutes
- Alert threshold: >60 minutes sustained

**Current Value**: 18 minutes

**Trend**: ↓ Improving

**Historical** (30 days):
- Average: 18 minutes
- Median: 12 minutes
- Max: 45 minutes
- Incidents: 2 (both resolved <45min)

---

## API Metrics

### API Uptime
**Definition**: Percentage of successful API responses over total requests.

**Calculation**: `(Successful responses / Total responses) × 100`

**Business Context**:
- Reflects reliability for integrated consumers
- Target: 99.9%+
- Alert threshold: <99%

**Current Value**: 99.97%

**Trend**: ↑ Exceeds target

---

### Authentication Pass Rate
**Definition**: Percentage of API requests with valid authentication credentials.

**Calculation**: `(Valid auth requests / Total requests) × 100`

**Business Context**:
- Security metric - invalid auth blocked by API gateway
- Should be 99%+
- Low pass rate indicates misconfigured consumers

**Current Value**: 99.98%

**Trend**: ↑ Consistent

---

### Rate Limiting Enforcement
**Definition**: Percentage of rate limit violations successfully blocked.

**Calculation**: `(Blocked violations / Total violations) × 100`

**Business Context**:
- Prevents API abuse and resource exhaustion
- Limits: 1000 requests/min per consumer
- Should be 99.9%+
- False positives: <0.1%

**Current Value**: 100%

**Trend**: → Consistent

---

### Active API Consumers
**Definition**: Number of distinct external systems actively calling API endpoints.

**Measurement**: Count

**Business Context**:
- Indicates platform adoption and value
- Affects: Support burden, feature prioritization
- Target: Growing adoption

**Current Value**: 12 active consumers

**Breakdown**:
- NYC DOT internal: 3
- City agencies: 4
- External partners: 3
- Development/testing: 2

---

## Data Governance Metrics

### PII Field Coverage
**Definition**: Percentage of known PII fields that are protected (masked/encrypted/access-controlled).

**Calculation**: `(Protected PII fields / Known PII fields) × 100`

**Business Context**:
- Privacy and compliance requirement (GDPR, CCPA)
- Target: 100% coverage
- Alert: Any unprotected PII discovered

**Current Value**: 100%

**Protected Fields**:
- Email addresses: masked
- Phone numbers: masked
- Addresses: encrypted at rest
- Names: access controlled (RBAC)
- SSN: not stored (reference only)

---

### Audit Trail Completeness
**Definition**: Percentage of data modifications captured in immutable audit log.

**Calculation**: `(Logged changes / Total changes) × 100`

**Business Context**:
- Compliance requirement (SOC 2, GDPR)
- Enables investigation of data issues
- Target: 100%
- Alert: Any missing audit entries

**Current Value**: 100%

**Captured Events**:
- Data inserts
- Data updates (before/after values)
- Data deletes
- User actions
- API calls
- Access events

---

### Compliance Violations
**Definition**: Count of policy violations detected and flagged.

**Measurement**: Number per period

**Business Context**:
- Zero tolerance - all violations must be investigated
- Violations: Unauthorized access, retention policy breach, encryption failure
- Response SLA: <1 hour investigation

**Current Value**: 0 (30-day rolling)

**Trend**: ↓ Consistent zero violations

---

## Entity Resolution Metrics

### Duplicate Detection Rate
**Definition**: Percentage of records identified as duplicates of existing records.

**Calculation**: `(Duplicate records / Total records) × 100`

**Business Context**:
- Duplicates skew analytics and KPIs
- Target: <0.1%
- Alert threshold: >0.5%

**Current Value**: 0.02%

**Trend**: ↓ Decreasing

**Detection Criteria**:
- Exact match on all key fields
- Fuzzy match on name + address
- Temporal proximity (same day/hour)

---

### Match Accuracy
**Definition**: Percentage of entity matches validated as correct by domain experts.

**Calculation**: `(Correct matches / Total matches reviewed) × 100`

**Business Context**:
- False matches cause data corruption
- Target: >99% accuracy
- Validation: Quarterly human review

**Current Value**: 99.2%

**Improvement Plan**:
- Increase weighted matching algorithm
- Add geographic proximity weighting
- Improve fuzzy matching parameters

---

### Deduplication Latency
**Definition**: Time from record ingestion to duplicate detection and resolution.

**Measurement**: Minutes

**Business Context**:
- Faster dedup = cleaner analytics sooner
- Target: <5 minutes
- Alert threshold: >15 minutes

**Current Value**: <2 minutes average

**Trend**: ↓ Improving

---

## Lineage Metrics

### Lineage Completeness
**Definition**: Percentage of data assets with fully documented parent-child relationships.

**Calculation**: `(Assets with complete lineage / Total assets) × 100`

**Business Context**:
- Complete lineage enables impact analysis
- Required for compliance (GDPR data deletion)
- Target: 100%
- Alert: Any orphaned assets

**Current Value**: 100%

**Coverage**:
- Data sources: 8/8 documented
- Transformations: 15/15 documented
- Target datasets: 50+/50+ documented

---

### Lineage Query Performance
**Definition**: Time to retrieve full lineage path from source to target.

**Measurement**: Milliseconds

**Business Context**:
- Fast lineage queries support impact analysis
- Target: <100ms
- Alert threshold: >500ms

**Current Value**: <50ms average

**Trend**: → Consistent

---

## Business Metrics

### Cost Per Record
**Definition**: Total infrastructure cost divided by records processed/stored.

**Calculation**: `(Total monthly cost / Records processed) × 1M`

**Business Context**:
- Indicates efficiency and scalability
- Helps justify platform investment
- Target: <$0.15 per million records

**Current Value**: $0.12 per million records

**Trend**: ↓ Decreasing (-15% YoY)

**Cost Breakdown**:
- Database: 45%
- Compute: 30%
- Storage: 15%
- Networking: 10%

---

### Time to Integrate Dataset
**Definition**: Hours from dataset discovery to first query.

**Measurement**: Hours

**Business Context**:
- Speed to value for new data sources
- Target: <4 hours
- Enabler: Automated schema discovery

**Current Value**: 2-4 hours

**Breakdown**:
- Schema discovery: <30 min
- Quality check setup: 30-60 min
- Access provisioning: 30-60 min
- Validation: <30 min

---

### Developer Onboarding Time
**Definition**: Time from first access to executing first query.

**Measurement**: Hours

**Business Context**:
- Reduces ramp-up time for new developers
- With Docker: <15 minutes
- Without: 2-4 hours

**Current Value**: <15 minutes (with Docker)

**Improvement**:
- Docker setup: 5 min
- Sample data: Pre-loaded
- Examples: 5 min to run
- Documentation: Clear & comprehensive

---

## SLA Metrics

### Quality SLA Compliance
**Definition**: Percentage of datasets meeting defined quality thresholds.

**Calculation**: `(Compliant datasets / Total datasets) × 100`

**Business Context**:
- Core measure of platform reliability
- Target: 99%+
- Violations trigger incident response

**Current Value**: 99.8%

**Trend**: ↑ Improving

**SLA Thresholds** (by dataset):
| Dataset | Completeness | Validity | Freshness |
|---|---|---|---|
| Sidewalk Inspections | 99% | 98% | <1h |
| 311 Complaints | 97% | 97% | <1h |
| Contractors | 99% | 99% | <4h |

---

### API SLA Compliance
**Definition**: Percentage of time API meets uptime and latency targets.

**Calculation**: Composite of uptime + latency within thresholds

**Business Context**:
- SLA: 99.9% uptime + p95 latency <500ms
- Violations: Service credits to consumers
- Target: 99.95%

**Current Value**: 99.97%

**Trend**: ↑ Exceeds target

---

## Monitoring and Alerting

### Alert Threshold Summary

| Metric | Warning | Critical | Response SLA |
|---|---|---|---|
| Uptime | <99% | <95% | 5 min |
| Query Latency (p95) | >500ms | >2s | 10 min |
| Completeness | <95% | <90% | 15 min |
| Freshness | SLA+10min | SLA+30min | 20 min |
| Duplicates | >0.5% | >1% | 30 min |
| Compliance Violations | Any | Any | 5 min |
| Audit Trail | Any gap | Any gap | 15 min |

---

## Dashboard Access

View real-time metrics:

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686

---

## Metric Calculation Frequency

| Metric | Frequency | Retention |
|---|---|---|
| Uptime/SLA | Real-time | 30 days |
| Query Latency | Per query (sampled) | 7 days |
| Completeness/Validity | Per refresh | 90 days |
| Audit Trail | Per operation | 7 years |
| Cost metrics | Daily aggregation | 12 months |

---

**Last Updated**: 2026-05-10  
**Review Cycle**: Quarterly  
**Owner**: Data Platform Team

