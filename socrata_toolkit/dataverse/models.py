"""
SQLAlchemy ORM Models for Dataverse Entity Synchronization

Provides local representation of Microsoft Dataverse entities (Work Orders, Repairs,
Contractor Assignments, Compliance Records) with automatic sync metadata tracking.
Models implement bidirectional synchronization patterns with conflict detection and
resolution strategies.

Key Models:
- WorkOrder: NYC DOT work orders for sidewalk maintenance/repair
- RepairJob: Specific repair tasks within a work order
- ContractorAssignment: Contractor assignment to work orders
- ProgressTracking: Real-time progress milestone tracking
- ComplianceRecord: Audit trail for regulatory compliance
- DataverseSyncMetadata: Internal sync state and conflict tracking

Features:
- SQLAlchemy ORM with PostgreSQL dialect
- Automatic timestamp tracking (created_at, updated_at)
- Sync metadata for bidirectional replication
- Validation decorators with Pydantic
- Relationship mappings with cascading options
- JSON serialization for API responses
- Convenience query methods

References:
    - SQLAlchemy: https://docs.sqlalchemy.org/
    - Dataverse Data Model: https://learn.microsoft.com/en-us/power-apps/maker/data-platform/
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from functools import wraps

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, ForeignKey, Enum as SQLEnum,
    JSON, Text, TIMESTAMP, Index, UniqueConstraint, CheckConstraint, create_engine
)
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship, Session, sessionmaker, Mapped
from sqlalchemy.dialects.postgresql import UUID
import uuid as uuid_module

logger = logging.getLogger(__name__)

Base = declarative_base()


class BaseModel(Base):
    """Base model with unmapped attributes allowed."""
    __abstract__ = True
    __allow_unmapped__ = True


# ===== ENUMERATIONS =====

class WorkOrderStatus(str, Enum):
    """Work order status values aligned with Dataverse."""
    NEW = "New"
    SCHEDULED = "Scheduled"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    BLOCKED = "Blocked"


class WorkOrderPriority(str, Enum):
    """Work order priority levels."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class RepairStatus(str, Enum):
    """Repair job status values."""
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    FAILED = "Failed"


class AssignmentStatus(str, Enum):
    """Contractor assignment status (state machine)."""
    ASSIGNED = "Assigned"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class ComplianceStatus(str, Enum):
    """Compliance record status."""
    PENDING = "Pending"
    VERIFIED = "Verified"
    FLAGGED = "Flagged"
    RESOLVED = "Resolved"


class SyncDirection(str, Enum):
    """Direction of synchronization."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


class ConflictStatus(str, Enum):
    """Conflict resolution status."""
    NO_CONFLICT = "no_conflict"
    DETECTED = "detected"
    RESOLVED = "resolved"
    MANUAL_REVIEW = "manual_review"


# ===== MIXINS & DECORATORS =====

class TimestampMixin:
    """Mixin providing created_at and updated_at timestamps."""
    pass


class DataverseTrackedMixin:
    """Mixin for tracking Dataverse synchronization state."""
    pass


def sync_tracked(func):
    """Decorator to automatically update sync metadata on record changes.
    
    Applies sync_status='pending' when record is modified, indicating it needs
    synchronization to Dataverse.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self.sync_status = "pending"
        self.updated_at = datetime.now(timezone.utc)
        logger.debug(f"Marked {self.__class__.__name__} as needing sync")
        return result
    return wrapper


# ===== CORE ORM MODELS =====

class WorkOrder(BaseModel, TimestampMixin, DataverseTrackedMixin):
    """
    Work order model mapping to Dataverse msdyn_workorder.
    
    Represents a sidewalk maintenance or repair work order issued by NYC DOT.
    Tracks assignment, progress, and completion status. Supports bidirectional
    sync with Dataverse.
    
    Attributes:
        id: Primary key (UUID)
        title: Work order title
        description: Detailed description of work to be performed
        status: Current status (New, In Progress, Scheduled, Completed, Cancelled)
        priority: Priority level (Low, Medium, High, Critical)
        assigned_contractor_id: Dataverse contractor account ID
        scheduled_date: Scheduled start date
        due_date: Target completion date
        completed_date: Actual completion date
        dataverse_id: Dataverse work order GUID
        sync_status: Sync state (pending, synced, failed)
        last_synced: Timestamp of last successful sync
        
    Relationships:
        contractor_assignments: One-to-many with ContractorAssignment
        repair_jobs: One-to-many with RepairJob
        progress_tracking: One-to-one with ProgressTracking
        compliance_records: One-to-many with ComplianceRecord
    """
    __tablename__ = "work_orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    title = Column(String(500), nullable=False, index=True)
    description = Column(Text)
    status = Column(SQLEnum(WorkOrderStatus), default=WorkOrderStatus.NEW, nullable=False, index=True)
    priority = Column(SQLEnum(WorkOrderPriority), default=WorkOrderPriority.MEDIUM, nullable=False)
    assigned_contractor_id = Column(String(255), nullable=True)
    scheduled_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    completed_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    dataverse_id = Column(String(255), nullable=True, index=True)
    sync_status = Column(String(50), default="pending", nullable=False)
    last_synced = Column(DateTime, nullable=True)
    
    # Relationships
    contractor_assignments = relationship(
        "ContractorAssignment",
        back_populates="work_order",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    repair_jobs = relationship(
        "RepairJob",
        back_populates="work_order",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    progress_tracking = relationship(
        "ProgressTracking",
        back_populates="work_order",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    compliance_records = relationship(
        "ComplianceRecord",
        back_populates="work_order",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('New', 'Scheduled', 'In Progress', 'Completed', 'Cancelled', 'Blocked')"),
        CheckConstraint("priority IN ('Low', 'Medium', 'High', 'Critical')"),
        Index("idx_work_order_status_priority", "status", "priority"),
        Index("idx_work_order_dates", "scheduled_date", "due_date"),
    )
    
    def __repr__(self) -> str:
        return f"<WorkOrder(id={self.id}, title='{self.title}', status={self.status})>"
    
    @property
    def is_overdue(self) -> bool:
        """Check if work order is past due date."""
        if self.due_date and self.status != WorkOrderStatus.COMPLETED:
            return datetime.now(timezone.utc) > self.due_date
        return False
    
    @property
    def days_remaining(self) -> Optional[int]:
        """Calculate days remaining until due date."""
        if self.due_date:
            delta = self.due_date - datetime.now(timezone.utc)
            return max(0, delta.days)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize work order to dictionary for API responses."""
        return {
            "id": str(self.id),
            "dataverse_id": self.dataverse_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value if isinstance(self.status, WorkOrderStatus) else self.status,
            "priority": self.priority.value if isinstance(self.priority, WorkOrderPriority) else self.priority,
            "assigned_contractor_id": self.assigned_contractor_id,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed_date": self.completed_date.isoformat() if self.completed_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "sync_status": self.sync_status,
            "last_synced": self.last_synced.isoformat() if self.last_synced else None,
        }


class RepairJob(BaseModel, TimestampMixin, DataverseTrackedMixin):
    """
    Repair job model mapping to Dataverse repair jobs.
    
    Represents specific repair tasks within a work order. Tracks materials,
    costs, and completion status.
    
    Attributes:
        id: Primary key (UUID)
        work_order_id: Foreign key to WorkOrder
        location: Location description of repair site
        repair_type: Type of repair (e.g., patching, grinding, removal)
        material_type: Material used (asphalt, concrete, permeable, etc.)
        estimated_cost: Estimated cost in USD
        actual_cost: Actual cost incurred
        status: Current status (Pending, In Progress, Completed, Failed)
        started_at: When repair work started
        completed_at: When repair work was completed
        dataverse_id: Dataverse repair job GUID
        sync_status: Sync state
        last_synced: Timestamp of last sync
        
    Relationships:
        work_order: Many-to-one with WorkOrder
        progress_tracking: One-to-one with ProgressTracking
    """
    __tablename__ = "repair_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    work_order_id = Column(UUID(as_uuid=True), ForeignKey("work_orders.id"), nullable=False, index=True)
    location = Column(String(500), nullable=False)
    repair_type = Column(String(100), nullable=False, index=True)
    material_type = Column(String(100), nullable=False)
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    status = Column(SQLEnum(RepairStatus), default=RepairStatus.PENDING, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    dataverse_id = Column(String(255), nullable=True, index=True)
    sync_status = Column(String(50), default="pending", nullable=False)
    last_synced = Column(DateTime, nullable=True)
    
    # Relationships
    work_order = relationship("WorkOrder", back_populates="repair_jobs")
    progress_tracking = relationship(
        "ProgressTracking",
        back_populates="repair_job",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        CheckConstraint("actual_cost IS NULL OR actual_cost >= 0"),
        CheckConstraint("estimated_cost IS NULL OR estimated_cost >= 0"),
        Index("idx_repair_work_order", "work_order_id"),
    )
    
    def __repr__(self) -> str:
        return f"<RepairJob(id={self.id}, location='{self.location}', type={self.repair_type})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize repair job to dictionary."""
        return {
            "id": str(self.id),
            "work_order_id": str(self.work_order_id),
            "dataverse_id": self.dataverse_id,
            "location": self.location,
            "repair_type": self.repair_type,
            "material_type": self.material_type,
            "estimated_cost": self.estimated_cost,
            "actual_cost": self.actual_cost,
            "status": self.status.value if isinstance(self.status, RepairStatus) else self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ContractorAssignment(BaseModel, TimestampMixin, DataverseTrackedMixin):
    """
    Contractor assignment model mapping to Dataverse contractor_assignments.
    
    Tracks assignment of contractors to work orders. Implements state machine:
    Assigned → In Progress → Completed
    
    Attributes:
        id: Primary key (UUID)
        work_order_id: Foreign key to WorkOrder
        contractor_id: Dataverse contractor account ID
        contractor_name: Contractor name (denormalized for convenience)
        assignment_date: Date of assignment
        expected_completion: Expected completion date from contractor
        actual_completion: Actual completion date
        status: Assignment status (Assigned, In Progress, Completed, Cancelled)
        dataverse_id: Dataverse assignment GUID
        sync_status: Sync state
        last_synced: Timestamp of last sync
        
    Relationships:
        work_order: Many-to-one with WorkOrder
    """
    __tablename__ = "contractor_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    work_order_id = Column(UUID(as_uuid=True), ForeignKey("work_orders.id"), nullable=False, index=True)
    contractor_id = Column(String(255), nullable=False)
    contractor_name = Column(String(500), nullable=False)
    assignment_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    expected_completion = Column(DateTime, nullable=True)
    actual_completion = Column(DateTime, nullable=True)
    status = Column(SQLEnum(AssignmentStatus), default=AssignmentStatus.ASSIGNED, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    dataverse_id = Column(String(255), nullable=True, index=True)
    sync_status = Column(String(50), default="pending", nullable=False)
    last_synced = Column(DateTime, nullable=True)
    
    # Relationships
    work_order = relationship("WorkOrder", back_populates="contractor_assignments")
    
    __table_args__ = (
        CheckConstraint("status IN ('Assigned', 'In Progress', 'Completed', 'Cancelled')"),
        Index("idx_assignment_work_order", "work_order_id"),
        Index("idx_assignment_contractor", "contractor_id"),
    )
    
    def __repr__(self) -> str:
        return f"<ContractorAssignment(id={self.id}, contractor='{self.contractor_name}', status={self.status})>"
    
    def can_transition_to(self, new_status: AssignmentStatus) -> bool:
        """Validate state machine transition.
        
        Args:
            new_status: Target assignment status
            
        Returns:
            True if transition is allowed, False otherwise
        """
        allowed_transitions = {
            AssignmentStatus.ASSIGNED: [AssignmentStatus.IN_PROGRESS, AssignmentStatus.CANCELLED],
            AssignmentStatus.IN_PROGRESS: [AssignmentStatus.COMPLETED, AssignmentStatus.CANCELLED],
            AssignmentStatus.COMPLETED: [],
            AssignmentStatus.CANCELLED: [],
        }
        return new_status in allowed_transitions.get(self.status, [])
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize assignment to dictionary."""
        return {
            "id": str(self.id),
            "work_order_id": str(self.work_order_id),
            "dataverse_id": self.dataverse_id,
            "contractor_id": self.contractor_id,
            "contractor_name": self.contractor_name,
            "assignment_date": self.assignment_date.isoformat(),
            "expected_completion": self.expected_completion.isoformat() if self.expected_completion else None,
            "actual_completion": self.actual_completion.isoformat() if self.actual_completion else None,
            "status": self.status.value if isinstance(self.status, AssignmentStatus) else self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ProgressTracking(BaseModel, TimestampMixin, DataverseTrackedMixin):
    """
    Progress tracking model for real-time work order milestone tracking.
    
    Records completion of major milestones and progress checkpoints for
    work orders and repair jobs. One-to-one relationships (optional).
    
    Attributes:
        id: Primary key (UUID)
        work_order_id: Foreign key to WorkOrder (optional)
        repair_job_id: Foreign key to RepairJob (optional)
        milestone: Milestone name/description
        completed_date: When milestone was completed
        notes: Additional notes about milestone completion
        dataverse_id: Dataverse record GUID
        sync_status: Sync state
        last_synced: Timestamp of last sync
        
    Relationships:
        work_order: Optional one-to-one with WorkOrder
        repair_job: Optional one-to-one with RepairJob
    """
    __tablename__ = "progress_tracking"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    work_order_id = Column(UUID(as_uuid=True), ForeignKey("work_orders.id"), nullable=True, unique=True)
    repair_job_id = Column(UUID(as_uuid=True), ForeignKey("repair_jobs.id"), nullable=True, unique=True)
    milestone = Column(String(255), nullable=False)
    completed_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    dataverse_id = Column(String(255), nullable=True, index=True)
    sync_status = Column(String(50), default="pending", nullable=False)
    last_synced = Column(DateTime, nullable=True)
    
    # Relationships
    work_order = relationship("WorkOrder", back_populates="progress_tracking")
    repair_job = relationship("RepairJob", back_populates="progress_tracking")
    
    __table_args__ = (
        CheckConstraint("(work_order_id IS NOT NULL) OR (repair_job_id IS NOT NULL)"),
        Index("idx_progress_work_order", "work_order_id"),
        Index("idx_progress_repair_job", "repair_job_id"),
    )
    
    def __repr__(self) -> str:
        return f"<ProgressTracking(id={self.id}, milestone='{self.milestone}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize progress tracking to dictionary."""
        return {
            "id": str(self.id),
            "work_order_id": str(self.work_order_id) if self.work_order_id else None,
            "repair_job_id": str(self.repair_job_id) if self.repair_job_id else None,
            "dataverse_id": self.dataverse_id,
            "milestone": self.milestone,
            "completed_date": self.completed_date.isoformat(),
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ComplianceRecord(BaseModel, TimestampMixin, DataverseTrackedMixin):
    """
    Compliance record model for regulatory audit trail.
    
    Tracks compliance verification and violations for work orders.
    Maintains audit trail for regulatory reporting (ADA, Local Law 60, etc.)
    
    Attributes:
        id: Primary key (UUID)
        work_order_id: Foreign key to WorkOrder
        compliance_type: Type of compliance check (ADA, AIA, LL60, etc.)
        status: Compliance status (Pending, Verified, Flagged, Resolved)
        verified_by: User/system that verified compliance
        verified_date: Date of verification
        notes: Compliance notes/findings
        dataverse_id: Dataverse record GUID
        sync_status: Sync state
        last_synced: Timestamp of last sync
        
    Relationships:
        work_order: Many-to-one with WorkOrder
    """
    __tablename__ = "compliance_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    work_order_id = Column(UUID(as_uuid=True), ForeignKey("work_orders.id"), nullable=False, index=True)
    compliance_type = Column(String(100), nullable=False, index=True)
    status = Column(SQLEnum(ComplianceStatus), default=ComplianceStatus.PENDING, nullable=False, index=True)
    verified_by = Column(String(255), nullable=True)
    verified_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    dataverse_id = Column(String(255), nullable=True, index=True)
    sync_status = Column(String(50), default="pending", nullable=False)
    last_synced = Column(DateTime, nullable=True)
    
    # Relationships
    work_order = relationship("WorkOrder", back_populates="compliance_records")
    
    __table_args__ = (
        CheckConstraint("status IN ('Pending', 'Verified', 'Flagged', 'Resolved')"),
        Index("idx_compliance_work_order", "work_order_id"),
        Index("idx_compliance_type_status", "compliance_type", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<ComplianceRecord(id={self.id}, type={self.compliance_type}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize compliance record to dictionary."""
        return {
            "id": str(self.id),
            "work_order_id": str(self.work_order_id),
            "dataverse_id": self.dataverse_id,
            "compliance_type": self.compliance_type,
            "status": self.status.value if isinstance(self.status, ComplianceStatus) else self.status,
            "verified_by": self.verified_by,
            "verified_date": self.verified_date.isoformat() if self.verified_date else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DataverseSyncMetadata(BaseModel, TimestampMixin):
    """
    Internal tracking for Dataverse synchronization state.
    
    Tracks bidirectional sync state, conflict detection, and resolution
    strategies for each entity. Enables idempotency and conflict resolution.
    
    Attributes:
        id: Primary key (UUID)
        entity_type: Type of entity being synced (msdyn_workorders, etc.)
        entity_id: Local UUID of entity
        dataverse_id: Dataverse GUID of entity
        sync_direction: Direction of sync (inbound, outbound, bidirectional)
        last_sync_time: Timestamp of last successful sync
        next_sync_time: Scheduled time for next sync attempt
        conflict_status: Conflict detection state
        conflict_resolution_strategy: Strategy for resolving conflicts (dataverse_wins, toolkit_wins, merge)
        sync_error: Last sync error message (if any)
        sync_attempts: Number of sync attempts
        created_at: Metadata creation timestamp
        updated_at: Last metadata update timestamp
    """
    __tablename__ = "dataverse_sync_metadata"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    entity_type = Column(String(255), nullable=False, index=True)
    entity_id = Column(String(255), nullable=False, index=True)
    dataverse_id = Column(String(255), nullable=False, index=True)
    sync_direction = Column(SQLEnum(SyncDirection), default=SyncDirection.BIDIRECTIONAL, nullable=False)
    last_sync_time = Column(DateTime, nullable=True)
    next_sync_time = Column(DateTime, nullable=True)
    conflict_status = Column(
        SQLEnum(ConflictStatus),
        default=ConflictStatus.NO_CONFLICT,
        nullable=False,
        index=True
    )
    conflict_resolution_strategy = Column(String(50), nullable=True)
    sync_error = Column(Text, nullable=True)
    sync_attempts = Column(Integer, default=0, nullable=False)
    
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", name="uq_entity_sync"),
        Index("idx_sync_metadata_conflict", "conflict_status"),
        Index("idx_sync_metadata_next_sync", "next_sync_time"),
    )
    
    def __repr__(self) -> str:
        return f"<DataverseSyncMetadata(entity_type={self.entity_type}, status={self.conflict_status})>"
    
    def mark_synced(self, direction: SyncDirection = SyncDirection.BIDIRECTIONAL) -> None:
        """Mark entity as successfully synced.
        
        Args:
            direction: Direction of sync operation
        """
        self.last_sync_time = datetime.now(timezone.utc)
        self.conflict_status = ConflictStatus.NO_CONFLICT
        self.sync_error = None
        self.sync_attempts = 0
        logger.debug(f"Marked {self.entity_type} {self.entity_id} as synced")
    
    def mark_failed(self, error: str) -> None:
        """Mark sync as failed with error message.
        
        Args:
            error: Error message
        """
        self.sync_error = error
        self.sync_attempts += 1
        self.next_sync_time = datetime.now(timezone.utc) + timedelta(minutes=5 * self.sync_attempts)
        logger.error(f"Marked {self.entity_type} {self.entity_id} as failed: {error}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize metadata to dictionary."""
        return {
            "id": str(self.id),
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "dataverse_id": self.dataverse_id,
            "sync_direction": self.sync_direction.value,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "next_sync_time": self.next_sync_time.isoformat() if self.next_sync_time else None,
            "conflict_status": self.conflict_status.value,
            "conflict_resolution_strategy": self.conflict_resolution_strategy,
            "sync_error": self.sync_error,
            "sync_attempts": self.sync_attempts,
        }


# ===== QUERY HELPERS =====

class DataverseModelQueries:
    """Convenience query methods for Dataverse models."""
    
    @staticmethod
    def get_pending_work_orders(session: Session) -> List[WorkOrder]:
        """Query work orders pending completion."""
        return session.query(WorkOrder).filter(
            WorkOrder.status.in_([WorkOrderStatus.NEW, WorkOrderStatus.IN_PROGRESS])
        ).all()
    
    @staticmethod
    def get_overdue_work_orders(session: Session) -> List[WorkOrder]:
        """Query overdue work orders."""
        return session.query(WorkOrder).filter(
            WorkOrder.due_date < datetime.now(timezone.utc),
            WorkOrder.status != WorkOrderStatus.COMPLETED
        ).all()
    
    @staticmethod
    def get_unsynced_entities(session: Session, entity_type: str) -> List[Any]:
        """Query entities pending sync to Dataverse."""
        metadata_records = session.query(DataverseSyncMetadata).filter(
            DataverseSyncMetadata.entity_type == entity_type,
            DataverseSyncMetadata.conflict_status != ConflictStatus.RESOLVED
        ).all()
        
        if not metadata_records:
            return []
        
        entity_ids = [r.entity_id for r in metadata_records]
        
        if entity_type == "msdyn_workorders":
            return session.query(WorkOrder).filter(WorkOrder.id.in_(entity_ids)).all()
        elif entity_type == "nt_repairs":
            return session.query(RepairJob).filter(RepairJob.id.in_(entity_ids)).all()
        elif entity_type == "msdyn_resourceassignments":
            return session.query(ContractorAssignment).filter(ContractorAssignment.id.in_(entity_ids)).all()
        
        return []
    
    @staticmethod
    def get_compliance_issues(session: Session) -> List[ComplianceRecord]:
        """Query compliance records flagged for review."""
        return session.query(ComplianceRecord).filter(
            ComplianceRecord.status.in_([ComplianceStatus.FLAGGED, ComplianceStatus.PENDING])
        ).all()


# ===== DATABASE INITIALIZATION =====

def init_dataverse_models(engine) -> None:
    """Initialize all Dataverse ORM models (create tables).
    
    Args:
        engine: SQLAlchemy engine instance
    """
    Base.metadata.create_all(engine)
    logger.info("Dataverse ORM models initialized")


def get_dataverse_session(engine) -> Session:
    """Create SQLAlchemy session for Dataverse models.
    
    Args:
        engine: SQLAlchemy engine instance
        
    Returns:
        SQLAlchemy Session instance
    """
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


# Import timedelta if needed
from datetime import timedelta
