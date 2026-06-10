# API Versioning Strategy

## Overview

NYC DOT API supports multiple concurrent versions with graceful deprecation and breaking change management.

## Version Lifecycle

**Status Progression:**
```
ACTIVE → DEPRECATED → SUNSET
```

- **ACTIVE**: Currently supported, recommended for new consumers
- **DEPRECATED**: Still supported but not recommended, warning issued
- **SUNSET**: No longer supported, requests rejected

## Current Versions

| Version | Status | Release Date | Sunset Date | Notes |
|---------|--------|--------------|-------------|-------|
| v1 | ACTIVE | 2025-11 | - | Initial release |
| v2 | ACTIVE | 2025-12 | - | Added versioning support |
| v3 | ACTIVE | 2026-01 | - | Enhanced auth |
| v4 | ACTIVE | 2026-05 | - | Comprehensive governance |

## Version Negotiation

### Accept Header
```http
GET /api/datasets
Accept: application/json; version=v2
```

### Query Parameter
```http
GET /api/datasets?api_version=v2
```

### URL Path
```http
GET /api/v2/datasets
```

### Default Behavior
If no version specified, latest active version is used (currently v4).

## Breaking Changes

### v1 → v2
- Added API versioning support
- Response headers include `X-API-Version`

### v2 → v3
- Enhanced JWT validation with RS256 support
- Added role-based access control

### v3 → v4
- Added rate limiting per user
- Introduced data governance policies
- Added PII field masking
- Breaking: Some endpoints require explicit dataset classification

## Backward Compatibility

Old versions continue to work with deprecation warnings:
```
HTTP/1.1 200 OK
X-API-Version: v2
X-API-Version-Deprecated: true
X-API-Version-Sunset: 2026-08-15
```

## Migration Guide

### From v1 to v2
No breaking changes, deprecation warnings only.

### From v2 to v3
No code changes required, RBAC is automatically enforced.

### From v3 to v4
Datasets now require governance policies. Add this before using v4 endpoints:
```python
governance.set_policy(
    dataset_id="your_dataset",
    classification="public|internal|sensitive|restricted"
)
```

## Schema Evolution

Each version tracks schema changes:
```python
from socrata_toolkit.api.versioning import VersionManager

manager = VersionManager()
changes = manager.get_schema_changes("v1", "v3")
# Returns: List[SchemaChange]
```

## Deprecation Timeline

### v1 Deprecation (if planned)
```python
manager.deprecate_version(
    "v1",
    deprecation_date=datetime.now(),
    sunset_date=datetime.now() + timedelta(days=90),
)
```

After sunset date, v1 endpoints return 410 Gone.

## Implementation

```python
from socrata_toolkit.api.versioning import VersionManager

manager = VersionManager()

# Negotiation
result = manager.negotiate_version(
    request_version=request.args.get("api_version")
)

if result.is_deprecated:
    response.headers["X-API-Version-Deprecated"] = "true"
    logger.warning(result.deprecation_warning)

return response_for_version(result.negotiated_version)
```

## Best Practices

1. **Version in URL**: `/api/v2/datasets` is preferred
2. **Graceful Degradation**: Old clients work with warnings
3. **Long Support Windows**: Minimum 6 months from deprecation to sunset
4. **Clear Communication**: Document breaking changes early
5. **Testing**: Test both old and new versions in CI/CD

## References

- Implementation: `socrata_toolkit/api/versioning.py`
- Tests: `tests/test_api_security.py`
