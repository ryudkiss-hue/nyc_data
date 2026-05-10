# Integration Checklist

**Step-by-step checklist for onboarding a new dataset to the NYC Data Toolkit**

Complete end-to-end in 30-45 minutes.

---

## Phase 1: Discovery & Planning (5 minutes)

### Dataset Information

- [ ] **Dataset Name** (required)
  - Example: "Street Cleaning Schedule"
  - Keep it descriptive and unique

- [ ] **Data Owner** (required)
  - Name: _________________
  - Email: _________________
  - Slack: _________________

- [ ] **Source System** (required)
  - [ ] Socrata/Open Data Portal
  - [ ] CSV/Excel file
  - [ ] Database table
  - [ ] API endpoint
  - [ ] Other: _________________

- [ ] **Expected Volume**
  - Record count: _________________
  - Refresh frequency: [ ] Hourly [ ] Daily [ ] Weekly [ ] Monthly [ ] On-demand
  - Historical data: [ ] Yes [ ] No (if yes, how much?)

- [ ] **Business Purpose**
  - Use case: _________________
  - Stakeholders: _________________
  - Success metrics: _________________

---

## Phase 2: Schema Registration (5 minutes)

### 1. Get Data Sample

```bash
# Socrata dataset
socrata-toolkit dataset fetch --socrata-id abc123 --limit 100 > sample.csv

# Or local file
# Just ensure you have a CSV with headers
```

### 2. Register Schema

```bash
# Auto-register schema from sample
socrata-toolkit schema register \
  --dataset-name "street_cleaning" \
  --sample-file sample.csv \
  --source-type csv

# Verify registration
socrata-toolkit schema show street_cleaning
```

**Schema Registration Checklist:**
- [ ] All columns detected correctly
- [ ] Data types inferred correctly
- [ ] Primary key identified (if applicable)
- [ ] No unexpected columns

### 3. Review Schema

```bash
# View detailed schema
docker-compose exec postgres psql -U dot_user -d sidewalk_db -c "
  SELECT column_name, data_type, is_nullable
  FROM information_schema.columns
  WHERE table_name = 'street_cleaning'
  ORDER BY ordinal_position;
"
```

---

## Phase 3: Data Governance (3 minutes)

### 1. Set Data Classification

- [ ] **Classification Level** (required)
  - [ ] **Public** - Available to anyone, published datasets
  - [ ] **Internal** - NYC agencies only, operational data
  - [ ] **Sensitive** - Restricted access, contains PII/confidential info

### 2. Identify PII Fields

```bash
# Mark fields containing personally identifiable information
socrata-toolkit governance mark-pii \
  --dataset street_cleaning \
  --columns operator_email,operator_phone
```

**Common PII:**
- [ ] Email addresses
- [ ] Phone numbers
- [ ] Personal names
- [ ] Home addresses
- [ ] SSN/ID numbers
- [ ] Dates of birth

### 3. Set Retention Policy

- [ ] **Retention Period** (required)
  - [ ] 30 days
  - [ ] 90 days
  - [ ] 1 year
  - [ ] 3 years
  - [ ] 7 years (default for most operational data)
  - [ ] Indefinite

```bash
# Set retention policy
socrata-toolkit governance retention \
  --dataset street_cleaning \
  --retention-days 365
```

### 4. Assign Data Owner

```bash
# Set owner for access control
socrata-toolkit governance owner \
  --dataset street_cleaning \
  --owner-email data_owner@nyc.local
```

- [ ] Owner notified
- [ ] Owner acknowledged

---

## Phase 4: Quality Expectations (5 minutes)

### 1. Set Quality Rules

```bash
# Create quality expectations file
cat > street_cleaning_expectations.yaml <<EOF
dataset: street_cleaning
expectations:
  - name: "No null schedule_date"
    type: NotNull
    column: schedule_date
    
  - name: "Valid borough codes"
    type: ValueInSet
    column: borough
    values: ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
    
  - name: "Schedule date must be future"
    type: CustomSQL
    sql: "schedule_date > CURRENT_DATE"
    
  - name: "Completeness > 95%"
    type: Completeness
    threshold: 0.95
EOF

# Register expectations
socrata-toolkit quality register \
  --dataset street_cleaning \
  --expectations-file street_cleaning_expectations.yaml
```

**Quality Rules Checklist:**
- [ ] Completeness rule (missing values)
- [ ] Validity rule (format/type)
- [ ] Consistency rule (cross-field logic)
- [ ] Uniqueness rule (if applicable)
- [ ] Business rule (domain-specific)

### 2. Define SLA Targets

```bash
# Set SLA for dataset
socrata-toolkit sla create \
  --dataset street_cleaning \
  --completeness-target 99 \
  --validity-target 98 \
  --freshness-target-minutes 1440
```

**SLA Checklist:**
- [ ] Completeness target: _____ %
- [ ] Validity target: _____ %
- [ ] Freshness SLA: _____ minutes
- [ ] Duplication tolerance: _____ %

### 3. Test Quality Checks

```bash
# Run quality checks on sample
socrata-toolkit quality validate \
  --dataset street_cleaning \
  --data-file sample.csv

# Review report
cat quality_report.json
```

**Expected Output:**
```json
{
  "dataset": "street_cleaning",
  "records_total": 500,
  "records_valid": 495,
  "validity_percentage": 99.0,
  "completeness_percentage": 99.8,
  "anomalies_detected": 2,
  "status": "PASS"
}
```

- [ ] Validity > 95%
- [ ] No unexpected anomalies
- [ ] All expectations defined

---

## Phase 5: Entity Resolution (5-10 minutes)

### If Dataset Contains Entities (people, locations, vendors, etc.)

### 1. Define Entity Matching Rules

```bash
# For contractor/vendor data
socrata-toolkit entity-matching create \
  --dataset street_cleaning_contractors \
  --entity-type contractor \
  --match-fields "name,address,zip" \
  --fuzzy-threshold 0.85
```

**Matching Strategy:**
- [ ] **Exact match**: Same values on all key fields
- [ ] **Fuzzy match**: Similarity >85% on name/address
- [ ] **Geographic proximity**: Distance <100m for locations
- [ ] **Temporal proximity**: Within same day/week

### 2. Test Deduplication

```bash
# Detect duplicates
socrata-toolkit entity-matching find-duplicates \
  --dataset street_cleaning_contractors \
  --limit 100

# Review matches
socrata-toolkit entity-matching review \
  --dataset street_cleaning_contractors \
  --pending-only
```

**Deduplication Checklist:**
- [ ] No false positives (correct non-matches)
- [ ] No false negatives (actual duplicates missed)
- [ ] Match confidence >95%

### 3. Approve Merges

```bash
# Approve and merge identified duplicates
socrata-toolkit entity-matching approve \
  --dataset street_cleaning_contractors \
  --all
```

- [ ] All merges reviewed by data owner
- [ ] Audit trail recorded
- [ ] Master entities created

---

## Phase 6: Ingestion Configuration (5 minutes)

### 1. Configure Data Source

```bash
# Register data source
socrata-toolkit source register \
  --name "street_cleaning_prod" \
  --type socrata \
  --socrata-id abc123 \
  --dataset street_cleaning
```

**OR for CSV/file source:**

```bash
socrata-toolkit source register \
  --name "street_cleaning_files" \
  --type csv \
  --location "s3://nyc-data/street_cleaning/" \
  --dataset street_cleaning
```

**OR for API source:**

```bash
socrata-toolkit source register \
  --name "street_cleaning_api" \
  --type api \
  --endpoint "https://api.example.com/street_cleaning" \
  --dataset street_cleaning
```

### 2. Set Refresh Schedule

```bash
# Configure automatic refresh
socrata-toolkit schedule create \
  --dataset street_cleaning \
  --frequency daily \
  --time "02:00 UTC" \
  --timeout-minutes 60 \
  --on-failure "alert_owner"
```

**Refresh Options:**
- [ ] **Hourly**: For frequently changing data
- [ ] **Daily** (default): Most operational datasets
- [ ] **Weekly**: Reference/master data
- [ ] **On-demand**: Manual or event-triggered
- [ ] **Real-time**: High-frequency data (requires CDC)

### 3. Test Ingestion

```bash
# Run first ingestion (dry-run)
socrata-toolkit ingest --dataset street_cleaning --dry-run

# Check logs
docker-compose logs api | grep street_cleaning

# Run actual ingestion
socrata-toolkit ingest --dataset street_cleaning --full
```

**Ingestion Checklist:**
- [ ] Records ingested successfully
- [ ] No schema violations
- [ ] Quality checks pass
- [ ] Lineage recorded
- [ ] Audit trail captured
- [ ] Notification sent to owner

---

## Phase 7: Lineage Configuration (2 minutes)

### 1. Document Data Lineage

```bash
# Register upstream dependencies
socrata-toolkit lineage add-source \
  --dataset street_cleaning \
  --source-dataset operational_schedule \
  --transformation "Extract by schedule status = 'active'"

# Register downstream consumers
socrata-toolkit lineage add-consumer \
  --dataset street_cleaning \
  --consumer-dataset cleaning_kpis \
  --transformation "Aggregate by borough and day"
```

**Lineage Checklist:**
- [ ] Source(s) documented
- [ ] Transformation(s) described
- [ ] Consumer(s) identified
- [ ] Impact analysis available

### 2. Verify Lineage

```bash
# View complete lineage
socrata-toolkit lineage tree street_cleaning

# Expected output:
# operational_schedule
#   └─> street_cleaning (Extract active)
#       └─> cleaning_kpis (Aggregate)
```

---

## Phase 8: Access Control (3 minutes)

### 1. Set RBAC Permissions

```bash
# Grant read access to analysts
socrata-toolkit access grant \
  --dataset street_cleaning \
  --group analysts \
  --permission read

# Grant admin access to owner
socrata-toolkit access grant \
  --dataset street_cleaning \
  --user data_owner@nyc.local \
  --permission admin

# Grant write access to data team
socrata-toolkit access grant \
  --dataset street_cleaning \
  --group data_team \
  --permission write
```

**Access Levels:**
- [ ] **Read** - Query only, no exports
- [ ] **Write** - Upload/modify data
- [ ] **Admin** - Full control, governance settings
- [ ] **Owner** - Ultimate responsibility

### 2. Verify Access

```bash
# List access permissions
socrata-toolkit access show --dataset street_cleaning

# Test access as restricted user
socrata-toolkit query "SELECT COUNT(*) FROM street_cleaning" \
  --as-user analyst@nyc.local
```

**Access Checklist:**
- [ ] Owner has admin access
- [ ] Team members have appropriate access
- [ ] No overly broad permissions
- [ ] Quarterly access review scheduled

---

## Phase 9: API Configuration (2 minutes)

### 1. Enable API Endpoints

```bash
# Make dataset queryable via API
socrata-toolkit api enable \
  --dataset street_cleaning \
  --read-only false \
  --rate-limit 1000/min
```

### 2. Test API Endpoints

```bash
# Get API key
export API_KEY="sk_test_demo_admin_abc123"

# Query dataset via API
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/street_cleaning?limit=5"

# Get statistics
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/street_cleaning/stats"

# Get schema
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/street_cleaning/schema"
```

**API Checklist:**
- [ ] Endpoints are public (or restricted appropriately)
- [ ] Rate limiting configured
- [ ] Pagination works
- [ ] Filtering works
- [ ] Schema endpoint available

---

## Phase 10: Monitoring & Alerts (2 minutes)

### 1. Configure Alerts

```bash
# Set up data quality alert
socrata-toolkit alert create \
  --dataset street_cleaning \
  --type quality \
  --condition "completeness < 95" \
  --action "email" \
  --recipients data_owner@nyc.local

# Set up freshness alert
socrata-toolkit alert create \
  --dataset street_cleaning \
  --type freshness \
  --condition "last_update > 25 hours" \
  --action "slack" \
  --channel "#data-platform"
```

**Alert Checklist:**
- [ ] Quality alerts configured
- [ ] Freshness alerts configured
- [ ] Owner receives notifications
- [ ] Escalation path defined

### 2. Create Dashboard

```bash
# Add to Grafana dashboards
# (Manual step: visit http://localhost:3000)
```

**Dashboard Checklist:**
- [ ] Data quality panel
- [ ] Ingestion status panel
- [ ] Record count trend
- [ ] API query rate panel

---

## Phase 11: Documentation (2 minutes)

### 1. Data Dictionary

```bash
# Generate data dictionary
socrata-toolkit docs data-dictionary \
  --dataset street_cleaning \
  --output data_dictionary_street_cleaning.md
```

**Document:**
- [ ] Column descriptions
- [ ] Sample values
- [ ] Business rules
- [ ] Known limitations

### 2. Integration Guide

Create `docs/INTEGRATION_GUIDE_street_cleaning.md`:

```markdown
# Street Cleaning Integration Guide

## Dataset Overview
- **Name**: Street Cleaning Schedule
- **Owner**: [Name]
- **Records**: ~[count]
- **Update Frequency**: Daily at 2:00 AM UTC

## Accessing Data

### Via API
\`\`\`bash
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/api/v1/street_cleaning?limit=10
\`\`\`

### Via Database
\`\`\`sql
SELECT * FROM street_cleaning LIMIT 10;
\`\`\`

### Via Dashboard
Visit Grafana: http://localhost:3000

## Quality Metrics
- Completeness: 99.8%
- Validity: 99.2%
- Freshness: <1 hour

## Common Queries
[Add example queries]

## Support
Contact: data_owner@nyc.local
```

---

## Phase 12: Verification & Sign-off (5 minutes)

### 1. End-to-End Testing

```bash
# Test complete flow
./tests/test_integration_quick_start.py street_cleaning

# Check logs
docker-compose logs api | grep street_cleaning

# Verify data appears in all systems
docker-compose exec postgres psql -U dot_user -d sidewalk_db -c "
  SELECT COUNT(*) FROM street_cleaning;
"

# Check API response
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/street_cleaning/stats"

# Check metrics
curl http://localhost:9090/api/v1/query?query=pg_stat_user_tables_n_live_tup
```

**Verification Checklist:**
- [ ] Records ingested: _____ (should be non-zero)
- [ ] Quality checks pass: [ ] Yes [ ] No
- [ ] API responds with data: [ ] Yes [ ] No
- [ ] Metrics visible in Prometheus: [ ] Yes [ ] No
- [ ] Lineage recorded: [ ] Yes [ ] No
- [ ] Audit trail populated: [ ] Yes [ ] No

### 2. Owner Sign-off

- [ ] **Data Owner Approval**: ___________________ Date: _______
- [ ] **Data Quality Passed**: [ ] Yes [ ] No
- [ ] **Governance Rules Applied**: [ ] Yes [ ] No
- [ ] **Documentation Complete**: [ ] Yes [ ] No
- [ ] **Ready for Production**: [ ] Yes [ ] No

### 3. Handoff & Support

- [ ] Owner trained on:
  - [ ] Dashboard access
  - [ ] Alert configuration
  - [ ] Escalation procedures
  - [ ] API documentation

---

## Final Checklist

### ✅ All Phases Complete?

- [ ] Phase 1: Discovery & Planning
- [ ] Phase 2: Schema Registration
- [ ] Phase 3: Data Governance
- [ ] Phase 4: Quality Expectations
- [ ] Phase 5: Entity Resolution (if applicable)
- [ ] Phase 6: Ingestion Configuration
- [ ] Phase 7: Lineage Configuration
- [ ] Phase 8: Access Control
- [ ] Phase 9: API Configuration
- [ ] Phase 10: Monitoring & Alerts
- [ ] Phase 11: Documentation
- [ ] Phase 12: Verification & Sign-off

### 📊 Metrics Summary

| Metric | Target | Actual |
|--------|--------|--------|
| Completeness | 99% | _____ % |
| Validity | 98% | _____ % |
| Freshness SLA | <1h | _____ |
| Deduplication Accuracy | 99% | _____ % |
| API Availability | 99.9% | _____ % |
| Documentation Status | 100% | _____ % |

---

## Post-Integration

### Ongoing Operations

1. **Weekly Review** (15 min)
   - Check data quality metrics
   - Review alerts
   - Verify freshness SLA

2. **Monthly Audit** (30 min)
   - Access control review
   - Lineage validation
   - Cost analysis

3. **Quarterly Assessment** (1 hour)
   - Performance review
   - Roadmap discussion
   - Feedback collection

---

## Support

**Need Help?**

- **Technical Issues**: slack #data-platform
- **Data Governance**: data-governance@nyc.local
- **Security**: security@nyc.local
- **Performance**: ops-team@nyc.local

---

**Integration Date**: _________________  
**Dataset Name**: _________________  
**Data Owner**: _________________  
**Completed By**: _________________  
**Status**: [ ] In Progress [ ] Complete [ ] Production Ready

