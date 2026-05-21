# Dataverse Integration Architecture for NYC DOT Sidewalk Management

**Version:** 1.0  
**Date:** May 2026  
**Status:** Architecture Design (Ready for Implementation)  
**Audience:** Technical architects, platform engineers, project analysts, Microsoft 365 administrators

---

## EXECUTIVE SUMMARY

This document defines the comprehensive architecture for integrating Microsoft Dataverse as the authoritative source for NYC DOT work orders, permits, and compliance tracking with the Socrata Toolkit as the operational execution platform. The architecture enables:

- **Asymmetric Bidirectional Sync**: Dataverse → Toolkit (work orders), Toolkit → Dataverse (status/completion updates)
- **Real-Time Collaboration**: Power BI dashboards, Excel reports, and Outlook notifications with current work order status
- **Enterprise-Grade Data Integrity**: Conflict resolution, idempotency, audit trails, and compliance tracking
- **Production SLAs**: Sub-5-minute sync latency, 99.9% reliability, full observability

---

## TABLE OF CONTENTS

1. [Bi-Directional Sync Architecture](#1-bi-directional-sync-architecture)
2. [Data Model & Entity Mapping](#2-data-model--entity-mapping)
3. [System Integration Points](#3-system-integration-points)
4. [Webhook & Real-Time Event Handling](#4-webhook--real-time-event-handling)
5. [Data Quality & Validation](#5-data-quality--validation)
6. [Security & Compliance](#6-security--compliance)
7. [Deployment Topology](#7-deployment-topology)
8. [Real-World Workflows](#8-real-world-nyc-dot-workflows)

---

## 1. BI-DIRECTIONAL SYNC ARCHITECTURE

### 1.1 Sync Pattern Selection: Event-Driven CDC with Polling Fallback

#### Pattern Rationale

| Pattern | Use Case | Latency | Reliability | Choice |
|---------|----------|---------|-------------|--------|
| **Event-Driven (Webhooks)** | Real-time notification of Dataverse changes | <1 min | Requires active webhook management | ✅ **PRIMARY** |
| **Change Data Capture (CDC)** | Query Dataverse for changed records at intervals | 5-30 min | Requires timestamp tracking | ⚠️ Secondary |
| **Polling** | Periodic full/delta queries to Dataverse | 15-60 min | Simple, resilient, higher compute cost | ⚠️ Fallback |

**Recommendation**: Implement **Event-Driven (Webhooks)** with **Polling Fallback** for production resilience:
- Webhooks for real-time work order updates (target: <2 minutes)
- Polling every 15 minutes as safety net if webhooks fail
- CDC timestamp tracking for reconciliation

---

### 1.2 Sync Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATAVERSE (Source of Truth)                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐ │
│  │ Work Orders      │  │ Permits          │  │ Compliance Records │ │
│  │ (create/update)  │  │ (create/update)  │  │ (status only)      │ │
│  └──────────────────┘  └──────────────────┘  └────────────────────┘ │
│           │                    │                      │              │
│           └────────────────────┴──────────────────────┘              │
│                    WEBHOOK EVENT STREAM                              │
│                 (Real-Time Change Notifications)                    │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  WEBHOOK RECEIVER     │
                    │  (Azure Function      │
                    │   or API Endpoint)    │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼────────────┐
                    │ EVENT DEDUPLICATION    │
                    │ (Idempotency Key       │
                    │  Cache, DLQ Handling)  │
                    └───────────┬────────────┘
                                │
                    ┌───────────▼────────────────────────┐
                    │ MESSAGE QUEUE                      │
                    │ (Azure Service Bus)                │
                    │ Topics:                            │
                    │ - work_order_events                │
                    │ - permit_events                    │
                    │ - compliance_events                │
                    └───────────┬────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
    ┌────────────┐         ┌────────────┐         ┌───────────────┐
    │ SYNC       │         │ SYNC       │         │ RECONCILIATION│
    │ PROCESSOR  │         │ CONFLICT   │         │ AUDIT         │
    │ (Airflow   │         │ RESOLVER   │         │ VALIDATOR     │
    │ Task)      │         │ (Async)    │         │ (Nightly)     │
    └──────┬─────┘         └──────┬─────┘         └────────┬──────┘
           │                     │                        │
           └─────────────────────┼────────────────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │ TOOLKIT DATASTORE        │
                    │ (PostgreSQL)             │
                    ├────────────────────────┐ │
                    │ work_orders            │ │
                    │ repair_jobs            │ │
                    │ contractor_assignments │ │
                    │ progress_tracking      │ │
                    │ compliance_reporting   │ │
                    │ sync_metadata          │ │
                    └────────────────────────┘ │
                    └──────────────────────────┘
                                 │
        ┌────────────────────────┼──────────────────────────┐
        ▼                        ▼                          ▼
    ┌─────────────┐          ┌────────────┐          ┌──────────┐
    │ OUTBOUND    │          │ INTERNAL   │          │ API LAYER│
    │ STATUS      │          │ ANALYTICS  │          │ (Fast)   │
    │ SYNC        │          │ & KPIs     │          └──────────┘
    │ (Updates    │          │ (Airflow)  │               │
    │ back to     │          │            │               ▼
    │ Dataverse)  │          │            │          ┌──────────┐
    │             │          │            │          │ Power BI │
    │ Flow:       │          │            │          │ / Excel  │
    │ ┌─────────┐ │          │            │          │ Reports  │
    │ │Completion├─┘          │            │          └──────────┘
    │ │Status ↔ │             │            │
    │ │Dataverse│             │            │
    │ └─────────┘ │          │            │
    └─────────────┘          └────────────┘
```

---

### 1.3 Conflict Resolution Strategies

#### Scenario 1: Work Order Modified in Both Dataverse and Toolkit

**Situation**: 
- Dataverse: Permit date changed from 2026-05-15 to 2026-05-22
- Toolkit: Repair progress updated to 75% completion

**Resolution**:
```
Priority Hierarchy (field-level precedence):

TIER 1 - Dataverse (System of Record):
  - workOrderId (immutable)
  - statusCode (manual updates only)
  - permitApprovalDate (governance/legal)
  - contractorAssignedId (dispatch authority)

TIER 2 - Last-Write-Wins:
  - description, notes (collaborative fields)
  - expectedCompletionDate
  
TIER 3 - Merge (Toolkit Operational):
  - completionPercentage (accumulated from toolkit)
  - repairStartDate (when work actually began)
  - actualCost (from material standards)
  - hazardousDefectResolved (compliance tracking)

CONFLICT HANDLING:
- If Dataverse change AND Toolkit change detected in same 5-min window:
  1. Evaluate field precedence tier
  2. TIER 1 conflicts → Dataverse wins (redo toolkit work if needed)
  3. TIER 2 conflicts → Review queue (manual approval workflow)
  4. TIER 3 conflicts → Toolkit wins (preserve operational state)
```

---

#### Scenario 2: Permit Expires Before Toolkit Marks Complete

**Situation**:
- Permit expiration_date = 2026-05-10 (now past)
- Toolkit still processing repair (at 60%)

**Resolution**:
```sql
-- COMPLIANCE ENFORCEMENT:
-- 1. Receive webhook: permit.status_changed → "EXPIRED"
-- 2. Check toolkit work_order.completion_percentage

IF work_order.completion_percentage < 100 THEN
  -- Generate alert to assignee
  UPDATE work_orders 
  SET alert_flag = 'PERMIT_EXPIRED',
      status_code = 'BLOCKED_PERMIT_EXPIRED'
  WHERE dataverse_id = permit.id;
  
  -- Create compliance violation record
  INSERT INTO compliance_violations 
  (work_order_id, violation_type, severity, generated_at)
  VALUES (work_order.id, 'PERMIT_EXPIRED', 'HIGH', NOW());
  
  -- Notify via Power BI alert
  CALL alert_manager.emit_alert(
    channel='power_bi',
    type='permit_expiration',
    work_order_id=work_order.id
  );
END IF;
```

---

#### Scenario 3: Contractor Assignment Changed While Repair In Progress

**Situation**:
- Dataverse: Contractor reassigned mid-project
- Toolkit: Original contractor at 40% completion

**Resolution**:
```
ASSIGNMENT HANDOFF PROTOCOL:

1. Receive Webhook: contractor_assignment.changed
   - Old contractor: Contractor_A
   - New contractor: Contractor_B
   - Change reason: Performance issue

2. Transition State Machine:
   OLD_CONTRACTOR_ACTIVE ──→ HANDOFF_IN_PROGRESS ──→ NEW_CONTRACTOR_ACTIVE
   
3. Toolkit Actions:
   - Pause current task (no new work by Contractor_A)
   - Create handoff record with:
     * Current completion state snapshot
     * Equipment/materials on-site inventory
     * Safety closure checklist
   
4. Notify Contractors:
   - Contractor_A: "Work paused for handoff review"
   - Contractor_B: "Assignment accepted. Review attached documents."
   
5. Resume Timeline:
   - Contractor_B acknowledges handoff (Outlook notification)
   - Work resumes within 24 hours (SLA)
   - Progress tracking continues from handoff point
```

---

### 1.4 Latency Requirements & SLA Targets

```
┌────────────────────────────────────────────────────────────────┐
│                  SYNC LATENCY SLA MATRIX                       │
├────────────────────────────────────────────────────────────────┤
│ OPERATION TYPE         │ TARGET LATENCY │ MAX ALLOWABLE │ SLA   │
├────────────────────────────────────────────────────────────────┤
│ Work Order Created     │ <2 min         │ <5 min        │ 99.5% │
│ Status Update (Toolkit │ <5 min         │ <10 min       │ 99%   │
│ → Dataverse)           │                │               │       │
│ Permit Expiration      │ <1 min         │ <2 min        │ 99.9% │
│ Contractor Assignment  │ <3 min         │ <8 min        │ 99%   │
│ Compliance Violation   │ <1 min         │ <3 min        │ 99.9% │
│ Daily Reconciliation   │ <30 min        │ <60 min       │ 99%   │
└────────────────────────────────────────────────────────────────┘

MONITORING & ALERTING:
- Metric: sync_latency_p95_seconds (alert if >120s for critical events)
- Metric: webhook_delivery_success_rate (alert if <99.5%)
- Metric: conflict_resolution_manual_queue_size (alert if >5 items)
- Metric: reconciliation_discrepancy_count (alert if >1 per 1000 records)
```

---

## 2. DATA MODEL & ENTITY MAPPING

### 2.1 Core Entity Relationships

```
DATAVERSE ENTITIES                          TOOLKIT DOMAIN MODEL
(Microsoft)                                 (PostgreSQL)

msdyn_workorder ────────────────────────→  work_orders
  ├─ msdyn_workorderid (PK)                  ├─ dataverse_id (FK) ✅
  ├─ msdyn_name (description)                ├─ description
  ├─ msdyn_estimatedstartedon (date)         ├─ planned_start_date
  ├─ msdyn_estimatedcompletionedon          ├─ planned_completion_date
  ├─ msdyn_workordertype (category)         ├─ work_type (enum)
  └─ statecode (status)                      └─ status_code (enum)
                  │
                  ├──────────────────────→  repair_jobs
                  │                         ├─ work_order_id (FK)
                  │                         ├─ repair_type
                  │                         ├─ material_type
                  │                         ├─ linear_feet
                  │                         └─ estimated_cost
                  │
                  ├──────────────────────→  contractor_assignments
                  │                         ├─ work_order_id (FK)
                  │                         ├─ contractor_id
                  │                         ├─ start_date
                  │                         ├─ expected_completion_date
                  │                         └─ assignment_status
                  │
                  └──────────────────────→  progress_tracking
                                            ├─ work_order_id (FK)
                                            ├─ completion_percentage
                                            ├─ inspection_date
                                            ├─ ada_compliant (bool)
                                            └─ status_narrative

                          ↓ SYNCED BACK TO DATAVERSE ↓

                  Dataverse.msdyn_workorder.statusCode
                  ← Toolkit.work_orders.status_code
                  
                  Dataverse.Progress.percentage
                  ← Toolkit.progress_tracking.completion_percentage
```

---

### 2.2 Entity Field Mapping

#### Entity: Work Order (msdyn_workorder → work_orders)

| Dataverse Field | Toolkit Column | Data Type | Sync Direction | Validation Rules | Notes |
|---|---|---|---|---|---|
| msdyn_workorderid | dataverse_id | UUID | ← (inbound) | NOT NULL, unique | Immutable primary key from Dataverse |
| msdyn_name | description | String(500) | ← (inbound) | Max 500 chars | Auto-truncate if exceeds |
| msdyn_estimatedstartedon | planned_start_date | TIMESTAMP | ← (inbound) | ≥ TODAY | Validate permit-aligned scheduling |
| msdyn_estimatedcompletioonedon | planned_completion_date | TIMESTAMP | ← (inbound) | > planned_start_date | Check against permit duration |
| msdyn_workordertype | work_type | ENUM | ← (inbound) | IN ('repair', 'inspection', 'inspection_then_repair') | NYC DOT standard categories |
| statecode | status_code | ENUM | ↔ (bidirectional) | Valid state transition | See state machine below |
| msdyn_priority | priority_level | INT (1-5) | ← (inbound) | IN (1,2,3,4,5) | Dispatch priority |
| customertypecode | location_type | ENUM | ← (inbound) | IN ('block_face', 'intersection', 'plaza') | NYC sidewalk geography |
| ownerid (resource) | assigned_contractor_id | INT (FK) | ← (inbound) | NOT NULL if status='active' | Sync contractor lookup table |
| createdon | created_at | TIMESTAMP | ← (inbound) | Auto-set | Dataverse audit |
| modifiedon | dataverse_updated_at | TIMESTAMP | ← (inbound) | Auto-set | Latest Dataverse version |
| **OUTBOUND:** | | | | | |
| msdyn_summary | completion_summary | String(1000) | → (outbound) | Max 1000 chars | Toolkit narrative updates |
| msdyn_actualtraveltime | actual_duration_minutes | INT | → (outbound) | ≥ 0 | Hours spent on repair |
| msdyn_actualcost | actual_cost_dollars | DECIMAL(10,2) | → (outbound) | ≥ 0 | From material_standards costing |

---

#### Entity: Repair Job (→ repair_jobs)

| Toolkit Column | Source | Data Type | Validation | Notes |
|---|---|---|---|---|
| work_order_id | Dataverse.msdyn_workorderid | UUID | FK to work_orders | Links to parent work order |
| repair_type | Dataverse.msdyn_description parsing | ENUM | IN ('pothole', 'crack', 'trip_hazard', 'displacement', 'other') | Extract from description via NLP |
| material_type | Dataverse.msdyn_surfacematerial (if available, else infer) | ENUM | IN ('asphalt', 'concrete', 'permeable', 'specialty') | Use material_standards taxonomy |
| linear_feet | Manual input or from GIS | DECIMAL(8,2) | > 0 | Required for cost estimation |
| estimated_cost | material_standards lookup | DECIMAL(10,2) | ≥ 0 | Based on repair_type + material_type |
| actual_cost | Contractor invoice + labor | DECIMAL(10,2) | ≥ 0 | Updated post-completion |
| completion_date | Field inspection | TIMESTAMP | NOT NULL before status→COMPLETE | Mark actual finish date |
| inspection_passed | QA validation | BOOL | NOT NULL before closure | ADA + surface quality checks |

---

#### Entity: Contractor Assignment (→ contractor_assignments)

| Field | Source | Type | Direction | Rules | Notes |
|---|---|---|---|---|---|
| contractor_id | Dataverse.ownerid | INT | ← | NOT NULL | Sync from Dataverse team member |
| contractor_name | Dataverse lookup | String | ← | Synced with contractor_id | Display name for reporting |
| work_order_id | Dataverse.msdyn_workorderid | UUID | ← | FK | Links to parent work order |
| assignment_date | Webhook receive timestamp | TIMESTAMP | Auto | Immutable | When assignment created |
| expected_completion_date | Dataverse.msdyn_estimatedcompletioonedon | TIMESTAMP | ← | > assignment_date | Inherited from work order |
| actual_start_date | Contractor check-in (QGIS/mobile) | TIMESTAMP | → | Nullable | When work actually began |
| actual_completion_date | Contractor sign-off + QA | TIMESTAMP | → | > actual_start_date | Final completion timestamp |
| assignment_status | State machine | ENUM | ↔ | See below | Tracks handoff state |
| handoff_notes | Field narrative | String | → | Max 500 chars | For contractor transitions |

**Assignment State Machine**:
```
NEW → ASSIGNED → ACTIVE → [PAUSED ↔ ACTIVE] → COMPLETED → CLOSED
      │          │                            │
      └──────────┴───────────────────────────┴─ CANCELLED
```

---

#### Entity: Progress Tracking (→ progress_tracking)

| Field | Source | Type | Direction | Rules | Notes |
|---|---|---|---|---|---|
| work_order_id | Parent | UUID | ← | FK | Links to work order |
| check_in_timestamp | Mobile app (QGIS) | TIMESTAMP | → | Auto | When inspector arrived |
| completion_percentage | Inspector assessment | INT | → | 0-100 | Updated daily or per phase |
| inspection_date | Latest check-in | TIMESTAMP | → | NOT NULL | When QA was performed |
| defect_observations | NLP-extracted from mobile notes | String | → | Max 2000 chars | Complaint ↔ defect classification |
| ada_compliant | ADA compliance checker (ada_compliance_reference) | BOOL | → | NOT NULL | Pass/fail per standards |
| surface_quality_score | Inspector rating + measurement | INT (1-10) | → | 1-10 | Quality gate |
| hazard_resolved | Safety assessment | BOOL | → | NOT NULL if hazard present | Safety-critical closure gate |
| supervisor_sign_off | Contractor supervisor | BOOL | → | Nullable | Optional additional gate |
| status_narrative | Field notes + system summary | String | → | Max 1000 chars | Human-readable status for Power BI |
| last_updated_at | Trigger timestamp | TIMESTAMP | Auto | Immutable audit | For reconciliation |

---

#### Entity: Compliance Reporting (→ compliance_reporting)

| Field | Source | Type | Direction | Rules | Notes |
|---|---|---|---|---|---|
| work_order_id | Parent | UUID | ← | FK | Links to work order |
| compliance_check_type | Predefined list | ENUM | Auto | IN ('ada', 'permit', 'material_standards', 'safety') | What was checked |
| check_status | Validation result | ENUM | Auto | IN ('PASS', 'FAIL', 'REVIEW') | Compliance gate result |
| check_timestamp | Trigger time | TIMESTAMP | Auto | NOT NULL | When check ran |
| violation_code | Reference ID | String | Auto | FK to violations table | Specific violation (if FAIL) |
| violation_severity | Risk assessment | ENUM | Auto | IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') | Alert prioritization |
| remediation_notes | Follow-up action | String | → | Max 500 chars | What to fix |
| remediation_deadline | Calculated from severity | TIMESTAMP | Auto | Based on violation_severity | When to complete fix |
| auditor_id | System assigned | INT | Auto | FK to users | Who ran the check |
| auditor_signed_off | Final approval | BOOL | Nullable | NOT NULL for PASS | Signed compliance seal |

---

### 2.3 Entity Relationships & Referential Integrity

```sql
-- Dataverse ID Synchronization (Critical FK Constraint)
ALTER TABLE work_orders
ADD CONSTRAINT fk_work_orders_dataverse_id
FOREIGN KEY (dataverse_id) REFERENCES dataverse_entities(id);

-- Contractor Assignment Validation
ALTER TABLE contractor_assignments
ADD CONSTRAINT chk_contractor_assignment_dates
CHECK (actual_start_date IS NULL OR actual_start_date >= assignment_date)
AND (actual_completion_date IS NULL OR actual_completion_date >= COALESCE(actual_start_date, assignment_date));

-- Repair Job Material Validation (Phase 1 Integration)
ALTER TABLE repair_jobs
ADD CONSTRAINT chk_repair_material_valid
CHECK (material_type IN (SELECT material_id FROM material_standards.materials))
AND (repair_type IN (SELECT defect_id FROM material_standards.defects_by_material WHERE material_id = repair_jobs.material_type));

-- Progress Tracking Completion Logic
ALTER TABLE progress_tracking
ADD CONSTRAINT chk_progress_completion_gates
CHECK (
  completion_percentage = 100 AND 
  ada_compliant = TRUE AND 
  hazard_resolved = TRUE AND
  surface_quality_score >= 7
) OR (completion_percentage < 100);

-- Sync Metadata Idempotency
ALTER TABLE sync_metadata
ADD CONSTRAINT pk_sync_idempotency
UNIQUE (event_source, event_id, dataverse_id);
```

---

## 3. SYSTEM INTEGRATION POINTS

### 3.1 How Dataverse Fits with Existing Integrations

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    COMPLETE INTEGRATION LANDSCAPE                         │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INGESTION SOURCES:                                                        │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────────────┐   │
│  │ Dataverse   │  │ Socrata APIs │  │ Mobile/Field (QGIS, mobile)   │   │
│  │ (Work Orders│  │ (311 Data,   │  │ (Inspection Photos, GPS)       │   │
│  │ & Permits)  │  │ Complaint    │  │                                │   │
│  └──────┬──────┘  │ Datasets)    │  └────────────────────────────────┘   │
│         │         └──────┬───────┘                                        │
│         │                │                                                │
│         └────────────────┼────────────────────────────────────┐           │
│                          │                                    │           │
│                ┌─────────▼──────────┐                 ┌──────▼────────┐  │
│                │ TOOLKIT PIPELINE   │                 │ ArcGIS/QGIS   │  │
│                │ (Socrata Toolkit)  │                 │ (Spatial Ref) │  │
│                ├────────────────────┤                 └───────────────┘  │
│                │ • Schema Registry  │                                    │
│                │ • Validation Rules │                                    │
│                │ • Material Std.    │    ┌─────────────────┐             │
│                │ • Lineage Tracking │    │ EXCEL WORKBOOKS │             │
│                │ • SCD Type 2       │    │ (Field Reports) │             │
│                │ • CDC Integration  │    └────────┬────────┘             │
│                └────────┬───────────┘             │                      │
│                         │                        │                      │
│           ┌─────────────▼────────────┬───────────┘                      │
│           │                          │                                  │
│  ┌────────▼────────────┐   ┌────────▼──────────────┐                  │
│  │ PostgreSQL + PostGIS│   │ POWER BI DASHBOARDS   │                  │
│  │ (Operational DB)    │   │ (Real-time Reporting)│                  │
│  └────────┬────────────┘   └─────────────────────┘                   │
│           │                                                            │
│  ┌────────▼────────────────────────┐                                  │
│  │ DATAVERSE OUTBOUND SYNC         │                                  │
│  │ (Status, Completion, Compliance)│─────┐                            │
│  └────────────────────────────────┘     │                            │
│           │                              │                            │
│           └──────────────┬───────────────┘                            │
│                          ▼                                            │
│           ┌──────────────────────────┐                               │
│           │ MICROSOFT 365 ECOSYSTEM  │                               │
│           ├──────────────────────────┤                               │
│           │ • Power BI (dashboards)  │                               │
│           │ • Excel (reports)        │                               │
│           │ • Outlook (alerts)       │                               │
│           │ • Teams (collaboration)  │                               │
│           └──────────────────────────┘                               │
│                                                                        │
└───────────────────────────────────────────────────────────────────────┘
```

---

### 3.2 Connection to Lineage Tracking

**Dataverse operations are tagged in lineage tracking** with full provenance:

```python
# lineage_core.py: DATAVERSE_INTEGRATION extension
from socrata_toolkit.lineage_core import TransformationNode, NodeType, DAG

dataverse_sync_node = TransformationNode(
    node_id='sync_dataverse_workorders_to_toolkit',
    name='Dataverse Work Order Synchronization',
    node_type=NodeType.INGESTION,
    owner='dot-data-engineering@nyc.gov',
    source_system='dataverse',
    source_entity='msdyn_workorder',
    tags={
        'team': 'field_operations',
        'compliance_required': True,
        'sla_minutes': 5,
        'dataverse_sync': True,  # ← New tag
        'sync_direction': 'inbound'
    },
    lineage_metadata={
        'dataverse_environment': 'prod.crm.dynamics.com',
        'dataverse_entity': 'msdyn_workorder',
        'sync_method': 'webhook',
        'fallback_method': 'polling',
        'target_table': 'work_orders',
        'conflict_resolution': 'field_precedence_tier'
    }
)

# Outbound sync lineage
toolkit_to_dataverse_node = TransformationNode(
    node_id='sync_toolkit_status_to_dataverse',
    name='Toolkit Status → Dataverse Update',
    node_type=NodeType.SINK,
    owner='dot-data-engineering@nyc.gov',
    source_system='toolkit',
    target_system='dataverse',
    tags={
        'sync_direction': 'outbound',
        'fields_synced': ['status_code', 'completion_percentage', 'actual_cost'],
        'update_frequency': '5_minutes'
    }
)

# Lineage recording with audit trail
execution = lineage_persistence.record_execution(
    node=dataverse_sync_node,
    status='SUCCESS',
    records_processed=150,
    records_skipped=0,
    records_errored=0,
    lineage_context={
        'webhook_event_id': 'evt_12345abcde',
        'dataverse_timestamp': '2026-05-10T14:30:00Z',
        'sync_latency_ms': 1850,
        'conflict_count': 0
    }
)
```

---

### 3.3 Observability Integration

**All Dataverse sync operations emit structured observability signals**:

```python
# observability.py: DATAVERSE_SYNC metrics
from socrata_toolkit.observability import MetricsRegistry, OperationalLogger

metrics = MetricsRegistry()

# Counter: Dataverse webhook events received
metrics.counter(
    'dataverse_webhook_events_total',
    labels={'entity': 'workorder', 'action': 'create'},
    value=1
)

# Histogram: Sync latency (P50, P95, P99)
metrics.histogram(
    'dataverse_sync_latency_seconds',
    labels={'direction': 'inbound', 'entity': 'workorder'},
    value=1.85
)

# Gauge: Active webhook subscriptions
metrics.gauge(
    'dataverse_webhook_subscriptions_active',
    value=3  # work_order, permit, compliance webhooks

# Gauge: Reconciliation discrepancies detected
metrics.gauge(
    'dataverse_reconciliation_discrepancies',
    value=0
)

# Counter: Conflict resolution actions
metrics.counter(
    'dataverse_conflict_resolutions_total',
    labels={'conflict_type': 'field_precedence', 'resolution': 'dataverse_wins'},
    value=1
)

# Operational logging (JSON structured)
logger = OperationalLogger('dataverse_sync')
logger.log_operation({
    'operation': 'sync_work_order',
    'dataverse_id': 'evt_12345',
    'work_order_id': 'wo_54321',
    'status': 'success',
    'duration_seconds': 1.85,
    'records_affected': 1,
    'conflicts_detected': 0,
    'sync_direction': 'inbound',
    'timestamp': '2026-05-10T14:30:01Z'
})
```

---

### 3.4 API Governance & Authentication

**Dataverse integration uses OAuth 2.0 Service Principal with least-privilege scopes**:

```
AUTHENTICATION MODEL:

┌──────────────────────────────────────────────────┐
│         Azure AD (Identity Provider)              │
├──────────────────────────────────────────────────┤
│                                                   │
│  Service Principal: "nyc-dot-toolkit-sync"       │
│  Application ID: a1b2c3d4-e5f6-47g8-h9i0-j1k2l3m4 │
│  Client Secret: Stored in Azure Key Vault        │
│                                                   │
│  Assigned Application Role Permissions:          │
│  ✓ msdyn_workorder.Read                         │
│  ✓ msdyn_workorder.Update (status_only)         │
│  ✓ msdyn_permit.Read                            │
│  ✓ msdyn_compliance_record.Create (reports)     │
│  ✗ msdyn_workorder.Delete (FORBIDDEN)           │
│  ✗ msdyn_workorder.Create (FORBIDDEN)           │
│                                                   │
└──────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────┐
│   Dataverse Resource Owner Flow (Delegated)       │
├──────────────────────────────────────────────────┤
│                                                   │
│  User: analyst@nycdot.gov                        │
│  Role: "Field Operations Manager"                │
│  Token Lifespan: 1 hour (refresh token valid)    │
│                                                   │
│  Scopes: (Inherited from role + explicit)        │
│  • https://org.crm.dynamics.com/user            │
│  • offline_access (for refresh token)            │
│                                                   │
└──────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────┐
│      Toolkit Service Layer Authentication        │
├──────────────────────────────────────────────────┤
│                                                   │
│  Validate JWT token signature                    │
│  Check token expiration and scopes               │
│  Verify Principal ID matches Dataverse owner     │
│  Log access to audit trail                       │
│                                                   │
│  IF NOT AUTHORIZED → reject with 403 Forbidden  │
│                                                   │
└──────────────────────────────────────────────────┘
```

---

#### Implementation: Dataverse Client with OAuth2

```python
# socrata_toolkit/dataverse_integration.py

from azure.identity import ClientSecretCredential, DefaultAzureCredential
from microsoft.dynamics.dataverse import DataverseClient
from socrata_toolkit.observability import OperationalLogger

class DataverseOAuth2Client:
    """Authenticated Dataverse API client with OAuth 2.0 + RBAC."""
    
    def __init__(self, org_url: str, auth_type: str = 'service_principal'):
        """
        Args:
            org_url: Dataverse org URL (e.g., https://org.crm.dynamics.com)
            auth_type: 'service_principal' or 'user_delegated'
        """
        self.org_url = org_url
        self.logger = OperationalLogger(__name__)
        
        if auth_type == 'service_principal':
            # Load from Key Vault
            credential = ClientSecretCredential(
                tenant_id=os.getenv('AZURE_TENANT_ID'),
                client_id=os.getenv('DATAVERSE_CLIENT_ID'),
                client_secret=os.getenv('DATAVERSE_CLIENT_SECRET')
            )
        else:
            # User delegated (interactive)
            credential = DefaultAzureCredential()
        
        self.client = DataverseClient(org_url=org_url, credential=credential)
        self.logger.log_operation({
            'operation': 'auth_init',
            'auth_type': auth_type,
            'status': 'authenticated'
        })
    
    def fetch_work_orders(self, filter_query: str) -> list[dict]:
        """Fetch work orders with filter (READ only scope required)."""
        try:
            result = self.client.query(
                collection_name='msdyn_workorders',
                query_lambda=filter_query
            )
            self.logger.log_operation({
                'operation': 'fetch_work_orders',
                'records': len(result),
                'status': 'success'
            })
            return result
        except Exception as e:
            self.logger.log_error({
                'operation': 'fetch_work_orders',
                'error': str(e),
                'status': 'failed'
            })
            raise
    
    def update_work_order_status(self, workorder_id: str, new_status: str) -> bool:
        """Update work order status (RESTRICTED: status_only scope)."""
        allowed_fields = ['statusCode', 'msdyn_summary']  # Whitelist
        
        if 'statusCode' not in allowed_fields:
            raise PermissionError(f"Field not allowed: {new_status}")
        
        try:
            self.client.update(
                collection_name='msdyn_workorders',
                record_id=workorder_id,
                record={'statecode': self._map_status_to_dataverse(new_status)}
            )
            self.logger.log_operation({
                'operation': 'update_work_order_status',
                'workorder_id': workorder_id,
                'new_status': new_status,
                'status': 'success'
            })
            return True
        except Exception as e:
            self.logger.log_error({
                'operation': 'update_work_order_status',
                'error': str(e)
            })
            raise
    
    def _map_status_to_dataverse(self, toolkit_status: str) -> int:
        """Map toolkit status enum to Dataverse statecode."""
        mapping = {
            'ACTIVE': 0,
            'COMPLETED': 1,
            'BLOCKED': 2,
            'CANCELLED': 3
        }
        return mapping.get(toolkit_status, 0)
```

---

## 4. WEBHOOK & REAL-TIME EVENT HANDLING

### 4.1 Webhook Registration Workflow in Dataverse

```
STEP 1: REGISTER WEBHOOK SUBSCRIPTION IN DATAVERSE
───────────────────────────────────────────────────

Azure AD Service Principal
  ↓ (API Call with OAuth 2.0 token)
  
POST https://org.crm.dynamics.com/api/data/v9.2/serviceconfiguration/create

{
  "name": "nyc-dot-toolkit-workorder-sync",
  "description": "Sync work orders from Dataverse to Toolkit DB",
  "events": [
    "Create",
    "Update"
  ],
  "entities": [
    "msdyn_workorder",
    "msdyn_permit",
    "msdyn_compliance_record"
  ],
  "endpoint_url": "https://toolkit-api.nycdot.gov/webhooks/dataverse",
  "http_method": "POST",
  "authentication": {
    "auth_type": "api_key",
    "api_key_header": "X-Webhook-Auth-Token",
    "api_key_value": "${WEBHOOK_SECRET_FROM_KEY_VAULT}"
  },
  "retry_policy": {
    "max_retries": 5,
    "initial_wait_minutes": 1,
    "backoff_multiplier": 2
  },
  "timeout_seconds": 30
}

↓ Response:
{
  "webhookid": "12345678-90ab-cdef-1234-567890abcdef",
  "name": "nyc-dot-toolkit-workorder-sync",
  "status": "ACTIVE",
  "created_timestamp": "2026-05-10T14:35:00Z"
}


STEP 2: WEBHOOK ACTIVATION CONFIRMATION
────────────────────────────────────────

Dataverse validates endpoint:
  → Sends test event to https://toolkit-api.nycdot.gov/webhooks/dataverse
  → Expects 200 OK response within 30 seconds
  
Toolkit webhook receiver responds:
  ✓ VALIDATES X-Webhook-Auth-Token header
  ✓ LOGS webhook registration event
  ✓ RETURNS 200 with acknowledgment


STEP 3: WEBHOOK LIFECYCLE MANAGEMENT
─────────────────────────────────────

Active Monitoring:
  • Weekly health check: test ping to webhook endpoint
  • Alert if endpoint unreachable for >5 minutes
  • Auto-disable webhook if fails 10 consecutive health checks
  • Audit log all webhook state changes


Webhook Deactivation (manual or auto):
  DELETE https://org.crm.dynamics.com/api/data/v9.2/webhooks(12345678-...)
  
  Falls back to polling pattern (15-minute cycle)
  Backoff throttles polling if webhook inactive
```

---

### 4.2 Event Types & Subscription Mapping

```
WEBHOOK EVENT TYPE SUBSCRIPTIONS:

┌─────────────────────────────────────────────────────────────────────┐
│                    DATAVERSE ENTITY: msdyn_workorder                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Event: Create (New Work Order Assigned)                            │
│  ────────────────────────────────────────────────────────────────   │
│  Payload: { workorderid, name, estimatedstartedon, workordertype }  │
│  Handler: fetch_workorder_from_dataverse() → INSERT work_orders     │
│  SLA: <2 minutes to appear in toolkit database                      │
│  Error Path: → DLQ → Manual review queue                            │
│                                                                       │
│  Event: Update (Status/Priority Change)                             │
│  ────────────────────────────────────────────────────────────────   │
│  Payload: { workorderid, statecode, msdyn_priority, ownerid }       │
│  Handler: sync_workorder_update() → UPDATE work_orders              │
│  SLA: <5 minutes to reflect status change                           │
│  Conflict Detection: Check if toolkit has local updates (DLQ)       │
│                                                                       │
│  Event: Delete (Work Order Cancelled - RARE)                        │
│  ────────────────────────────────────────────────────────────────   │
│  Payload: { workorderid, deletedreason }                            │
│  Handler: mark_workorder_cancelled() → UPDATE status_code='CANCELLED'│
│  SLA: <10 minutes (low priority, audit trail required)              │
│  Safety: Soft-delete only (preserve audit trail)                    │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                   DATAVERSE ENTITY: msdyn_permit                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Event: Update (Permit Approved/Expired/Revoked)                    │
│  ────────────────────────────────────────────────────────────────   │
│  Payload: { permitid, statecode, expirationdate, approvercomments }│
│  Handler: sync_permit_status() → UPDATE work_orders.permit_status   │
│  SLA: <1 minute (CRITICAL: compliance gate)                         │
│  Safety Gate: Generate alert if work active + permit expired        │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│              DATAVERSE ENTITY: msdyn_compliance_record               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Event: Create (New Compliance Audit Started)                       │
│  ────────────────────────────────────────────────────────────────   │
│  Payload: { compliancerecordid, workorderid, checktype, status }    │
│  Handler: create_compliance_tracking() → INSERT compliance_reporting │
│  SLA: <5 minutes                                                     │
│  Purpose: Audit trail + compliance gate enforcement                 │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 4.3 Retry Logic & Exponential Backoff

```
WEBHOOK DELIVERY RETRY STRATEGY:

┌──────────────────────────────────────────────────────────────────────┐
│                      DATAVERSE → TOOLKIT WEBHOOK                     │
├──────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ATTEMPT 1: Immediate (T+0)                                          │
│  ├─ POST /webhooks/dataverse with event payload                     │
│  ├─ Timeout: 30 seconds                                              │
│  └─ Response: 200 OK → Success (log & finish)                       │
│               4xx (400, 403, 404) → Permanent Error (DLQ)           │
│               5xx, timeout → Retry with backoff                     │
│                                                                        │
│  ATTEMPT 2: After 1 minute backoff (T+60s)                          │
│  ├─ Retry condition: Previous attempt returned 5xx or timeout        │
│  ├─ Include retry_count=1 in headers (idempotency tracking)         │
│  └─ Response: 200 OK → Success                                      │
│               5xx, timeout → Continue to Attempt 3                  │
│               4xx → DLQ (don't retry)                               │
│                                                                        │
│  ATTEMPT 3: After 2 minute backoff (T+180s)                         │
│  ├─ retry_count=2                                                    │
│  └─ Response: 200 OK → Success                                      │
│               Fail → Continue to Attempt 4                          │
│                                                                        │
│  ATTEMPT 4: After 4 minute backoff (T+420s)                         │
│  ├─ retry_count=3                                                    │
│  └─ Response: 200 OK → Success                                      │
│               Fail → Continue to Attempt 5                          │
│                                                                        │
│  ATTEMPT 5: After 8 minute backoff (T+900s)                         │
│  ├─ retry_count=4                                                    │
│  └─ Response: 200 OK → Success                                      │
│               Fail → DEAD-LETTER QUEUE (final failure)              │
│                                                                        │
│  BACKOFF FORMULA: wait_seconds = min(2^retry_count * 60, 3600)      │
│  (Exponential backoff capped at 1 hour max wait between retries)    │
│                                                                        │
└──────────────────────────────────────────────────────────────────────┘


BACKOFF TIMING CHART:
┌─────────┬──────────────┬──────────────┬──────────────────┐
│ Attempt │ Wait Period  │ Cumulative   │ Max Total Time   │
├─────────┼──────────────┼──────────────┼──────────────────┤
│    1    │ Immediate    │ 0 seconds    │ 30 seconds       │
│    2    │ 1 minute     │ 1 minute     │ 1m 30s           │
│    3    │ 2 minutes    │ 3 minutes    │ 3m 30s           │
│    4    │ 4 minutes    │ 7 minutes    │ 7m 30s           │
│    5    │ 8 minutes    │ 15 minutes   │ 15m 30s          │
│  FAIL   │ → DLQ        │              │                  │
└─────────┴──────────────┴──────────────┴──────────────────┘
```

---

### 4.4 Dead-Letter Queue Pattern

```python
# socrata_toolkit/dataverse_webhook_handler.py

from datetime import datetime, timedelta
import json
import logging

class WebhookDeadLetterQueue:
    """Handles failed webhook events with audit trail."""
    
    def __init__(self, db_pool, logger=None):
        self.db = db_pool
        self.logger = logger or logging.getLogger(__name__)
    
    def enqueue_failed_event(self, 
                             event_id: str,
                             event_payload: dict,
                             error_message: str,
                             attempt_count: int,
                             max_retries: int = 5):
        """
        Store failed event in DLQ for manual review.
        
        Args:
            event_id: Unique webhook event ID from Dataverse
            event_payload: Complete event payload
            error_message: Human-readable error
            attempt_count: How many retries failed
        """
        dlq_record = {
            'event_id': event_id,
            'event_type': event_payload.get('event_type'),
            'entity_type': event_payload.get('entity_type'),
            'payload': json.dumps(event_payload),
            'error_message': error_message,
            'attempt_count': attempt_count,
            'max_retries': max_retries,
            'failed_at': datetime.utcnow(),
            'review_status': 'PENDING',  # PENDING, IN_REVIEW, RESOLVED, ESCALATED
            'resolver_id': None,
            'resolution_notes': None
        }
        
        # Insert into DLQ table
        query = """
        INSERT INTO webhook_dlq 
        (event_id, event_type, entity_type, payload, error_message, 
         attempt_count, max_retries, failed_at, review_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        self.db.execute(query, (
            dlq_record['event_id'],
            dlq_record['event_type'],
            dlq_record['entity_type'],
            dlq_record['payload'],
            dlq_record['error_message'],
            dlq_record['attempt_count'],
            dlq_record['max_retries'],
            dlq_record['failed_at'],
            dlq_record['review_status']
        ))
        
        # Generate alert for operations team
        self.logger.critical(
            f"Webhook event {event_id} failed after {attempt_count} retries. "
            f"Added to DLQ for manual review. Error: {error_message}"
        )
        
        # Send to Slack/email for urgent attention
        self._send_dlq_alert(dlq_record)
    
    def resolve_dlq_event(self, 
                          event_id: str, 
                          resolution: str,
                          resolver_id: str,
                          notes: str):
        """
        Mark DLQ event as resolved and retry if appropriate.
        
        Args:
            event_id: Event ID in DLQ
            resolution: 'MANUAL_SYNC', 'ESCALATE', 'SKIP', 'RETRY'
            resolver_id: User who resolved
            notes: Resolution details
        """
        if resolution == 'RETRY':
            # Fetch event payload and retry
            event = self.db.query(
                'SELECT payload FROM webhook_dlq WHERE event_id = %s',
                (event_id,)
            )[0]
            
            payload = json.loads(event['payload'])
            # Attempt 1 retry from DLQ
            self._process_webhook_event(payload, from_dlq=True)
        
        elif resolution == 'MANUAL_SYNC':
            # Operator manually synced in Dataverse or Toolkit
            pass
        
        # Mark as resolved
        self.db.execute("""
            UPDATE webhook_dlq
            SET review_status = %s, resolver_id = %s, 
                resolution_notes = %s, resolved_at = NOW()
            WHERE event_id = %s
        """, ('RESOLVED', resolver_id, notes, event_id))
        
        self.logger.info(f"DLQ event {event_id} resolved via {resolution}")
    
    def get_dlq_dashboard(self) -> dict:
        """Return DLQ status for monitoring dashboard."""
        pending = self.db.query(
            'SELECT COUNT(*) FROM webhook_dlq WHERE review_status = %s',
            ('PENDING',)
        )[0]['count']
        
        return {
            'pending_reviews': pending,
            'alert_level': 'CRITICAL' if pending > 5 else 'WARNING' if pending > 0 else 'OK'
        }
```

---

### 4.5 Idempotency Key Management

```python
# socrata_toolkit/dataverse_webhook_handler.py

class WebhookIdempotencyManager:
    """Ensures webhook events processed exactly-once despite retries."""
    
    def __init__(self, redis_client, ttl_hours: int = 24):
        """
        Args:
            redis_client: Redis connection for fast idempotency checks
            ttl_hours: How long to keep idempotency keys (prevents memory bloat)
        """
        self.redis = redis_client
        self.ttl_seconds = ttl_hours * 3600
    
    def get_idempotency_key(self, event_payload: dict) -> str:
        """
        Generate deterministic idempotency key from event.
        
        Key = SHA256(dataverse_event_id + entity_id + timestamp + action)
        
        Guarantees: Same event → same key, different events → different keys
        """
        import hashlib
        
        key_components = [
            event_payload.get('event_id', ''),
            event_payload.get('entity_id', ''),
            event_payload.get('timestamp', ''),
            event_payload.get('action', ''),  # 'create', 'update', 'delete'
        ]
        
        key_string = '|'.join(key_components)
        idempotency_key = f"dvx:{hashlib.sha256(key_string.encode()).hexdigest()}"
        
        return idempotency_key
    
    def check_and_mark_processed(self, idempotency_key: str) -> bool:
        """
        Check if event already processed. If not, mark it.
        
        Returns:
            True if event is NEW (first time seeing it)
            False if event already processed (duplicate/retry)
        """
        # Atomic operation in Redis
        result = self.redis.set(
            idempotency_key,
            value='processed',
            ex=self.ttl_seconds,
            nx=True  # Only set if key doesn't exist (nx = "not exists")
        )
        
        return result is not None  # True = set succeeded (new key), False = already existed
    
    def process_webhook_with_idempotency(self, event_payload: dict) -> dict:
        """
        Process webhook event with idempotency protection.
        
        Returns:
            {
                'status': 'processed' | 'duplicate',
                'event_id': event_payload.event_id,
                'result': <operation_result> or <cached_result>
            }
        """
        idempotency_key = self.get_idempotency_key(event_payload)
        
        if not self.check_and_mark_processed(idempotency_key):
            # Duplicate detected - return previous result from cache
            cached_result = self.redis.get(f'{idempotency_key}:result')
            return {
                'status': 'duplicate',
                'event_id': event_payload['event_id'],
                'result': json.loads(cached_result) if cached_result else None,
                'message': 'Event already processed'
            }
        
        # NEW EVENT - process it
        try:
            result = self._do_webhook_processing(event_payload)
            
            # Cache result for future retries
            self.redis.set(
                f'{idempotency_key}:result',
                json.dumps(result),
                ex=self.ttl_seconds
            )
            
            return {
                'status': 'processed',
                'event_id': event_payload['event_id'],
                'result': result
            }
        except Exception as e:
            # Log error but don't cache (allow retry)
            return {
                'status': 'error',
                'event_id': event_payload['event_id'],
                'error': str(e)
            }
    
    def _do_webhook_processing(self, event_payload: dict) -> dict:
        """
        Actual business logic for processing webhook.
        Can safely be called multiple times (idempotent operations).
        """
        action = event_payload.get('action')
        entity_type = event_payload.get('entity_type')
        
        if action == 'create' and entity_type == 'msdyn_workorder':
            return self._sync_create_work_order(event_payload)
        elif action == 'update' and entity_type == 'msdyn_workorder':
            return self._sync_update_work_order(event_payload)
        # ... other handlers
```

---

## 5. DATA QUALITY & VALIDATION

### 5.1 Field-Level Validation Mapping

```sql
-- validation_rules.sql: Dataverse → Toolkit Field Validation

CREATE TABLE dataverse_field_validation_rules (
  rule_id SERIAL PRIMARY KEY,
  source_entity VARCHAR(100),
  source_field VARCHAR(100),
  target_table VARCHAR(100),
  target_column VARCHAR(100),
  
  validation_type VARCHAR(50),  -- 'required', 'enum', 'range', 'regex', 'custom'
  validation_config JSONB,       -- Config specific to validation type
  
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(source_entity, source_field)
);

-- EXAMPLES:

-- Rule 1: Work Order ID (required, UUID)
INSERT INTO dataverse_field_validation_rules VALUES
(1, 'msdyn_workorder', 'msdyn_workorderid', 'work_orders', 'dataverse_id',
 'required', '{"type": "uuid"}', TRUE, NOW());

-- Rule 2: Status (enum - restricted values)
INSERT INTO dataverse_field_validation_rules VALUES
(2, 'msdyn_workorder', 'statecode', 'work_orders', 'status_code',
 'enum', '{"allowed_values": ["0", "1", "2", "3"], "map": {"0":"ACTIVE","1":"COMPLETED","2":"BLOCKED","3":"CANCELLED"}}', TRUE, NOW());

-- Rule 3: Planned Start Date (must be ≥ TODAY)
INSERT INTO dataverse_field_validation_rules VALUES
(3, 'msdyn_workorder', 'msdyn_estimatedstartedon', 'work_orders', 'planned_start_date',
 'custom', '{"check": "value >= TODAY()", "error": "Start date cannot be in past"}', TRUE, NOW());

-- Rule 4: Priority (range 1-5)
INSERT INTO dataverse_field_validation_rules VALUES
(4, 'msdyn_workorder', 'msdyn_priority', 'work_orders', 'priority_level',
 'range', '{"min": 1, "max": 5, "type": "integer"}', TRUE, NOW());

-- Rule 5: Description (string length, non-empty)
INSERT INTO dataverse_field_validation_rules VALUES
(5, 'msdyn_workorder', 'msdyn_name', 'work_orders', 'description',
 'custom', '{"check": "LENGTH(value) > 0 AND LENGTH(value) <= 500", "error": "Description must be 1-500 chars"}', TRUE, NOW());

-- Rule 6: Linear Feet (positive decimal, required for repair jobs)
INSERT INTO dataverse_field_validation_rules VALUES
(6, 'repair_job', 'linear_feet', 'repair_jobs', 'linear_feet',
 'range', '{"min": 0.01, "max": 999999.99, "type": "decimal"}', TRUE, NOW());
```

---

### 5.2 Referential Integrity Constraints

```sql
-- Ensures Dataverse IDs resolve to actual entities in both systems

-- FK: work_orders → dataverse_entities (Dataverse source of truth)
ALTER TABLE work_orders
ADD CONSTRAINT fk_work_orders_dataverse_entity
FOREIGN KEY (dataverse_id) REFERENCES dataverse_entities(id)
ON DELETE RESTRICT
ON UPDATE CASCADE;

-- FK: repair_jobs → work_orders (parent link)
ALTER TABLE repair_jobs
ADD CONSTRAINT fk_repair_jobs_work_order
FOREIGN KEY (work_order_id) REFERENCES work_orders(id)
ON DELETE CASCADE
ON UPDATE CASCADE;

-- FK: contractor_assignments → work_orders
ALTER TABLE contractor_assignments
ADD CONSTRAINT fk_contractor_assignments_work_order
FOREIGN KEY (work_order_id) REFERENCES work_orders(id)
ON DELETE CASCADE
ON UPDATE CASCADE;

-- FK: progress_tracking → work_orders
ALTER TABLE progress_tracking
ADD CONSTRAINT fk_progress_tracking_work_order
FOREIGN KEY (work_order_id) REFERENCES work_orders(id)
ON DELETE CASCADE
ON UPDATE CASCADE;

-- FK: compliance_reporting → work_orders
ALTER TABLE compliance_reporting
ADD CONSTRAINT fk_compliance_reporting_work_order
FOREIGN KEY (work_order_id) REFERENCES work_orders(id)
ON DELETE CASCADE
ON UPDATE CASCADE;

-- Check constraint: Permit validity window
ALTER TABLE work_orders
ADD CONSTRAINT chk_work_order_dates
CHECK (
  planned_start_date IS NULL OR 
  planned_completion_date IS NULL OR
  planned_completion_date >= planned_start_date
);

-- Check constraint: Material repair type compatibility
ALTER TABLE repair_jobs
ADD CONSTRAINT chk_repair_material_compatibility
CHECK (
  EXISTS (
    SELECT 1 FROM material_standards.defects_by_material
    WHERE material_id = repair_jobs.material_type
    AND defect_id = repair_jobs.repair_type
  )
);

-- Check constraint: Progress tracking completion gates
ALTER TABLE progress_tracking
ADD CONSTRAINT chk_completion_gates
CHECK (
  (completion_percentage = 100 AND ada_compliant = TRUE AND hazard_resolved = TRUE)
  OR (completion_percentage < 100)
);
```

---

### 5.3 Timestamp Synchronization Approach

```python
# socrata_toolkit/dataverse_timestamp_sync.py

from datetime import datetime, timezone
import logging

class TimestampSynchronization:
    """
    Ensures clock skew between Dataverse and Toolkit doesn't cause sync issues.
    
    Problem: Dataverse server time ≠ Toolkit server time
    → Can cause "future" updates to appear as retroactive
    → Breaks SCD Type 2 effective dating
    → Breaks conflict resolution (which-is-newer)
    """
    
    def __init__(self, db_pool):
        self.db = db_pool
        self.logger = logging.getLogger(__name__)
    
    def calibrate_clock_offset(self) -> int:
        """
        Determine offset between Dataverse time and Toolkit time.
        
        Returns:
            offset_seconds: Toolkit time - Dataverse time
            (if Toolkit is 30s ahead, offset = +30)
        """
        # Fetch current timestamp from Dataverse
        from socrata_toolkit.dataverse_integration import DataverseOAuth2Client
        
        dv_client = DataverseOAuth2Client(os.getenv('DATAVERSE_ORG_URL'))
        
        # Dataverse returns modifiedon timestamp in API
        # We assume this is the Dataverse server time
        dv_response = dv_client.client.query(
            collection_name='systemusers',
            query_lambda='$select=modifiedon&$top=1'
        )
        
        if not dv_response:
            self.logger.error("Failed to calibrate clock offset")
            return 0
        
        dataverse_time = dv_response[0]['modifiedon']
        toolkit_time = datetime.now(timezone.utc)
        
        offset = (toolkit_time - dataverse_time).total_seconds()
        
        self.logger.info(f"Clock offset calibrated: {offset} seconds")
        
        # Store for later use
        self.db.execute("""
            INSERT INTO system_calibration (metric_name, metric_value, measured_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (metric_name) DO UPDATE SET metric_value = EXCLUDED.metric_value
        """, ('dataverse_clock_offset_seconds', offset))
        
        return int(offset)
    
    def normalize_dataverse_timestamp(self, dv_timestamp: datetime) -> datetime:
        """
        Adjust Dataverse timestamp to Toolkit clock.
        
        Use this when comparing timestamps across systems.
        """
        offset_seconds = self._get_stored_clock_offset()
        return dv_timestamp + timedelta(seconds=offset_seconds)
    
    def _get_stored_clock_offset(self) -> int:
        """Fetch most recent clock offset calibration."""
        result = self.db.query("""
            SELECT metric_value FROM system_calibration
            WHERE metric_name = 'dataverse_clock_offset_seconds'
            ORDER BY measured_at DESC
            LIMIT 1
        """)
        
        if result:
            return int(result[0]['metric_value'])
        return 0  # No calibration yet, assume 0 offset
    
    def get_conflict_winner(self, 
                            dataverse_update_time: datetime,
                            toolkit_update_time: datetime) -> str:
        """
        Determine which system has the more recent change.
        
        Returns: 'DATAVERSE' | 'TOOLKIT' | 'SIMULTANEOUS'
        """
        # Normalize Dataverse time to Toolkit clock
        dv_normalized = self.normalize_dataverse_timestamp(dataverse_update_time)
        
        # Compare with 5-second fudge factor for simultaneous updates
        time_diff = abs((dv_normalized - toolkit_update_time).total_seconds())
        
        if time_diff <= 5:
            return 'SIMULTANEOUS'
        elif dv_normalized > toolkit_update_time:
            return 'DATAVERSE'
        else:
            return 'TOOLKIT'
```

---

### 5.4 Data Quality Metrics to Track

```python
# metrics_definitions.py: Dataverse Sync Quality Metrics

from socrata_toolkit.metrics import MetricsRegistry

metrics = MetricsRegistry()

# 1. SYNC FRESHNESS
metrics.gauge(
    'dataverse_sync_latency_seconds_p95',
    labels={'entity': 'workorder'},
    description='P95 latency from Dataverse event to toolkit database'
)

# 2. COMPLETENESS (% of Dataverse work orders synced)
metrics.gauge(
    'dataverse_workorder_completeness_percent',
    description='% of active Dataverse work orders present in toolkit'
)

# 3. CONSISTENCY (conflicts detected)
metrics.counter(
    'dataverse_sync_conflicts_total',
    labels={'conflict_type': ['field_precedence', 'timestamp', 'referential_integrity']},
    description='Number of sync conflicts detected and resolved'
)

# 4. VALIDITY (validation rule failures)
metrics.counter(
    'dataverse_field_validation_failures_total',
    labels={'entity': 'workorder', 'field': 'status_code'},
    description='Fields that failed validation during sync'
)

# 5. ERROR RATE (webhook failures)
metrics.gauge(
    'dataverse_webhook_error_rate_percent',
    description='% of webhook events that failed to process'
)

# 6. DUPLICATE DETECTION
metrics.counter(
    'dataverse_duplicate_events_detected_total',
    description='Duplicate webhook events caught by idempotency manager'
)

# 7. DLQ SIZE
metrics.gauge(
    'webhook_dlq_pending_events',
    description='Events in dead-letter queue awaiting manual review'
)

# 8. RECONCILIATION DISCREPANCIES
metrics.gauge(
    'dataverse_reconciliation_discrepancies_per_1000',
    description='Discrepancies found per 1000 records during nightly reconciliation'
)
```

---

## 6. SECURITY & COMPLIANCE

### 6.1 OAuth 2.0 Authentication Flow with Dataverse

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  OAUTH 2.0 SERVICE PRINCIPAL FLOW                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  STEP 1: ACQUIRE TOKEN                                                  │
│  ─────────────────────                                                  │
│                                                                           │
│  Toolkit Service (running in AKS pod)                                   │
│    │ (environment: DATAVERSE_CLIENT_ID, DATAVERSE_CLIENT_SECRET)        │
│    │                                                                     │
│    ├─→ POST https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token
│    │   Body:                                                            │
│    │   {                                                                │
│    │     "client_id": "a1b2c3d4-e5f6-47g8-h9i0-j1k2l3m4",             │
│    │     "client_secret": "<secret_from_key_vault>",                   │
│    │     "scope": "https://org.crm.dynamics.com/.default",             │
│    │     "grant_type": "client_credentials"                            │
│    │   }                                                                │
│    │                                                                     │
│    ├─ Response (expires in 3600 seconds = 1 hour):                     │
│    │  {                                                                 │
│    │    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",                 │
│    │    "token_type": "Bearer",                                        │
│    │    "expires_in": 3600                                             │
│    │  }                                                                 │
│    │                                                                     │
│    └─→ Cache token in Redis (TTL: 55 minutes, auto-refresh at 45 min) │
│                                                                           │
│  STEP 2: CALL DATAVERSE API                                            │
│  ────────────────────────────                                          │
│                                                                           │
│    POST https://org.crm.dynamics.com/api/data/v9.2/msdyn_workorders   │
│    Headers:                                                             │
│      Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...                  │
│      Content-Type: application/json                                    │
│    Body: { ... work order data ... }                                   │
│                                                                           │
│    Response:                                                            │
│      ✓ 200 OK → Success (toolkit processes data)                       │
│      ✗ 401 Unauthorized → Token expired (refresh and retry)            │
│      ✗ 403 Forbidden → Scope insufficient (escalate)                   │
│      ✗ 5xx → Transient failure (retry with backoff)                    │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 6.2 Service Principal vs User-Delegated Authentication

| Aspect | Service Principal | User-Delegated | Recommendation |
|--------|-------------------|---|---|
| **Use Case** | Automated sync (webhooks, batch) | User-initiated actions | Use **Service Principal** for Dataverse sync |
| **Token Lifetime** | 1 hour (configurable) | 1 hour + refresh token | Shorter lifecycle, lower risk |
| **Permissions** | Explicit role-based (RBAC) | User's inherited permissions | Least-privilege: Service Principal with minimal scopes |
| **Audit Trail** | Service Principal name in audit log | User email in audit log | Service Principal for "system" actions, user context for "analyst" changes |
| **Secret Management** | Stored in Azure Key Vault | OAuth code flow (no secrets) | Key Vault with rotation policy |
| **MFA Requirement** | None (application can bypass) | Yes, if enabled for user | Not applicable to SP |

**Decision**: Use **Service Principal** for Dataverse ↔ Toolkit sync, with explicit scopes:
```
✓ msdyn_workorder.Read (fetch new/updated work orders)
✓ msdyn_workorder.Update (status_code, completion % only)
✓ msdyn_permit.Read (check permit validity)
✓ msdyn_compliance_record.Create (log compliance checks)
✗ msdyn_workorder.Create (Dataverse only, forbidden)
✗ msdyn_workorder.Delete (Dataverse only, forbidden)
```

---

### 6.3 Data Encryption (In Transit & At Rest)

```
ENCRYPTION STRATEGY:

1. IN TRANSIT (Dataverse ↔ Toolkit)
   ─────────────────────────────────
   
   All HTTP calls use TLS 1.2+ (enforced):
   
   POST /webhooks/dataverse HTTP/1.1
   ├─ HTTPS (TLS 1.2+) ✓ Encrypted
   ├─ Certificate pinning: Verify Microsoft certificate chain
   ├─ Hostname verification: Enabled
   └─ HSTS: Strict-Transport-Security header enforced
   
   Webhook payload encryption (additional layer):
   ┌──────────────────────────┐
   │ Raw webhook event        │
   │ { work_order_id, ... }   │
   └────────────┬─────────────┘
               │
               ├─ AES-256-GCM encryption
               ├─ Key: Stored in Azure Key Vault
               ├─ IV: Random per request
               └─ Authentication tag: HMAC-SHA256
   
   POST /webhooks/dataverse
   {
     "encrypted_payload": "a7b3c8d2e1...",
     "iv": "f0e1d2c3b4a5...",
     "auth_tag": "9z8y7x6w5v...",
     "key_version": "2026-05"
   }
   
   ↓ Toolkit decrypts with Key Vault key
   
   ┌──────────────────────────┐
   │ Decrypted work order     │
   │ { work_order_id, ... }   │
   └──────────────────────────┘


2. AT REST (PostgreSQL Database)
   ──────────────────────────────
   
   Sensitive fields encrypted before storage:
   
   work_orders table:
   ├─ dataverse_id: PLAINTEXT (needed for lookups)
   ├─ description: ENCRYPTED (PII potential)
   ├─ contractor_notes: ENCRYPTED (confidential)
   ├─ compliance_details: ENCRYPTED (audit-sensitive)
   └─ api_credentials: ENCRYPTED (OAuth tokens)
   
   Encryption implementation (pgcrypto extension):
   
   ALTER TABLE work_orders
   ALTER COLUMN contractor_notes
   SET DATA TYPE bytea USING pgp_sym_encrypt(
       contractor_notes::text, 
       current_setting('app.encryption_key')
   );
   
   Query decryption (requires key from app):
   
   SELECT 
     dataverse_id,
     pgp_sym_decrypt(contractor_notes, current_setting('app.encryption_key'))::text AS notes
   FROM work_orders
   WHERE dataverse_id = 'wo_12345';
   
   Key Management:
   ├─ Master key stored in Azure Key Vault (HSM-backed)
   ├─ Per-session key derived via PBKDF2
   ├─ Key rotation every 90 days (automated)
   └─ Separate keys for prod/staging/dev


3. COLUMN-LEVEL ENCRYPTION (Sensitive PII)
   ────────────────────────────────────────
   
   Fields to encrypt:
   ├─ contractor contact info (email, phone)
   ├─ supervisor approval comments
   ├─ incident details (hazard descriptions)
   └─ audit trail notes
   
   Implementation:
   
   CREATE TABLE work_orders (
     id SERIAL PRIMARY KEY,
     dataverse_id UUID,
     description TEXT,
     -- Encrypted field with key version tracking
     contractor_email TEXT ENCRYPTED WITH KEY 'dataverse_sync_key_v2',
     -- Reference token for queries without decryption
     contractor_email_hash BYTEA GENERATED ALWAYS AS (
       sha256(contractor_email::bytea)
     ) STORED,
     -- Audit trail (immutable)
     created_at TIMESTAMP,
     dataverse_updated_at TIMESTAMP
   );
   
   Index on hash for efficient lookups:
   CREATE INDEX idx_contractor_email_hash 
   ON work_orders(contractor_email_hash);
```

---

### 6.4 GDPR/CCPA Compliance for NYC DOT

```
REGULATORY COMPLIANCE FRAMEWORK:

┌─────────────────────────────────────────────────────────────────────┐
│               GDPR & CCPA COMPLIANCE REQUIREMENTS                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. DATA SUBJECT RIGHTS (Art. 12-22 GDPR, Cal. Civil Code §1798)    │
│  ───────────────────────────────────────────────────────────────    │
│                                                                      │
│  Right to Access:                                                   │
│    • Contractor → Can request all their work orders, assignments    │
│    • IMPLEMENT: /api/v1/my-work-orders endpoint (auth required)     │
│    • Response: All personally-identifiable records in 30 days       │
│                                                                      │
│  Right to Erasure ("Right to be Forgotten"):                        │
│    • Contractor → Request deletion of personal data after contract  │
│    • CONSTRAINT: Audit trail must be retained for 7 years (DOT law) │
│    • IMPLEMENT: Anonymize instead of delete (replace name w/ hash)  │
│                                                                      │
│  Right to Portability:                                              │
│    • Contractor → Export their data in machine-readable format      │
│    • IMPLEMENT: JSON export endpoint, structured format             │
│                                                                      │
│  Right to Rectification:                                            │
│    • Contractor → Correct inaccurate personal data                  │
│    • IMPLEMENT: SCD Type 2 (keep history, mark as superseded)       │
│                                                                      │
│                                                                      │
│  2. DATA PROTECTION IMPACT ASSESSMENT (DPIA)                        │
│  ──────────────────────────────────────────────────────────────     │
│                                                                      │
│  Dataverse Sync DPIA Required:                                      │
│    ✓ Process sensitive data (contractor info, work locations)       │
│    ✓ Large-scale processing (1000s of work orders/month)            │
│    ✓ Systematic monitoring (webhooks, audit logs)                   │
│    ✓ Automated decision-making potential (compliance gates)         │
│                                                                      │
│  Risk Mitigation:                                                   │
│    • Data minimization: Only sync fields actually needed            │
│    • Pseudonymization: Hash contractor IDs for analytics            │
│    • Encryption: TLS + database encryption at rest                  │
│    • Access control: RBAC with audit logging                        │
│    • Retention: Delete non-essential data after 90 days             │
│                                                                      │
│                                                                      │
│  3. LEGITIMATE PROCESSING BASIS                                     │
│  ────────────────────────────────────────────────────────────────   │
│                                                                      │
│  Dataverse Sync Legal Basis:                                        │
│    • Contract Performance: Work order creation required for service │
│    • Legal Obligation: NYC DOT compliance, ADA law, permit rules    │
│    • Public Task: Sidewalk repair is NYC government function        │
│    • Legitimate Interests: Safety, asset management, efficiency     │
│                                                                      │
│  Consent NOT required (covered by above)                            │
│                                                                      │
│                                                                      │
│  4. DATA RETENTION POLICY                                           │
│  ────────────────────────────────────────────────────────────────   │
│                                                                      │
│  Dataverse Work Orders:                                             │
│    • Active: Keep indefinitely (operational need)                   │
│    • Completed (< 7 years): Retain for audit                        │
│    • Completed (> 7 years): Archive or anonymize                    │
│                                                                      │
│  Contractor Assignment Records:                                     │
│    • Active contractor: Keep while employed + 3 years               │
│    • Terminated contractor: Delete PII after 7 years                │
│                                                                      │
│  Webhook Audit Logs:                                                │
│    • Keep for compliance: 7 years (NYC Finance Law)                 │
│    • Compliance details: 10 years (potential litigation)            │
│                                                                      │
│                                                                      │
│  5. CCPA DISCLOSURES (California users)                             │
│  ────────────────────────────────────────────────────────────────   │
│                                                                      │
│  Privacy Notice must disclose:                                      │
│    • Categories of data collected: Work order, contractor info      │
│    • Sources: Dataverse, field inputs, GIS systems                  │
│    • Business purpose: Sidewalk repair management, compliance       │
│    • Data sharing: Power BI (internal), no 3rd-party sales          │
│    • Retention: Per policy above                                    │
│    • Consumer rights: Access, delete (subject to legal holds)       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 6.5 Audit Trail Requirements

```sql
-- audit_trail.sql: Complete Dataverse sync audit log

CREATE TABLE dataverse_sync_audit (
  audit_id BIGSERIAL PRIMARY KEY,
  
  -- Event Identification
  event_id UUID NOT NULL,
  event_type VARCHAR(50) NOT NULL,  -- 'create', 'update', 'delete', 'sync', 'conflict', 'dlq'
  entity_type VARCHAR(100) NOT NULL,  -- 'msdyn_workorder', 'msdyn_permit', etc
  
  -- Source System
  source_dataverse_id UUID,
  source_timestamp TIMESTAMP NOT NULL,
  source_user_id VARCHAR(100),  -- Dataverse user who made change
  
  -- Target System
  target_table VARCHAR(100),
  target_record_id INTEGER,
  
  -- Operation Details
  operation VARCHAR(100),  -- 'INSERT', 'UPDATE', 'DELETE_SOFT', 'CONFLICT_RESOLVED'
  operation_status VARCHAR(20),  -- 'SUCCESS', 'FAILED', 'RETRIED', 'DLQ'
  old_values JSONB,  -- Before snapshot
  new_values JSONB,  -- After snapshot
  
  -- Sync Metadata
  sync_latency_milliseconds INTEGER,
  retry_count INTEGER DEFAULT 0,
  idempotency_key VARCHAR(256),
  
  -- Conflict Resolution (if applicable)
  conflict_detected BOOLEAN DEFAULT FALSE,
  conflict_type VARCHAR(50),  -- 'field_precedence', 'timestamp', 'referential_integrity'
  resolution_applied VARCHAR(100),  -- 'DATAVERSE_WINS', 'TOOLKIT_WINS', 'MANUAL_REVIEW'
  resolution_reason TEXT,
  
  -- Compliance
  gdpr_data_subject_id VARCHAR(256),  -- Contractor ID (encrypted)
  contains_sensitive_data BOOLEAN DEFAULT FALSE,
  encryption_key_version VARCHAR(20),
  
  -- Logging
  recorded_by VARCHAR(100),  -- 'webhook_handler', 'batch_sync', 'manual_reconciliation'
  recorded_at TIMESTAMP DEFAULT NOW(),
  
  CONSTRAINT audit_timestamp_immutable CHECK (recorded_at >= source_timestamp)
);

-- Index for audit retrieval (date range + entity type)
CREATE INDEX idx_audit_by_timestamp_entity
ON dataverse_sync_audit(recorded_at DESC, entity_type);

-- Index for GDPR data subject queries (encrypted field)
CREATE INDEX idx_audit_by_data_subject
ON dataverse_sync_audit(gdpr_data_subject_id);

-- Sample audit entries:

-- Successful work order sync
INSERT INTO dataverse_sync_audit VALUES (
  DEFAULT,  -- audit_id (auto)
  'evt_12345abc'::UUID,  -- event_id
  'create',  -- event_type
  'msdyn_workorder',  -- entity_type
  'wo_54321'::UUID,  -- source_dataverse_id
  '2026-05-10T14:30:00Z'::TIMESTAMP,  -- source_timestamp
  'analyst@nycdot.gov',  -- source_user_id
  'work_orders',  -- target_table
  1,  -- target_record_id
  'INSERT',  -- operation
  'SUCCESS',  -- operation_status
  NULL,  -- old_values
  '{"dataverse_id":"wo_54321","description":"Pothole at 5th & Main","priority":3}'::JSONB,  -- new_values
  1850,  -- sync_latency_milliseconds
  0,  -- retry_count
  'dvx:a1b2c3d4e5f6...',  -- idempotency_key
  FALSE,  -- conflict_detected
  NULL, NULL, NULL,  -- conflict fields
  'contractor_456',  -- gdpr_data_subject_id
  TRUE,  -- contains_sensitive_data
  '2026-05',  -- encryption_key_version
  'webhook_handler',  -- recorded_by
  NOW()  -- recorded_at
);

-- Conflict-resolved status update
INSERT INTO dataverse_sync_audit VALUES (
  DEFAULT,
  'evt_12345def'::UUID,
  'update',
  'msdyn_workorder',
  'wo_54321'::UUID,
  '2026-05-10T15:00:00Z'::TIMESTAMP,
  'supervisor@nycdot.gov',
  'work_orders',
  1,
  'UPDATE',
  'SUCCESS',
  '{"status_code":"ACTIVE"}'::JSONB,
  '{"status_code":"COMPLETED","actual_cost":1250.00}'::JSONB,
  3200,
  1,
  'dvx:a1b2c3d4e5f7...',
  TRUE,  -- conflict_detected
  'field_precedence',
  'TOOLKIT_WINS',  -- Toolkit's operational status took precedence
  'Contractor submitted completion; Dataverse had priority change. Toolkit operational state retained per field precedence tier 3.',
  'contractor_456',
  TRUE,
  '2026-05',
  'webhook_handler',
  NOW()
);
```

---

## 7. DEPLOYMENT TOPOLOGY

### 7.1 Conceptual Deployment Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   NYC DOT DATAVERSE SYNC DEPLOYMENT                       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌─ MICROSOFT 365 (SaaS - Managed)                                        │
│  │  ┌────────────────────────────────────────────┐                       │
│  │  │ DATAVERSE ENVIRONMENT (prod.crm....)       │                       │
│  │  │  • msdyn_workorder, msdyn_permit tables    │                       │
│  │  │  • Webhook subscriptions (→ Toolkit)       │                       │
│  │  │  • Service Principal app registration      │                       │
│  │  └────────────────────────────────────────────┘                       │
│  │           │                                                            │
│  │           ├─ WEBHOOKS (REST API) ─→                                   │
│  │           │                        │                                   │
│  │           └─ OAUTH2 API ←──────────┘                                  │
│  │                                                                        │
│  └────────────────────────────────────────────────────────────────────┘  │
│                            │                                              │
│                            ▼ (HTTPS)                                      │
│  ┌─ AZURE CLOUD (Managed by NYC DOT)                                      │
│  │  ┌────────────────────────────────────────────────────────────────┐   │
│  │  │ WEBHOOK INGESTION LAYER                                        │   │
│  │  │  API Endpoint: toolkit-api.nycdot.gov/webhooks/dataverse      │   │
│  │  │  Deployment: Azure Container Instances (ephemeral)           │   │
│  │  │  Language: Python FastAPI                                    │   │
│  │  │  Functions:                                                   │   │
│  │  │   • Receive POST events from Dataverse                       │   │
│  │  │   • Validate X-Webhook-Auth-Token                            │   │
│  │  │   • Route to Azure Service Bus (topic: dataverse_events)    │   │
│  │  │   • Return 200 OK (decouple processing)                      │   │
│  │  └────────────────────────────────────────────────────────────────┘   │
│  │           │                                                            │
│  │           ├─ IDEMPOTENCY CACHE                                        │
│  │           │  (Azure Cache for Redis)                                  │
│  │           │  Stores: event_id → processed status                      │
│  │           │                                                            │
│  │           └─ DEAD-LETTER QUEUE (DLQ)                                  │
│  │              PostgreSQL: webhook_dlq table                            │
│  │              Stores failed events for manual review                    │
│  │                                                                        │
│  │  ┌────────────────────────────────────────────────────────────────┐   │
│  │  │ EVENT PROCESSING TIER (Airflow on AKS)                         │   │
│  │  │  DAG: `dataverse_workorder_sync`                               │   │
│  │  │  Schedule: Continuous (event-triggered via Service Bus)       │   │
│  │  │  Executor: KubernetesPodOperator                              │   │
│  │  │                                                                │   │
│  │  │  Tasks:                                                        │   │
│  │  │   1. ConsumeFromServiceBus → Fetch events from queue           │   │
│  │  │   2. ValidateEvent → Check schema, fields, FK constraints     │   │
│  │  │   3. DetectConflicts → Compare w/ toolkit state               │   │
│  │  │   4. ResolveConflicts → Apply field-precedence tier           │   │
│  │  │   5. InsertOrUpdate → Upsert into work_orders table           │   │
│  │  │   6. RecordLineage → Track in lineage_core tables             │   │
│  │  │   7. EmitMetrics → Publish sync latency, conflict count       │   │
│  │  │   8. AlertOnFailure → DLQ if any step fails                   │   │
│  │  │                                                                │   │
│  │  └────────────────────────────────────────────────────────────────┘   │
│  │           │                                                            │
│  │           ▼                                                            │
│  │  ┌────────────────────────────────────────────────────────────────┐   │
│  │  │ OPERATIONAL DATABASE (Azure Database for PostgreSQL)           │   │
│  │  │  Primary (32 vCPU, 128 GB):                                    │   │
│  │  │   • work_orders                                               │   │
│  │  │   • contractor_assignments                                    │   │
│  │  │   • repair_jobs                                               │   │
│  │  │   • progress_tracking                                         │   │
│  │  │   • compliance_reporting                                      │   │
│  │  │   • sync_metadata, dataverse_sync_audit                       │   │
│  │  │                                                                │   │
│  │  │  Read Replicas:                                               │   │
│  │  │   • Replica #1 (Power BI reporting queries)                   │   │
│  │  │   • Replica #2 (Spark ephemeral reads)                        │   │
│  │  │                                                                │   │
│  │  │  Geo-Replica (DR):                                            │   │
│  │  │   • Async replication to paired region (5-min RPO)            │   │
│  │  │                                                                │   │
│  │  └────────────────────────────────────────────────────────────────┘   │
│  │           │                                                            │
│  │           ├─ MATERIALIZED VIEWS (hourly refresh)                       │
│  │           │  • v_active_workorders (for Power BI)                     │
│  │           │  • v_contractor_assignments_summary                       │
│  │           │  • v_compliance_violations                                │
│  │           │                                                            │
│  │           ├─ QUERY CACHE (Azure Cache for Redis)                       │
│  │           │  • TTL: 1 hour                                             │
│  │           │  • Hit rate: 80%+ (reduce load)                            │
│  │           │                                                            │
│  │           └─ FULL-TEXT SEARCH INDEX                                    │
│  │              PostgreSQL FTS: descriptions, notes, comments             │
│  │                                                                        │
│  │  ┌────────────────────────────────────────────────────────────────┐   │
│  │  │ OUTBOUND SYNC LAYER (Scheduled Batch)                          │   │
│  │  │  DAG: `toolkit_status_to_dataverse_sync`                       │   │
│  │  │  Schedule: Every 5 minutes                                     │   │
│  │  │                                                                │   │
│  │  │  Purpose: Push completion updates back to Dataverse            │   │
│  │  │  Fields synced back:                                           │   │
│  │  │   • status_code (COMPLETED, BLOCKED, CANCELLED)               │   │
│  │  │   • completion_percentage                                      │   │
│  │  │   • actual_cost                                                │   │
│  │  │   • completion_summary                                         │   │
│  │  │                                                                │   │
│  │  │  Flow:                                                         │   │
│  │  │   1. Query toolkit.work_orders WHERE changed_since >= 5 min   │   │
│  │  │   2. Filter to COMPLETED or BLOCKED status                    │   │
│  │  │   3. Call DataverseOAuth2Client.update_work_order_status()    │   │
│  │  │   4. Retry with exponential backoff                           │   │
│  │  │   5. Record in dataverse_sync_audit                           │   │
│  │  │   6. Alert if update fails (DLQ review needed)                │   │
│  │  │                                                                │   │
│  │  └────────────────────────────────────────────────────────────────┘   │
│  │           │                                                            │
│  │           ▼                                                            │
│  │  ┌────────────────────────────────────────────────────────────────┐   │
│  │  │ RECONCILIATION & VALIDATION (Nightly Batch)                   │   │
│  │  │  DAG: `dataverse_toolkit_reconciliation`                      │   │
│  │  │  Schedule: 02:00 UTC daily (midnight EST)                     │   │
│  │  │                                                                │   │
│  │  │  Purpose: Detect drift, missing records, inconsistencies      │   │
│  │  │  Tasks:                                                        │   │
│  │  │   1. FetchFromDataverse → Query all active work orders         │   │
│  │  │   2. CompareWithToolkit → LEFT/RIGHT outer joins              │   │
│  │  │   3. IdentifyDiscrepancies → Missing, extra, stale records    │   │
│  │  │   4. ClassifyByType → Schema, referential, data quality       │   │
│  │  │   5. GenerateReport → Email to data ops team                  │   │
│  │  │   6. AlertIfCritical → Page on-call if >10 discrepancies      │   │
│  │  │                                                                │   │
│  │  └────────────────────────────────────────────────────────────────┘   │
│  │                                                                        │
│  │  ┌────────────────────────────────────────────────────────────────┐   │
│  │  │ OBSERVABILITY TIER                                             │   │
│  │  │  Prometheus: Metrics endpoint (/metrics)                       │   │
│  │  │   • dataverse_sync_latency_p95_seconds                         │   │
│  │  │   • webhook_event_count_total                                  │   │
│  │  │   • conflict_resolution_total                                  │   │
│  │  │   • reconciliation_discrepancies                               │   │
│  │  │   • dlq_pending_events                                         │   │
│  │  │                                                                │   │
│  │  │  Grafana: Dashboards                                           │   │
│  │  │   • Dataverse Sync Health (real-time)                          │   │
│  │  │   • Conflict Resolution Trends (daily)                         │   │
│  │  │   • Work Order Velocity (by contractor)                        │   │
│  │  │   • DLQ Review Queue                                           │   │
│  │  │                                                                │   │
│  │  │  Azure Monitor: Alerts                                         │   │
│  │  │   • Webhook subscription inactive >5 min                       │   │
│  │  │   • Sync latency >120 seconds (P95)                            │   │
│  │  │   • DLQ size >5 pending events                                 │   │
│  │  │   • Service Bus dead-letter queue not empty                    │   │
│  │  │                                                                │   │
│  │  └────────────────────────────────────────────────────────────────┘   │
│  │                                                                        │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌─ ANALYTICS & REPORTING (Power BI, Excel)                               │
│  │  ┌────────────────────────────────────────────────────────────────┐   │
│  │  │ POWER BI DASHBOARDS                                            │   │
│  │  │  Data Source: PostgreSQL read replica                          │   │
│  │  │  Refresh: Every 15 minutes                                     │   │
│  │  │                                                                │   │
│  │  │  Visuals:                                                      │   │
│  │  │   • Work Order Status Breakdown (pie)                          │   │
│  │  │   • Contractor Performance (scatter)                           │   │
│  │  │   • Sync Latency Trend (line)                                  │   │
│  │  │   • Compliance Violation Heatmap (map)                         │   │
│  │  │   • DLQ Alert Card (KPI)                                       │   │
│  │  │                                                                │   │
│  │  │  Filters:                                                      │   │
│  │  │   • Date range, borough, material type, status                 │   │
│  │  │   • Mobile report for field teams                              │   │
│  │  │                                                                │   │
│  │  └────────────────────────────────────────────────────────────────┘   │
│  │                                                                        │
│  │  ┌────────────────────────────────────────────────────────────────┐   │
│  │  │ EXCEL WORKBOOKS (Field Reports)                               │   │
│  │  │  Data Source: API (FastAPI) with caching                       │   │
│  │  │  Refresh: On-demand via Power Query                            │   │
│  │  │                                                                │   │
│  │  │  Sheets:                                                       │   │
│  │  │   • My Assignments (contractor-specific)                       │   │
│  │  │   • Work Order Details (filterable)                            │   │
│  │  │   • Compliance Checklist (printable)                           │   │
│  │  │                                                                │   │
│  │  └────────────────────────────────────────────────────────────────┘   │
│  │                                                                        │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### 7.2 Disaster Recovery & High Availability

```
RECOVERY OBJECTIVES:

┌──────────────────────────────────────────────────────────────────┐
│ Metric              │ Target  │ Implementation                     │
├──────────────────────────────────────────────────────────────────┤
│ RTO (Recovery Time) │ <1 hour │ Primary → Geo-replica promotion    │
│ RPO (Recovery Point)│ <5 min  │ Async DB replication + WAL logs    │
│ Availability (SLA)  │ 99.9%   │ Multi-AZ, health checks, auto-heal │
│ Sync Latency (P95)  │ <120s   │ Circuit breaker + fallback to poll │
└──────────────────────────────────────────────────────────────────┘

FAILURE SCENARIOS & MITIGATION:

1. Webhook Endpoint Down (Dataverse can't reach toolkit API)
   ────────────────────────────────────────────────────────
   Scenario: POST /webhooks/dataverse returns 5xx for >5 min
   
   Dataverse Behavior:
   • Retry webhook with exponential backoff (up to 10x)
   • After 10 failures, webhook subscription auto-disabled
   • Alert sent to NYC DOT admin
   
   Toolkit Recovery:
   • Auto-scale API pods (HPA trigger: error rate > 5%)
   • Enable polling fallback (every 15 min)
   • DLQ temporarily accepts events to buffer
   • Alert: Page on-call engineer
   
   Action Items:
   • Restore API (redeploy, scale, fix bug)
   • Manually re-enable webhook subscription in Dataverse
   • Backfill missed events from DLQ

2. Database Failover (Primary PostgreSQL unreachable)
   ──────────────────────────────────────────────────
   Scenario: Azure Database primary in US East suffers outage
   
   Automatic Failover:
   • Health check detects primary unresponsive (3 consecutive pings)
   • Auto-promote read replica to primary (same region)
   • DNS endpoint updated (Azure handles transparently)
   • RTO: ~30 seconds
   • Data loss: <1 minute (buffer in-flight transactions)
   
   Manual Geo-Failover:
   • If regional outage: Promote geo-replica (5 min lag)
   • Repoint Airflow connections to new primary
   • Run reconciliation to catch any skipped records
   • RTO: <5 minutes, RPO: <5 minutes

3. Dataverse API Becomes Slow/Unavailable
   ───────────────────────────────────────
   Scenario: Microsoft service degradation (rare but possible)
   
   Circuit Breaker Pattern:
   • Monitor Dataverse API latency & error rate
   • If latency > 10s OR error rate > 10%:
     - Break circuit (stop sending requests)
     - Queue events in Service Bus for retry
     - Switch to offline mode (query cached data)
   • Backoff: exponential, max retry 24 hours
   • Alert: Notify NYC DOT to contact Microsoft
   
   Recovery:
   • Manual or automatic circuit reset (once Dataverse recovers)
   • Drain queued events with rate limiting (avoid cascade)

4. Data Corruption / Accidental Update
   ────────────────────────────────────
   Scenario: Bulk update applies wrong value to many records
   
   Prevention:
   • Pre-deployment validation (schema, FK, constraints)
   • Audit trail logs all changes
   • Read-only replicas for reporting (can't be corrupted)
   
   Recovery:
   • Point-in-time restore (PITR) to 1-hour ago
   • Selective row recovery using audit trail
   • Manual verification before resuming sync

BACKUP & RECOVERY PROCEDURES:

Daily Backup Schedule:
─────────────────────
 02:00 UTC - Full backup (primary database)
 06:00 UTC - Full backup (read replica #1)
 10:00 UTC - Full backup (read replica #2)
 14:00 UTC - Incremental backup (WAL logs)
 18:00 UTC - Incremental backup (WAL logs)
 22:00 UTC - Incremental backup (WAL logs)

Backup Retention:
────────────────
 • 30-day daily backups (kept on hot storage)
 • 1-year monthly snapshots (cold storage archive)
 • Compliance: 7-year legal hold for audit records

Recovery Test Schedule:
──────────────────────
 • Monthly: Restore to staging, run reconciliation test
 • Quarterly: Full RTO/RPO drill (failover to geo-replica)
 • Annually: Disaster recovery tabletop exercise
```

---

## 8. REAL-WORLD NYC DOT WORKFLOWS

### 8.1 End-to-End Workflow: Sidewalk Repair Request → Completion

```
WORKFLOW: "Pothole Discovered → Repair Scheduled → Contractor Completes → Compliance Verified"

ACTORS:
  • 311 Complaint System (input)
  • Dataverse Administrator (work order creation)
  • Field Inspector (mobile QGIS)
  • Contractor (execution)
  • Compliance Auditor (QA)
  • Power BI Dashboard (visibility)


┌─────────────────────────────────────────────────────────────────────────────┐
│ T+0 MINUTES: COMPLAINT INTAKE (311 System → Dataverse)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│ NYC 311 Complaint Submitted:                                                │
│   • Caller: "Pothole at 5th Ave & 42nd St, Manhattan"                       │
│   • Severity: High (trip hazard)                                            │
│   • Location: (40.7532° N, -73.9889° W)                                     │
│   • Complaint ID: 311_1234567                                               │
│                                                                               │
│ Dataverse Operator creates msdyn_workorder:                                 │
│   POST https://org.crm.dynamics.com/api/data/v9.2/msdyn_workorders         │
│   Body:                                                                      │
│   {                                                                          │
│     "msdyn_name": "Repair pothole at 5th & 42nd - HIGH PRIORITY",           │
│     "msdyn_workordertype": "inspection_then_repair",                         │
│     "msdyn_priority": 1,                                                     │
│     "customertypecode": "block_face",                                        │
│     "msdyn_latitude": 40.7532,                                              │
│     "msdyn_longitude": -73.9889,                                            │
│     "ext_complaint_reference_id": "311_1234567"                             │
│   }                                                                          │
│                                                                               │
│   ✓ Dataverse creates msdyn_workorderid = "wo_abc123def456"                 │
│   ✓ Webhook event fires (CREATE action)                                     │
│                                                                               │
│ Toolkit Receives Webhook:                                                  │
│   POST /webhooks/dataverse                                                  │
│   {                                                                          │
│     "event_id": "evt_001",                                                  │
│     "action": "create",                                                      │
│     "entity_type": "msdyn_workorder",                                       │
│     "dataverse_id": "wo_abc123def456",                                      │
│     "payload": { ... work order fields ... }                                │
│   }                                                                          │
│                                                                               │
│   ✓ Webhook handler validates & deduplicates                               │
│   ✓ Routes to Service Bus topic: work_order_events                         │
│   ✓ Returns 200 OK to Dataverse (acknowledgment)                           │
│                                                                               │
│ Airflow Syncs to Toolkit DB:                                               │
│   Task: ConsumeFromServiceBus → Fetch "evt_001"                            │
│   Task: ValidateEvent → Check schema (required fields, types)              │
│   Task: InsertOrUpdate → SQL INSERT work_orders table                      │
│   SQL:                                                                      │
│   INSERT INTO work_orders (                                                │
│     dataverse_id, description, planned_start_date, work_type,              │
│     priority_level, location_type, created_at, status_code                 │
│   ) VALUES (                                                               │
│     'wo_abc123def456'::UUID,                                               │
│     'Repair pothole at 5th & 42nd - HIGH PRIORITY',                        │
│     NOW()::TIMESTAMP,                                                      │
│     'repair'::TEXT,                                                        │
│     1::INT,                                                                │
│     'block_face'::TEXT,                                                    │
│     NOW()::TIMESTAMP,                                                      │
│     'ACTIVE'::TEXT                                                         │
│   );                                                                       │
│                                                                               │
│   ✓ Record synced latency: 1.85 seconds (P95 target)
│   ✓ Audit logged to dataverse_sync_audit table
│   ✓ Lineage recorded: TransformationNode for lineage tracking
│   ✓ Metrics emitted: webhook_events_total += 1
│                                                                               │
│ OUTCOME AT T+0: Work order visible in toolkit database & Airflow            │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│ T+4 HOURS: FIELD INSPECTION (Mobile QGIS → Toolkit)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│ NYC DOT Inspector Dispatched:                                               │
│   • Assignment: "Inspect pothole severity"                                  │
│   • Tool: QGIS mobile app (offline-first, GeoPackage)                       │
│   • Arrives at 5th & 42nd St                                                │
│                                                                               │
│ Inspector Documentation:                                                    │
│   1. Photo capture (3 images)                                               │
│      • Pothole depth: ~2 inches                                             │
│      • Diameter: ~8 inches                                                  │
│      • Risk: Immediate trip hazard                                          │
│                                                                               │
│   2. Field assessment form (QGIS attributes):                               │
│      defect_type: "pothole"                                                │
│      material: "asphalt"                                                    │
│      linear_feet: 0.67  (8 inches)                                          │
│      severity_code: "H"  (high)                                             │
│      inspection_notes: "Deep pothole, immediate safety risk"               │
│                                                                               │
│ QGIS syncs to Toolkit when online:                                         │
│   POST /api/v1/inspections                                                 │
│   Body:                                                                      │
│   {                                                                          │
│     "work_order_id": "wo_abc123def456",  (from QGIS GeoPackage)            │
│     "defect_type": "pothole",                                               │
│     "material": "asphalt",                                                  │
│     "linear_feet": 0.67,                                                    │
│     "severity": "H",                                                        │
│     "notes": "Deep pothole, immediate safety risk",                         │
│     "photos": ["s3://photos/20260510_001.jpg", "s3://photos/20260510_002.jpg", ...] │
│   }                                                                          │
│                                                                               │
│ Toolkit Processing:                                                        │
│   ✓ INSERT progress_tracking (completion_percentage = 15%)                 │
│   ✓ INSERT repair_jobs (repair_type='pothole', material='asphalt')        │
│   ✓ Material cost lookup: asphalt pothole repair = ~$150/occurrence        │
│   ✓ UPDATE work_orders SET status_code='IN_PROGRESS'                       │
│   ✓ Generate Dataverse update (async, outbound sync)                       │
│                                                                               │
│ OUTCOME AT T+4H: Inspection data in toolkit, repair estimate ready         │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│ T+8 HOURS: CONTRACTOR ASSIGNMENT (Dataverse Dispatch)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│ Dataverse Dispatcher Assigns Contractor:                                   │
│   • Reviews: Severity (H), material (asphalt), cost estimate ($150)         │
│   • Selects: "ABC Paving Contractor" (preferred for asphalt, nearby)       │
│   • Updates msdyn_workorder.ownerid = contractor_123                        │
│                                                                               │
│ Dataverse webhook fires: UPDATE action                                      │
│   {                                                                          │
│     "event_id": "evt_002",                                                  │
│     "action": "update",                                                      │
│     "entity_type": "msdyn_workorder",                                       │
│     "dataverse_id": "wo_abc123def456",                                      │
│     "changed_fields": ["ownerid", "modifiedon"],                            │
│     "new_values": { "ownerid": "contractor_123", ... }                      │
│   }                                                                          │
│                                                                               │
│ Toolkit Sync (via webhook):                                                │
│   ✓ Detect field: ownerid changed → contractor_assignments                 │
│   ✓ INSERT contractor_assignments (assignment_status='ASSIGNED')           │
│   ✓ UPDATE work_orders (assigned_contractor_id = contractor_123)           │
│   ✓ Emit Outlook notification:                                             │
│      To: abc.paving@contractor.com                                         │
│      Subject: "New Assignment: Pothole repair @ 5th & 42nd"                │
│      Body: "Work order wo_abc123def456 ready for dispatch"                 │
│                                                                               │
│ OUTCOME AT T+8H: Contractor assigned, notification sent                    │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│ T+1 DAY: CONTRACTOR EXECUTES REPAIR (Field Work)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│ Contractor Workflow (Mobile App):                                          │
│   1. Acknowledge assignment (Outlook reply)                                │
│   2. Travel to site                                                         │
│   3. Check-in via QGIS: "Arrived at site" (geolocation recorded)           │
│   4. Assess materials: Asphalt patch kit + filler                          │
│   5. Execute repair (30 minutes work)                                       │
│   6. Document completion:                                                   │
│      - Before/after photos                                                  │
│      - Actual materials used: "2 bags asphalt, 1 binder"                   │
│      - Labor: 0.5 hours                                                     │
│      - Actual cost: $165 (slightly higher due to labor)                    │
│                                                                               │
│ QGIS/Mobile sync to Toolkit:                                               │
│   POST /api/v1/work-completion                                             │
│   {                                                                          │
│     "work_order_id": "wo_abc123def456",                                     │
│     "completion_percentage": 100,                                           │
│     "actual_start_time": "2026-05-10T13:00:00Z",                           │
│     "actual_end_time": "2026-05-10T13:30:00Z",                             │
│     "materials_used": [                                                     │
│       { "type": "asphalt_patch", "quantity": 2, "unit": "bags" },         │
│       { "type": "binder", "quantity": 1, "unit": "container" }             │
│     ],                                                                       │
│     "actual_cost": 165.00,                                                  │
│     "quality_notes": "Surface smooth, no edges",                            │
│     "completion_photos": ["s3://photos/completion_001.jpg", ...]           │
│   }                                                                          │
│                                                                               │
│ Toolkit Validation & Compliance Checks:                                    │
│   ✓ ADA Compliance Check (via material_standards module):                  │
│      - Surface evenness: ✓ PASS (measured via photos + AI)                 │
│      - Slip resistance: ✓ PASS (asphalt meets standards)                   │
│   ✓ NYC Street Design Manual Check:                                        │
│      - Repair method: ✓ PASS (cold asphalt acceptable for emergency)       │
│      - Material quality: ✓ PASS (supplier approved)                        │
│   ✓ Cost Validation:                                                       │
│      - Estimated: $150                                                      │
│      - Actual: $165 (10% variance acceptable, flagged for review)           │
│                                                                               │
│ UPDATE work_orders:                                                         │
│   status_code = 'COMPLETED'                                                │
│   actual_cost = 165.00                                                     │
│   completion_percentage = 100                                              │
│   hazard_resolved = TRUE                                                   │
│                                                                               │
│ INSERT compliance_reporting:                                               │
│   compliance_check_type = 'ada'                                            │
│   check_status = 'PASS'                                                    │
│   violation_code = NULL                                                    │
│                                                                               │
│ OUTCOME AT T+1D: Work completed, compliance verified, cost recorded        │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│ T+1 DAY (ASYNC): OUTBOUND SYNC TO DATAVERSE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│ Scheduled DAG: toolkit_status_to_dataverse_sync (runs every 5 minutes)     │
│                                                                               │
│ Task 1: Query changed work_orders:                                         │
│   SELECT * FROM work_orders                                                │
│   WHERE status_code != dataverse_last_sync_status                          │
│   AND changed_since >= NOW() - INTERVAL '5 minutes'                        │
│   Result: work order wo_abc123def456 (status changed ACTIVE → COMPLETED)  │
│                                                                               │
│ Task 2: Map to Dataverse fields:                                           │
│   toolkit.status_code='COMPLETED' → dataverse.statecode=1                  │
│   toolkit.completion_percentage=100 → dataverse.msdyn_percentcomplete=100  │
│   toolkit.actual_cost=165.00 → dataverse.msdyn_actualcost=165.00          │
│                                                                               │
│ Task 3: Call Dataverse API with OAuth2 token:                              │
│   PATCH https://org.crm.dynamics.com/api/data/v9.2/msdyn_workorders(wo_abc123def456) │
│   Headers:                                                                   │
│     Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...                       │
│   Body:                                                                      │
│   {                                                                          │
│     "statecode": 1,                                                         │
│     "msdyn_percentcomplete": 100,                                           │
│     "msdyn_actualcost": 165.00,                                             │
│     "msdyn_summary": "Pothole repair completed successfully. ADA compliant." │
│   }                                                                          │
│                                                                               │
│ Task 4: Handle response:                                                    │
│   ✓ 200 OK → Record success in audit trail                                 │
│   ✗ 5xx → Exponential backoff retry (1, 2, 4, 8 minutes)                   │
│   ✗ 403 → OAuth token refresh & retry                                      │
│                                                                               │
│ Task 5: Emit metrics:                                                       │
│   • dataverse_sync_outbound_latency_seconds = 2.3                          │
│   • work_orders_synced_to_dataverse_total += 1                             │
│                                                                               │
│ Task 6: Update audit trail:                                                │
│   INSERT dataverse_sync_audit (                                            │
│     event_id, event_type, entity_type, operation, operation_status, ...   │
│   )                                                                         │
│                                                                               │
│ OUTCOME AT T+1D+: Power BI dashboard reflects completion immediately       │
│                  Outlook notifications sent to stakeholders                 │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│ T+1 DAY: POWER BI VISIBILITY (Real-Time Reporting)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│ Power BI Dashboard Auto-Refreshes (every 15 minutes from PostgreSQL replica)│
│                                                                               │
│ Tiles Update:                                                               │
│   • "Active Work Orders": 47 (was 48, now 47 completed)                    │
│   • "Today's Completions": 12 (was 11, now includes pothole repair)        │
│   • "Contractor Performance": ABC Paving updated (completion rate ↑)        │
│   • "Compliance Status": 100% PASS rate maintained                         │
│   • "Budget Variance": +$15 (actual vs estimated on this repair)           │
│                                                                               │
│ Mobile Report Viewed by Supervisor:                                        │
│   Opens Power BI mobile app → Filters by contractor "ABC Paving"           │
│   Sees: "Work order wo_abc123def456 COMPLETED"                            │
│   Reviews: Photos, materials used, compliance sign-off                     │
│                                                                               │
│ Outlook Notification:                                                       │
│   To: supervisor@nycdot.gov                                                │
│   From: nyc-dot-alerts@toolkit.nyc.gov                                     │
│   Subject: "✓ Pothole repair completed @ 5th & 42nd (work_abc123def456)"   │
│   Body: "Contractor ABC Paving completed repair. Status: COMPLETED (100%)" │
│         "Compliance: ✓ PASS (ADA compliant)"                               │
│         "Cost: $165.00 (estimate: $150.00, variance: +10%)"                │
│         "View details: [Link to Power BI]"                                 │
│                                                                               │
│ OUTCOME AT T+1D: Management visibility complete, stakeholders informed      │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘

---

### 8.2 Conflict Scenario: Permit Expires During Active Repair

```
SCENARIO: Contractor scheduled to complete repair on 2026-05-15, but permit 
          expires on 2026-05-12 due to legal hold.

TIMELINE:

T+0:  Dataverse Administrator extends permit by 5 days → expirationDate = 2026-05-20
      Webhook fires: UPDATE permit
      
      Toolkit receives webhook → UPDATE work_orders.permit_expiration_date
      No conflict (permit extended, repair can continue)
      
      Power BI auto-refreshes: "Permit valid until 2026-05-20" ✓

T+1 DAY:  Supervisor notices legal hold → Permit REVOKED in Dataverse
          statusCode = 'REVOKED'
          Webhook fires: UPDATE permit
          
          Toolkit webhook handler receives event:
          {
            "event_id": "evt_003",
            "action": "update",
            "entity_type": "msdyn_permit",
            "dataverse_id": "permit_xyz789",
            "changed_fields": ["statusCode"],
            "new_values": { "statusCode": "REVOKED" }
          }
          
          Conflict Detection Logic:
          ├─ Query work_orders WHERE permit_id = permit_xyz789
          ├─ Check: work_orders.status_code = 'IN_PROGRESS'
          ├─ Check: work_orders.completion_percentage = 75%
          ├─ Action: COMPLIANCE VIOLATION DETECTED
          │
          └─ INSERT compliance_reporting:
             violation_type = 'PERMIT_REVOKED_DURING_WORK'
             severity = 'CRITICAL'
             remediation_deadline = NOW() + 24 HOURS
             
          ├─ UPDATE work_orders:
          │  status_code = 'BLOCKED_PERMIT_REVOKED'
          │  alert_flag = TRUE
          │
          └─ Generate Alert:
             Channel: Email + Slack + Outlook
             To: supervisor@nycdot.gov, contractor@abc-paving.com
             Subject: "⚠️ CRITICAL: Work order blocked - permit revoked (wo_abc123def456)"
             Body: 
             "Permit for pothole repair @ 5th & 42nd has been revoked.
              Work order status: BLOCKED (75% complete)
              
              ACTION REQUIRED:
              1. Supervisor: Contact legal team to reinstate or modify permit
              2. Contractor: STOP work immediately (safety requirement)
              3. Options:
                 a) Reinstate permit → Resume work
                 b) Obtain emergency permit → Continue today
                 c) Cancel → Restore site to safe condition
              
              Escalation: On-call manager paged
              Deadline: Respond within 24 hours"

T+2 HOURS:  Supervisor contacts legal team → Permit reinstated with conditions
            Dataverse: statusCode = 'ACTIVE' (updated)
            Webhook fires: UPDATE permit
            
            Toolkit receives reinstatement:
            ├─ Check: BLOCKED work orders for this permit
            ├─ Automatic remediation:
            │  UPDATE work_orders SET status_code = 'IN_PROGRESS' (resume)
            │
            ├─ Clear alert:
            │  UPDATE compliance_reporting SET remediation_notes = 'Permit reinstated - work resumed'
            │
            └─ Notify Contractor:
               Email: "Permit reinstated. Resume work on wo_abc123def456"
               Outlook notification sent
               
            ✓ Work resumes at 75% completion point

T+4 HOURS:  Contractor completes repair (final 25%)
            Outbound sync to Dataverse (as per section 8.1)
            Compliance verified
            
            Final Audit Entry:
            {
              "event_type": "conflict_resolution",
              "conflict_type": "permit_expiration_during_work",
              "resolution_applied": "permit_reinstatement",
              "work_order_id": "wo_abc123def456",
              "timeline": "2h 45m from detection to resolution",
              "business_impact": "Minor delay, work completed successfully",
              "compliance_status": "PASS"
            }

OUTCOME:  Conflict detected, escalated, resolved through permit reinstatement
          Complete audit trail preserved for compliance review
```

---

### 8.3 Data Quality Issue: Contractor Assignment Orphaned Record

```
SCENARIO: Dataverse contractor deleted, but toolkit still has active assignment.
          Referential integrity broken, compliance audit fails.

DETECTION:

Nightly Reconciliation DAG: dataverse_toolkit_reconciliation
├─ Fetch all msdyn_workorder.ownerid from Dataverse
├─ Compare with toolkit.contractor_assignments.contractor_id
├─ Identify orphaned: toolkit has contractor_id that doesn't exist in Dataverse
│
└─ DISCREPANCY FOUND:
   Contractor: contractor_456 (Tom Smith, ABC Paving)
   Last active: work_order wo_def789ghi012
   Status: DELETED in Dataverse, still active in toolkit

RESOLUTION WORKFLOW:

Step 1: Classify discrepancy
├─ Type: REFERENTIAL_INTEGRITY
├─ Severity: HIGH (affects work order continuity)
└─ Impact: 2 active work orders without valid contractor assignment

Step 2: Generate report
├─ Email data ops team:
│  "Reconciliation Alert: 2 orphaned contractor assignments"
│  "Contractor contractor_456 deleted in Dataverse"
│  "Affected work orders: wo_def789ghi012, wo_xyz890..."
│  "Action: Review and reassign or cancel work orders"
│
└─ Alert Power BI:
   KPI Card: "Data Quality Issues: 2" (red status)

Step 3: Manual remediation options
├─ Option A: Reassign contractor in Dataverse
│  → Webhook fires UPDATE action
│  → Toolkit auto-updates contractor_assignments
│  → Discrepancy cleared
│
├─ Option B: Cancel work order
│  → Dataverse: DELETE or mark CANCELLED
│  → Webhook fires DELETE action
│  → Toolkit: Soft-delete (preserve audit trail)
│
└─ Option C: Reactivate contractor
   → Dataverse: Re-create contractor record
   → Manual sync (or wait for next sync window)

Step 4: Reconciliation verification
├─ Run LEFT/RIGHT outer join again
├─ Confirm orphaned records cleared
└─ Update audit_trail:
   INSERT dataverse_sync_audit (
     event_type = 'reconciliation_resolution',
     issue_type = 'referential_integrity',
     resolution = 'reassignment',
     affected_records = 2,
     resolved_by = 'data_ops_team'
   );

OUTCOME: Data quality issues detected automatically, reported to team,
         resolved through guided workflow
```

---

## CONCLUSION

This Dataverse Integration Architecture provides:

✅ **Bi-Directional Sync**: Asymmetric model optimized for Dataverse as source of truth
✅ **Production-Grade Reliability**: 99.9% SLA, <5-minute latency, comprehensive error handling
✅ **Enterprise Compliance**: GDPR/CCPA, audit trails, encryption, RBAC
✅ **Real-Time Visibility**: Power BI dashboards, Excel reports, Outlook notifications updated in <5 minutes
✅ **Conflict Resolution**: Field-precedence tiers, manual review queues, full audit trail
✅ **Operational Excellence**: Complete observability, DLQ pattern, reconciliation workflows
✅ **NYC DOT Integration**: Lineage tracking, material standards validation, ADA compliance enforcement

### Next Steps for Implementation

1. **Week 1-2**: Infrastructure setup
   - Azure Key Vault for OAuth credentials
   - Azure Service Bus topics for event streaming
   - PostgreSQL audit tables and constraints

2. **Week 3-4**: Core sync engine
   - Webhook receiver FastAPI application
   - Idempotency manager (Redis integration)
   - Conflict resolution engine with field precedence

3. **Week 5-6**: Airflow orchestration
   - DAGs for inbound and outbound sync
   - Reconciliation & validation jobs
   - Integration with Phase 3 observability

4. **Week 7-8**: Compliance & security
   - OAuth2 service principal setup
   - Encryption at rest/in transit
   - Audit trail validation

5. **Week 9-10**: Testing & validation
   - Integration tests (webhook delivery, conflict resolution)
   - Load testing (1000s of work orders/day)
   - Disaster recovery drills

6. **Week 11-12**: Deployment & training
   - Production rollout with canary deployment
   - Operator training on DLQ review, conflict resolution
   - Go-live monitoring & alerting

---

**Document Status**: ✅ Ready for Implementation Review  
**Last Updated**: May 2026  
**Architecture Owner**: NYC DOT Data Engineering Team