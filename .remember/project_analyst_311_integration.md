---
name: project-analyst-311-analysis
description: Integration of 311 Service Requests (erm2-nwe9) with SIM Program analysis workflows
metadata:
  type: project
---

# 311 Service Requests Integration

## Dataset: 311 Service Requests from 2020 to Present
**Fourfour:** erm2-nwe9  
**URL:** https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9/about_data  
**Size:** ~21.3M rows (as of 2026-06-11)  
**Update Frequency:** Daily  
**Key Columns:** complaint_type, description, status, location_zip, latitude, longitude, created_date, closed_date, agency, complaint_id

## Strategic Value for Project Analyst

**311 is the LEADING INDICATOR for sidewalk problems:**
```
Citizen Reports 311 Complaint (Trip Hazard, Cracked Slab, Pothole)
    ↓
Project Analyst identifies patterns/hotspots
    ↓
DOT inspects (SIM inspection)
    ↓
Violation issued (violations dataset)
    ↓
Repair prioritized + scheduled
```

**Key analyses enabled:**
1. **Complaint hotspots** — Where are citizens reporting problems? (Heat map by complaint type)
2. **Complaint-to-inspection gap** — Which 311 reports led to formal SIM inspection? Which gaps remain?
3. **Response time** — Days from 311 report → inspection → repair (SLA tracking)
4. **Citizen impact weighting** — Prioritize repairs by # of complaints (not just violation severity)
5. **Coverage analysis** — Are high-complaint areas being inspected?
6. **Complaint type correlation** — Do "Trip Hazard" complaints match "Concrete Defect" violations?

## New Dashboards for Phase 1

### 1. Complaint Hotspot Map (Daily)
```
311 complaints by complaint_type (spatial)
├─ Filter: status = "Open" (unresolved)
├─ Visualize: Hex-bin density + complaint type overlay
├─ Action: "Send these 20 locations to inspection crew"
└─ Output: Map + prioritized location list
```

### 2. Complaint → Inspection Pipeline
```
LEFT JOIN: complaints.location → inspections.location (buffer 50m)
├─ Matched: "This 311 complaint was addressed by inspection"
├─ Unmatched: "This citizen report has NO SIM inspection yet (GAP)"
├─ Timespan: "Days from complaint to inspection"
└─ Dashboard: % complaint conversion, avg response time by borough
```

### 3. Complaint Type Analysis
```
Group by complaint_type (Pothole, Trip Hazard, Cracked Slab, etc.)
├─ Count by borough, community board
├─ Trend over time (is Trip Hazard increasing?)
├─ Map which complaint_types correlate with violation_types
└─ Insight: "Trip Hazards in BK are up 40% YoY → increase inspection frequency"
```

### 4. Unresolved Complaint Tracker
```
SELECT * FROM complaints WHERE status = 'Open' AND created_date > NOW() - 90 DAYS
├─ How many open complaints per borough?
├─ How old is the oldest complaint? (breach SLA if >30 days)
├─ Which complaint_types are backlogged?
└─ Weekly alert: "47 open complaints in MANHATTAN, oldest is 65 days"
```

## Integration with Existing Workflows

### Conflict Detection (Enhanced)
Instead of: permit overlaps + inspections  
Now add: 311 complaints in the same area (citizen-reported problems confirm priority)

### Hotspot Ranking (Enhanced)
Instead of: violations + cost  
Now add: # of complaints in area (citizen impact weighting)  
Example: "This block has 3 violations + 12 complaints → higher priority than block with 5 violations + 1 complaint"

### Construction List Prioritization
Rank by: violations + cost + **# unresolved complaints**  
Output: "Complete these 10 areas first (high citizen impact)"

## Implementation Order

1. **Week 1:** Add complaints dataset to DuckDB pipeline (raw → staging)
2. **Week 2:** Complaint hotspot map (hex-bin) + unresolved complaint tracker (dashboard)
3. **Week 3:** Complaint-to-inspection gap analysis (LEFT JOIN, response time SLA)
4. **Week 4:** Integrate complaint weighting into hotspot ranking + construction prioritization

## Why This Matters for Your Role

**Current situation:** You analyze violations (what DOT found) to prioritize repairs.  
**With 311:** You see **citizen demand** + **DOT findings** together. This gives you:
- **Legitimacy:** "47 people complained about this block → we inspect & fix"
- **Efficiency:** Focus on areas with highest citizen impact, not just worst conditions
- **Responsiveness:** Close the complaint-to-repair loop faster
- **Leadership insights:** "Our ramp program is working — complaints down 18% YoY"

## Data Quality Notes

- 311 complaints may have location errors (citizens can misreport location)
- Some complaints are out-of-scope (not DOT-addressable)
- Closed_date may be "report closed" not "issue resolved" (check status carefully)
- Duplicate complaints are common (same issue reported multiple times)
- Consider deduping by location + complaint_type + created_date (within 24h, <100m)
