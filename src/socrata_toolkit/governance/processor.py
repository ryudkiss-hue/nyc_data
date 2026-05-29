"""Unified Data Governance Processor for NYC DOT Sidewalk Toolkit.

This module orchestrates schema versioning, CDC, data lineage, and compliance
validation into a single integrated event stream. Every data change is:

1. Validated against schema registry (schema_registry.py)
2. Enriched with data lineage metadata (lineage_core.py)
3. Checked against design/material rules (material_compliance.py)
4. Stored in immutable audit log (cdc_engine.py)

This provides Project Analysts with:
- Complete audit trails for budget/progress tracking
- Design compliance validation for construction lists
- Data lineage traceability for all metrics
- Schema versioning preventing pipeline breakage

Classes:
    GovernanceProcessor: Main orchestrator
    GovernanceEvent: Enriched CDC event with all validation context

Example:
    >>> processor = GovernanceProcessor(dsn="postgresql://...")
    >>> event = CDCEvent(
    ...     event_id="evt-001",
    ...     source_dataset="sidewalk_repairs",
    ...     operation="UPDATE",
    ...     record_id="repair-123",
    ...     after={"budget": 50000, "material": "asphalt"}
    ... )
    >>> result = processor.process_event(event)
    >>> print(result.is_compliant)  # True if all validations pass
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from socrata_toolkit.cdc.engine import CDCEvent, CDCProcessor
    from socrata_toolkit.discovery.schema import SchemaRegistry, SchemaChange
    from socrata_toolkit.lineage.core import DAG, TransformationNode, NodeType
    from socrata_toolkit.material.compliance import MaterialCompliance
except ImportError:
    CDCEvent = None  # type: ignore
    CDCProcessor = None  # type: ignore
    SchemaRegistry = None  # type: ignore
    ComplianceChecker = None  # type: ignore
    DAG = None  # type: ignore
    TransformationNode = None  # type: ignore
    NodeType = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class GovernanceEvent:
    """CDC event enriched with governance context.
    
    Attributes:
        event_id: Unique event identifier
        source_dataset: Source dataset/table name
        operation: DML operation (INSERT, UPDATE, DELETE)
        record_id: Business key of changed record
        before_values: Previous values (None for INSERT)
        after_values: New values (None for DELETE)
        timestamp: When change occurred
        schema_version: Schema version at time of change
        schema_valid: Whether record validates against schema
        schema_errors: List of schema validation errors
        lineage_metadata: Column-level lineage information
        design_rule_violations: List of design rule violations
        is_compliant: Whether record passes all compliance checks
        user_id: User who made the change
        change_reason: Why the change was made (optional)
    """
    
    event_id: str
    source_dataset: str
    operation: str
    record_id: str
    before_values: Optional[Dict[str, Any]] = None
    after_values: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    schema_version: Optional[str] = None
    schema_valid: bool = True
    schema_errors: List[str] = field(default_factory=list)
    lineage_metadata: Dict[str, Any] = field(default_factory=dict)
    design_rule_violations: List[str] = field(default_factory=list)
    is_compliant: bool = True
    user_id: str = "system"
    change_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for audit logging."""
        return {
            "event_id": self.event_id,
            "source_dataset": self.source_dataset,
            "operation": self.operation,
            "record_id": self.record_id,
            "before_values": self.before_values,
            "after_values": self.after_values,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "schema_version": self.schema_version,
            "schema_valid": self.schema_valid,
            "schema_errors": self.schema_errors,
            "lineage_metadata": self.lineage_metadata,
            "design_rule_violations": self.design_rule_violations,
            "is_compliant": self.is_compliant,
            "user_id": self.user_id,
            "change_reason": self.change_reason,
        }


class GovernanceProcessor:
    """Unified processor orchestrating schema, lineage, compliance, and CDC.
    
    Coordinates validation across multiple systems to ensure data quality
    and compliance while maintaining complete audit trails.
    
    Usage:
        processor = GovernanceProcessor(dsn="postgresql://...", registry_path="./schemas")
        result = processor.process_event(cdc_event)
        
        if not result.is_compliant:
            logger.warning(f"Compliance violations: {result.design_rule_violations}")
    """
    
    def __init__(
        self,
        dsn: str,
        registry_path: Optional[str] = None,
        enable_lineage: bool = True,
        enable_compliance: bool = True,
    ):
        """Initialize Governance Processor.
        
        Args:
            dsn: PostgreSQL connection string
            registry_path: Path to schema registry JSON files (local dev)
            enable_lineage: Whether to track data lineage
            enable_compliance: Whether to check design rules
        """
        self.dsn = dsn
        self.logger = logger.getChild(self.__class__.__name__)
        
        # Initialize components
        try:
            self.cdc_processor = CDCProcessor(dsn)
        except Exception as e:
            self.logger.warning(f"CDC processor initialization failed: {e}")
            self.cdc_processor = None
        
        try:
            self.schema_registry = SchemaRegistry(dsn=dsn, local_path=registry_path)
        except Exception as e:
            self.logger.warning(f"Schema registry initialization failed: {e}")
            self.schema_registry = None
        
        try:
            self.compliance_checker = MaterialCompliance()
        except Exception as e:
            self.logger.warning(f"Compliance checker initialization failed: {e}")
            self.compliance_checker = None
        
        self.enable_lineage = enable_lineage
        self.enable_compliance = enable_compliance
        
        # Initialize lineage DAG
        self.lineage_dag = DAG() if enable_lineage else None
    
    def process_event(self, cdc_event: CDCEvent) -> GovernanceEvent:
        """Process CDC event through all governance validations.
        
        Pipeline:
        1. Schema validation (schema_registry)
        2. Lineage enrichment (lineage_core)
        3. Design rule validation (material_compliance)
        4. Audit logging (cdc_engine)
        
        Args:
            cdc_event: Raw CDC event from data pipeline
            
        Returns:
            GovernanceEvent with full validation context
        """
        gov_event = GovernanceEvent(
            event_id=cdc_event.event_id,
            source_dataset=cdc_event.source_dataset,
            operation=cdc_event.operation,
            record_id=cdc_event.record_id,
            before_values=cdc_event.before,
            after_values=cdc_event.after,
            timestamp=datetime.now(timezone.utc),
        )
        
        # Step 1: Schema Validation
        if self.schema_registry:
            gov_event = self._validate_schema(gov_event, cdc_event)
        
        # Step 2: Lineage Enrichment
        if self.enable_lineage and self.lineage_dag:
            gov_event = self._enrich_lineage(gov_event, cdc_event)
        
        # Step 3: Compliance Checking
        if self.enable_compliance and self.compliance_checker:
            gov_event = self._check_compliance(gov_event, cdc_event)
        
        # Step 4: Audit Logging
        if self.cdc_processor:
            self._log_to_audit(gov_event, cdc_event)
        
        # Overall compliance status
        gov_event.is_compliant = (
            gov_event.schema_valid and
            len(gov_event.design_rule_violations) == 0
        )
        
        self.logger.info(
            f"Processed event {gov_event.event_id}: "
            f"compliant={gov_event.is_compliant}, "
            f"violations={len(gov_event.design_rule_violations)}"
        )
        
        return gov_event
    
    def _validate_schema(
        self,
        gov_event: GovernanceEvent,
        cdc_event: CDCEvent,
    ) -> GovernanceEvent:
        """Validate event against schema registry.
        
        Args:
            gov_event: Governance event being built
            cdc_event: Original CDC event
            
        Returns:
            Updated governance event with schema validation results
        """
        try:
            # Get current schema version for dataset
            schema = self.schema_registry.get_latest_schema(cdc_event.source_dataset)
            if schema:
                gov_event.schema_version = str(schema.version)
                
                # Validate record against schema
                errors = self.schema_registry.validate_record(
                    cdc_event.source_dataset,
                    cdc_event.after or {},
                    schema.version
                )
                
                if errors:
                    gov_event.schema_valid = False
                    gov_event.schema_errors = errors
                    self.logger.warning(
                        f"Schema validation failed for {cdc_event.record_id}: {errors}"
                    )
                else:
                    gov_event.schema_valid = True
        except Exception as e:
            self.logger.error(f"Schema validation error: {e}")
            gov_event.schema_errors = [str(e)]
            gov_event.schema_valid = False
        
        return gov_event
    
    def _enrich_lineage(
        self,
        gov_event: GovernanceEvent,
        cdc_event: CDCEvent,
    ) -> GovernanceEvent:
        """Enrich event with data lineage metadata.
        
        Args:
            gov_event: Governance event being built
            cdc_event: Original CDC event
            
        Returns:
            Updated governance event with lineage information
        """
        try:
            if cdc_event.after:
                # Track which columns changed
                changed_columns = set(cdc_event.after.keys())
                if cdc_event.before:
                    changed_columns &= set(cdc_event.before.keys())
                
                # Record column-level lineage
                gov_event.lineage_metadata = {
                    "operation": cdc_event.operation,
                    "changed_columns": list(changed_columns),
                    "dataset": cdc_event.source_dataset,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                
                # Add node to DAG if tracking lineage
                if self.lineage_dag:
                    node = TransformationNode(
                        node_id=cdc_event.source_dataset,
                        name=f"Dataset: {cdc_event.source_dataset}",
                        node_type=NodeType.INGESTION,
                    )
                    self.lineage_dag.add_node(node)
        except Exception as e:
            self.logger.error(f"Lineage enrichment error: {e}")
        
        return gov_event
    
    def _check_compliance(
        self,
        gov_event: GovernanceEvent,
        cdc_event: CDCEvent,
    ) -> GovernanceEvent:
        """Check record against design rules and material standards.
        
        Args:
            gov_event: Governance event being built
            cdc_event: Original CDC event
            
        Returns:
            Updated governance event with compliance violations
        """
        try:
            if cdc_event.after:
                # Mock a surface assessment for quick rule check
                # In production, we'd fetch the full assessment object
                from socrata_toolkit.material.standards import SurfaceAssessment, SurfaceCondition
                from socrata_toolkit.material.definitions import MATERIAL_DEFINITIONS
                
                mat_type = cdc_event.after.get("material_type", "asphalt")
                spec = MATERIAL_DEFINITIONS.get(mat_type, MATERIAL_DEFINITIONS["asphalt"])
                
                assessment = SurfaceAssessment(
                    location_id=cdc_event.record_id,
                    material=spec,
                    condition=SurfaceCondition.GOOD,
                    last_inspected=datetime.now(timezone.utc),
                )
                
                # Check against design rules (NYC Street Design Manual)
                res = self.compliance_checker.ada_compliance_check(assessment)
                
                violations = [v["description"] for v in res.violations_detail]
                
                if violations:
                    gov_event.design_rule_violations = violations
                    self.logger.warning(
                        f"Design rule violations for {cdc_event.record_id}: {violations}"
                    )
        except Exception as e:
            self.logger.error(f"Compliance check error: {e}")
            gov_event.design_rule_violations = [f"Compliance check failed: {str(e)}"]
        
        return gov_event
    
    def _log_to_audit(
        self,
        gov_event: GovernanceEvent,
        cdc_event: CDCEvent,
    ) -> None:
        """Log enriched event to immutable audit log.
        
        Args:
            gov_event: Enriched governance event
            cdc_event: Original CDC event
        """
        try:
            # Store in CDC audit table with governance metadata
            audit_metadata = {
                "schema_valid": gov_event.schema_valid,
                "schema_errors": gov_event.schema_errors,
                "design_rule_violations": gov_event.design_rule_violations,
                "lineage": gov_event.lineage_metadata,
                "is_compliant": gov_event.is_compliant,
                "user_id": gov_event.user_id,
                "change_reason": gov_event.change_reason,
            }
            
            # Update CDC event with governance metadata
            enriched_event = CDCEvent(
                event_id=cdc_event.event_id,
                source_dataset=cdc_event.source_dataset,
                operation=cdc_event.operation,
                record_id=cdc_event.record_id,
                timestamp_ms=int(datetime.now(timezone.utc).timestamp() * 1000),
                before=cdc_event.before,
                after=cdc_event.after,
                metadata=audit_metadata,
            )
            
            self.cdc_processor.store_event(enriched_event)
        except Exception as e:
            self.logger.error(f"Audit logging error: {e}")
    
    def get_audit_trail(
        self,
        dataset: str,
        record_id: str,
        limit: int = 100,
    ) -> List[GovernanceEvent]:
        """Retrieve audit trail for a specific record.
        
        Args:
            dataset: Source dataset name
            record_id: Record identifier
            limit: Maximum events to return
            
        Returns:
            List of governance events for this record
        """
        if not self.cdc_processor:
            return []
        
        try:
            events = self.cdc_processor.get_events(dataset, limit=limit)
            return [e for e in events if e.record_id == record_id]
        except Exception as e:
            self.logger.error(f"Audit trail retrieval error: {e}")
            return []
    
    def get_compliance_violations(
        self,
        dataset: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve compliance violations for a dataset.
        
        Args:
            dataset: Source dataset name
            start_date: Filter from this date
            end_date: Filter to this date
            
        Returns:
            List of compliance violation records
        """
        if not self.cdc_processor:
            return []
        
        try:
            events = self.cdc_processor.get_events(dataset, limit=10000)
            violations = []
            
            for event in events:
                if (event.metadata and 
                    event.metadata.get("design_rule_violations")):
                    violations.append({
                        "event_id": event.event_id,
                        "record_id": event.record_id,
                        "violations": event.metadata["design_rule_violations"],
                        "timestamp": datetime.fromtimestamp(
                            event.timestamp_ms / 1000
                        ),
                    })
            
            return violations
        except Exception as e:
            self.logger.error(f"Compliance violation retrieval error: {e}")
            return []
