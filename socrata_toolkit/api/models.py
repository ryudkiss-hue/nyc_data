"""SQLAlchemy ORM models for Phase 3 materialized views and audit tables.

Maps domain entities (sidewalk segments, incidents, repairs, KPIs) to
database tables. All models read from Phase 3 materialized views.

Models:
    - SidewalkSegment: dim_street_segments
    - IncidentReport: fact_incidents
    - RepairSchedule: fact_repair_schedule
    - MaterialMetrics: materialized_view_material_metrics
    - ADAMetrics: materialized_view_ada_metrics
    - HazardMetrics: materialized_view_hazard_coverage
    - ContractorMetrics: materialized_view_contractor_performance
    - CostMetrics: materialized_view_cost_analytics
    - AuditLog: audit_log (read-only, Phase 2)

Standards:
    - Use lazy loading for relationships
    - Include created_at/updated_at timestamps
    - Use SQL-safe column names
    - Include type hints
    - Document all relationships

Example:
    from socrata_toolkit.api.models import SidewalkSegment
    session.query(SidewalkSegment).filter_by(material_type='asphalt').all()
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    Boolean,
    ForeignKey,
    Index,
    Numeric,
    Date,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class SidewalkSegment(Base):
    """Sidewalk segment dimension (Phase 1 domain model).

    Represents a distinct sidewalk segment identified by segment_id.
    Segments have material type, length, location, and operational status.

    Attributes:
        segment_id: Unique segment identifier
        geometry: WKT geometry string
        material_type: Material type (asphalt, concrete, other)
        length_feet: Segment length in linear feet
        created_at: Timestamp when segment was created
        updated_at: Timestamp when segment was last updated
    """

    __tablename__ = "dim_street_segments"

    segment_id = Column(String(50), primary_key=True, doc="Unique segment ID (seg_123)")
    geometry = Column(Text, nullable=False, doc="WKT geometry")
    material_type = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Material type: asphalt, concrete, other",
    )
    length_feet = Column(Float, nullable=False, doc="Segment length in linear feet")
    created_at = Column(DateTime, default=datetime.utcnow, doc="Creation timestamp")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, doc="Last update timestamp")

    # Relationships (lazy loading)
    incidents: List[IncidentReport] = relationship("IncidentReport", back_populates="segment", lazy="select")
    repairs: List[RepairSchedule] = relationship("RepairSchedule", back_populates="segment", lazy="select")

    def __repr__(self) -> str:
        return f"<SidewalkSegment {self.segment_id} ({self.material_type})>"


class IncidentReport(Base):
    """Incident fact table (Phase 3 materialized view).

    Tracks complaints and reports filed for sidewalk defects.
    Incidents are linked to specific segments.

    Attributes:
        incident_id: Unique incident identifier
        segment_id: Foreign key to SidewalkSegment
        complaint_type: Type of complaint (pothole, crack, etc.)
        severity: Severity level (low, medium, high)
        created_at: When incident was reported
        updated_at: When incident was last updated
        description: Detailed description of issue
        status: Current status (open, assigned, resolved)
    """

    __tablename__ = "fact_incidents"

    incident_id = Column(String(50), primary_key=True, doc="Unique incident ID")
    segment_id = Column(String(50), ForeignKey("dim_street_segments.segment_id"), nullable=False, index=True)
    complaint_type = Column(String(100), nullable=False, index=True, doc="Type of complaint")
    severity = Column(String(20), nullable=False, index=True, doc="Severity: low, medium, high")
    created_at = Column(DateTime, default=datetime.utcnow, doc="Report timestamp")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    description = Column(Text, nullable=True, doc="Detailed description")
    status = Column(String(20), nullable=False, default="open", doc="Status: open, assigned, resolved")

    # Relationships
    segment = relationship("SidewalkSegment", back_populates="incidents", lazy="select")
    repairs = relationship("RepairSchedule", back_populates="incident", lazy="select")

    __table_args__ = (
        Index("idx_incidents_segment_severity", "segment_id", "severity"),
        Index("idx_incidents_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<IncidentReport {self.incident_id} ({self.severity})>"


class RepairSchedule(Base):
    """Repair scheduling fact table (Phase 3 materialized view).

    Tracks repair work orders and schedules. Links incidents to
    contractors and tracks costs and completion status.

    Attributes:
        repair_id: Unique repair identifier
        incident_id: Foreign key to IncidentReport
        segment_id: Foreign key to SidewalkSegment
        contractor_id: Contractor performing repair
        status: Current status (scheduled, in_progress, completed)
        estimated_cost: Estimated repair cost
        actual_cost: Actual repair cost (null until completed)
        scheduled_date: Scheduled repair date
        completion_date: Actual completion date
    """

    __tablename__ = "fact_repair_schedule"

    repair_id = Column(String(50), primary_key=True, doc="Unique repair ID")
    incident_id = Column(String(50), ForeignKey("fact_incidents.incident_id"), nullable=False, index=True)
    segment_id = Column(String(50), ForeignKey("dim_street_segments.segment_id"), nullable=False, index=True)
    contractor_id = Column(String(50), nullable=False, index=True, doc="Contractor ID")
    status = Column(
        String(20),
        nullable=False,
        default="scheduled",
        index=True,
        doc="Status: scheduled, in_progress, completed",
    )
    estimated_cost = Column(Numeric(10, 2), nullable=False, doc="Estimated cost in USD")
    actual_cost = Column(Numeric(10, 2), nullable=True, doc="Actual cost (null until completed)")
    scheduled_date = Column(Date, nullable=False, doc="Scheduled repair date")
    completion_date = Column(Date, nullable=True, doc="Actual completion date")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    segment = relationship("SidewalkSegment", back_populates="repairs", lazy="select")
    incident = relationship("IncidentReport", back_populates="repairs", lazy="select")

    __table_args__ = (Index("idx_repairs_contractor_status", "contractor_id", "status"),)

    def __repr__(self) -> str:
        return f"<RepairSchedule {self.repair_id} ({self.status})>"


class MaterialMetrics(Base):
    """Material-type KPI metrics (Phase 3 materialized view).

    Aggregated metrics by material type: defect rates, age distribution,
    hazard counts. Updated daily by kpi_materialization DAG.

    Attributes:
        material_type: Material type (asphalt, concrete, other)
        defect_rate_pct: Percentage of segments with defects
        avg_age_years: Average age of segments
        hazard_count: Number of hazardous defects
        total_linear_feet: Total linear feet of this material
        updated_at: Last refresh timestamp
    """

    __tablename__ = "materialized_view_material_metrics"

    material_type = Column(String(50), primary_key=True, doc="Material type")
    defect_rate_pct = Column(Float, nullable=False, doc="Defect rate percentage")
    avg_age_years = Column(Float, nullable=False, doc="Average age in years")
    hazard_count = Column(Integer, nullable=False, doc="Number of hazards")
    total_linear_feet = Column(Float, nullable=False, doc="Total linear feet")
    updated_at = Column(DateTime, default=datetime.utcnow, doc="Last refresh timestamp")

    def __repr__(self) -> str:
        return f"<MaterialMetrics {self.material_type} ({self.defect_rate_pct:.1f}%)>"


class ADAMetrics(Base):
    """ADA compliance metrics by segment (Phase 3 materialized view).

    Tracks ADA compliance score for segments and specific failures.

    Attributes:
        segment_id: Segment identifier
        compliance_score: ADA compliance score (0-100)
        failures: JSON array of ADA failures
        recommended_repairs: Recommended repairs for compliance
        updated_at: Last refresh timestamp
    """

    __tablename__ = "materialized_view_ada_metrics"

    segment_id = Column(String(50), primary_key=True, doc="Segment ID")
    compliance_score = Column(Integer, nullable=False, doc="Compliance score 0-100")
    failures = Column(Text, nullable=True, doc="JSON array of failures")
    recommended_repairs = Column(Text, nullable=True, doc="JSON array of recommended repairs")
    updated_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ADAMetrics {self.segment_id} (score: {self.compliance_score})>"


class HazardMetrics(Base):
    """Hazardous defect coverage metrics (Phase 3 materialized view).

    Aggregated metrics on hazardous defects: total count, linear feet,
    days to SLA violation, clearance rate.

    Attributes:
        metric_date: Date of metric snapshot
        hazard_count: Total number of hazardous defects
        linear_feet: Total linear feet with hazards
        clearance_rate_pct: Percentage cleared within SLA
        days_to_sla_violation: Days until SLA violation
        updated_at: Last refresh timestamp
    """

    __tablename__ = "materialized_view_hazard_coverage"

    metric_date = Column(Date, primary_key=True, doc="Metric date")
    hazard_count = Column(Integer, nullable=False, doc="Count of hazards")
    linear_feet = Column(Float, nullable=False, doc="Linear feet with hazards")
    clearance_rate_pct = Column(Float, nullable=False, doc="Clearance rate percentage")
    days_to_sla_violation = Column(Integer, nullable=False, doc="Days until SLA violation")
    updated_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<HazardMetrics {self.metric_date} ({self.hazard_count} hazards)>"


class ContractorMetrics(Base):
    """Contractor performance KPI metrics (Phase 3 materialized view).

    Quality scores, cost analysis, and material certifications by contractor.

    Attributes:
        contractor_id: Contractor identifier
        name: Contractor name
        quality_score: Quality score (0-100)
        avg_cost_sqft: Average cost per square foot
        completion_rate_pct: Percentage of jobs completed on time
        defect_rate_pct: Percentage of repairs with defects
        material_expertise: JSON array of certified materials
        updated_at: Last refresh timestamp
    """

    __tablename__ = "materialized_view_contractor_performance"

    contractor_id = Column(String(50), primary_key=True, doc="Contractor ID")
    name = Column(String(200), nullable=False, doc="Contractor name")
    quality_score = Column(Integer, nullable=False, doc="Quality score 0-100")
    avg_cost_sqft = Column(Float, nullable=False, doc="Average cost per square foot")
    completion_rate_pct = Column(Float, nullable=False, doc="On-time completion rate")
    defect_rate_pct = Column(Float, nullable=False, doc="Defect rate percentage")
    material_expertise = Column(Text, nullable=True, doc="JSON array of materials")
    updated_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ContractorMetrics {self.name} (score: {self.quality_score})>"


class CostMetrics(Base):
    """Cost analytics by material type (Phase 3 materialized view).

    Cost per linear foot, ROI, and cost trends by material.

    Attributes:
        material_type: Material type
        cost_per_linear_foot: Cost in USD per linear foot
        total_cost: Total cost for all segments of this material
        roi_estimate: Estimated ROI percentage
        trend_yoy_pct: Year-over-year cost trend percentage
        updated_at: Last refresh timestamp
    """

    __tablename__ = "materialized_view_cost_analytics"

    material_type = Column(String(50), primary_key=True, doc="Material type")
    cost_per_linear_foot = Column(Float, nullable=False, doc="Cost per linear foot")
    total_cost = Column(Numeric(15, 2), nullable=False, doc="Total cost")
    roi_estimate = Column(Float, nullable=False, doc="ROI estimate percentage")
    trend_yoy_pct = Column(Float, nullable=False, doc="YoY trend percentage")
    updated_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<CostMetrics {self.material_type} (${self.cost_per_linear_foot:.2f}/ft)>"


class AuditLog(Base):
    """Audit trail for compliance and observability (Phase 2).

    Read-only table tracking all data modifications and access.
    Immutable records for regulatory compliance.

    Attributes:
        operation_id: Unique operation identifier
        actor: User ID or system account performing action
        action: Action type (create, read, update, delete)
        dataset_id: Dataset affected
        resource_id: Specific resource identifier
        details: JSON details of change
        created_at: When action occurred
    """

    __tablename__ = "audit_log"

    operation_id = Column(String(50), primary_key=True, doc="Unique operation ID")
    actor = Column(String(100), nullable=False, index=True, doc="User or system account")
    action = Column(String(50), nullable=False, index=True, doc="Action type")
    dataset_id = Column(String(100), nullable=True, index=True, doc="Dataset ID")
    resource_id = Column(String(100), nullable=True, doc="Specific resource ID")
    details = Column(Text, nullable=True, doc="JSON details")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (Index("idx_audit_actor_date", "actor", "created_at"),)

    def __repr__(self) -> str:
        return f"<AuditLog {self.operation_id} ({self.action})>"
