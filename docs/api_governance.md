# Data Governance & PII Protection Guide

## Overview

The API enforces data governance policies including classification, PII masking, quality gates, and retention policies.

## Data Classification

### PUBLIC
- No restrictions on access or use
- Suitable for external sharing
- Example: City budget summaries

### INTERNAL
- For NYC government employees only
- Can be exported by authorized users
- Requires basic authentication

### SENSITIVE
- Restricted to authorized analysts
- Requires approval workflow
- Cannot be exported without audit
- Example: Sidewalk repair locations (security concern)

### RESTRICTED
- Admin-only access
- Immutable audit trail required
- Example: Personal information, financial data

## PII Field Types

| Type | Pattern | Example | Default Mask |
|------|---------|---------|--------------|
| EMAIL | user@domain.com | john@example.com | j***@example.com |
| PHONE | (555) 123-4567 | (555) 123-4567 | (***) ***-4567 |
| SSN | 123-45-6789 | 123-45-6789 | ***-**-6789 |
| ADDRESS | Full address | 123 Main St... | [MASKED], [MASKED] 10001 |
| NAME | Full name | John Doe | J*o* D** |
| DOB | YYYY-MM-DD | 1990-01-15 | 1990-** -** |
| CREDIT_CARD | 1234-5678-... | 1234-5678-9012-3456 | 1234-****-****-3456 |

## Configuration Examples

### Dataset with Public Classification
```python
from socrata_toolkit.api.governance import GovernanceEnforcer, Classification

governance = GovernanceEnforcer()
governance.set_policy(
    dataset_id="budget_summary_2025",
    classification=Classification.PUBLIC,
    owner="analytics@nycdot.gov",
)
# No PII masking needed for public data
```

### Dataset with Sensitive Data
```python
governance.set_policy(
    dataset_id="sidewalk_repairs",
    classification=Classification.SENSITIVE,
    owner="operations@nycdot.gov",
    retention_days=2555,  # ~7 years
)

# Add PII fields
governance.add_pii_field(
    "sidewalk_repairs",
    "contractor_contact",
    PIIType.PHONE,
    MaskingStrategy.MASK,
)
```

### Auto-Detection of PII
```python
sample_data = [
    {"email": "john@example.com", "phone": "(555) 123-4567"},
    {"email": "jane@example.com", "phone": "(555) 234-5678"},
]

detected = governance.auto_detect_pii(
    "new_dataset",
    sample_data,
    threshold=0.5,  # 50% of records must match
)
# Returns: {"email": PIIType.EMAIL, "phone": PIIType.PHONE}
```

## Quality Gates

Minimum quality requirements before data is served:

```python
governance.set_quality_gate(
    dataset_id="critical_data",
    min_completeness=0.95,  # 95% fields populated
    min_validity=0.99,      # 99% valid values
    min_timeliness=0.8,     # Data within 1 day
    min_accuracy=0.95,      # 95% correct
)

# Enforcement happens automatically in request pipeline
```

## Access Control by Classification

| Role | PUBLIC | INTERNAL | SENSITIVE | RESTRICTED |
|------|--------|----------|-----------|------------|
| Guest | READ | - | - | - |
| Data Consumer | READ, EXPORT | READ, EXPORT | - | - |
| Data Engineer | READ, WRITE, EXPORT | READ, WRITE, EXPORT | READ, EXPORT* | - |
| Admin | READ, WRITE, DELETE, ADMIN | READ, WRITE, DELETE, ADMIN | READ, WRITE, DELETE, ADMIN | READ, WRITE, DELETE, ADMIN |

*Requires approval workflow

## Masking Strategies

### HIDE
Replaces entire value with replacement string (default "****")
```python
enforcer.add_pii_field(
    "dataset",
    "password_hash",
    PIIType.CUSTOM,
    MaskingStrategy.HIDE,
    replacement_value="[ENCRYPTED]",
)
```

### MASK
Partial masking preserving some information
```python
# Shows format: j***@example.com
# Shows format: (***) ***-4567
# Shows format: ***-**-6789
```

### REDACT
Completely removes field
```python
enforcer.add_pii_field(
    "dataset",
    "ssn",
    PIIType.SSN,
    MaskingStrategy.REDACT,
)
```

### HASH
One-way hash (cannot be reversed)
```python
enforcer.add_pii_field(
    "dataset",
    "customer_id",
    PIIType.CUSTOM,
    MaskingStrategy.HASH,
)
```

### CUSTOM
User-defined masking function
```python
def mask_credit_card(value):
    if len(str(value)) >= 4:
        return f"****-****-****-{str(value)[-4:]}"
    return "****"

enforcer.add_pii_field(
    "dataset",
    "card_number",
    PIIType.CREDIT_CARD,
    MaskingStrategy.CUSTOM,
    custom_function=mask_credit_card,
)
```

## Audit Trail

All data access is logged:
- User ID and role
- Dataset ID and classification
- Fields accessed
- Timestamp and action
- IP address and user agent

Query audit logs:
```python
# Via API (requires ADMIN role)
GET /api/v1/compliance/audit-log?dataset_id=xyz&limit=100

# Via database
SELECT * FROM api_audit_log 
WHERE dataset_id = 'xyz' 
ORDER BY timestamp DESC 
LIMIT 100;
```

## Retention Policy

Data retention based on classification:
```python
governance.set_policy(
    "dataset_xyz",
    retention_days=2555,  # ~7 years
)

# After retention period, data is automatically deleted
# Exception: Always retain audit logs for compliance
```

## Performance

- Policy lookup: < 1ms (cached)
- PII masking: < 2ms per record
- Quality gate check: < 5ms
- Total governance overhead: < 5ms per request

## Best Practices

1. **Classify Early**: Set classification when dataset is created
2. **Auto-Detect PII**: Use auto-detection as starting point
3. **Audit Access**: Always log access to sensitive data
4. **Role-Based Masking**: Different roles see different levels of detail
5. **Quality First**: Enforce quality gates for critical data
6. **Retention Policy**: Comply with data retention regulations

## Troubleshooting

### PII Not Being Masked
```python
# Check policy exists
policy = governance.get_policy("dataset_123")
assert policy is not None

# Check PII field is configured
assert "email" in policy.pii_masks
```

### Access Denied to Sensitive Data
```python
decision = governance.validate_access("dataset_xyz", user_role)
if not decision.allowed:
    print(decision.reason)  # Check classification and role
    if decision.requires_approval:
        # Initiate approval workflow
        pass
```

## References

- Implementation: `socrata_toolkit/api/governance.py`
- Database: `sql/009_api_governance_tables.sql`
- Tables: `governance_policies`, `governance_pii_mappings`
