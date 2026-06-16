"""Legal Hold & Compliance Classifier — Record retention & sensitivity classification.

This module provides the LegalHoldClassifier that evaluates dataset records for
litigation hold requirements and compliance status across five dimensions:

1. Record Type: INSPECTION, VIOLATION, DISMISSAL, CORRESPONDENCE
2. Sensitivity: PUBLIC, SENSITIVE, PROTECTED
3. Retention Requirement: STANDARD, EXTENDED, INDEFINITE
4. Data Integrity: Audit trail completeness, change tracking, immutability
5. Compliance: COMPLIANT, AT_RISK, NON_COMPLIANT

Retention periods:
- STANDARD: 3 years (routine records)
- EXTENDED: 7 years (violation history, dismissal rationale)
- INDEFINITE: Forever (ongoing disputes, appeals, litigation holds)

Sensitivity classification:
- PUBLIC: Aggregated, no PII, safe for disclosure
- SENSITIVE: Includes location/building identifiers, protected from FOIL
- PROTECTED: Includes inspector names, personal data, requires legal hold
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

class RecordType(Enum):
    """Classification of record type."""
    INSPECTION = "inspection"
    VIOLATION = "violation"
    DISMISSAL = "dismissal"
    CORRESPONDENCE = "correspondence"
    COMPLAINT = "complaint"
    APPEAL = "appeal"
    UNKNOWN = "unknown"

class Sensitivity(Enum):
    """Data sensitivity classification."""
    PUBLIC = "public"              # Aggregated, no PII
    SENSITIVE = "sensitive"        # Location/building identifiers
    PROTECTED = "protected"        # Inspector names, personal data, legal hold

class RetentionRequirement(Enum):
    """Retention period classification."""
    STANDARD = "standard"          # 3 years
    EXTENDED = "extended"          # 7 years
    INDEFINITE = "indefinite"      # Forever (litigation hold)

class ComplianceStatus(Enum):
    """Record compliance status."""
    COMPLIANT = "compliant"
    AT_RISK = "at_risk"
    NON_COMPLIANT = "non_compliant"

@dataclass
class AuditTrailMetrics:
    """Audit trail completeness for a record."""
    total_changes: int
    audit_entries: int
    creation_logged: bool
    last_update_logged: bool
    deletion_logged: bool
    gaps_detected: list[str] = field(default_factory=list)
    chain_of_custody_complete: bool = False

    def is_complete(self) -> bool:
        """Check if audit trail is complete (no gaps)."""
        return (
            self.creation_logged
            and self.last_update_logged
            and not self.gaps_detected
            and self.audit_entries >= self.total_changes
        )

@dataclass
class LegalHoldMetrics:
    """Raw metrics for legal hold classification."""
    record_id: str
    dataset_key: str
    fourfour: str
    created_date: datetime | None
    last_modified: datetime | None
    record_type: RecordType
    has_pii: bool
    has_location_data: bool
    has_sensitive_identifiers: bool
    audit_trail: AuditTrailMetrics
    data_integrity_checks_passed: bool
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class LegalHoldReport:
    """Classified legal hold status and remediation guidance."""
    record_id: str
    dataset_key: str
    fourfour: str
    record_type: RecordType
    sensitivity: Sensitivity
    retention_requirement: RetentionRequirement
    compliance_status: ComplianceStatus
    retention_years: int
    audit_trail_complete: bool
    data_integrity_verified: bool
    alerts: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    litigation_hold_active: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "record_id": self.record_id,
            "dataset_key": self.dataset_key,
            "fourfour": self.fourfour,
            "record_type": self.record_type.value,
            "sensitivity": self.sensitivity.value,
            "retention_requirement": self.retention_requirement.value,
            "compliance_status": self.compliance_status.value,
            "retention_years": self.retention_years,
            "audit_trail_complete": self.audit_trail_complete,
            "data_integrity_verified": self.data_integrity_verified,
            "litigation_hold_active": self.litigation_hold_active,
            "alerts": self.alerts,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
        }

class LegalHoldClassifier:
    """Classify records for litigation hold and legal compliance.

    Usage:
        classifier = LegalHoldClassifier()
        metrics = LegalHoldMetrics(
            record_id="12345",
            dataset_key="violations",
            fourfour="6kbp-uz6m",
            created_date=datetime(2024, 1, 15),
            last_modified=datetime(2024, 1, 20),
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
        print(f"Retention: {report.retention_requirement.value}")
    """

    def __init__(self):
        """Initialize legal hold classifier."""
        self.retention_years_map = {
            RetentionRequirement.STANDARD: 3,
            RetentionRequirement.EXTENDED: 7,
            RetentionRequirement.INDEFINITE: 999,
        }

    def classify(self, metrics: LegalHoldMetrics) -> LegalHoldReport:
        """Classify record for legal hold status.

        Returns a LegalHoldReport with sensitivity, retention requirement,
        and compliance status.
        """
        alerts: list[str] = []
        recommendations: list[str] = []
        compliance_status = ComplianceStatus.COMPLIANT

        # 1. Determine sensitivity classification
        sensitivity = self._classify_sensitivity(metrics, alerts)

        # 2. Determine retention requirement
        retention_requirement = self._classify_retention(metrics, alerts, sensitivity)

        # 3. Verify audit trail completeness
        audit_trail_complete = metrics.audit_trail.is_complete()
        if not audit_trail_complete:
            alerts.append(
                f"Audit trail incomplete: {len(metrics.audit_trail.gaps_detected)} gaps detected"
            )
            recommendations.append("Complete missing audit entries before litigation")
            compliance_status = ComplianceStatus.AT_RISK

        # 4. Verify data integrity
        if not metrics.data_integrity_checks_passed:
            alerts.append("Data integrity verification failed")
            recommendations.append("Run data integrity checks and remediate failures")
            compliance_status = ComplianceStatus.NON_COMPLIANT

        # 5. Determine if litigation hold should be active
        litigation_hold_active = (
            retention_requirement == RetentionRequirement.INDEFINITE
            or (
                sensitivity == Sensitivity.PROTECTED
                and audit_trail_complete
                and metrics.data_integrity_checks_passed
            )
        )

        # 6. Build compliance assessment
        if compliance_status == ComplianceStatus.COMPLIANT:
            if not audit_trail_complete or not metrics.data_integrity_checks_passed:
                compliance_status = ComplianceStatus.AT_RISK
            if metrics.error_message:
                compliance_status = ComplianceStatus.NON_COMPLIANT

        # 7. Add defensibility recommendations
        if litigation_hold_active:
            recommendations.append("Document chain of custody for litigation hold")
            recommendations.append("Enable immutable audit logging for this record")
            if sensitivity == Sensitivity.PROTECTED:
                recommendations.append("Encrypt PII/sensitive identifiers in audit logs")

        return LegalHoldReport(
            record_id=metrics.record_id,
            dataset_key=metrics.dataset_key,
            fourfour=metrics.fourfour,
            record_type=metrics.record_type,
            sensitivity=sensitivity,
            retention_requirement=retention_requirement,
            compliance_status=compliance_status,
            retention_years=self.retention_years_map.get(retention_requirement, 3),
            audit_trail_complete=audit_trail_complete,
            data_integrity_verified=metrics.data_integrity_checks_passed,
            litigation_hold_active=litigation_hold_active,
            alerts=alerts,
            recommendations=recommendations,
            metadata=metrics.metadata,
        )

    def _classify_sensitivity(
        self,
        metrics: LegalHoldMetrics,
        alerts: list[str],
    ) -> Sensitivity:
        """Determine data sensitivity level."""
        # PROTECTED: Has PII or sensitive identifiers
        if metrics.has_pii or metrics.has_sensitive_identifiers:
            return Sensitivity.PROTECTED

        # SENSITIVE: Has location data or building identifiers
        if metrics.has_location_data:
            return Sensitivity.SENSITIVE

        # PUBLIC: No sensitive data
        return Sensitivity.PUBLIC

    def _classify_retention(
        self,
        metrics: LegalHoldMetrics,
        alerts: list[str],
        sensitivity: Sensitivity,
    ) -> RetentionRequirement:
        """Determine retention requirement based on record type and sensitivity."""
        if metrics.record_type == RecordType.INSPECTION:
            return RetentionRequirement.STANDARD

        if metrics.record_type == RecordType.VIOLATION:
            # Violations require extended retention (appeal period + statute)
            return RetentionRequirement.EXTENDED

        if metrics.record_type == RecordType.DISMISSAL:
            # Dismissals require extended retention (appeal period)
            return RetentionRequirement.EXTENDED

        if metrics.record_type == RecordType.APPEAL:
            # Appeals require indefinite retention (ongoing disputes)
            return RetentionRequirement.INDEFINITE

        if metrics.record_type == RecordType.CORRESPONDENCE:
            # Correspondence in litigation context requires indefinite retention
            return RetentionRequirement.INDEFINITE

        if metrics.record_type == RecordType.COMPLAINT:
            # Complaints may trigger litigation hold
            return RetentionRequirement.EXTENDED

        # Default: STANDARD retention
        return RetentionRequirement.STANDARD
