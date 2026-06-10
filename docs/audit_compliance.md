# Audit Trail and Compliance Reporting

## Overview

The audit trail system provides comprehensive compliance reporting for regulatory requirements including:

- **GDPR**: Data access, modification, and deletion tracking
- **HIPAA**: Healthcare data change tracking
- **SOC 2**: Data integrity and immutability verification
- **Internal Compliance**: Change control and approval tracking
- **Regulatory Reporting**: Audit trail exports and reports

## Audit Trail Structure

### Core Audit Data

Every audit event captures:

```python
{
    "audit_id": "550e8400-e29b-41d4-a716-446655440000",  # Unique identifier
    "timestamp": "2026-03-15T10:30:00Z",                 # When it happened
    "user_name": "inspector@nyc.gov",                    # Who did it
    "action": "UPDATE",                                   # What action (INSERT/UPDATE/DELETE)
    "entity_type": "sidewalk_conditions",                # What table
    "entity_id": "sidewalk_123",                         # Which record
    "change_type": "DATA_CHANGE",                        # Type of change
    "old_values": {...},                                 # Before state
    "new_values": {...},                                 # After state
    "diff": {"condition": ["fair", "excellent"]},       # What changed
    "reason": "Monthly inspection completed",            # Why changed
    "lineage_node_id": "...",                           # Link to W3 lineage
    "correlation_id": "...",                            # Link to W4 logs
    "ip_address": "203.0.113.42",                       # Source IP
    "user_agent": "sidewalk-inspector-mobile-v2.1",    # Client info
}
```

### Immutability Guarantee

The audit trail is immutable via PostgreSQL rules:

```sql
-- No updates to audit trail
CREATE OR REPLACE RULE audit_trail_no_update AS ON UPDATE TO audit_trail
    DO INSTEAD NOTHING;

-- No deletes from audit trail  
CREATE OR REPLACE RULE audit_trail_no_delete AS ON DELETE TO audit_trail
    DO INSTEAD NOTHING;
```

This means:
- ✓ Records can only be inserted (appended)
- ✗ Existing records cannot be modified
- ✗ Existing records cannot be deleted
- ✓ Can query any point in time with confidence

## Compliance Use Cases

### 1. Data Subject Access Requests (GDPR)

```python
from socrata_toolkit.audit_trail import AuditTrail
from datetime import date

audit = AuditTrail(dsn="...")

# Find all operations for a specific person/entity
person_id = "person_12345"
events = audit.get_events(
    entity_type="citizen_records",
    entity_id=person_id
)

# Export for data subject
report = {
    "data_subject": person_id,
    "export_date": date.today().isoformat(),
    "operations": []
}

for event in events:
    report["operations"].append({
        "date": event.timestamp.isoformat(),
        "action": event.action,
        "fields_accessed": list(event.new_values.keys()) if event.new_values else [],
        "changed_by": event.user_name,
        "reason": event.reason,
    })

# Export as JSON for data subject
import json
with open(f"dsar_{person_id}.json", "w") as f:
    json.dump(report, f, indent=2)
```

### 2. Change Control Auditing

```python
# Find all changes in production in last 30 days
from datetime import date, timedelta

changes = audit.search_events({
    "change_type": "DATA_CHANGE",
    "start_date": date.today() - timedelta(days=30),
    "end_date": date.today(),
})

# Group by user
from collections import defaultdict
by_user = defaultdict(list)
for event in changes:
    by_user[event.user_name].append(event)

# Generate change summary
print("Production Changes - Last 30 Days")
print("=" * 60)
for user, events in sorted(by_user.items()):
    print(f"\n{user}: {len(events)} changes")
    for event in events:
        print(f"  {event.timestamp.date()} - {event.action} on {event.entity_type}/{event.entity_id}")
        if event.reason:
            print(f"    Reason: {event.reason}")
```

### 3. Deletion Justification

Track and verify all deletions are justified:

```python
# Find all deletions
deletions = audit.get_events_by_action("DELETE")

# Verify each has a reason
missing_reason = [e for e in deletions if not e.reason]
if missing_reason:
    print(f"WARNING: {len(missing_reason)} deletions without reason!")

# Export deletion log
with open("deletion_log.csv", "w") as f:
    import csv
    writer = csv.DictWriter(f, fieldnames=[
        "timestamp", "deleted_by", "entity_type", "entity_id", "reason"
    ])
    writer.writeheader()
    for event in deletions:
        writer.writerow({
            "timestamp": event.timestamp.isoformat(),
            "deleted_by": event.user_name,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "reason": event.reason or "NOT PROVIDED",
        })
```

### 4. Unauthorized Access Detection

```python
# Find unusual access patterns
from datetime import datetime, timedelta, timezone

suspicious = audit.search_events({
    "change_type": "DATA_CHANGE",
})

# Analyze patterns
off_hours = []
for event in suspicious:
    hour = event.timestamp.hour
    if hour < 6 or hour > 22:  # Off-hours access
        off_hours.append(event)

weekend = []
for event in suspicious:
    if event.timestamp.weekday() >= 5:  # Saturday/Sunday
        weekend.append(event)

print(f"Off-hours changes: {len(off_hours)}")
print(f"Weekend changes: {len(weekend)}")

# Alert on unusual patterns
if len(off_hours) > 100:
    print("ALERT: Unusual amount of off-hours activity!")
    # Could trigger incident response
```

### 5. Audit Trail Completeness Verification

```python
from socrata_toolkit.cdc_compliance import CDCReconciler

reconciler = CDCReconciler(dsn="...")

# Verify audit trail is complete
result = reconciler.verify_audit_trail_completeness()

if result.passed:
    print("✓ Audit trail is complete and immutable")
else:
    print("✗ AUDIT TRAIL ISSUES DETECTED:")
    for issue in result.issues:
        print(f"  - {issue}")
    # Escalate to compliance team

# Check coverage
coverage = reconciler.check_audit_trail_coverage()
if coverage.passed:
    print("✓ 100% time period coverage verified")
```

## Compliance Reports

### Generate Monthly Compliance Report

```python
def generate_monthly_compliance_report(audit, month_date):
    """Generate compliance report for a month."""
    from datetime import date
    from dateutil.relativedelta import relativedelta
    
    month_start = date(month_date.year, month_date.month, 1)
    month_end = month_start + relativedelta(months=1) - relativedelta(days=1)
    
    # Get all events in month
    events = audit.search_events({
        "start_date": month_start,
        "end_date": month_end,
    }, limit=999999)
    
    # Analyze
    stats = {
        "period": f"{month_start} to {month_end}",
        "total_events": len(events),
        "by_action": {},
        "by_user": {},
        "by_table": {},
        "changes_with_reason": 0,
        "changes_without_reason": 0,
    }
    
    for event in events:
        # Count by action
        stats["by_action"][event.action] = stats["by_action"].get(event.action, 0) + 1
        
        # Count by user
        stats["by_user"][event.user_name] = stats["by_user"].get(event.user_name, 0) + 1
        
        # Count by table
        stats["by_table"][event.entity_type] = stats["by_table"].get(event.entity_type, 0) + 1
        
        # Reason coverage
        if event.reason:
            stats["changes_with_reason"] += 1
        else:
            stats["changes_without_reason"] += 1
    
    # Generate report
    report = f"""
    COMPLIANCE REPORT - {month_start.strftime('%B %Y')}
    {'=' * 60}
    
    SUMMARY
    Total audit events: {stats['total_events']}
    Changes with reason: {stats['changes_with_reason']}
    Changes without reason: {stats['changes_without_reason']}
    
    BREAKDOWN BY ACTION
    """
    
    for action, count in sorted(stats['by_action'].items()):
        report += f"\n    {action}: {count}"
    
    report += "\n\n    BREAKDOWN BY USER\n"
    for user, count in sorted(stats['by_user'].items(), key=lambda x: x[1], reverse=True):
        report += f"\n    {user}: {count}"
    
    report += "\n\n    BREAKDOWN BY TABLE\n"
    for table, count in sorted(stats['by_table'].items(), key=lambda x: x[1], reverse=True):
        report += f"\n    {table}: {count}"
    
    return report, stats

# Generate for March 2026
from datetime import date
report, stats = generate_monthly_compliance_report(audit, date(2026, 3, 1))
print(report)

# Save report
with open("compliance_report_202603.txt", "w") as f:
    f.write(report)
```

### Audit Trail Export for Compliance

```python
import csv
from datetime import date

# Export full audit trail for given period
export_criteria = {
    "start_date": date(2026, 3, 1),
    "end_date": date(2026, 3, 31),
}

# Export to CSV for Excel/analytics
with open("audit_export_202603.csv", "w") as f:
    count = audit.export_csv(f, criteria=export_criteria)
    print(f"Exported {count} audit entries to CSV")

# Export to JSON for system import
events_json = audit.export_json(criteria=export_criteria)
with open("audit_export_202603.json", "w") as f:
    import json
    json.dump(events_json, f, indent=2, default=str)
    print(f"Exported {len(events_json)} audit entries to JSON")
```

## Regulatory Compliance Checklist

### GDPR Requirements

```python
class GDPRCompliance:
    """Verify GDPR compliance requirements."""
    
    @staticmethod
    def verify_right_to_access(audit, person_id):
        """Verify data subject access rights."""
        events = audit.get_events("citizen_records", person_id)
        return {
            "person_id": person_id,
            "data_access_events": len(events),
            "can_export": len(events) > 0,
            "data_available": True,
        }
    
    @staticmethod
    def verify_right_to_erasure(audit, person_id):
        """Verify right to be forgotten can be documented."""
        # Check if person has been deleted
        deletions = audit.search_events({
            "entity_id": person_id,
            "action": "DELETE",
        })
        
        return {
            "person_id": person_id,
            "deletion_events": len(deletions),
            "deleted_on": [e.timestamp.isoformat() for e in deletions],
            "can_prove_deletion": len(deletions) > 0,
        }
    
    @staticmethod
    def verify_audit_trail_integrity(reconciler):
        """Verify audit trail meets GDPR requirements."""
        result = reconciler.verify_audit_trail_completeness()
        return {
            "immutable": result.passed,
            "complete": result.passed,
            "issues": result.issues,
            "gdpr_compliant": result.passed and len(result.issues) == 0,
        }

# Run GDPR checks
gdpr = GDPRCompliance()

# Check person
person_check = gdpr.verify_right_to_access(audit, "person_12345")
print(f"GDPR Access Check: {'PASS' if person_check['can_export'] else 'FAIL'}")

# Check deletion
deletion_check = gdpr.verify_right_to_erasure(audit, "person_12345")
print(f"GDPR Erasure Check: {'PASS' if deletion_check['can_prove_deletion'] else 'FAIL'}")

# Check infrastructure
infra_check = gdpr.verify_audit_trail_integrity(reconciler)
print(f"GDPR Audit Compliance: {'PASS' if infra_check['gdpr_compliant'] else 'FAIL'}")
```

## Incident Response

### Security Incident Logging

```python
# Log security incident with full context
import json

def log_security_incident(audit, incident_type, description, affected_ids):
    """Log a security incident for audit trail."""
    
    # Create audit events for investigation
    for entity_id in affected_ids:
        audit.log_update(
            table="security_incidents",
            entity_id=incident_type,
            old={},
            new={
                "incident_type": incident_type,
                "description": description,
                "affected_entity": entity_id,
                "investigation_required": True,
            },
            user="SECURITY_SYSTEM",
            reason=f"Security incident: {incident_type}",
        )

# Log breach example
log_security_incident(
    audit,
    incident_type="unauthorized_access",
    description="Multiple failed login attempts from IP 203.0.113.99",
    affected_ids=["citizen_12345", "citizen_12346", "citizen_12347"],
)

# Query for security events
security_events = audit.search_events({
    "reason_contains": "security",
})

print(f"Security events: {len(security_events)}")
for event in security_events:
    print(f"  {event.timestamp}: {event.reason}")
```

### Breach Notification

```python
def generate_breach_notification(audit, breach_date):
    """Generate notification of data breach."""
    
    # Find all accesses around breach date
    from datetime import datetime, timedelta
    
    suspicious_window_start = breach_date - timedelta(days=1)
    suspicious_window_end = breach_date + timedelta(days=1)
    
    events = audit.search_events({
        "start_date": suspicious_window_start,
        "end_date": suspicious_window_end,
    }, limit=999999)
    
    # Analyze
    affected_tables = set(e.entity_type for e in events)
    affected_records = set(e.entity_id for e in events)
    accessing_users = set(e.user_name for e in events)
    
    notification = f"""
    DATA BREACH NOTIFICATION
    
    Breach Date: {breach_date.isoformat()}
    Discovery Date: {datetime.now().date().isoformat()}
    
    AFFECTED DATA
    Tables: {', '.join(affected_tables)}
    Approx Records: {len(affected_records)}
    Users with Access: {len(accessing_users)}
    
    AUDIT TRAIL ANALYSIS
    Events in window: {len(events)}
    Date range: {suspicious_window_start} to {suspicious_window_end}
    
    ACTIONS TAKEN
    1. Audit trail reviewed for unauthorized access
    2. Access logs exported for forensic analysis
    3. All accesses logged for investigation
    
    INVESTIGATION DETAILS
    {json.dumps([e.to_dict() for e in events[:5]], indent=2, default=str)}
    ... ({len(events) - 5} more events, see full export)
    """
    
    return notification

# Generate breach notification
notification = generate_breach_notification(audit, date(2026, 3, 15))
print(notification)

# Save for official records
with open("breach_notification_202603.txt", "w") as f:
    f.write(notification)
```

## Key Compliance Metrics

```python
def compliance_scorecard(audit, reconciler):
    """Generate compliance scorecard."""
    
    # Audit trail completeness
    completeness = reconciler.check_audit_trail_coverage()
    completeness_score = 100 if completeness.passed else 70
    
    # Event ordering
    ordering = reconciler.verify_cdc_event_ordering()
    ordering_score = 100 if ordering.passed else 0
    
    # Overall audit trail
    overall = reconciler.verify_audit_trail_completeness()
    overall_score = 100 if overall.passed else 0
    
    # Reason coverage
    all_events = audit.search_events({}, limit=999999)
    with_reason = sum(1 for e in all_events if e.reason)
    reason_coverage = (with_reason / len(all_events) * 100) if all_events else 0
    
    scorecard = {
        "audit_trail_completeness": completeness_score,
        "event_ordering": ordering_score,
        "immutability": overall_score,
        "reason_coverage": reason_coverage,
        "overall_compliance": (
            (completeness_score + ordering_score + overall_score + reason_coverage) / 4
        ),
    }
    
    print("COMPLIANCE SCORECARD")
    print("=" * 40)
    print(f"Audit Completeness: {scorecard['audit_trail_completeness']:.0f}%")
    print(f"Event Ordering:     {scorecard['event_ordering']:.0f}%")
    print(f"Immutability:       {scorecard['immutability']:.0f}%")
    print(f"Reason Coverage:    {scorecard['reason_coverage']:.0f}%")
    print("=" * 40)
    print(f"OVERALL COMPLIANCE: {scorecard['overall_compliance']:.0f}%")
    
    return scorecard
```

## Best Practices

1. **Always include reason**: Every change should have a documented reason
2. **Verify immutability regularly**: Run compliance checks monthly
3. **Export regularly**: Keep backup exports for forensics
4. **Monitor off-hours access**: Alert on unusual patterns
5. **Test deletion workflows**: Verify soft/hard delete works correctly
6. **Audit the auditors**: Monitor who accesses audit trail
7. **Use correlation IDs**: Link to observability logs (W4)
8. **Document exceptions**: If reason is missing, investigate
9. **Retention compliance**: Ensure deletions follow policy
10. **Annual compliance audit**: Full end-to-end verification

## See Also

- `docs/cdc_guide.md` - CDC fundamentals
- `docs/temporal_analytics.md` - Time-series analysis
- `socrata_toolkit/audit_trail.py` - API reference
- `socrata_toolkit/cdc_compliance.py` - Compliance checks
