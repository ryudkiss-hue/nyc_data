"""Pydantic request/response schemas for FastAPI validation.

Provides typed request/response models with validation, examples, and
documentation for OpenAPI schema generation.

Schema Categories:
    - Request Schemas: IncidentFilterRequest, RepairFilterRequest, etc.
    - Response Schemas: SegmentResponse, IncidentResponse, etc.
    - Error Schemas: ErrorResponse

Standards:
    - Use Pydantic v2 Config
    - Include Field validators and examples
    - Document all fields for OpenAPI
    - Use timezone-aware datetimes (UTC)
    - Provide reasonable defaults

Example:
    from socrata_toolkit.api.schemas import IncidentResponse
    incident = IncidentResponse(
        incident_id="inc_123",
        segment_id="seg_456",
        severity="high"
    )
"""

from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, field_validator
import json


# Enums for standard values
class SeverityLevel(str, Enum):
    """Incident severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MaterialType(str, Enum):
    """Material types."""

    ASPHALT = "asphalt"
    CONCRETE = "concrete"
    OTHER = "other"


class RepairStatus(str, Enum):
    """Repair status values."""

    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


class IncidentStatus(str, Enum):
    """Incident status values."""

    OPEN = "open"
    ASSIGNED = "assigned"
    RESOLVED = "resolved"


# REQUEST SCHEMAS


class DateRangeFilter(BaseModel):
    """Date range filter for queries.

    Attributes:
        date_from: Start date (inclusive)
        date_to: End date (inclusive)
    """

    date_from: Optional[date] = Field(None, description="Start date (YYYY-MM-DD)")
    date_to: Optional[date] = Field(None, description="End date (YYYY-MM-DD)")

    @field_validator("date_to")
    @classmethod
    def validate_date_range(cls, v: Optional[date], info) -> Optional[date]:
        """Ensure date_to >= date_from."""
        if v and info.data.get("date_from") and v < info.data.get("date_from"):
            raise ValueError("date_to must be >= date_from")
        return v


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints.

    Attributes:
        limit: Max results to return (1-1000, default 100)
        offset: Number of results to skip (default 0)
        sort_by: Field to sort by
        sort_order: asc or desc
    """

    limit: int = Field(100, ge=1, le=1000, description="Max results (1-1000)")
    offset: int = Field(0, ge=0, description="Results to skip")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Optional[str] = Field("asc", pattern="^(asc|desc)$", description="Sort direction")


class IncidentFilterRequest(BaseModel):
    """Filter for incident list queries.

    Attributes:
        segment_id: Filter by segment
        material_type: Filter by material type
        severity: Filter by severity level
        status: Filter by incident status
        date_range: Date range filter
        pagination: Pagination params
    """

    segment_id: Optional[str] = Field(None, description="Segment ID")
    material_type: Optional[MaterialType] = Field(None, description="Material type")
    severity: Optional[SeverityLevel] = Field(None, description="Severity level")
    status: Optional[IncidentStatus] = Field(None, description="Incident status")
    date_from: Optional[date] = Field(None, description="Start date")
    date_to: Optional[date] = Field(None, description="End date")
    limit: int = Field(100, ge=1, le=1000, description="Max results")
    offset: int = Field(0, ge=0, description="Results to skip")

    class Config:
        json_schema_extra = {
            "example": {
                "material_type": "asphalt",
                "severity": "high",
                "limit": 50,
                "offset": 0,
            }
        }


class RepairFilterRequest(BaseModel):
    """Filter for repair list queries.

    Attributes:
        contractor_id: Filter by contractor
        status: Filter by repair status
        material_type: Filter by material type
        date_from: Start date
        date_to: End date
        pagination: Pagination params
    """

    contractor_id: Optional[str] = Field(None, description="Contractor ID")
    status: Optional[RepairStatus] = Field(None, description="Repair status")
    material_type: Optional[MaterialType] = Field(None, description="Material type")
    date_from: Optional[date] = Field(None, description="Start date")
    date_to: Optional[date] = Field(None, description="End date")
    limit: int = Field(100, ge=1, le=1000, description="Max results")
    offset: int = Field(0, ge=0, description="Results to skip")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "in_progress",
                "contractor_id": "cont_123",
                "limit": 50,
            }
        }


class KPIFilterRequest(BaseModel):
    """Filter for KPI queries.

    Attributes:
        material_type: Filter by material type
        date_from: Start date
        date_to: End date
        percentile: Percentile for metrics (25, 50, 75)
    """

    material_type: Optional[MaterialType] = Field(None, description="Material type")
    date_from: Optional[date] = Field(None, description="Start date")
    date_to: Optional[date] = Field(None, description="End date")
    percentile: Optional[int] = Field(50, ge=1, le=99, description="Percentile (1-99)")

    class Config:
        json_schema_extra = {
            "example": {
                "material_type": "asphalt",
                "percentile": 75,
            }
        }


class AuditFilterRequest(BaseModel):
    """Filter for audit log queries.

    Attributes:
        actor: Filter by actor (user/system)
        action: Filter by action type
        dataset_id: Filter by dataset
        date_from: Start date
        date_to: End date
        pagination: Pagination params
    """

    actor: Optional[str] = Field(None, description="Actor (user or system)")
    action: Optional[str] = Field(None, description="Action type")
    dataset_id: Optional[str] = Field(None, description="Dataset ID")
    date_from: Optional[date] = Field(None, description="Start date")
    date_to: Optional[date] = Field(None, description="End date")
    limit: int = Field(100, ge=1, le=1000, description="Max results")
    offset: int = Field(0, ge=0, description="Results to skip")


# RESPONSE SCHEMAS


class SegmentResponse(BaseModel):
    """Response model for sidewalk segment.

    Attributes:
        segment_id: Unique segment ID
        material_type: Material type
        length_feet: Segment length
        last_updated: Last update timestamp
    """

    segment_id: str = Field(..., description="Unique segment ID")
    material_type: MaterialType = Field(..., description="Material type")
    length_feet: float = Field(..., gt=0, description="Length in linear feet")
    last_updated: datetime = Field(..., description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "segment_id": "seg_123",
                "material_type": "asphalt",
                "length_feet": 250.5,
                "last_updated": "2026-05-10T01:51:19Z",
            }
        }


class IncidentResponse(BaseModel):
    """Response model for incident.

    Attributes:
        incident_id: Unique incident ID
        segment_id: Segment ID
        complaint_type: Type of complaint
        severity: Severity level
        status: Current status
        created_at: Creation timestamp
        updated_at: Last update timestamp
        description: Detailed description
    """

    incident_id: str = Field(..., description="Unique incident ID")
    segment_id: str = Field(..., description="Associated segment ID")
    complaint_type: str = Field(..., description="Type of complaint")
    severity: SeverityLevel = Field(..., description="Severity level")
    status: IncidentStatus = Field(..., description="Current status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    description: Optional[str] = Field(None, description="Detailed description")

    class Config:
        json_schema_extra = {
            "example": {
                "incident_id": "inc_123",
                "segment_id": "seg_456",
                "complaint_type": "pothole",
                "severity": "high",
                "status": "assigned",
                "created_at": "2026-05-10T01:51:19Z",
                "updated_at": "2026-05-10T01:51:19Z",
                "description": "Large pothole on sidewalk",
            }
        }


class RepairResponse(BaseModel):
    """Response model for repair.

    Attributes:
        repair_id: Unique repair ID
        incident_id: Associated incident ID
        segment_id: Associated segment ID
        contractor_id: Contractor performing repair
        status: Current status
        estimated_cost: Estimated cost
        actual_cost: Actual cost (null if not completed)
        scheduled_date: Scheduled date
        completion_date: Completion date (null if not completed)
    """

    repair_id: str = Field(..., description="Unique repair ID")
    incident_id: str = Field(..., description="Associated incident ID")
    segment_id: str = Field(..., description="Associated segment ID")
    contractor_id: str = Field(..., description="Contractor ID")
    status: RepairStatus = Field(..., description="Current status")
    estimated_cost: float = Field(..., gt=0, description="Estimated cost in USD")
    actual_cost: Optional[float] = Field(None, ge=0, description="Actual cost in USD")
    scheduled_date: date = Field(..., description="Scheduled repair date")
    completion_date: Optional[date] = Field(None, description="Completion date")

    class Config:
        json_schema_extra = {
            "example": {
                "repair_id": "rep_789",
                "incident_id": "inc_123",
                "segment_id": "seg_456",
                "contractor_id": "cont_123",
                "status": "in_progress",
                "estimated_cost": 1500.00,
                "actual_cost": None,
                "scheduled_date": "2026-05-15",
                "completion_date": None,
            }
        }


class MaterialMetricsResponse(BaseModel):
    """Response model for material-type KPI metrics.

    Attributes:
        material_type: Material type
        defect_rate_pct: Defect rate percentage
        avg_age_years: Average age
        hazard_count: Number of hazards
        total_linear_feet: Total linear feet
        lifecycle_cost_sqft: Lifecycle cost per square foot
    """

    material_type: MaterialType = Field(..., description="Material type")
    defect_rate_pct: float = Field(..., ge=0, le=100, description="Defect rate %")
    avg_age_years: float = Field(..., ge=0, description="Average age in years")
    hazard_count: int = Field(..., ge=0, description="Number of hazards")
    total_linear_feet: float = Field(..., ge=0, description="Total linear feet")
    lifecycle_cost_sqft: Optional[float] = Field(None, ge=0, description="Lifecycle cost/sqft")

    class Config:
        json_schema_extra = {
            "example": {
                "material_type": "asphalt",
                "defect_rate_pct": 12.5,
                "avg_age_years": 8.2,
                "hazard_count": 45,
                "total_linear_feet": 15000.0,
                "lifecycle_cost_sqft": 125.00,
            }
        }


class ADAMetricsResponse(BaseModel):
    """Response model for ADA compliance metrics.

    Attributes:
        segment_id: Segment ID
        compliance_score: Score 0-100
        failures: List of ADA failures
        recommended_repairs: Recommended repairs
    """

    segment_id: str = Field(..., description="Segment ID")
    compliance_score: int = Field(..., ge=0, le=100, description="Compliance score 0-100")
    failures: List[str] = Field(default_factory=list, description="ADA failures")
    recommended_repairs: List[str] = Field(default_factory=list, description="Recommended repairs")

    class Config:
        json_schema_extra = {
            "example": {
                "segment_id": "seg_123",
                "compliance_score": 75,
                "failures": ["cross_slope_exceeds_2pct", "edge_drop_gt_1_4in"],
                "recommended_repairs": ["grind_down_cross_slope", "repair_edge"],
            }
        }


class HazardMetricsResponse(BaseModel):
    """Response model for hazard coverage metrics.

    Attributes:
        hazard_count: Total number of hazards
        linear_feet: Linear feet with hazards
        clearance_rate_pct: Clearance rate %
        days_until_sla_violation: Days until SLA violation
    """

    hazard_count: int = Field(..., ge=0, description="Total hazards")
    linear_feet: float = Field(..., ge=0, description="Linear feet with hazards")
    clearance_rate_pct: float = Field(..., ge=0, le=100, description="Clearance rate %")
    days_until_sla_violation: int = Field(..., description="Days until SLA violation")

    class Config:
        json_schema_extra = {
            "example": {
                "hazard_count": 156,
                "linear_feet": 8500.0,
                "clearance_rate_pct": 88.5,
                "days_until_sla_violation": 3,
            }
        }


class ContractorMetricsResponse(BaseModel):
    """Response model for contractor performance metrics.

    Attributes:
        contractor_id: Contractor ID
        name: Contractor name
        quality_score: Score 0-100
        avg_cost_sqft: Average cost per square foot
        completion_rate_pct: On-time completion rate
        defect_rate_pct: Defect rate %
        material_expertise: Materials contractor is certified for
    """

    contractor_id: str = Field(..., description="Contractor ID")
    name: str = Field(..., description="Contractor name")
    quality_score: int = Field(..., ge=0, le=100, description="Quality score 0-100")
    avg_cost_sqft: float = Field(..., ge=0, description="Average cost per sqft")
    completion_rate_pct: float = Field(..., ge=0, le=100, description="Completion rate %")
    defect_rate_pct: float = Field(..., ge=0, le=100, description="Defect rate %")
    material_expertise: List[str] = Field(default_factory=list, description="Certified materials")

    class Config:
        json_schema_extra = {
            "example": {
                "contractor_id": "cont_123",
                "name": "Quality Pavement Inc.",
                "quality_score": 92,
                "avg_cost_sqft": 12.50,
                "completion_rate_pct": 95.5,
                "defect_rate_pct": 2.3,
                "material_expertise": ["asphalt", "concrete"],
            }
        }


class CostMetricsResponse(BaseModel):
    """Response model for cost analytics.

    Attributes:
        material_type: Material type
        cost_per_linear_foot: Cost per linear foot
        total_cost: Total cost for all segments
        roi_estimate: ROI estimate %
        trend_yoy_pct: Year-over-year trend %
    """

    material_type: MaterialType = Field(..., description="Material type")
    cost_per_linear_foot: float = Field(..., gt=0, description="Cost per linear foot")
    total_cost: float = Field(..., ge=0, description="Total cost")
    roi_estimate: float = Field(..., description="ROI estimate %")
    trend_yoy_pct: float = Field(..., description="YoY trend %")

    class Config:
        json_schema_extra = {
            "example": {
                "material_type": "asphalt",
                "cost_per_linear_foot": 15.00,
                "total_cost": 225000.00,
                "roi_estimate": 18.5,
                "trend_yoy_pct": -2.3,
            }
        }


class KPISummaryResponse(BaseModel):
    """Response model for KPI summary dashboard.

    Attributes:
        timestamp: Snapshot timestamp
        material_metrics: Metrics by material type
        ada_metrics: ADA compliance metrics
        hazard_metrics: Hazard coverage metrics
        contractor_metrics: Top contractors
        data_freshness_seconds: Age of data in seconds
    """

    timestamp: datetime = Field(..., description="Snapshot timestamp")
    material_metrics: List[MaterialMetricsResponse] = Field(..., description="Material KPIs")
    ada_metrics: ADAMetricsResponse = Field(..., description="ADA compliance metrics")
    hazard_metrics: HazardMetricsResponse = Field(..., description="Hazard coverage metrics")
    contractor_metrics: List[ContractorMetricsResponse] = Field(..., description="Contractor metrics")
    data_freshness_seconds: int = Field(..., ge=0, description="Data age in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-05-10T01:51:19Z",
                "material_metrics": [],
                "ada_metrics": {},
                "hazard_metrics": {},
                "contractor_metrics": [],
                "data_freshness_seconds": 3600,
            }
        }


class AuditLogResponse(BaseModel):
    """Response model for audit log entry.

    Attributes:
        operation_id: Unique operation ID
        actor: User or system account
        action: Action type
        dataset_id: Dataset ID
        resource_id: Resource ID
        timestamp: When action occurred
        details: Additional details
    """

    operation_id: str = Field(..., description="Unique operation ID")
    actor: str = Field(..., description="User or system account")
    action: str = Field(..., description="Action type")
    dataset_id: Optional[str] = Field(None, description="Dataset ID")
    resource_id: Optional[str] = Field(None, description="Resource ID")
    timestamp: datetime = Field(..., description="Action timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")

    class Config:
        json_schema_extra = {
            "example": {
                "operation_id": "op_123",
                "actor": "user_456",
                "action": "update_repair_status",
                "dataset_id": "repairs",
                "resource_id": "rep_789",
                "timestamp": "2026-05-10T01:51:19Z",
                "details": {"old_status": "scheduled", "new_status": "in_progress"},
            }
        }


class ErrorResponse(BaseModel):
    """Response model for errors.

    Attributes:
        error_code: Standard error code
        message: Error message
        status_code: HTTP status code
        request_id: Request ID for tracing
        details: Additional error details
        timestamp: Error timestamp
    """

    error_code: str = Field(..., description="Standard error code")
    message: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    request_id: str = Field(..., description="Request ID for tracing")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    timestamp: datetime = Field(..., description="Error timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "error_code": "RESOURCE_NOT_FOUND",
                "message": "Segment 'seg_123' not found",
                "status_code": 404,
                "request_id": "req_abc123def456",
                "details": {"resource_type": "segment", "resource_id": "seg_123"},
                "timestamp": "2026-05-10T01:51:19Z",
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check endpoint.

    Attributes:
        status: Overall status (healthy, degraded, unhealthy)
        timestamp: Check timestamp
        database: Database connection status
        cache: Cache connection status
        version: API version
    """

    status: str = Field(..., description="Overall status")
    timestamp: datetime = Field(..., description="Check timestamp")
    database: str = Field(..., description="Database status")
    cache: str = Field(..., description="Cache status")
    version: str = Field(..., description="API version")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2026-05-10T01:51:19Z",
                "database": "healthy",
                "cache": "healthy",
                "version": "v1",
            }
        }


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper.

    Attributes:
        data: Response data items
        total: Total number of items available
        limit: Limit used in query
        offset: Offset used in query
        timestamp: Response timestamp
        data_freshness_seconds: Age of data
    """

    data: List[Any] = Field(..., description="Response data items")
    total: int = Field(..., ge=0, description="Total items available")
    limit: int = Field(..., ge=1, description="Limit used in query")
    offset: int = Field(..., ge=0, description="Offset used in query")
    timestamp: datetime = Field(..., description="Response timestamp")
    data_freshness_seconds: int = Field(..., ge=0, description="Data age in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "data": [],
                "total": 500,
                "limit": 100,
                "offset": 0,
                "timestamp": "2026-05-10T01:51:19Z",
                "data_freshness_seconds": 3600,
            }
        }
