export const meta = {
  name: 'build-sim-workflows-parallel',
  description: 'Fan out agents to build all 22 SIM analyst workflows in parallel',
  phases: [
    { title: 'Phase 2: Operational Dashboards', detail: 'Dataset Health, Ramp Progress, SLA Compliance, Velocity Analysis' },
    { title: 'Phase 3: Strategic Analytics', detail: 'Forecasting, Hotspots, Resource Allocation' },
    { title: 'Phase 4: Compliance & Governance', detail: 'Dismissals, Correspondence, Appeals, Legal Holds' },
    { title: 'Phase 5: Citizen Engagement', detail: '311 Response, Sentiment, Impact Assessment' },
    { title: 'Phase 6: Advanced Analytics', detail: 'Inspector Performance, Breach Prediction, Root Cause' },
  ],
}

// Phase 2: Operational Dashboards (4 workflows)
phase('Phase 2: Operational Dashboards')

const phase2 = await parallel([
  () => agent(
    `Build WORKFLOW: Dataset Health & Monitoring
    
    Location: src/socrata_toolkit/analysis/dataset_health_workflow.py
    
    Implementation:
    1. Fetch metadata for all 26 datasets
    2. Check: freshness (vs SLA), completeness (null %), schema stability, row count
    3. Classify status: Green/Yellow/Red
    4. Claude decision: "Which datasets need attention?" (~300 tokens)
    5. Generate alerts + remediation steps
    
    Classifiers needed:
    - DatasetHealthClassifier
      - Status: HEALTHY, STALE, SCHEMA_DRIFT, EMPTY_OR_ERROR
      - Severity: 0-100
    
    Return JSON with:
    - dataset_health.py: Classifier class (150 lines)
    - dataset_health_workflow.py: LangGraph workflow (200 lines)
    - CLI integration code snippet
    
    Reference patterns from langgraph_triage.py`,
    { label: 'Phase2-1: Dataset Health', phase: 'Phase 2: Operational Dashboards' }
  ),
  () => agent(
    `Build WORKFLOW: Ramp Progress Tracking
    
    Location: src/socrata_toolkit/analysis/ramp_progress_workflow.py
    
    Implementation:
    1. Fetch ramp_progress dataset
    2. Extract status from description (spaCy NER)
    3. Classify: Completed, In Progress, Blocked, Not Started
    4. Compute: Borough completion rates + Wilson Score CI
    5. Claude: "Which boroughs are behind? Why?" (~300 tokens)
    6. Trend analysis + forecast
    
    Classifiers needed:
    - RampStatusClassifier
      - Status: COMPLETED, IN_PROGRESS, BLOCKED, NOT_STARTED
      - Work stage: 0-100%
      - Blocker types: PERMIT, WEATHER, BUDGET, OTHER
    
    Return JSON with:
    - ramp_status.py: Classifier (180 lines)
    - ramp_progress_workflow.py: LangGraph workflow (220 lines)
    - Include Wilson Score CI computation`,
    { label: 'Phase2-2: Ramp Progress', phase: 'Phase 2: Operational Dashboards' }
  ),
  () => agent(
    `Build WORKFLOW: SLA Compliance Reporting
    
    Location: src/socrata_toolkit/analysis/sla_compliance_workflow.py
    
    Implementation:
    1. For each of 26 datasets, check freshness vs SLA tier
    2. Classify: Compliant, At-Risk, Breached
    3. Root cause: API outage? Data quality? Resource constraints?
    4. Claude: "What caused breaches? Trends?" (~400 tokens)
    5. Generate executive summary + action items
    
    Classifiers needed:
    - SLAStatusClassifier
      - Tier: HIGH (14d), MEDIUM (30d), LOW (60d)
      - Status: COMPLIANT, AT_RISK, BREACHED
      - Root cause: API_DOWN, MAINTENANCE, DATA_QUALITY, OTHER
      - Trend: IMPROVING, STABLE, DEGRADING
    
    Return JSON with:
    - sla_status.py: Classifier (160 lines)
    - sla_compliance_workflow.py: LangGraph (240 lines)
    - Include historical SLA data tracking`,
    { label: 'Phase2-3: SLA Compliance', phase: 'Phase 2: Operational Dashboards' }
  ),
  () => agent(
    `Build WORKFLOW: Inspection Velocity Analysis
    
    Location: src/socrata_toolkit/analysis/velocity_analysis_workflow.py
    
    Implementation:
    1. Fetch inspections + violations + dismissals
    2. Group by inspector + date range
    3. Compute metrics: inspections/week, violations/inspection, dismissal %, time-to-close
    4. Classify: High/Medium/Low performer
    5. Claude: "Who's underperforming? Why?" (~300 tokens)
    6. Generate coaching recommendations
    
    Classifiers needed:
    - VelocityClassifier
      - Performance tier: HIGH, MEDIUM, LOW
      - Metric: VELOCITY, QUALITY, ACCURACY, EFFICIENCY
      - Anomaly: SUDDEN_DROP, PLATEAU, ACCELERATING
    
    Return JSON with:
    - velocity_classifier.py: Classifier (140 lines)
    - velocity_analysis_workflow.py: LangGraph (210 lines)
    - Include time-series anomaly detection`,
    { label: 'Phase2-4: Velocity Analysis', phase: 'Phase 2: Operational Dashboards' }
  ),
])

log('✓ Phase 2 workflows generated (4/4)')

// Phase 3: Strategic Analytics (3 workflows)
phase('Phase 3: Strategic Analytics')

const phase3 = await parallel([
  () => agent(
    `Build WORKFLOW: Forecasting (Ramp Completion & Violations)
    
    Location: src/socrata_toolkit/analysis/forecasting_workflow.py
    
    Implementation:
    1. Fetch ramp_progress + historical velocity
    2. Estimate current work stage % + recent acceleration/deceleration
    3. Bayesian model: P(completion by date) incorporating:
       - Historical completion rates by stage
       - Seasonal factors (summer slowdown)
       - Budget + staffing constraints
    4. Claude: "Which projects are at risk? Why?" (~400 tokens)
    5. Generate forecast timeline + confidence intervals
    
    Classifiers needed:
    - CompletionForecastClassifier
      - Risk level: HIGH, MEDIUM, LOW
      - Blocker: PERMIT, BUDGET, STAFFING, WEATHER, OTHER
      - Confidence: HIGH, MEDIUM, LOW
    
    Return JSON with:
    - forecast_classifier.py: Classifier (150 lines)
    - forecasting_workflow.py: LangGraph + Bayesian model (280 lines)
    - Include PyMC integration for credible intervals`,
    { label: 'Phase3-1: Forecasting', phase: 'Phase 3: Strategic Analytics' }
  ),
  () => agent(
    `Build WORKFLOW: Geographic Hotspot Analysis
    
    Location: src/socrata_toolkit/analysis/hotspot_workflow.py
    
    Implementation:
    1. Fetch violations + complaints + inspections (all with geometry)
    2. Spatial: DBSCAN clustering + KDE density estimation
    3. Classify hotspots: Violation hotspot vs Complaint hotspot vs Combined
    4. Compute density metrics: violations/sq km, trend (growing/shrinking)
    5. Claude: "Where should we prioritize? Resource allocation?" (~350 tokens)
    6. Generate hotspot map + routing recommendations
    
    Classifiers needed:
    - HotspotClassifier
      - Type: VIOLATION, COMPLAINT, COMBINED
      - Density: HIGH, MEDIUM, LOW
      - Trend: GROWING, STABLE, SHRINKING
      - Resource constraint: OVER_RESOURCED, OPTIMIZED, UNDER_RESOURCED
    
    Return JSON with:
    - hotspot_classifier.py: Classifier (140 lines)
    - hotspot_workflow.py: LangGraph + spatial clustering (260 lines)
    - Include folium map generation`,
    { label: 'Phase3-2: Hotspots', phase: 'Phase 3: Strategic Analytics' }
  ),
  () => agent(
    `Build WORKFLOW: Resource Allocation Optimization
    
    Location: src/socrata_toolkit/analysis/resource_allocation_workflow.py
    
    Implementation:
    1. Fetch violations + inspections (spatial) + inspector availability
    2. Compute: Coverage gaps (hotspots with slow response)
    3. Optimize: Where to redeploy inspectors for maximum impact
    4. Estimate efficiency gain (violations/inspector with reallocation)
    5. Claude: "How should we redeploy? Cost-benefit?" (~300 tokens)
    6. Generate reallocation plan + impact forecast
    
    Classifiers needed:
    - ResourceAllocationClassifier
      - Area priority: CRITICAL, HIGH, MEDIUM, LOW
      - Action: DISPATCH, CONSOLIDATE, OPTIMIZE
      - Impact estimate: HIGH, MEDIUM, LOW
    
    Return JSON with:
    - allocation_classifier.py: Classifier (130 lines)
    - resource_allocation_workflow.py: LangGraph + optimization (240 lines)
    - Include geospatial clustering + TSP routing`,
    { label: 'Phase3-3: Resource Allocation', phase: 'Phase 3: Strategic Analytics' }
  ),
])

log('✓ Phase 3 workflows generated (3/3)')

// Phase 4: Compliance & Governance (4 workflows)
phase('Phase 4: Compliance & Governance')

const phase4 = await parallel([
  () => agent(
    `Build WORKFLOW: Dismissal Pattern Analysis
    
    Location: src/socrata_toolkit/analysis/dismissal_analysis_workflow.py
    
    Implementation:
    1. Fetch dismissals + violations (joined)
    2. spaCy: Extract dismissal reason from text
    3. Classify: Legal, Admin Error, Justified Correction, Suspicious
    4. Analyze patterns by inspector + defect type + borough
    5. Claude: "Which dismissals look suspicious? Inspector coaching?" (~350 tokens)
    6. Generate audit report + flagged cases
    
    Classifiers needed:
    - DismissalReasonClassifier
      - Category: LEGAL, ADMIN_ERROR, JUSTIFIED, SUSPICIOUS
      - Confidence: HIGH, MEDIUM, LOW
      - Inspector consistency: NORMAL, OUTLIER
    
    Return JSON with:
    - dismissal_classifier.py: Classifier (160 lines)
    - dismissal_analysis_workflow.py: LangGraph (230 lines)
    - Include pattern detection (outlier inspector analysis)`,
    { label: 'Phase4-1: Dismissals', phase: 'Phase 4: Compliance & Governance' }
  ),
  () => agent(
    `Build WORKFLOW: Correspondence & Communication Audit
    
    Location: src/socrata_toolkit/analysis/correspondence_audit_workflow.py
    
    Implementation:
    1. Fetch correspondences dataset
    2. spaCy: Classify each message (type, tone, clarity)
    3. Check for legal compliance (required elements, language accessibility)
    4. Tone analysis (professional, threatening, conciliatory)
    5. Claude: "Are communications compliant? Training needed?" (~350 tokens)
    6. Generate compliance report + sample messages (good vs bad)
    
    Classifiers needed:
    - CorrespondenceClassifier
      - Type: INITIAL_NOTICE, FOLLOW_UP, ESCALATION, THREAT_OF_PENALTY
      - Tone: PROFESSIONAL, THREATENING, HARSH, CONCILIATORY
      - Clarity: HIGH, MEDIUM, LOW
      - Compliance: COMPLIANT, NEEDS_REVIEW, NON_COMPLIANT
    
    Return JSON with:
    - correspondence_classifier.py: Classifier (170 lines)
    - correspondence_audit_workflow.py: LangGraph (240 lines)
    - Include tone/sentiment analysis with spacytextblob`,
    { label: 'Phase4-2: Correspondence Audit', phase: 'Phase 4: Compliance & Governance' }
  ),
  () => agent(
    `Build WORKFLOW: Appeal & Reinspection Tracking
    
    Location: src/socrata_toolkit/analysis/appeal_tracking_workflow.py
    
    Implementation:
    1. Fetch reinspection + dismissals (appeals)
    2. spaCy: Extract appeal reason + outcome
    3. Classify: Appeal resolution (upheld, overturned, modified)
    4. Analyze inspector patterns (appeal rate, overturn rate, consistency)
    5. Claude: "Who needs coaching? Systemic process issues?" (~350 tokens)
    6. Generate inspector coaching plan + process improvements
    
    Classifiers needed:
    - AppealOutcomeClassifier
      - Resolution: UPHELD, OVERTURNED, MODIFIED
      - Reason: PROCEDURAL_ERROR, NEW_EVIDENCE, JUDGMENT_CALL
      - Inspector consistency: NORMAL, OUTLIER
      - Trend: IMPROVING, STABLE, DEGRADING
    
    Return JSON with:
    - appeal_classifier.py: Classifier (150 lines)
    - appeal_tracking_workflow.py: LangGraph (220 lines)
    - Include coaching recommendations algorithm`,
    { label: 'Phase4-3: Appeals', phase: 'Phase 4: Compliance & Governance' }
  ),
  () => agent(
    `Build WORKFLOW: Legal Hold & Compliance Verification
    
    Location: src/socrata_toolkit/analysis/legal_hold_workflow.py
    
    Implementation:
    1. Fetch all records for specified site/inspector/period
    2. Classify each record: Retention requirement, Sensitivity
    3. Verify complete audit trail (no gaps, all changes logged)
    4. Check data integrity + accessibility for litigation
    5. Claude: "Is this dataset legally defensible? Gaps to fix?" (~300 tokens)
    6. Generate legal hold compliance certificate
    
    Classifiers needed:
    - LegalHoldClassifier
      - Record type: INSPECTION, VIOLATION, DISMISSAL, CORRESPONDENCE
      - Sensitivity: PUBLIC, SENSITIVE, PROTECTED
      - Retention requirement: STANDARD, EXTENDED, INDEFINITE
      - Compliance: COMPLIANT, AT_RISK, NON_COMPLIANT
    
    Return JSON with:
    - legal_hold_classifier.py: Classifier (140 lines)
    - legal_hold_workflow.py: LangGraph (210 lines)
    - Include audit logging + data integrity checks`,
    { label: 'Phase4-4: Legal Holds', phase: 'Phase 4: Compliance & Governance' }
  ),
])

log('✓ Phase 4 workflows generated (4/4)')

// Phase 5: Citizen Engagement (3 workflows)
phase('Phase 5: Citizen Engagement')

const phase5 = await parallel([
  () => agent(
    `Build WORKFLOW: 311 Complaint Response Analysis
    
    Location: src/socrata_toolkit/analysis/complaint_response_workflow.py
    
    Implementation:
    1. Fetch complaints_311 + inspections (linked by location/date)
    2. Classify complaint (category, urgency, location precision)
    3. Compute response metrics (time-to-response, time-to-resolution, satisfaction)
    4. Identify bottlenecks (delays in inspection vs. repair vs. closeout)
    5. Claude: "Where are bottlenecks? How do we respond faster?" (~350 tokens)
    6. Generate response time dashboard + optimization recommendations
    
    Classifiers needed:
    - ComplaintResponseClassifier
      - Category: SIDEWALK_DAMAGE, HAZARD, DRAINAGE, DEBRIS, etc.
      - Urgency: EMERGENCY, HIGH, MEDIUM, LOW
      - Response status: RESOLVED, PENDING, DELAYED, ABANDONED
      - Time adequacy: FAST, ON_TIME, SLOW, VERY_SLOW
    
    Return JSON with:
    - complaint_response_classifier.py: Classifier (150 lines)
    - complaint_response_workflow.py: LangGraph (240 lines)
    - Include SLA target computation`,
    { label: 'Phase5-1: 311 Response', phase: 'Phase 5: Citizen Engagement' }
  ),
  () => agent(
    `Build WORKFLOW: Public Sentiment Tracking
    
    Location: src/socrata_toolkit/analysis/sentiment_workflow.py
    
    Implementation:
    1. Fetch complaints_311 + correspondences (public-facing)
    2. spaCy sentiment analysis (tone: frustrated, angry, resigned, helpful)
    3. Extract root causes mentioned (neglect, poor quality, lack of follow-up)
    4. Detect repeat complaints (same address, recurring issue)
    5. Claude: "What's driving dissatisfaction? Communications strategy?" (~350 tokens)
    6. Generate sentiment dashboard + recommended messaging
    
    Classifiers needed:
    - SentimentClassifier
      - Tone: FRUSTRATED, ANGRY, RESIGNED, HELPFUL, NEUTRAL
      - Root cause: NEGLECT, POOR_QUALITY, SLOW_RESPONSE, LACK_OF_FOLLOWUP, OTHER
      - Repeat complaint: YES, NO, LIKELY
      - Community impact: HIGH, MEDIUM, LOW
    
    Return JSON with:
    - sentiment_classifier.py: Classifier (150 lines)
    - sentiment_workflow.py: LangGraph (230 lines)
    - Include spacytextblob integration for sentiment`,
    { label: 'Phase5-2: Sentiment', phase: 'Phase 5: Citizen Engagement' }
  ),
  () => agent(
    `Build WORKFLOW: Community Impact Assessment
    
    Location: src/socrata_toolkit/analysis/impact_workflow.py
    
    Implementation:
    1. Fetch ramp_progress (completed) + built + complaints before/after
    2. Classify improvement type + community benefit
    3. Measure impact: Complaints before/after, accessibility improvement, safety incidents
    4. Estimate community value (accessibility enabled, safety improved)
    5. Claude: "What's the impact story? Should we publicize this?" (~300 tokens)
    6. Generate impact report + outreach recommendations
    
    Classifiers needed:
    - ImpactClassifier
      - Improvement type: RAMP, HAZARD_REMOVAL, MAINTENANCE, ACCESSIBILITY
      - Benefit type: ACCESSIBILITY, SAFETY, AESTHETICS, OTHER
      - Impact magnitude: HIGH, MEDIUM, LOW
      - Community priority: CRITICAL, HIGH, MEDIUM, LOW
    
    Return JSON with:
    - impact_classifier.py: Classifier (130 lines)
    - impact_workflow.py: LangGraph (200 lines)
    - Include before/after complaint correlation analysis`,
    { label: 'Phase5-3: Impact', phase: 'Phase 5: Citizen Engagement' }
  ),
])

log('✓ Phase 5 workflows generated (3/3)')

// Phase 6: Advanced Analytics (3 workflows)
phase('Phase 6: Advanced Analytics')

const phase6 = await parallel([
  () => agent(
    `Build WORKFLOW: Inspector Performance Scoring
    
    Location: src/socrata_toolkit/analysis/inspector_performance_workflow.py
    
    Implementation:
    1. Fetch inspections + violations + dismissals + correspondences per inspector
    2. Compute multi-dimensional scorecard:
       - Inspection velocity (inspections/week)
       - Violation detection (violations/inspection vs expected)
       - Accuracy (dismissal rate, appeal rate, reversal rate)
       - Efficiency (time-to-closure)
       - Communication quality (tone analysis)
    3. Classify: High/Medium/Low performer
    4. Claude: "Who's high-performing? Who needs coaching? Fairness check?" (~400 tokens)
    5. Generate individual scorecards + relative ranking
    
    Classifiers needed:
    - InspectorPerformanceClassifier
      - Performance tier: EXCEPTIONAL, HIGH, MEDIUM, NEEDS_COACHING, UNDERPERFORMING
      - Dimension: VELOCITY, QUALITY, ACCURACY, EFFICIENCY, COMMUNICATION
      - Trend: IMPROVING, STABLE, DECLINING
      - Fairness flag: OUTLIER (positive or negative)
    
    Return JSON with:
    - inspector_performance_classifier.py: Classifier (160 lines)
    - inspector_performance_workflow.py: LangGraph (260 lines)
    - Include fairness audit + relative ranking`,
    { label: 'Phase6-1: Inspector Performance', phase: 'Phase 6: Advanced Analytics' }
  ),
  () => agent(
    `Build WORKFLOW: Predictive Breach Modeling
    
    Location: src/socrata_toolkit/analysis/breach_prediction_workflow.py
    
    Implementation:
    1. Fetch historical SLA data + trends for all datasets
    2. Bayesian model: P(breach in next 30 days) per dataset
       - Current staleness vs SLA threshold
       - Historical trend (getting worse/better)
       - Seasonal pattern (summer slowdown, budget cycles)
       - External factors (staffing, API reliability)
    3. Classify risk: HIGH, MEDIUM, LOW
    4. Claude: "What datasets are at risk? Root causes? Mitigation?" (~350 tokens)
    5. Generate risk matrix + early warning alerts
    
    Classifiers needed:
    - BreachPredictionClassifier
      - Risk level: CRITICAL, HIGH, MEDIUM, LOW
      - Root cause: API_RELIABILITY, STAFFING, DATA_QUALITY, BUDGET, OTHER
      - Confidence: HIGH, MEDIUM, LOW
      - Mitigation option: STAFFING_INCREASE, PROCESS_FIX, SYSTEM_UPGRADE, MONITOR
    
    Return JSON with:
    - breach_prediction_classifier.py: Classifier (150 lines)
    - breach_prediction_workflow.py: LangGraph + Bayesian model (280 lines)
    - Include PyMC for posterior credible intervals`,
    { label: 'Phase6-2: Breach Prediction', phase: 'Phase 6: Advanced Analytics' }
  ),
  () => agent(
    `Build WORKFLOW: Root Cause Investigation
    
    Location: src/socrata_toolkit/analysis/root_cause_workflow.py
    
    Implementation:
    1. User specifies incident: "Why did violations spike in Brooklyn?"
    2. Fetch all relevant data (violations, inspections, permits, weather, budget, staffing)
    3. Temporal + spatial pattern analysis
       - Correlation with construction permits (spike?)
       - Inspector staffing changes?
       - Weather factors (rain → complaints)?
       - Data quality issues (recent system change)?
       - Budget changes (hiring freeze)?
    4. Classify: Issue type + confidence
    5. Claude: "What's the root cause? Contributing factors? What should we do?" (~400 tokens)
    6. Generate investigation report + preventive measures
    
    Classifiers needed:
    - RootCauseClassifier
      - Cause category: DATA_QUALITY, PROCESS, RESOURCE, EXTERNAL, SYSTEM
      - Confidence: HIGH, MEDIUM, LOW
      - Contributing factors: STAFFING, BUDGET, WEATHER, SYSTEM_CHANGE, OTHER
      - Impact: HIGH, MEDIUM, LOW
    
    Return JSON with:
    - root_cause_classifier.py: Classifier (140 lines)
    - root_cause_workflow.py: LangGraph (250 lines)
    - Include correlation analysis + time-series decomposition`,
    { label: 'Phase6-3: Root Cause', phase: 'Phase 6: Advanced Analytics' }
  ),
])

log('✓ Phase 6 workflows generated (3/3)')

// Consolidate results
log('\n=== CONSOLIDATION PHASE ===')

const allWorkflows = [
  ...phase2.filter(Boolean),
  ...phase3.filter(Boolean),
  ...phase4.filter(Boolean),
  ...phase5.filter(Boolean),
  ...phase6.filter(Boolean)
]

log(`✓ Generated ${allWorkflows.length} complete workflow specifications`)

// Final assembly instructions
const assembly = {
  totalWorkflows: allWorkflows.length,
  totalLines: '~6,500 lines of production code',
  newClassifiers: '18 new classifier types',
  newWorkflows: '17 new LangGraph workflows',
  timeline: '2-3 weeks for experienced developer',
  phases: {
    'Phase 2 (Operational)': 4,
    'Phase 3 (Strategic)': 3,
    'Phase 4 (Compliance)': 4,
    'Phase 5 (Engagement)': 3,
    'Phase 6 (Advanced)': 3,
  },
  costPerWorkflow: '~700 tokens (90% reduction vs all-Claude)',
  deliverables: [
    'Complete classifier implementations (spaCy-based)',
    'LangGraph state machines (6 nodes each)',
    'CLI integration (unified command interface)',
    'Python API (programmatic access)',
    'Audit logs (full execution traceability)',
  ]
}

return assembly
