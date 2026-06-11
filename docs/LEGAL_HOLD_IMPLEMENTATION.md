# Legal Hold & Compliance Verification Workflow

## Overview

The Legal Hold & Compliance Verification workflow is a production-ready LangGraph-based orchestration system for classifying NYC DOT inspection records for litigation hold, verifying audit trail completeness, checking data integrity, and generating legal defensibility certificates.

**Location:** `src/socrata_toolkit/analysis/`

**Key Files:**
- `legal_hold_classifier.py` (140 lines) — Record classification engine
- `legal_hold_workflow.py` (210 lines) — LangGraph workflow orchestration
- `legal_hold_example.py` (250 lines) — Usage examples

## Architecture

### 1. Legal Hold Classifier (`legal_hold_classifier.py`)

Evaluates records across **5 dimensions:**

#### 1.1 Record Type Classification
```python
RecordType = {
    INSPECTION,      # Routine inspection records
    VIOLATION,       # Violation findings
    DISMISSAL,       # Dismissal decisions
    CORRESPONDENCE,  # Legal/administrative correspondence
    COMPLAINT,       # Complaint filings
    APPEAL,          # Appeal challenges
    UNKNOWN
}
```

#### 1.2 Sensitivity Classification
```python
Sensitivity = {
    PUBLIC,          # Aggregated, no PII, safe for disclosure
    SENSITIVE,       # Location/building identifiers, protected from FOIL
    PROTECTED        # Inspector names, personal data, requires legal hold
}
```

#### 1.3 Retention Requirement
```python
RetentionRequirement = {
    STANDARD,        # 3 years (routine records)
    EXTENDED,        # 7 years (violation history, dismissals)
    INDEFINITE       # Forever (appeals, disputes, litigation holds)
}
```

#### 1.4 Compliance Status
```python
ComplianceStatus = {
    COMPLIANT,       # All checks passed, defensible for litigation
    AT_RISK,         # Audit trail gaps or integrity issues detected
    NON_COMPLIANT    # Data integrity verification failed
}
```

#### 1.5 Data Structures

**AuditTrailMetrics:** Audit completeness for a record
```python
@dataclass
class AuditTrailMetrics:
    total_changes: int              # Expected changes
    audit_entries: int              # Logged entries
    creation_logged: bool           # Creation event logged
    last_update_logged: bool        # Most recent update logged
    deletion_logged: bool           # Deletion (if applicable) logged
    gaps_detected: list[str]        # Missing audit entries
    chain_of_custody_complete: bool # Unbroken change history
```

**LegalHoldMetrics:** Input metrics for classification
```python
@dataclass
class LegalHoldMetrics:
    record_id: str
    dataset_key: str
    fourfour: str
    created_date: datetime | None
    last_modified: datetime | None
    record_type: RecordType
    has_pii: bool                          # Has personally identifiable info
    has_location_data: bool                # Has geographic data
    has_sensitive_identifiers: bool        # Has inspector/sensitive IDs
    audit_trail: AuditTrailMetrics
    data_integrity_checks_passed: bool
    error_message: str | None
    metadata: dict[str, Any]
```

**LegalHoldReport:** Output classification result
```python
@dataclass
class LegalHoldReport:
    record_id: str
    dataset_key: str
    fourfour: str
    record_type: RecordType
    sensitivity: Sensitivity
    retention_requirement: RetentionRequirement
    compliance_status: ComplianceStatus
    retention_years: int                           # 3, 7, or 999
    audit_trail_complete: bool
    data_integrity_verified: bool
    alerts: list[str]                             # Issues found
    recommendations: list[str]                    # Remediation steps
    litigation_hold_active: bool
    metadata: dict[str, Any]
```

### 2. Classification Logic

The classifier determines retention requirements based on **record type and sensitivity:**

| Record Type | Base Retention | Notes |
|---|---|---|
| INSPECTION | STANDARD (3y) | Routine records |
| VIOLATION | EXTENDED (7y) | Appeal period + statute |
| DISMISSAL | EXTENDED (7y) | Appeal period |
| APPEAL | INDEFINITE | Ongoing disputes |
| CORRESPONDENCE | INDEFINITE | Legal/administrative hold |
| COMPLAINT | EXTENDED (7y) | Potential litigation |

**Sensitivity Logic:**
- PROTECTED: Has PII or sensitive identifiers → litigation hold recommended
- SENSITIVE: Has location data or building identifiers → FOIL-protected
- PUBLIC: Aggregated, no PII → standard disclosure

**Compliance Status Logic:**
```
IF audit_trail_incomplete → AT_RISK
IF data_integrity_failed → NON_COMPLIANT
IF error_detected → NON_COMPLIANT
ELSE → COMPLIANT
```

### 3. Legal Hold Workflow (`legal_hold_workflow.py`)

Multi-step LangGraph orchestration:

```
START
  ↓
[fetch_records] — Query Socrata for records (site/inspector/date range)
  ↓
[classify_records] — Apply LegalHoldClassifier to each record
  ↓
[verify_audit_trails] — Check audit completeness
  ↓
[check_integrity] — Verify data integrity checks passed
  ↓
[route_to_claude] — ← Conditional routing based on compliance
  ├→ [compliance = COMPLIANT] → [generate_certificate]
  └→ [compliance = AT_RISK|NON_COMPLIANT] → [claude_analysis]
  ↓
[generate_certificate] — Create legal hold compliance certificate
  ↓
[aggregate] — Build final report
  ↓
END
```

#### 3.1 Workflow Nodes

**fetch_records:** Fetch records from Socrata
- Applies WHERE filters: site_id, inspector_id, date range
- Logs via AuditLogger
- Returns: dict of records

**classify_records:** Classify each record
- Applies LegalHoldClassifier.classify()
- Infers record type from field values
- Returns: dict[record_id → LegalHoldReport]

**verify_audit_trails:** Verify audit completeness
- Checks AuditTrailMetrics.is_complete()
- Flags gaps and missing entries
- Returns: dict[record_id → bool]

**check_integrity:** Check data integrity
- Verifies data_integrity_checks_passed
- Builds high_risk_records list
- Returns: dict[record_id → bool]

**route_to_claude:** Send high-risk records to Claude
- Uses claude-haiku-4-5 (~300 tokens)
- Prompt: "Is this dataset legally defensible? Gaps to fix?"
- Returns: dict with analysis text

**generate_certificate:** Generate compliance certificate
```json
{
  "certificate_id": "uuid",
  "timestamp": "2026-06-10T...",
  "domain": "data.cityofnewyork.us",
  "fourfour": "6kbp-uz6m",
  "total_records": 100,
  "compliant": 92,
  "at_risk": 7,
  "non_compliant": 1,
  "litigation_hold_active": 5,
  "compliance_percentage": 92.0,
  "defensible_for_litigation": true,
  "audit_trail_reference": "run_id",
  "recommendations": ["Complete missing audit entries...", ...]
}
```

**aggregate:** Build final report
- Combines all workflow outputs
- Returns final state

#### 3.2 Conditional Routing

```python
def _decide_claude_routing(state: LegalHoldState) -> str:
    if not state["high_risk_records"]:
        return "compliant"      # Skip Claude, generate cert immediately
    return "at_risk"             # Send to Claude for analysis
```

### 4. Usage Examples

#### 4.1 Basic Record Classification
```python
from socrata_toolkit.analysis import (
    LegalHoldClassifier,
    LegalHoldMetrics,
    AuditTrailMetrics,
    RecordType,
)
from datetime import datetime, timezone

classifier = LegalHoldClassifier()

metrics = LegalHoldMetrics(
    record_id="v-12345",
    dataset_key="violations",
    fourfour="6kbp-uz6m",
    created_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
    last_modified=datetime(2024, 1, 20, tzinfo=timezone.utc),
    record_type=RecordType.VIOLATION,
    has_pii=False,
    has_location_data=True,
    has_sensitive_identifiers=False,
    audit_trail=AuditTrailMetrics(
        total_changes=3,
        audit_entries=3,
        creation_logged=True,
        last_update_logged=True,
        deletion_logged=False,
        chain_of_custody_complete=True,
    ),
    data_integrity_checks_passed=True,
)

report = classifier.classify(metrics)
print(f"Compliance: {report.compliance_status.value}")
print(f"Retention: {report.retention_requirement.value} ({report.retention_years}y)")
print(f"Litigation Hold: {report.litigation_hold_active}")
```

#### 4.2 Full Workflow Execution
```python
from socrata_toolkit.analysis import run_legal_hold_workflow
from datetime import datetime, timedelta, timezone
import json

report = run_legal_hold_workflow(
    domain="data.cityofnewyork.us",
    fourfour="6kbp-uz6m",
    site_id=None,
    inspector_id=None,
    start_date=datetime.now(timezone.utc) - timedelta(days=30),
    end_date=datetime.now(timezone.utc),
)

print(json.dumps(report, indent=2))
```

#### 4.3 Export to JSON
```python
certificate_dict = report.to_dict()
with open("compliance_certificate.json", "w") as f:
    json.dump(certificate_dict, f, indent=2)
```

## Features

### Audit Trail Integration
- **AuditLogger:** All classification decisions logged with `run_id`
- **Immutable tracking:** Change sequence preserved
- **Gap detection:** Missing audit entries flagged
- **Chain of custody:** Unbroken change history verified

### Data Integrity Checks
- Hash verification for audit entries
- Missing change detection
- Timestamp consistency checks
- Completeness validation

### Claude Integration
- **Model:** claude-haiku-4-5-20251001
- **Token budget:** ~300 tokens per analysis
- **Prompt:** Asks about legal defensibility and remediation
- **Fallback:** Graceful degradation if Claude unavailable

### Compliance Certificate
- Unique certificate ID (UUID)
- Timestamp of issuance
- Record counts by compliance status
- Litigation hold summary
- Actionable recommendations
- Audit trail reference for traceability

## Retention Requirements

| Category | Duration | Use Case |
|---|---|---|
| STANDARD | 3 years | Routine inspections, approved |
| EXTENDED | 7 years | Violations, dismissals, appeals |
| INDEFINITE | Forever | Ongoing litigation, appeals, disputes |

## Sensitivity Classifications

| Level | Definition | Protection |
|---|---|---|
| PUBLIC | Aggregated, no PII | Standard FOIL disclosure |
| SENSITIVE | Location/building identifiers | FOIL-protected |
| PROTECTED | Inspector/personal data | Legal hold, encryption |

## Compliance Statuses

| Status | Meaning | Action |
|---|---|---|
| COMPLIANT | All checks passed | Ready for litigation |
| AT_RISK | Audit gaps detected | Requires remediation |
| NON_COMPLIANT | Integrity failed | Escalate to legal |

## Error Handling

**Fallback Mode:** If LangGraph is unavailable:
```python
{
    "timestamp": "...",
    "error": "LangGraph not installed",
    "fallback_mode": True
}
```

**Graceful Degradation:**
- Missing Claude API key → Workflow continues, skips analysis
- Network timeout → Logged, continues to next record
- Invalid record format → Logged with error message

## File Structure

```
src/socrata_toolkit/analysis/
├── legal_hold_classifier.py      (140 lines)
│   ├── RecordType enum
│   ├── Sensitivity enum
│   ├── RetentionRequirement enum
│   ├── ComplianceStatus enum
│   ├── AuditTrailMetrics dataclass
│   ├── LegalHoldMetrics dataclass
│   ├── LegalHoldReport dataclass
│   └── LegalHoldClassifier class
│
├── legal_hold_workflow.py         (210 lines)
│   ├── LegalHoldState TypedDict
│   ├── LegalHoldWorkflow class
│   │   ├── _build_graph()
│   │   ├── run()
│   │   ├── _node_fetch_records()
│   │   ├── _node_classify_records()
│   │   ├── _node_verify_audit_trails()
│   │   ├── _node_check_integrity()
│   │   ├── _node_route_to_claude()
│   │   ├── _node_generate_certificate()
│   │   ├── _node_aggregate()
│   │   └── [helper methods]
│   ├── build_legal_hold_graph()
│   └── run_legal_hold_workflow()
│
└── legal_hold_example.py          (250 lines)
    ├── example_basic_classification()
    ├── example_protected_record()
    ├── example_non_compliant_record()
    ├── example_retention_periods()
    ├── example_compliance_certificate()
    └── example_workflow_integration()
```

## Integration Points

### With Socrata API
- `SocrataClient.fetch_dataframe()` — Fetch records
- `SocrataConfig` — Authentication/domain config

### With Governance Module
- `AuditLogger` — Log all classification decisions
- `audit_logger.py` — Audit trail storage

### With Claude API
- `anthropic.Anthropic` — Legal defensibility analysis
- Model: `claude-haiku-4-5-20251001`

### With LangGraph
- `StateGraph` — Workflow orchestration
- Optional dependency (graceful fallback if missing)

## Testing

Run examples:
```bash
python -c "import sys; sys.path.insert(0, 'src'); from socrata_toolkit.analysis.legal_hold_example import example_basic_classification, example_retention_periods; example_basic_classification(); example_retention_periods()"
```

Run full workflow (requires SOCRATA_APP_TOKEN):
```bash
python -c "import sys; sys.path.insert(0, 'src'); from socrata_toolkit.analysis.legal_hold_example import example_workflow_integration; example_workflow_integration()"
```

## Performance

- **Classification:** O(1) per record (single-pass analysis)
- **Workflow:** O(n) records (batch processing via Socrata)
- **Memory:** Minimal (streaming-friendly architecture)
- **Timeout:** 30 second API calls, configurable

## Security Considerations

1. **PII Handling:** Flagged for encryption in audit logs
2. **Sensitive Data:** FOIL-protected classification
3. **Credential Masking:** API tokens never logged
4. **Immutable Audit Trail:** Hash verification of changes
5. **Legal Hold Marking:** Explicit litigation hold flag

## Future Enhancements

1. **DuckDB Cache:** Store classifications locally for trend analysis
2. **Audit Trail Snapshot:** Periodic immutable snapshots
3. **Multi-User Holds:** Track hold requestor and reason
4. **Retention Calendar:** Automatic deletion after period expires
5. **Compliance Reporting:** Monthly/quarterly compliance dashboards
6. **Integration Tests:** Mock Socrata/Claude for CI/CD
7. **Batch Scheduling:** APScheduler for periodic compliance scans

## References

- **NYC FOIL Law:** Freedom of Information Law (Public Officers Law Article 6)
- **Litigation Hold:** Legal hold requirements per civil procedure rules
- **Retention Schedules:** Records management per municipal code
- **Data Integrity:** ISO 8601 timestamps, hash verification
- **Audit Standards:** NIST guidelines for audit logging

## Examples Location

Complete runnable examples in `legal_hold_example.py`:
- Basic classification
- Protected records with PII
- Non-compliant records
- Retention period comparison
- Compliance certificate export
- Full workflow integration

## Environment Variables

```bash
SOCRATA_APP_TOKEN=***set***         # For full-corpus Socrata fetches
ANTHROPIC_API_KEY=***set***         # For Claude legal analysis
SOCRATA_DOMAIN=data.cityofnewyork.us
```

## Author Notes

- Implements 5-dimension classification (type, sensitivity, retention, integrity, compliance)
- LangGraph workflow with conditional routing to Claude
- AuditLogger integration for governance compliance
- Graceful fallback if dependencies unavailable
- Production-ready error handling and logging
