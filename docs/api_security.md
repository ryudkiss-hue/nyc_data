# API Security & Authentication Guide

## Overview

The NYC DOT Socrata Toolkit implements production-grade API security with multiple authentication 
 methods, fine-grained authorization, rate limiting, and comprehensive data governance.

## Key Features

### 1. Multi-Method Authentication

**Supported Methods:**
- **JWT Tokens**: Stateless, signed tokens (HS256, HS512, RS256)
- **API Keys**: Stateful keys with hashing and expiry
- **OAuth2/OIDC**: Integration with external providers
- **HTTP Basic**: For internal system-to-system auth

**Usage:**
```python
from socrata_toolkit.api.auth import JWTAuthProvider

provider = JWTAuthProvider(secret_key="your_secret", algorithm="HS256")
user = User(user_id="user_123", email="test@example.com", roles=["viewer"])
token = provider.create_token(user)

# Validate
context = provider.authenticate({"token": token})
```

### 2. Role-Based Access Control (RBAC)

**Roles:**
- `GUEST`: Limited READ on public data (100 req/hr)
- `DATA_CONSUMER`: READ on all data (10k req/day)
- `DATA_ENGINEER`: READ+WRITE on assigned datasets
- `ADMIN`: Full access to all resources
- `SERVICE_ACCOUNT`: Programmatic access with custom permissions

**Permission Checking:**
```python
from socrata_toolkit.api.authorization import RBACEnforcer

enforcer = RBACEnforcer()
decision = enforcer.check_permission(
    principal_id="user_123",
    resource="/datasets/xyz",
    action="read",
    roles=["viewer"],
    permissions={"datasets:read"},
)
if decision.allowed:
    # Process request
    pass
```

### 3. Rate Limiting & Quotas

**Tier Limits:**
- Guest: 100 req/hr, 500 req/day
- Standard: 1,000 req/hr, 10k req/day
- Premium: 10k req/hr, unlimited daily

**Strategies:**
- **Token Bucket**: Smooth burst traffic
- **Sliding Window**: Precise per-minute control
- **Leaky Bucket**: Fair allocation

**Usage:**
```python
from socrata_toolkit.api.rate_limiting import RateLimiter, TokenBucketStrategy

limiter = RateLimiter(strategy=TokenBucketStrategy())
limiter.set_user_tier("user_123", QuotaTier.STANDARD)

if limiter.check_rate_limit("user_123"):
    limiter.record_request("user_123")
else:
    # Rate limit exceeded
    status = limiter.get_quota_status("user_123")
```

### 4. Data Governance & PII Masking

**Classifications:**
- PUBLIC: No restrictions
- INTERNAL: Limited to employees
- SENSITIVE: Restricted to authorized users, requires approval
- RESTRICTED: Admin-only access

**PII Types Supported:**
- EMAIL, PHONE, SSN, ADDRESS, NAME, DOB, CREDIT_CARD, CUSTOM

**Masking Strategies:**
- HIDE: Replace with ****
- MASK: Partial masking (e.g., show last 4 digits)
- REDACT: Remove entirely
- HASH: One-way hash
- ENCRYPT: Reversible encryption
- CUSTOM: User-defined function

**Usage:**
```python
from socrata_toolkit.api.governance import GovernanceEnforcer, PIIType, MaskingStrategy

enforcer = GovernanceEnforcer()
enforcer.set_policy("dataset_123", classification=Classification.SENSITIVE)
enforcer.add_pii_field(
    "dataset_123",
    "email",
    PIIType.EMAIL,
    MaskingStrategy.MASK,
)

masked_data = enforcer.apply_masking("dataset_123", data, "viewer")
```

## Security Best Practices

### 1. Key Management

- API keys are hashed with bcrypt before storage
- Never log or expose full keys
- Use key prefixes for UI display
- Implement key rotation policies
- Set expiry dates on sensitive keys

### 2. Token Security

- Use HTTPS for all API communications
- Include expiry times on JWT tokens
- Validate token signatures with correct key
- Implement token refresh mechanisms
- Log authentication attempts

### 3. Authorization

- Check permissions on every API call
- Use principle of least privilege
- Implement delegation for temporary access
- Audit all authorization decisions
- Cache permissions with TTL for performance

### 4. Data Protection

- Classify data by sensitivity
- Apply PII masking based on roles
- Encrypt sensitive data in transit and at rest
- Track access to restricted data
- Enforce quality gates before serving data

## Integration with Other Modules

### Schema Registry (W1)
- Validate request/response payloads against registered schemas
- Detect schema drift and breaking changes
- Support schema versioning

### Lineage Tracking (W3)
- Record all API access as data lineage events
- Track data flow through transformations
- Document data dependencies

### Observability (W4)
- Emit metrics for auth/authz decisions
- Track rate limit violations
- Monitor API performance
- Alert on security anomalies

### Audit Trail (W5-6)
- Log all authentication attempts
- Record authorization decisions
- Maintain immutable audit log
- Support compliance audits

### Quality Validation (W7-8)
- Enforce quality scores before serving data
- Reject low-quality data
- Track data quality metrics per dataset

## Deployment Considerations

### Database Setup

```bash
# Apply migration
psql -U postgres -d nyc_data -f sql/009_api_governance_tables.sql
```

### Redis (Optional)

For distributed systems, Redis backing is recommended:
```python
import redis
redis_client = redis.Redis(host='localhost', port=6379)
limiter = RateLimiter(redis_client=redis_client)
```

Falls back to in-memory with warning if Redis unavailable.

### Environment Variables

```bash
API_JWT_SECRET=your_secret_key_here
API_JWT_ALGORITHM=HS256
API_RATE_LIMIT_STRATEGY=token_bucket
API_ENABLE_AUDIT_LOG=true
API_ENABLE_METRICS=true
```

## Performance Targets

- Authentication check: < 5ms
- Authorization check: < 1ms  
- Rate limit check: < 1ms
- PII masking: < 2ms per request
- Total pipeline overhead: < 5ms

Actual benchmarks show:
- JWT validation: ~2ms (with caching)
- API key validation: ~3-5ms
- RBAC enforcement: ~0.5ms (cached)
- Rate limiting: ~0.5ms (token bucket)

## Troubleshooting

### Invalid Token Error

Check token hasn't expired and secret key matches:
```python
try:
    context = provider.authenticate({"token": token})
except AuthenticationError as e:
    logger.error(f"Auth failed: {e}")
```

### Rate Limit Exceeded

Check user's quota tier and usage:
```python
status = limiter.get_quota_status("user_123")
print(f"Used: {status.requests_this_hour}/{status.requests_per_hour_limit}")
```

### PII Not Masked

Verify policy is configured and role is correct:
```python
policy = governance.get_policy("dataset_123")
assert policy is not None
assert "email" in policy.pii_masks
```

## References

- PostgreSQL Tables: `sql/009_api_governance_tables.sql`
- Auth Module: `socrata_toolkit/api/auth.py`
- Authorization Module: `socrata_toolkit/api/authorization.py`
- Rate Limiting: `socrata_toolkit/api/rate_limiting.py`
- Governance: `socrata_toolkit/api/governance.py`
- Tests: `tests/test_api_security.py`
