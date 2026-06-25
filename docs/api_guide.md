# Phase 4 API Guide: NYC DOT Sidewalk Operational Intelligence

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Authentication](#authentication)
4. [Authorization](#authorization)
5. [Endpoints Reference](#endpoints-reference)
6. [Pagination & Filtering](#pagination--filtering)
7. [Error Handling](#error-handling)
8. [Caching Strategy](#caching-strategy)
9. [Rate Limiting](#rate-limiting)
10. [Integration Examples](#integration-examples)

## Overview

The NYC DOT Sidewalk Operational Intelligence API provides REST access to:
- **Sidewalk segments** with material classification and condition metrics
- **Incident reports** linked to segments and defect types
- **Repair schedules** with contractor assignments and cost tracking
- **Metric metrics** aggregated by material type, location, and contractor
- **ADA compliance** scores with failure details
- **Audit logs** for compliance and traceability
- **Data exports** in CSV and JSON formats

### Design Principles

- **Phase 1 Integration**: All responses include material_type from domain model
- **Phase 2 Observability**: All requests logged with structured JSON; metrics emitted
- **Phase 3 Caching**: Materialized view results cached with TTL management
- **Performance**: All GET endpoints <1s, list endpoints <5s with filtering
- **Security**: JWT authentication, role-based access control, request tracing
- **Reliability**: Graceful degradation if cache unavailable, comprehensive error codes

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/nyc_data.git
cd nyc_data

# Install dependencies
pip install -r requirements.txt
pip install fastapi uvicorn sqlalchemy psycopg redis pydantic python-dotenv PyJWT

# Set environment variables
export DATABASE_URL="postgresql://postgres:password@localhost:5432/nyc_sidewalk"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET_KEY="your-secret-key-at-least-32-characters-long"
```

### Running the API

```bash
# Development server
python -m uvicorn socrata_toolkit.api.main:app --reload

# Production server
uvicorn socrata_toolkit.api.main:app --host 0.0.0.0 --port 8000 --workers 4

# With Docker
docker-compose -f socrata_toolkit/api/docker-compose.yml up
```

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2026-05-10T01:51:19Z",
  "database": "healthy",
  "cache": "healthy",
  "version": "v1"
}
```

### OpenAPI Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Authentication

The API uses JWT (JSON Web Tokens) for authentication.

### Obtaining a Token

In production, tokens are typically issued by your identity provider. For testing:

```python
from socrata_toolkit.api.auth import create_access_token, JWTConfig, User, Role

# Create JWT config
config = JWTConfig(secret_key="your-secret-key-at-least-32-characters-long")

# Create user
user = User(
    user_id="user_123",
    email="analyst@nycdot.gov",
    roles=[Role.ANALYST]
)

# Generate token
token = create_access_token(user, config)
print(f"Authorization: Bearer {token}")
```

### Using the Token

Include the token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
     http://localhost:8000/api/v1/segments
```

### Token Structure

```
Header: {
  "alg": "HS256",
  "typ": "JWT"
}

Payload: {
  "user_id": "user_123",
  "email": "analyst@nycdot.gov",
  "roles": ["analyst"],
  "exp": 1684084279,
  "iat": 1683997879,
  "request_id": "req_abc123def456"
}

Signature: HMACSHA256(base64UrlEncode(header) + "." + base64UrlEncode(payload), secret_key)
```

## Authorization

The API implements role-based access control (RBAC) with three levels:

| Role | Permissions | Use Case |
|------|-------------|----------|
| **VIEWER** | Read-only: segments, incidents, repairs, Metrics, contractors, audit logs | Monitoring dashboards |
| **ANALYST** | VIEWER + write repairs, assign repairs, export data | Operations team |
| **ADMIN** | All permissions including delete | System administrators |

### Permission Matrix

| Endpoint | VIEWER | ANALYST | ADMIN |
|----------|--------|---------|-------|
| GET /segments | ✓ | ✓ | ✓ |
| GET /incidents | ✓ | ✓ | ✓ |
| POST /incidents/{id}/assign-repair | ✗ | ✓ | ✓ |
| PATCH /repairs/{id}/status | ✗ | ✓ | ✓ |
| GET /metrics/* | ✓ | ✓ | ✓ |
| GET /export/* | ✗ | ✓ | ✓ |
| GET /audit-log | ✓ | ✓ | ✓ |

### Authorization Example

```bash
# Try to update repair status without ANALYST role
curl -X PATCH \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  http://localhost:8000/api/v1/repairs/rep_123/status?new_status=in_progress

# Returns 403 Forbidden
{
  "error_code": "INSUFFICIENT_PERMISSIONS",
  "message": "This operation requires one of: analyst, admin",
  "status_code": 403,
  "request_id": "req_xyz789",
  "details": {
    "required_role": "analyst"
  }
}
```

## Endpoints Reference

### A. Segments (`/api/v1/segments`)

#### List Segments

```
GET /api/v1/segments
```

Query Parameters:
- `material_type` (string): Filter by material type (asphalt, concrete, other)
- `limit` (integer, 1-1000, default 100): Results per page
- `offset` (integer, default 0): Results to skip
- `sort_by` (string, default "segment_id"): Field to sort by
- `sort_order` (string, "asc" or "desc", default "asc"): Sort direction

Example:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/segments?material_type=asphalt&limit=50&offset=0"
```

Response:
```json
{
  "data": [
    {
      "segment_id": "seg_123",
      "material_type": "asphalt",
      "length_feet": 250.5,
      "last_updated": "2026-05-10T01:51:19Z"
    }
  ],
  "total": 1500,
  "limit": 50,
  "offset": 0,
  "timestamp": "2026-05-10T01:51:19Z",
  "data_freshness_seconds": 3600
}
```

#### Get Segment

```
GET /api/v1/segments/{segment_id}
```

Example:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/segments/seg_123
```

#### Get Segment Incidents

```
GET /api/v1/segments/{segment_id}/incidents
```

#### Get Segment Repairs

```
GET /api/v1/segments/{segment_id}/repairs
```

### B. Incidents (`/api/v1/incidents`)

#### List Incidents

```
GET /api/v1/incidents
```

Query Parameters:
- `segment_id` (string): Filter by segment
- `material_type` (string): Filter by material type
- `severity` (string): Filter by severity (low, medium, high)
- `status` (string): Filter by status (open, assigned, resolved)
- `date_from` (date): Start date (YYYY-MM-DD)
- `date_to` (date): End date (YYYY-MM-DD)
- `limit`, `offset`: Pagination

Example:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/incidents?severity=high&limit=50"
```

#### Get Incident

```
GET /api/v1/incidents/{incident_id}
```

#### Assign Repair (ANALYST+)

```
POST /api/v1/incidents/{incident_id}/assign-repair
```

Request Body:
```json
{
  "contractor_id": "cont_123",
  "estimated_cost": 1500.00,
  "scheduled_date": "2026-05-15"
}
```

### C. Repairs (`/api/v1/repairs`)

#### List Repairs

```
GET /api/v1/repairs
```

Query Parameters:
- `status` (string): Filter by status (scheduled, in_progress, completed)
- `contractor_id` (string): Filter by contractor
- `material_type` (string): Filter by material type
- `date_from`, `date_to`: Date range filter
- `limit`, `offset`: Pagination

#### Get Repair

```
GET /api/v1/repairs/{repair_id}
```

#### Update Repair Status (ANALYST+)

```
PATCH /api/v1/repairs/{repair_id}/status
```

Query Parameters:
- `new_status` (string, required): New status (scheduled, in_progress, completed)

Example:
```bash
curl -X PATCH \
  -H "Authorization: Bearer $ANALYST_TOKEN" \
  "http://localhost:8000/api/v1/repairs/rep_123/status?new_status=in_progress"
```

### D. Metrics & Metrics (`/api/v1/metrics`)

#### Metric Summary

```
GET /api/v1/metrics/summary
```

Returns complete citywide Metric snapshot with material metrics, ADA compliance, hazard coverage.

Cache: 2 hours

Example:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/metrics/summary
```

#### Material Metrics

```
GET /api/v1/metrics/by-material
```

Query Parameters:
- `material_type` (string): Filter by material

Example:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/metrics/by-material?material_type=asphalt"
```

Response:
```json
{
  "data": [
    {
      "material_type": "asphalt",
      "defect_rate_pct": 12.5,
      "avg_age_years": 8.2,
      "hazard_count": 45,
      "total_linear_feet": 15000.0,
      "lifecycle_cost_sqft": 125.00
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0,
  "timestamp": "2026-05-10T01:51:19Z",
  "data_freshness_seconds": 3600
}
```

#### ADA Compliance

```
GET /api/v1/metrics/ada-compliance
```

#### Hazard Coverage

```
GET /api/v1/metrics/hazard-coverage
```

#### Cost Analytics

```
GET /api/v1/metrics/cost-analytics
```

### E. Contractors (`/api/v1/contractors`)

#### List Contractors

```
GET /api/v1/contractors
```

Query Parameters:
- `sort_by` (string, default "quality_score"): Field to sort by
- `limit`, `offset`: Pagination

#### Get Contractor

```
GET /api/v1/contractors/{contractor_id}
```

### F. Compliance & Audit (`/api/v1/compliance`)

#### Audit Log

```
GET /api/v1/compliance/audit-log
```

Query Parameters:
- `actor` (string): Filter by user/system account
- `action` (string): Filter by action type
- `dataset_id` (string): Filter by dataset
- `date_from`, `date_to`: Date range
- `limit`, `offset`: Pagination

Note: Audit logs are never cached for compliance.

### G. Data Export (`/api/v1/export`)

#### Export Segments CSV (ANALYST+)

```
GET /api/v1/export/segments/csv
```

Query Parameters:
- `material_type` (string): Filter by material (optional)

Returns CSV file with headers: segment_id, material_type, length_feet, updated_at

#### Export Incidents CSV (ANALYST+)

```
GET /api/v1/export/incidents/csv
```

#### Export Metrics JSON

```
GET /api/v1/export/metrics/json
```

## Pagination & Filtering

### Pagination

All list endpoints support limit/offset pagination:

```bash
# Get first 50 results
curl "http://localhost:8000/api/v1/segments?limit=50&offset=0"

# Get next 50
curl "http://localhost:8000/api/v1/segments?limit=50&offset=50"

# Max limit is 1000
curl "http://localhost:8000/api/v1/segments?limit=1000"
```

Response includes pagination metadata:
```json
{
  "data": [...],
  "total": 5000,
  "limit": 50,
  "offset": 0,
  "timestamp": "2026-05-10T01:51:19Z",
  "data_freshness_seconds": 3600
}
```

### Filtering

Endpoints support column-specific query parameters:

```bash
# Filter incidents by severity and date range
curl "http://localhost:8000/api/v1/incidents?severity=high&date_from=2026-05-01&date_to=2026-05-10"

# Filter repairs by status and contractor
curl "http://localhost:8000/api/v1/repairs?status=in_progress&contractor_id=cont_123"

# Combine filters
curl "http://localhost:8000/api/v1/incidents?material_type=asphalt&severity=high&limit=25"
```

### Sorting

List endpoints support sorting:

```bash
# Sort by segment ID ascending
curl "http://localhost:8000/api/v1/segments?sort_by=segment_id&sort_order=asc"

# Sort by material type descending
curl "http://localhost:8000/api/v1/segments?sort_by=material_type&sort_order=desc"
```

## Error Handling

All errors return consistent format:

```json
{
  "error_code": "RESOURCE_NOT_FOUND",
  "message": "Segment 'seg_123' not found",
  "status_code": 404,
  "request_id": "req_abc123def456",
  "details": {
    "resource_type": "segment",
    "resource_id": "seg_123"
  },
  "timestamp": "2026-05-10T01:51:19Z"
}
```

### Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `INVALID_TOKEN` | 401 | JWT token is invalid |
| `EXPIRED_TOKEN` | 401 | JWT token has expired |
| `MISSING_TOKEN` | 401 | Authorization header missing |
| `INSUFFICIENT_PERMISSIONS` | 403 | User lacks required role |
| `ROLE_REQUIRED` | 403 | Specific role required |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource not found |
| `SEGMENT_NOT_FOUND` | 404 | Segment doesn't exist |
| `INCIDENT_NOT_FOUND` | 404 | Incident doesn't exist |
| `REPAIR_NOT_FOUND` | 404 | Repair doesn't exist |
| `CONTRACTOR_NOT_FOUND` | 404 | Contractor doesn't exist |
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `INVALID_REQUEST` | 422 | Invalid request format |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `DATABASE_ERROR` | 500 | Database operation failed |
| `CACHE_ERROR` | 500 | Cache operation failed |
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected error |

## Caching Strategy

The API caches responses with TTL management based on data type:

| Data Type | TTL | Refresh | Cache Key Pattern |
|-----------|-----|---------|-------------------|
| Summary Metrics | 2 hours | Daily via Phase 3 DAG | `metric:summary` |
| Segment Details | 24 hours | Static data | `segment:{segment_id}` |
| Contractor Metrics | 6 hours | Weekly repair DAG | `contractor:{contractor_id}` |
| Incident Lists | 1 hour | Daily incident DAG | `incidents:list` |
| Segment Incidents | 1 hour | Daily incident DAG | `segment:{id}:incidents` |
| Audit Logs | No cache | Always fresh | - |

### Cache Headers

All cached responses include:

```
X-Cache-Status: HIT|MISS
Cache-Control: max-age=3600
```

### Cache Invalidation

Write operations automatically invalidate related cache:

- POST `/incidents/{id}/assign-repair` → Clears `repair:*`
- PATCH `/repairs/{id}/status` → Clears `repair:*`, `metric:*`

### Graceful Degradation

If Redis is unavailable, the API automatically falls back to database queries without caching.

## Rate Limiting

The API enforces rate limits to prevent abuse:

- **Default**: 100 requests per minute per IP
- **Override**: Set `RATE_LIMIT_REQUESTS` environment variable

Rate limit errors:

```
HTTP/1.1 429 Too Many Requests

{
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded",
  "status_code": 429,
  "details": {
    "limit": 100,
    "window_seconds": 60,
    "retry_after": 45
  }
}
```

Response headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1684084334
Retry-After: 45
```

## Integration Examples

### Python Client

```python
import requests
from requests.auth import HTTPBearerAuth

# Configuration
BASE_URL = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Create client
auth = HTTPBearerAuth(TOKEN)

# Get incidents by severity
response = requests.get(
    f"{BASE_URL}/api/v1/incidents",
    params={
        "severity": "high",
        "limit": 50,
        "offset": 0
    },
    auth=auth
)

if response.status_code == 200:
    data = response.json()
    incidents = data["data"]
    print(f"Found {data['total']} incidents")
    for incident in incidents:
        print(f"  {incident['incident_id']}: {incident['severity']}")
else:
    error = response.json()
    print(f"Error: {error['error_code']} - {error['message']}")
```

### JavaScript/Fetch

```javascript
const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...";

async function getMetricSummary() {
  const response = await fetch(
    'http://localhost:8000/api/v1/metrics/summary',
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`${error.error_code}: ${error.message}`);
  }

  const data = await response.json();
  return data;
}

// Usage
getMetricSummary()
  .then(metrics => {
    console.log('Material metrics:', metrics.material_metrics);
    console.log('ADA compliance:', metrics.ada_metrics);
    console.log('Hazard coverage:', metrics.hazard_metrics);
  })
  .catch(error => console.error(error));
```

### cURL Examples

```bash
# Get all incidents with high severity
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/incidents?severity=high&limit=100"

# Get contractor performance metrics
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/contractors/cont_123"

# Update repair status (requires ANALYST role)
curl -X PATCH \
  -H "Authorization: Bearer $ANALYST_TOKEN" \
  "http://localhost:8000/api/v1/repairs/rep_123/status?new_status=completed"

# Export incidents as CSV (requires ANALYST role)
curl -H "Authorization: Bearer $ANALYST_TOKEN" \
  "http://localhost:8000/api/v1/export/incidents/csv?severity=high" \
  > incidents_high_severity.csv

# Query audit log for compliance
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/compliance/audit-log?action=update_repair_status&limit=50"
```

### Response Tracing

Use `X-Request-ID` header for distributed tracing:

```bash
# Make request with custom request ID
curl -H "Authorization: Bearer $TOKEN" \
  -H "X-Request-ID: my-custom-request-id" \
  http://localhost:8000/api/v1/segments/seg_123

# Response will include request ID
# X-Request-ID: my-custom-request-id
```

All logs will include this request ID for tracing end-to-end.

## Performance Tips

1. **Use pagination**: Always set reasonable limit (50-100) to avoid timeouts
2. **Filter early**: Use query parameters to filter data at the source
3. **Cache summary Metrics**: Summary endpoint has 2-hour cache, good for dashboards
4. **Batch export**: Use CSV export for bulk data rather than multiple GET requests
5. **Monitor freshness**: Check `data_freshness_seconds` in responses to understand data age
6. **Connection pooling**: Client libraries handle this automatically
7. **Retry logic**: Implement exponential backoff for transient failures

## Troubleshooting

### 401 Unauthorized

- Verify token is included in `Authorization: Bearer` header
- Check token hasn't expired (24 hours default)
- Verify secret key matches between client and server

### 403 Forbidden

- Check user role meets endpoint requirements
- List your user's roles: decode JWT token

### 404 Not Found

- Verify resource ID is correct
- Check resource exists (may have been deleted)
- Check filters don't eliminate all results

### 429 Rate Limited

- Wait `Retry-After` seconds before retrying
- Implement exponential backoff
- Contact admin to increase rate limit if needed

### 503 Service Unavailable

- Check database is running and accessible
- Check Redis is running (cache operations may fail but API continues)
- Check connectivity to Phase 3 materialized views

---

For more information, see:
- [API Deployment Guide](api_deployment.md)
- [Examples & Use Cases](api_examples.md)
- [OpenAPI Documentation](http://localhost:8000/docs)
