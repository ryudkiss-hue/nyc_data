"""Example usage of Legal Hold & Compliance Verification workflow.

This script demonstrates:
1. Creating a legal hold workflow
2. Classifying records for litigation hold
3. Verifying audit trail completeness
4. Checking data integrity
5. Generating compliance certificate

Usage:
    python -m socrata_toolkit.analysis.legal_hold_example
    # Or in code:
    from socrata_toolkit.analysis import run_legal_hold_workflow
    report = run_legal_hold_workflow(fourfour="6kbp-uz6m")
    print(json.dumps(report, indent=2))
"""

import json
from datetime import datetime, timedelta, timezone

from .legal_hold_classifier import (
    AuditTrailMetrics,
    LegalHoldClassifier,
    LegalHoldMetrics,
    RecordType,
)
from .legal_hold_workflow import run_legal_hold_workflow


def example_basic_classification():
    """Example 1: Basic record classification."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Record Classification")
    print("="*60)

    classifier = LegalHoldClassifier()

    # Example: Violation record with location data
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
    print(f"\nRecord Type: {report.record_type.value}")
    print(f"Sensitivity: {report.sensitivity.value}")
    print(f"Retention Requirement: {report.retention_requirement.value}")
    print(f"Retention Years: {report.retention_years}")
    print(f"Compliance Status: {report.compliance_status.value}")
    print(f"Litigation Hold Active: {report.litigation_hold_active}")
    print("\nAlerts:")
    for alert in report.alerts:
        print(f"  - {alert}")
    print("\nRecommendations:")
    for rec in report.recommendations:
        print(f"  - {rec}")

    return report


def example_protected_record():
    """Example 2: Protected record with PII."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Protected Record with PII")
    print("="*60)

    classifier = LegalHoldClassifier()

    # Example: Appeal record with inspector identifier
    metrics = LegalHoldMetrics(
        record_id="a-67890",
        dataset_key="violations",
        fourfour="6kbp-uz6m",
        created_date=datetime(2023, 6, 1, tzinfo=timezone.utc),
        last_modified=datetime(2023, 12, 15, tzinfo=timezone.utc),
        record_type=RecordType.APPEAL,
        has_pii=True,
        has_location_data=True,
        has_sensitive_identifiers=True,
        audit_trail=AuditTrailMetrics(
            total_changes=5,
            audit_entries=5,
            creation_logged=True,
            last_update_logged=True,
            deletion_logged=False,
            gaps_detected=["audit_entry_3"],
            chain_of_custody_complete=False,
        ),
        data_integrity_checks_passed=True,
    )

    report = classifier.classify(metrics)
    print(f"\nRecord Type: {report.record_type.value}")
    print(f"Sensitivity: {report.sensitivity.value}")
    print(f"Retention Requirement: {report.retention_requirement.value}")
    print(f"Compliance Status: {report.compliance_status.value}")
    print(f"Audit Trail Complete: {report.audit_trail_complete}")
    print(f"Data Integrity Verified: {report.data_integrity_verified}")
    print(f"\nAlerts ({len(report.alerts)}):")
    for alert in report.alerts:
        print(f"  - {alert}")
    print(f"\nRecommendations ({len(report.recommendations)}):")
    for rec in report.recommendations:
        print(f"  - {rec}")

    return report


def example_non_compliant_record():
    """Example 3: Non-compliant record with integrity failures."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Non-Compliant Record with Integrity Failures")
    print("="*60)

    classifier = LegalHoldClassifier()

    # Example: Dismissal record with integrity issues
    metrics = LegalHoldMetrics(
        record_id="d-54321",
        dataset_key="violations",
        fourfour="6kbp-uz6m",
        created_date=datetime(2024, 3, 10, tzinfo=timezone.utc),
        last_modified=datetime(2024, 3, 15, tzinfo=timezone.utc),
        record_type=RecordType.DISMISSAL,
        has_pii=False,
        has_location_data=True,
        has_sensitive_identifiers=False,
        audit_trail=AuditTrailMetrics(
            total_changes=2,
            audit_entries=1,
            creation_logged=True,
            last_update_logged=False,
            deletion_logged=False,
            gaps_detected=["update_entry_2"],
            chain_of_custody_complete=False,
        ),
        data_integrity_checks_passed=False,
        error_message="Hash verification failed for audit entry 2",
    )

    report = classifier.classify(metrics)
    print(f"\nRecord Type: {report.record_type.value}")
    print(f"Sensitivity: {report.sensitivity.value}")
    print(f"Retention Requirement: {report.retention_requirement.value}")
    print(f"Compliance Status: {report.compliance_status.value}")
    print(f"Audit Trail Complete: {report.audit_trail_complete}")
    print(f"Data Integrity Verified: {report.data_integrity_verified}")
    print(f"\nAlerts ({len(report.alerts)}):")
    for alert in report.alerts:
        print(f"  - {alert}")
    print(f"\nRecommendations ({len(report.recommendations)}):")
    for rec in report.recommendations:
        print(f"  - {rec}")

    return report


def example_retention_periods():
    """Example 4: Comparison of retention periods by record type."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Retention Periods by Record Type")
    print("="*60)

    classifier = LegalHoldClassifier()
    record_types = [
        RecordType.INSPECTION,
        RecordType.VIOLATION,
        RecordType.DISMISSAL,
        RecordType.APPEAL,
        RecordType.CORRESPONDENCE,
    ]

    print("\n{:<20} {:<15} {:<10}".format("Record Type", "Retention Req", "Years"))
    print("-" * 45)

    for record_type in record_types:
        metrics = LegalHoldMetrics(
            record_id=f"test-{record_type.value}",
            dataset_key="violations",
            fourfour="6kbp-uz6m",
            created_date=datetime.now(timezone.utc),
            last_modified=datetime.now(timezone.utc),
            record_type=record_type,
            has_pii=False,
            has_location_data=False,
            has_sensitive_identifiers=False,
            audit_trail=AuditTrailMetrics(
                total_changes=1,
                audit_entries=1,
                creation_logged=True,
                last_update_logged=True,
                deletion_logged=False,
            ),
            data_integrity_checks_passed=True,
        )
        report = classifier.classify(metrics)
        print(
            f"{record_type.value.capitalize():<20} {report.retention_requirement.value:<15} {str(report.retention_years):<10}"
        )


def example_compliance_certificate():
    """Example 5: Generate compliance certificate JSON."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Compliance Certificate JSON Export")
    print("="*60)

    classifier = LegalHoldClassifier()

    # Create multiple records with different compliance statuses
    records = [
        LegalHoldMetrics(
            record_id=f"r-{i:05d}",
            dataset_key="violations",
            fourfour="6kbp-uz6m",
            created_date=datetime.now(timezone.utc) - timedelta(days=i*10),
            last_modified=datetime.now(timezone.utc) - timedelta(days=i*5),
            record_type=RecordType.VIOLATION,
            has_pii=i % 3 == 0,
            has_location_data=True,
            has_sensitive_identifiers=i % 5 == 0,
            audit_trail=AuditTrailMetrics(
                total_changes=i + 1,
                audit_entries=i + 1,
                creation_logged=True,
                last_update_logged=True,
                deletion_logged=False,
                chain_of_custody_complete=(i % 2 == 0),
            ),
            data_integrity_checks_passed=(i % 3 != 0),
        )
        for i in range(5)
    ]

    classifications = [classifier.classify(m) for m in records]

    # Export as JSON
    certificate = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "domain": "data.cityofnewyork.us",
        "fourfour": "6kbp-uz6m",
        "total_records": len(classifications),
        "records": [c.to_dict() for c in classifications],
        "summary": {
            "compliant": sum(
                1 for c in classifications
                if c.compliance_status.value == "compliant"
            ),
            "at_risk": sum(
                1 for c in classifications
                if c.compliance_status.value == "at_risk"
            ),
            "non_compliant": sum(
                1 for c in classifications
                if c.compliance_status.value == "non_compliant"
            ),
            "litigation_hold_active": sum(
                1 for c in classifications if c.litigation_hold_active
            ),
        },
    }

    print("\nCertificate Summary:")
    print(json.dumps(certificate["summary"], indent=2))
    print("\nFull Certificate (first 2 records):")
    print(json.dumps(
        {
            "timestamp": certificate["timestamp"],
            "domain": certificate["domain"],
            "fourfour": certificate["fourfour"],
            "total_records": certificate["total_records"],
            "records": certificate["records"][:2],
            "summary": certificate["summary"],
        },
        indent=2,
    ))


def example_workflow_integration():
    """Example 6: Full workflow integration (requires live Socrata connection)."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Full Workflow Integration")
    print("="*60)
    print("\nNote: Requires SOCRATA_APP_TOKEN environment variable")
    print("This example shows how to run the complete workflow.\n")

    try:
        report = run_legal_hold_workflow(
            domain="data.cityofnewyork.us",
            fourfour="6kbp-uz6m",
            site_id=None,  # Can filter by site_id if needed
            inspector_id=None,  # Can filter by inspector_id if needed
            start_date=datetime.now(timezone.utc) - timedelta(days=30),
            end_date=datetime.now(timezone.utc),
        )
        print("Workflow completed successfully!")
        print(json.dumps(report, indent=2, default=str))
    except Exception as e:
        print(f"Workflow execution failed (expected in demo): {e}")
        print("\nTo run the workflow:")
        print("  1. Set SOCRATA_APP_TOKEN environment variable")
        print("  2. Ensure anthropic package is installed for Claude analysis")
        print("  3. Set ANTHROPIC_API_KEY for legal defensibility guidance")


if __name__ == "__main__":
    print("\nLegal Hold & Compliance Verification - Examples")
    print("=" * 60)

    example_basic_classification()
    example_protected_record()
    example_non_compliant_record()
    example_retention_periods()
    example_compliance_certificate()
    example_workflow_integration()

    print("\n" + "=" * 60)
    print("Examples completed!")
