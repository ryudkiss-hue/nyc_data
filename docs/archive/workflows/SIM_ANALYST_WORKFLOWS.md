# SIM Project Analyst Workflow Framework

Complete mapping of all NYC DOT SIM unit analyst workflows, from data quality to compliance, each powered by hardcoded NLP + LangGraph + Claude.

---

## Workflow Taxonomy

```
SIM PROJECT ANALYST WORKFLOWS
├── TIER 1: OPERATIONAL (Daily/Weekly)
│   ├── 1.1 Dataset Health & Monitoring
│   ├── 1.2 Violation Triage & Prioritization
│   ├── 1.3 Ramp Progress Tracking
│   └── 1.4 Conflict Detection (Construction vs. Inspection)
│
├── TIER 2: STRATEGIC (Weekly/Monthly)
│   ├── 2.1 SLA Compliance Reporting
│   ├── 2.2 Inspection Velocity Analysis
│   ├── 2.3 Forecasting (Ramp Completion, Violations)
│   └── 2.4 Geographic Hotspot Analysis
│
├── TIER 3: COMPLIANCE & GOVERNANCE (Monthly/Quarterly)
│   ├── 3.1 Dismissal Pattern Analysis
│   ├── 3.2 Correspondence & Communication Audit
│   ├── 3.3 Appeal & Reinspection Tracking
│   └── 3.4 Legal Hold & Compliance Verification
│
├── TIER 4: CITIZEN ENGAGEMENT (On-Demand)
│   ├── 4.1 311 Complaint Response Analysis
│   ├── 4.2 Public Feedback Trends
│   └── 4.3 Community Impact Assessment
│
└── TIER 5: ADVANCED ANALYTICS (Monthly/Quarterly)
    ├── 5.1 Inspector Performance Scoring
    ├── 5.2 Predictive Breach Modeling
    ├── 5.3 Resource Allocation Optimization
    └── 5.4 Root Cause Investigation
```

---

## Workflow Details & Implementation Status

### TIER 1: OPERATIONAL WORKFLOWS

#### 1.1 Dataset Health & Monitoring

**Purpose:** Daily check that all data sources are fresh, complete, and valid.

**Inputs:**
- All 26 datasets in registry
- SLA thresholds (HIGH=14d, MED=30d, LOW=60d)

**Workflow:**
```
Fetch metadata for all datasets
    ↓
Check: Freshness (age vs SLA)
Check: Completeness (null rate)
Check: Schema stability (schema drift detection)
Check: Row count (abnormal drops)
    ↓
Claude: "Which datasets need attention?"
    ↓
Generate alerts + recommendations
```

**Output:**
- Green/Yellow/Red status per dataset
- Specific issues flagged
- Recommended actions

**Implementation:** [Status: 🚧 See section 6.1]

---

#### 1.2 Violation Triage & Prioritization

**Purpose:** Classify violations by severity and route for action.

**Classifiers Needed:**
- InspectionViolationClassifier ✅ (already built)
- By borough × severity × defect type
- By urgency (imminent danger vs. routine maintenance)

**Workflow:**
```
Fetch violations (recent)
    ↓
spaCy: Classify (0 tokens)
    ├─ Category (STRUCTURAL_DAMAGE, TRIP_HAZARD, etc.)
    ├─ Severity (0-100)
    └─ Spatial clustering
    ↓
Claude: "What needs immediate field action?"
    ↓
Route to field inspection teams
Generate daily triage report
```

**Output:**
- Prioritized inspection queue
- Borough-level breakdown
- Daily summary email

**Implementation:** [Status: ✅ COMPLETE - langgraph_triage.py]

---

#### 1.3 Ramp Progress Tracking

**Purpose:** Monitor ADA ramp completion and SLA compliance.

**Classifiers Needed:**
- RampProgressClassifier (new)
  - Completed, In Progress, Blocked, Not Started
  - Severity: Accessibility barrier level
  - Borough priorities

**Workflow:**
```
Fetch ramp_progress dataset
    ↓
spaCy: Extract status from description
    ├─ Work stage
    ├─ Percent complete
    └─ Blockers (permit delays, weather, etc.)
    ↓
Compute: Borough completion rates + CI
    ↓
Claude: "Which boroughs are behind schedule?"
    ↓
Generate weekly progress report
```

**Output:**
- Completion % by borough + confidence interval
- Trend analysis (accelerating/decelerating)
- At-risk projects (>SLA threshold)

**Implementation:** [Status: 🚧 See section 6.2]

---

#### 1.4 Conflict Detection

**Purpose:** Find geographic overlaps between construction permits and inspection sites.

**Classifiers Needed:**
- ConstructionInspectionClassifier ✅ (already built)
- Conflict severity (resource conflict vs. safety hazard)

**Workflow:**
```
Fetch: street_permits + street_construction_inspections + inspections
    ↓
spaCy: Classify construction types + urgency
    ↓
Spatial: Buffer overlap detection
    ├─ Within 50m
    ├─ Within 100m
    └─ Cluster analysis
    ↓
Claude: "Which conflicts need coordination?"
    ↓
Generate conflict report + escalations
```

**Output:**
- Geographic conflict map
- High-priority overlaps
- Recommended coordination points

**Implementation:** [Status: ✅ PARTIAL - langgraph_triage.py (spatial_analysis_node)]

---

### TIER 2: STRATEGIC WORKFLOWS

#### 2.1 SLA Compliance Reporting

**Purpose:** Monthly dashboard of service level agreement adherence.

**Classifiers Needed:**
- SLAStatusClassifier (new)
  - High/Medium/Low tier datasets
  - Breach/At-Risk/Compliant status
  - Root cause (API down, maintenance, data quality)

**Workflow:**
```
For each of 26 datasets:
    Check: Last updated date vs SLA threshold
    Classify: Breach category (if applicable)
    Track: Historical trend
    ↓
Claude: "What caused SLA breaches this month?"
    ↓
Generate: Executive summary + action items
```

**Output:**
- SLA scorecard (% on-time)
- Breach analysis + root causes
- Trend forecasting
- Recommended fixes

**Implementation:** [Status: 🚧 See section 6.3]

---

#### 2.2 Inspection Velocity Analysis

**Purpose:** Track inspection completion rate and resource efficiency.

**Classifiers Needed:**
- InspectionVelocityClassifier (new)
  - Inspector productivity (inspections/week)
  - Closure rate (% violations corrected)
  - Time-to-close trend

**Workflow:**
```
Fetch: inspections + violations + dismissals
    ↓
Group by inspector + date range
    ↓
Compute: Velocity metrics
    ├─ Inspections/week
    ├─ Violations found/inspection
    ├─ Dismissal rate
    └─ Time-to-close (days)
    ↓
Claude: "Which inspectors are underperforming? Why?"
    ↓
Generate: Inspector scorecards + coaching recommendations
```

**Output:**
- Inspector performance dashboard
- Team-level trends
- Anomaly alerts (sudden drop in productivity)

**Implementation:** [Status: 🚧 See section 6.4]

---

#### 2.3 Forecasting (Ramp Completion, Violations)

**Purpose:** Predict when ramps will be complete and when violations will be resolved.

**Classifiers Needed:**
- CompletionForecastClassifier (new)
  - Work stage + historical completion rates
  - Blockers (weather, permits, budget)
  - Confidence intervals (Bayesian)

**Workflow:**
```
Fetch: ramp_progress + historical completion data
    ↓
Analyze: Current stage + velocity
    ↓
Bayesian Model: P(completion by date)
    ├─ Historical trend
    ├─ Weather impact
    └─ Budget constraints
    ↓
Claude: "Which ramps are at risk? Why?"
    ↓
Generate: Completion timeline + risk matrix
```

**Output:**
- Ramp completion forecast (dates + CI)
- Risk assessment
- Resource reallocation recommendations

**Implementation:** [Status: 🚧 Requires Bayesian model integration]

---

#### 2.4 Geographic Hotspot Analysis

**Purpose:** Identify areas with concentrated violations or complaints.

**Classifiers Needed:**
- HotspotClassifier (new)
  - High-density violation area
  - Recurring complaint zone
  - Resource-constrained neighborhood

**Workflow:**
```
Fetch: violations + complaints_311 + inspections (all with geometry)
    ↓
Spatial: DBSCAN clustering + buffer analysis
    ↓
Classify: Hotspot severity
    ├─ Type (violation hotspot vs complaint hotspot)
    ├─ Density (violations/sq km)
    └─ Trend (growing vs shrinking)
    ↓
Claude: "Where should DOT prioritize inspections?"
    ↓
Generate: Hotspot map + resource allocation plan
```

**Output:**
- Interactive hotspot map
- Area-level summary (violations, complaints, coverage)
- Inspector routing recommendations

**Implementation:** [Status: ✅ PARTIAL - langgraph_triage.py (spatial_analysis_node)]

---

### TIER 3: COMPLIANCE & GOVERNANCE WORKFLOWS

#### 3.1 Dismissal Pattern Analysis

**Purpose:** Understand why violations are dismissed and detect anomalies.

**Classifiers Needed:**
- DismissalReasonClassifier (new)
  - Reason category (legal issue, admin error, legitimate correction, etc.)
  - Severity (low-confidence dismissal vs. justified)
  - Inspector consistency (are certain inspectors dismissed more?)

**Workflow:**
```
Fetch: dismissals + violations (joined)
    ↓
spaCy: Extract dismissal reason from text
    ├─ Category (legal, admin, justified, etc.)
    └─ Confidence score
    ↓
Analyze: Patterns
    ├─ By inspector
    ├─ By defect type
    └─ By borough
    ↓
Claude: "Which dismissals look suspicious? Why?"
    ↓
Generate: Audit report + inspector coaching
```

**Output:**
- Dismissal rate dashboard
- Anomaly flags (unusual patterns)
- Inspector audit recommendations

**Implementation:** [Status: 🚧 See section 6.5]

---

#### 3.2 Correspondence & Communication Audit

**Purpose:** Track all inspector-to-property-owner communication and compliance.

**Classifiers Needed:**
- CorrespondenceClassifier (new)
  - Message type (initial notice, follow-up, threat of penalty, etc.)
  - Tone/compliance (professional, threatening, unclear)
  - Language quality (understandable vs. technical jargon)

**Workflow:**
```
Fetch: correspondences dataset
    ↓
spaCy: Classify each message
    ├─ Type (notice, follow-up, escalation)
    ├─ Tone (professional, harsh, conciliatory)
    └─ Clarity score
    ↓
Claude: "Are communications legally compliant? Accessible?"
    ↓
Generate: Compliance audit + training recommendations
```

**Output:**
- Compliance scorecard
- Sample messages (good vs. problematic)
- Training curriculum

**Implementation:** [Status: 🚧 See section 6.6]

---

#### 3.3 Appeal & Reinspection Tracking

**Purpose:** Monitor appeal outcomes and reinspection compliance.

**Classifiers Needed:**
- AppealOutcomeClassifier (new)
  - Appeal resolution (upheld, overturned, modified)
  - Reason (new evidence, procedural error, judgment call)
  - Inspector consistency (are appeals clustered by inspector?)

**Workflow:**
```
Fetch: reinspection + dismissals (appeals)
    ↓
spaCy: Extract appeal reason
    ├─ Category (procedural, evidence, judgment)
    └─ Confidence
    ↓
Analyze: Inspector patterns
    ├─ Appeal rate by inspector
    ├─ Overturn rate
    └─ Trend
    ↓
Claude: "Which inspectors need coaching? Are there systemic issues?"
    ↓
Generate: Inspector coaching plan + process improvement
```

**Output:**
- Appeal analytics dashboard
- Inspector coaching recommendations
- Process improvement insights

**Implementation:** [Status: 🚧 See section 6.7]

---

#### 3.4 Legal Hold & Compliance Verification

**Purpose:** Ensure data retention and audit trail integrity for potential litigation.

**Classifiers Needed:**
- LegalHoldClassifier (new)
  - Record type (inspection, violation, dismissal, correspondence)
  - Sensitivity level (public, sensitive, protected)
  - Retention requirement (standard, extended for hold)

**Workflow:**
```
Fetch: All relevant records for a site/inspector/time period
    ↓
Classify: Legal sensitivity + retention requirement
    ↓
Verify: Complete audit trail exists
    ├─ All changes logged
    ├─ All communications retained
    └─ No data gaps
    ↓
Claude: "Is this dataset legally compliant and defensible?"
    ↓
Generate: Compliance certificate + recommendations
```

**Output:**
- Legal hold verification report
- Data gaps identified
- Retention policy enforcement

**Implementation:** [Status: 🚧 Requires audit logging extension]

---

### TIER 4: CITIZEN ENGAGEMENT WORKFLOWS

#### 4.1 311 Complaint Response Analysis

**Purpose:** Track how quickly and effectively 311 complaints are addressed.

**Classifiers Needed:**
- Complaint311Classifier ✅ (already built)
- ResponseTimeClassifier (new)
  - Complaint urgency
  - Time-to-response
  - Response adequacy (did it fix the issue?)

**Workflow:**
```
Fetch: complaints_311 + inspections (linked by location/date)
    ↓
spaCy: Classify complaint
    ├─ Category (sidewalk, ramp, hazard, debris)
    ├─ Urgency (emergency, high, medium, low)
    └─ Location precision
    ↓
Compute: Response metrics
    ├─ Time from complaint to inspection
    ├─ Time from inspection to resolution
    └─ Customer satisfaction (if available)
    ↓
Claude: "Are we responding fast enough? Where are the bottlenecks?"
    ↓
Generate: Response time report + process optimization
```

**Output:**
- Response time dashboard
- Bottleneck analysis
- SLA compliance (are we meeting response targets?)
- Process improvement recommendations

**Implementation:** [Status: 🚧 See section 6.8]

---

#### 4.2 Public Feedback Trends

**Purpose:** Monitor sentiment in complaints and identify systemic issues from public perspective.

**Classifiers Needed:**
- SentimentClassifier (new)
  - Tone (frustrated, angry, resigned, helpful)
  - Root cause mentioned (neglect, poor quality, lack of follow-up)
  - Repeat complaint detection

**Workflow:**
```
Fetch: complaints_311 + correspondences (public-facing)
    ↓
spaCy: Sentiment analysis + root cause extraction
    ├─ Tone (frustrated, angry, etc.)
    ├─ Mentioned causes (neglect, abandonment, etc.)
    └─ Repeat issue flag
    ↓
Aggregate: Themes
    ├─ Most common complaints
    ├─ Geographic clusters
    └─ Trend (improving vs. worsening)
    ↓
Claude: "What's driving public dissatisfaction? What should we prioritize?"
    ↓
Generate: Public sentiment report + communications strategy
```

**Output:**
- Sentiment dashboard
- Top complaint themes
- Geographic analysis
- Communications strategy

**Implementation:** [Status: 🚧 See section 6.9]

---

#### 4.3 Community Impact Assessment

**Purpose:** Measure positive impact of sidewalk improvements for community engagement.

**Classifiers Needed:**
- ImpactClassifier (new)
  - Improvement type (accessibility ramp, hazard removal, maintenance)
  - Community benefit (accessibility, safety, aesthetics)
  - Follow-on complaints (did it resolve the issue?)

**Workflow:**
```
Fetch: ramp_progress + built (completed) + complaints_311 (before/after)
    ↓
Classify: Improvement type + benefit
    ↓
Measure: Impact
    ├─ Complaints before/after completion
    ├─ Accessibility improvement
    └─ Safety incidents (reduction)
    ↓
Claude: "What's the community impact of our improvements? Should we promote this?"
    ↓
Generate: Impact report + outreach recommendations
```

**Output:**
- Impact dashboard (ramps completed → accessibility improved)
- Before/after complaint analysis
- Community outreach recommendations
- Funding justification

**Implementation:** [Status: 🚧 See section 6.10]

---

### TIER 5: ADVANCED ANALYTICS WORKFLOWS

#### 5.1 Inspector Performance Scoring

**Purpose:** Objective performance evaluation for inspectors.

**Classifiers Needed:**
- InspectorPerformanceClassifier (new)
  - Inspection quality (violations found vs. expected)
  - Accuracy (dismissal rate, appeal rate)
  - Efficiency (inspections/week)
  - Communication quality (tone, clarity)

**Workflow:**
```
Fetch: inspections + violations + dismissals + correspondences
    ↓
Group by inspector
    ↓
Compute: Multi-dimensional scorecard
    ├─ Inspection velocity (inspections/week)
    ├─ Violation detection rate (violations found/inspection)
    ├─ Dismissal rate (% violations dismissed later)
    ├─ Appeal rate (% of dismissals appealed)
    ├─ Reversal rate (% of appeals successful)
    ├─ Time-to-closure (days to resolution)
    └─ Communication quality (spaCy tone analysis)
    ↓
Claude: "Who's high-performing? Who needs coaching? Any fairness issues?"
    ↓
Generate: Inspector scorecards + coaching recommendations
```

**Output:**
- Objective performance scorecards
- Relative ranking
- Coaching recommendations
- Team-level trends

**Implementation:** [Status: 🚧 See section 6.11]

---

#### 5.2 Predictive Breach Modeling

**Purpose:** Forecast which datasets or inspectors will violate SLA in the coming month.

**Classifiers Needed:**
- BreachPredictionClassifier (new)
  - Dataset health trajectory
  - Inspector workload + velocity trend
  - Seasonal factors (weather, budget cycles)

**Workflow:**
```
Fetch: Historical SLA data + trends
    ↓
Bayesian Model: P(breach in next 30 days)
    ├─ Current staleness
    ├─ Historical trend (getting worse/better)
    ├─ Seasonal pattern (summer slowdown, etc.)
    └─ Budget constraints (affects fieldwork)
    ↓
Claude: "Which datasets/inspectors are at risk? What's the root cause?"
    ↓
Generate: Risk matrix + mitigation plan
```

**Output:**
- Breach probability forecast
- Root cause analysis
- Mitigation strategies
- Early warning alerts

**Implementation:** [Status: 🚧 Requires Bayesian model]

---

#### 5.3 Resource Allocation Optimization

**Purpose:** Recommend where to deploy inspectors for maximum impact.

**Classifiers Needed:**
- ResourceAllocationClassifier (new)
  - Violation density (violations/sq km)
  - Response time (current vs. target)
  - Inspector availability
  - Geographic coverage gaps

**Workflow:**
```
Fetch: violations + inspections + inspector locations
    ↓
Spatial: Compute hotspot density + coverage gaps
    ↓
Classify: Allocation priority
    ├─ High-density, slow-response areas (dispatch inspectors)
    ├─ Remote areas (consider mobile units)
    └─ Over-resourced areas (redeploy)
    ↓
Claude: "How should we redeploy inspectors for better coverage?"
    ↓
Generate: Reallocation plan + efficiency gains
```

**Output:**
- Resource allocation heatmap
- Redeployment recommendations
- Efficiency impact (projected violations/inspector)
- Cost-benefit analysis

**Implementation:** [Status: 🚧 See section 6.12]

---

#### 5.4 Root Cause Investigation

**Purpose:** Deep-dive into specific incidents (spike, anomaly, complaint pattern).

**Classifiers Needed:**
- RootCauseClassifier (new)
  - Issue type (data quality, process, resource, external)
  - Confidence level
  - Related factors (weather, staffing, budget)

**Workflow:**
```
User specifies: "Why did violations spike in Brooklyn last month?"
    ↓
Fetch: All relevant data (violations, inspections, permits, weather, budget)
    ↓
Analyze: Temporal + spatial patterns
    ├─ Correlation with construction (permits spike?)
    ├─ Inspector staffing changes?
    ├─ Weather factors (rain → more complaints)?
    └─ Data quality issues (recent system change)?
    ↓
Claude: "What's the root cause? What should we do?"
    ↓
Generate: Investigation report + recommendations
```

**Output:**
- Root cause analysis
- Contributing factors
- Recommendations
- Preventive measures

**Implementation:** [Status: 🚧 See section 6.13]

---

## Implementation Roadmap

### Phase 1: Core Workflows (2 weeks) ✅ COMPLETE
- [x] 1.2 Violation Triage (langgraph_triage.py)
- [x] 1.4 Conflict Detection (spatial_analysis in langgraph_triage.py)

### Phase 2: Operational Dashboards (3 weeks) 🚧 IN PROGRESS
- [ ] 1.1 Dataset Health & Monitoring
- [ ] 1.3 Ramp Progress Tracking
- [ ] 2.1 SLA Compliance Reporting
- [ ] 2.2 Inspection Velocity Analysis

### Phase 3: Strategic Analytics (4 weeks) 🚧 PLANNED
- [ ] 2.3 Forecasting (Ramp, Violations)
- [ ] 2.4 Geographic Hotspot Analysis
- [ ] 5.3 Resource Allocation Optimization

### Phase 4: Compliance & Governance (3 weeks) 🚧 PLANNED
- [ ] 3.1 Dismissal Pattern Analysis
- [ ] 3.2 Correspondence Audit
- [ ] 3.3 Appeal Tracking
- [ ] 3.4 Legal Hold Verification

### Phase 5: Citizen Engagement (2 weeks) 🚧 PLANNED
- [ ] 4.1 311 Response Analysis
- [ ] 4.2 Public Sentiment Tracking
- [ ] 4.3 Community Impact Assessment

### Phase 6: Advanced Analytics (4 weeks) 🚧 PLANNED
- [ ] 5.1 Inspector Performance Scoring
- [ ] 5.2 Breach Prediction
- [ ] 5.4 Root Cause Investigation

**Total effort:** ~16 weeks for all 22 workflows  
**Estimated code:** ~8,000 lines (2,350 already written)

---

## Architecture for All Workflows

All workflows follow the same pattern:

```python
# Each workflow is a LangGraph state machine
from langgraph.graph import StateGraph

# Step 1: Define workflow-specific state
class WorkflowState(dict):
    """Custom state for this workflow"""
    pass

# Step 2: Define nodes (fetch, classify, analyze, decide)
def fetch_data(state):
    # Get data from Socrata
    pass

def classify_records(state):
    # Use hardcoded spaCy classifier
    # 0 tokens, ~100ms
    pass

def analyze(state):
    # Hardcoded analysis (spatial, aggregation, etc.)
    # 0 tokens
    pass

def claude_decision(state):
    # Claude reads hardcoded facts, makes decision
    # ~300-500 tokens
    pass

def generate_report(state):
    # Final Claude synthesis
    # ~400-600 tokens
    pass

# Step 3: Build graph
graph = StateGraph(WorkflowState)
graph.add_node("fetch", fetch_data)
graph.add_node("classify", classify_records)
# ... etc

# Step 4: Expose as public API
def run_workflow(param1, param2, ...):
    state = WorkflowState()
    state["context"] = WorkflowContext(param1, param2, ...)
    workflow = build_workflow()
    return workflow.invoke(state)
```

Each workflow:
- Costs **~700-1000 tokens** (Claude only at decision points)
- Takes **~2-5 seconds** (mostly API latency)
- Produces **structured output** (dashboards, reports, recommendations)
- Is **fully auditable** (execution_log in state)

---

## Integration Points

All workflows connect to:

1. **Socrata API** (data source)
2. **spaCy** (text classification, 0 tokens)
3. **Claude** (interpretation/decision, ~700 tokens/workflow)
4. **Spatial tools** (geographic analysis)
5. **Reporting layer** (dashboards, PDFs, alerts)

Unified CLI:
```bash
python -m socrata_toolkit.analysis.sim_workflows violations-triage --limit 1000
python -m socrata_toolkit.analysis.sim_workflows dataset-health --check-all
python -m socrata_toolkit.analysis.sim_workflows ramp-progress --borough MN
python -m socrata_toolkit.analysis.sim_workflows inspector-performance --month 2026-06
python -m socrata_toolkit.analysis.sim_workflows root-cause --issue "violations-spike-brooklyn"
```

Unified Python API:
```python
from socrata_toolkit.analysis.sim_workflows import run_workflow

result = run_workflow("violations-triage", max_rows=1000)
result = run_workflow("dataset-health", check_all=True)
result = run_workflow("inspector-performance", month="2026-06")
```

---

## Next: Implement Phase 2

Ready to build the remaining 10 Phase 2 workflows?

Each workflow takes ~3-4 hours:
1. Design classifier (keyword-based like we did for violations)
2. Build LangGraph workflow (6 nodes, 100-150 lines)
3. Wire CLI entry point
4. Test with sample data

Should I start with:
- [ ] 1.1 Dataset Health & Monitoring (impacts all other workflows)
- [ ] 1.3 Ramp Progress (high priority for program managers)
- [ ] 2.1 SLA Compliance (daily priority for ops)
- [ ] All of the above (comprehensive)

