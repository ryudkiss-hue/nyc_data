# SIM Relevance Matrix & Implementation Strategy

## Domain Alignment Statement
The NYC DOT is highly compartmentalized. While our broader datasets cover overall municipal infrastructure, the **Sidewalk Inspection and Management (SIM)** division possesses a strict operational mandate. 

SIM does **not** pave streets, fill roadway potholes, or mix asphalt—those belong to Roadway Repair & Maintenance (RRM). SIM's jurisdiction covers:
1.  **Sidewalk Defects & Violations**: Issuing notices to property owners, tracking grace periods, and dispatching city contractors when owners default.
2.  **Pedestrian Ramps (ADA)**: Enforcing compliance, managing installations, and responding to accessibility complaints.
3.  **Cross-Agency Coordination**: Specifically managing "Tree Smash" (Parks Department tree roots destroying sidewalks) and utility street cuts overlapping with curb infrastructure.

Accordingly, the previous 20-question matrix has been aggressively culled and bucketed by exact relevance to the SIM Project Analyst role.

---

## Tier 1: Core SIM Operations (Fully Implemented)
*These questions dictate the daily operational success of SIM and have been fully implemented in the analytical engine (`app/sim_core_analytics.py`).*

1.  **[PQ-05] The Default Predictor**: *To what extent can property assessed value and year of last structural alteration predict the probability of a homeowner defaulting to City-repair in Defective Lots?*
    *   **SIM Value**: If SIM knows a homeowner will default with 90% probability, they can pre-stage city contractors rather than waiting the full 75-day legal grace period, vastly reducing the backlog.
2.  **[PQ-03] NLP Triage**: *To what extent can NLP negative sentiment polarity and initial transcript length predict the probability of identifying a severe safety hazard in the 311 Complaint Backlog?*
    *   **SIM Value**: Identifies "trip-and-fall" hazards in real-time from unstructured citizen complaints, prioritizing HIQA inspector routing.
3.  **[DQ-04] Parks Coordination (Tree Smash)**: *What are the key characteristics of high-demand pedestrian corridors regarding overlap with outstanding Parks Department tree-damage?*
    *   **SIM Value**: Isolates where DOT is legally blocked from repairing a sidewalk until the Parks Dept removes a tree root, highlighting inter-agency bottlenecks in high-traffic zones.
4.  **[DQ-03] Legal Friction**: *What are the key characteristics of Sidewalk Violations dismissed in court regarding the primary cited defect type?*
    *   **SIM Value**: Identifies systemic errors in how HIQA inspectors are writing violations (e.g., misclassifying 'hardware' vs 'trip hazard'), allowing for targeted retraining to prevent lost revenue.

---

## Tier 2: SIM-Adjacent / Coordination (Retained for Reference)
*These questions require SIM coordination but rely on external division triggers. They remain in the visualization dashboard but are secondary priorities.*

5.  **[RQ-04]**: Relationship between planimetric sidewalk width and curb metal defects. (Shared with Highway Design).
6.  **[PQ-04]**: ADA Ramps vs distance to transit hubs. (Shared with Transit Policy).
7.  **[CQ-01]**: MTTR vs Equity Multipliers. (Shared with Commissioner's Office).

---

## Tier 3: Out of Scope / Roadway Maintenance (Discarded)
*These questions involve street paving and roadway deterioration, which fall entirely under the RRM division. They have been stripped from the SIM operational queue.*

*   *(Discarded)* [PQ-01]: Markov Decay for Street Segments (Potholes).
*   *(Discarded)* [CQ-02]: In-house resurfacing vs contracted crews.
*   *(Discarded)* [CQ-04]: Hot-mix vs warm-mix asphalt paving.
*   *(Discarded)* [RQ-02]: Post-paving pavement degradation rate.