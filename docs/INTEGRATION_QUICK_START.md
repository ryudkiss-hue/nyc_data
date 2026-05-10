# Integration Quick Start Guide

**Get your first dataset into the system in 15 minutes**

Complete end-to-end walkthrough of data ingestion, validation, quality checks, and API access.

---

## Prerequisites

Ensure Docker environment is running:

```bash
# Start services
./scripts/docker-start.sh

# Verify API is ready
curl http://localhost:8000/health
# Response: {"status": "healthy"}
```

---

## Step 1: Load Sample Data (2 minutes)

The Docker environment comes pre-seeded with sample data. Verify it's loaded:

```bash
# Connect to database
docker-compose exec postgres psql -U dot_user -d sidewalk_db

# Check sample data
SELECT COUNT(*) as inspection_count FROM sidewalk_inspections;
SELECT COUNT(*) as complaint_count FROM complaints_311;
SELECT COUNT(*) as contractor_count FROM contractors;

# Exit PostgreSQL
\q
```

**Expected Output:**
```
 inspection_count
──────────────────
          1000
(1 row)

 complaint_count
─────────────────
          500
(1 row)

 contractor_count
──────────────────
           50
(1 row)
```

---

## Step 2: Validate Schema (1 minute)

Verify the schema is correctly registered:

```bash
# Check schema via PostgreSQL
docker-compose exec postgres psql -U dot_user -d sidewalk_db -c "
  SELECT 
    column_name,
    data_type,
    is_nullable
  FROM information_schema.columns
  WHERE table_name = 'sidewalk_inspections'
  ORDER BY ordinal_position
  LIMIT 10;
"
```

**Expected Output:**
```
      column_name       | data_type | is_nullable
───────────────────────┼───────────┼─────────────
 id                    | integer   | NO
 inspection_id         | character | NO
 block_id              | integer   | YES
 lot_id                | integer   | YES
 bin                   | character | YES
 location              | geography | YES
 inspection_date       | date      | YES
 inspector_id          | character | YES
 material_type         | character | YES
 condition_rating      | character | YES
```

---

## Step 3: Run Quality Check (2 minutes)

Check data quality metrics:

```bash
# Access quality metrics
docker-compose exec postgres psql -U dot_user -d sidewalk_db -c "
  SELECT 
    dataset_name,
    metric_name,
    metric_value,
    measurement_timestamp
  FROM quality_metrics
  WHERE dataset_name = 'sidewalk_inspections'
  ORDER BY measurement_timestamp DESC
  LIMIT 5;
"
```

**Expected Output:**
```
      dataset_name       |  metric_name  | metric_value |     measurement_timestamp
────────────────────────┼───────────────┼──────────────┼─────────────────────────────
 sidewalk_inspections   | consistency   |      99.5000 | 2026-05-10 14:13:00
 sidewalk_inspections   | validity      |      98.8000 | 2026-05-10 14:13:00
 sidewalk_inspections   | completeness  |      99.2000 | 2026-05-10 14:13:00
```

---

## Step 4: Query Data via API (2 minutes)

Access the data through the REST API:

```bash
# Get API key (demo admin key)
export API_KEY="sk_test_demo_admin_abc123"

# Query sidewalk inspections (first 5 records)
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/sidewalk_inspections?limit=5" | python -m json.tool
```

**Expected Output:**
```json
{
  "data": [
    {
      "id": 1,
      "inspection_id": "INSP_000001",
      "material_type": "Concrete",
      "condition_rating": "Good",
      "ada_compliant": true,
      "defect_count": 5,
      "estimated_repair_cost": 2500.00,
      "inspection_date": "2025-08-15",
      "created_at": "2026-05-10T14:13:00Z"
    },
    ...
  ],
  "total": 1000,
  "limit": 5,
  "offset": 0
}
```

### Additional API Queries

```bash
# Get 311 complaints
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/complaints_311?limit=5" | python -m json.tool

# Get contractors
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/contractors?limit=5" | python -m json.tool

# Filter sidewalk inspections by material type
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/sidewalk_inspections?material_type=Concrete&limit=5" | python -m json.tool

# Get ADA compliance statistics
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/sidewalk_inspections/stats/ada_compliance" | python -m json.tool

# Get data by location (geospatial query)
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/sidewalk_inspections/near?lat=40.75&lon=-74.00&radius_meters=1000" | python -m json.tool
```

---

## Step 5: View Lineage & Audit Trail (3 minutes)

Check data provenance and change history:

```bash
# View data lineage
docker-compose exec postgres psql -U dot_user -d sidewalk_db -c "
  SELECT source_dataset, target_dataset, transformation
  FROM data_lineage
  WHERE source_dataset = 'sidewalk_inspections'
  ORDER BY created_at;
"
```

**Expected Output:**
```
  source_dataset      |   target_dataset    |           transformation
──────────────────────┼─────────────────────┼────────────────────────────────
 sidewalk_inspections | compliance_metrics  | ADA compliance calculation
 sidewalk_inspections | material_analytics  | Material type aggregation
```

### Check Audit Trail

```bash
# View audit log entries (recent changes)
docker-compose exec postgres psql -U dot_user -d sidewalk_db -c "
  SELECT 
    table_name,
    operation,
    record_id,
    changed_at
  FROM audit_log
  ORDER BY changed_at DESC
  LIMIT 10;
"
```

---

## Step 6: Check Compliance Status (2 minutes)

Verify compliance metrics:

```bash
# Query compliance information
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/api/v1/sidewalk_inspections/compliance/ada" | python -m json.tool

# Expected output:
# {
#   "total_records": 1000,
#   "ada_compliant": 700,
#   "ada_non_compliant": 200,
#   "unknown": 100,
#   "compliance_percentage": 70.0,
#   "status": "NEEDS_ATTENTION"
# }
```

Check data governance:

```bash
# View data classification
docker-compose exec postgres psql -U dot_user -d sidewalk_db -c "
  SELECT 
    dataset_name,
    record_count,
    created_at
  FROM sample_datasets;
"
```

---

## Step 7: Explore Dashboards (3+ minutes)

Interactive visualization of data and metrics:

### Grafana Dashboard

1. **Open Grafana**: http://localhost:3000
2. **Login**: admin / admin
3. **Explore Pre-configured Dashboards**:

#### Data Quality Dashboard
- Shows completeness, validity, consistency metrics
- Filter by dataset and time range
- Real-time alerts

#### System Overview
- API performance metrics
- Database connection pool
- Cache hit rates

#### Material Compliance
- ADA compliance by material type
- Condition ratings distribution
- Defect trends

### Prometheus Metrics

Access raw metrics at: http://localhost:9090

**Useful Queries:**
```promql
# API request rate (requests per second)
rate(http_requests_total[1m])

# API response time (p95)
histogram_quantile(0.95, http_request_duration_seconds)

# Database connection pool usage
pg_stat_activity_count

# Cache hit rate
redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)
```

### Jaeger Distributed Tracing

Access at: http://localhost:16686

**Explore**:
- Select "api" service
- Choose endpoint (e.g., "/api/v1/sidewalk_inspections")
- View distributed traces
- Analyze latency breakdowns

---

## What's Happening Under the Hood

### Data Flow

```
1. Data Source (CSV/API)
   ↓
2. Ingestion Pipeline
   ↓
3. Schema Validation
   ↓
4. Quality Checks
   ↓
5. Deduplication
   ↓
6. Entity Resolution
   ↓
7. Compliance Checks
   ↓
8. Storage (PostgreSQL)
   ↓
9. Indexing & Cache (Redis)
   ↓
10. API Availability
   ↓
11. Monitoring (Prometheus/Grafana)
   ↓
12. Audit Logging
```

### Services in Action

| Service | Role |
|---------|------|
| **PostgreSQL** | Primary data store |
| **Redis** | Query caching, rate limiting |
| **API** | REST endpoints, authentication |
| **Prometheus** | Metrics collection |
| **Grafana** | Dashboard visualization |
| **Jaeger** | Request tracing |

---

## Next: Integrate Your Own Data

Once sample data is working, follow the **[INTEGRATION_CHECKLIST.md](INTEGRATION_CHECKLIST.md)** to:

1. Register a new dataset
2. Define schema and quality rules
3. Configure governance
4. Run validation
5. Set up ingestion schedule
6. Verify end-to-end

**Total time: 30-45 minutes**

---

## Testing with Python

Run the integration example:

```bash
# Run Python example
python examples/integration_example.py

# Expected output:
# Connected to API successfully
# Schema registered: sidewalk_inspections (25 columns)
# Quality check passed: 99.2% valid
# Stored 10 records via API
# Retrieved 5 records via query
```

---

## Testing with Bash

Run the bash example:

```bash
# Run bash example
bash examples/integration_example.sh

# Expected output:
# [OK] API is healthy
# [OK] Database connection successful
# [OK] Schema registry shows 8 datasets
# [OK] Sample queries return data
# [OK] Quality metrics are good
```

---

## Troubleshooting

### "Connection Refused" Errors

```bash
# Verify services are running
docker-compose ps

# Check API logs
docker-compose logs api

# Ensure all services are healthy
for service in postgres redis api; do
  docker-compose exec $service true && echo "$service: OK" || echo "$service: FAILED"
done
```

### API Key Not Working

```bash
# Verify API key exists
docker-compose exec postgres psql -U dot_user -d sidewalk_db -c "
  SELECT key, is_active FROM demo_api_keys LIMIT 3;
"

# Use the correct key from output
export API_KEY="sk_test_demo_admin_abc123"
```

### Query Returns No Results

```bash
# Check data is loaded
docker-compose exec postgres psql -U dot_user -d sidewalk_db -c "
  SELECT COUNT(*) FROM sidewalk_inspections;
"

# If count is 0, re-initialize:
./scripts/docker-reset.sh
./scripts/docker-start.sh
```

### Slow Performance

```bash
# Check database performance
docker-compose exec postgres psql -U dot_user -d sidewalk_db -c "
  EXPLAIN ANALYZE
  SELECT * FROM sidewalk_inspections LIMIT 10;
"

# Monitor resource usage
docker stats
```

---

## API Documentation

Full API reference available at:

**http://localhost:8000/docs** (interactive Swagger UI)

**http://localhost:8000/redoc** (ReDoc documentation)

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/sidewalk_inspections` | GET | List inspections |
| `/api/v1/complaints_311` | GET | List complaints |
| `/api/v1/contractors` | GET | List contractors |
| `/api/v1/sidewalk_inspections/stats/ada_compliance` | GET | ADA compliance stats |
| `/api/v1/sidewalk_inspections/near` | GET | Geospatial queries |

---

## Success Checklist

- [ ] Docker environment started successfully
- [ ] All services healthy (docker-compose ps)
- [ ] Sample data loaded (1000 inspections, 500 complaints, 50 contractors)
- [ ] Schema validated
- [ ] Quality metrics show >95% validity
- [ ] API responds with sample data
- [ ] Lineage shows transformations
- [ ] Audit log captures changes
- [ ] Compliance metrics available
- [ ] Grafana dashboards display data
- [ ] Prometheus metrics collected
- [ ] Jaeger traces captured

---

## Time Summary

| Step | Time | Total |
|------|------|-------|
| 1. Load Data | 2 min | 2 min |
| 2. Validate Schema | 1 min | 3 min |
| 3. Quality Check | 2 min | 5 min |
| 4. Query API | 2 min | 7 min |
| 5. Lineage & Audit | 3 min | 10 min |
| 6. Check Compliance | 2 min | 12 min |
| 7. Explore Dashboards | 3+ min | 15+ min |

---

## Next Steps

1. **Understand Architecture**: Read [COMPREHENSIVE_ARCHITECTURE_ASSESSMENT.md](COMPREHENSIVE_ARCHITECTURE_ASSESSMENT.md)
2. **Integrate Your Data**: Follow [INTEGRATION_CHECKLIST.md](INTEGRATION_CHECKLIST.md)
3. **Monitor System**: View [EXECUTIVE_DASHBOARD.md](EXECUTIVE_DASHBOARD.md)
4. **Reference Metrics**: Check [METRICS_GLOSSARY.md](METRICS_GLOSSARY.md)
5. **Setup Guide**: Review [DOCKER_SETUP.md](DOCKER_SETUP.md)

---

**Created**: 2026-05-10  
**Last Updated**: 2026-05-10  
**Status**: Production Ready

