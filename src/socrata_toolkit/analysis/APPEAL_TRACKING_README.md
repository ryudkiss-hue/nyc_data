# Appeal & Reinspection Tracking Workflow

## Overview

The Appeal & Reinspection Tracking system analyzes NYC DOT inspector performance by examining appeal and reinspection outcomes. It uses deterministic NLP classification to extract resolution patterns, identifies performance outliers requiring coaching, and surfaces systemic process issues.

**Key capabilities:**
- Appeal outcome classification (upheld/overturned/modified)
- Inspector-level performance metrics with statistical trends
- Automatic outlier detection and coaching recommendations
- Systemic process issue identification
- Claude-powered assessment (~350 tokens) for contextual analysis

---

## Architecture

### Components

#### 1. **appeal_classifier.py** (150 lines)
Deterministic spaCy-based classifier for appeal outcomes.

**Classes:**
- `AppealOutcomeClassifier` — Classifies resolution (upheld/overturned/modified) and reason (procedural_error/new_evidence/etc)
- `InspectorAppealAnalyzer` — Aggregates appeals by inspector, computes statistics, identifies outliers
- `InspectorAppealStats` (dataclass) — Per-inspector metrics with coaching recommendations

**Key Methods:**
```python
# Classify single appeal
classifier = AppealOutcomeClassifier()
result = classifier.classify("Inspector error in documentation. Appeal overturned.")
# → AppealClassificationResult with resolution, reason, confidence

# Analyze inspector performance
analyzer = InspectorAppealAnalyzer()
stats = analyzer.compute_inspector_stats(df)
# → Dict[inspector_id, InspectorAppealStats]

outliers = analyzer.identify_outliers(stats, overturn_threshold=0.25)
# → List of InspectorAppealStats for coaches

systemic = analyzer.compute_systemic_issues(df)
# → Dict with reversal_rate_by_reason, recommended_improvements
```

#### 2. **appeal_tracking_workflow.py** (220 lines)
LangGraph workflow orchestrating the full analysis pipeline.

**Nodes (in sequence):**
1. `fetch_data` — Fetch reinspection (gx72-kirf) + dismissal (p4u2-3jgx) datasets
2. `classify_appeals` — Run spaCy classifier on all appeal decision texts
3. `compute_inspector_stats` — Aggregate by inspector, compute metrics
4. `identify_outliers` — Flag high overturn rates, procedural error patterns
5. `claude_assess` — Claude API assessment of performance patterns
6. `generate_coaching_plan` — Detailed coaching recommendations for outliers
7. `generate_report` — Structured JSON report with all findings

**State Flow:**
```
Raw appeals → Classifications → Inspector Stats → Outliers → Claude → Coaching → Report
```

---

## Data Sources

| Dataset | Fourfour | Description | Notes |
|---------|----------|-------------|-------|
| `reinspection` | gx72-kirf | Follow-up inspections of flagged violations | Primary data source |
| `dismissals` | p4u2-3jgx | Appeals where violations were dismissed | Supplementary data |

**Key columns** (may vary by dataset):
- Inspector ID/name
- Decision/outcome text (for classification)
- Created date (for trend analysis)

---

## Classification Schema

### Appeal Resolution (Output)
```
UPHELD       → Original inspection decision confirmed
OVERTURNED   → Original decision reversed (appeal won)
MODIFIED     → Partial modification to original finding
INCONCLUSIVE → Unable to determine from text
```

### Appeal Reason (Output)
```
PROCEDURAL_ERROR      → Inspector error in process/documentation
NEW_EVIDENCE          → New facts/repairs made since original
JUDGMENT_CALL         → Disagreement on interpretation/severity
ADMINISTRATIVE        → Clerical or record-keeping issue
INSUFFICIENT_EVIDENCE → Lack of supporting documentation
```

### Inspector Consistency Signal
```
NORMAL        → Performance consistent with peer group
OUTLIER_HIGH  → Unusually high overturn rate (>30%)
OUTLIER_LOW   → Unusually low overturn rate (<5%)
UNRELIABLE    → Extreme variance in appeals
```

### Performance Trend
```
IMPROVING         → Fewer overturns in recent period
STABLE            → Consistent performance over time
DEGRADING         → More overturns in recent period
INSUFFICIENT_DATA → <5 appeals in analysis window
```

---

## Usage

### Option 1: Full Workflow (Recommended)

```python
from socrata_toolkit.analysis.appeal_tracking_workflow import create_appeal_tracking_workflow

# Create and run
workflow = create_appeal_tracking_workflow()
result = workflow.invoke({
    "context": None,
    "max_rows": 500,
    "include_coaching_plan": True,
    "execution_log": [],
})

# Access results
print(f"Inspectors analyzed: {len(result['inspector_stats'])}")
print(f"Outliers identified: {len(result['outliers'])}")
print(f"Claude assessment:\n{result['claude_assessment']}")
print(f"Coaching plan:\n{result['coaching_recommendations']}")
```

### Option 2: Just Classification

```python
from socrata_toolkit.analysis.appeal_classifier import AppealOutcomeClassifier

classifier = AppealOutcomeClassifier()
texts = ["Overturned due to new evidence", "Upheld, proper documentation"]
results = classifier.batch_classify(texts)

for result in results:
    print(f"{result.resolution.value}: {result.reason.value}")
```

### Option 3: Inspector Analysis Only

```python
from socrata_toolkit.analysis.appeal_classifier import InspectorAppealAnalyzer

analyzer = InspectorAppealAnalyzer()
stats = analyzer.compute_inspector_stats(
    df,
    inspector_id_col="inspector_id",
    inspector_name_col="inspector_name",
    outcome_col="decision_notes"
)

# Find outliers
outliers = analyzer.identify_outliers(stats, overturn_threshold=0.25)
for outlier in outliers:
    print(f"{outlier.inspector_name}: {outlier.overturn_rate:.1%} overturn rate")
```

---

## Output Format

### Final Report Structure

```json
{
  "timestamp": "2026-06-11T10:30:45",
  "summary": {
    "total_appeals": 156,
    "appeals_analyzed": 156,
    "inspectors_analyzed": 28,
    "outliers_identified": 5
  },
  "classification_summary": {
    "upheld": 92,
    "overturned": 48,
    "modified": 16
  },
  "outlier_performance": [
    {
      "inspector_id": "INS042",
      "inspector_name": "Agent Smith",
      "overturn_rate": 0.52,
      "total_appeals": 21,
      "reason": "High overturn rate: 52.4% (11/21)",
      "trend": "degrading"
    }
  ],
  "systemic_issues": {
    "overall_reversal_rate": 0.31,
    "reversal_rate_by_reason": {
      "procedural_error": 0.45,
      "new_evidence": 0.28,
      "judgment_call": 0.18
    },
    "recommended_improvements": [
      "Standardize inspection documentation and procedures",
      "Implement follow-up inspection requirement before closing tickets"
    ]
  },
  "claude_assessment": "...(350 tokens of analysis)...",
  "coaching_recommendations": "...(detailed plan)...",
  "next_action": "escalate_training"
}
```

---

## Coaching Recommendations Algorithm

Automatically generated based on performance signals:

| Condition | Coaching Needed | Intervention |
|-----------|-----------------|--------------|
| Overturn rate > 30% | **Yes** | Document with photos, peer review, accuracy refresher |
| Overturn rate 20-30% | **Yes** | Review severity criteria, shadowing with high performer |
| Procedural errors > 30% | **Yes** | Standardize documentation procedures |
| Trend = DEGRADING | **Yes** | Performance discussion, root cause analysis |
| Trend = IMPROVING | **No** | Recognition/reinforcement |
| Sample < 10 appeals | **Low confidence** | Continue monitoring |

---

## Systemic Process Issues

Detected patterns:
- **High procedural error rate** → Implement standardized inspection checklist
- **High new_evidence rate** → Require follow-up before closure
- **High modification rate** → Peer review process needed
- **Overall reversal rate > 25%** → Institute quality assurance gate

---

## Performance Metrics

### Inspector-Level
- **Appeal Rate**: Appeals / Total Inspections (0-1)
- **Overturn Rate**: Overturned Appeals / Total Appeals (0-1)
- **Modification Rate**: Modified Appeals / Total Appeals (0-1)
- **Upheld Rate**: Upheld Appeals / Total Appeals (0-1)
- **Trend**: Performance trajectory over time

### Reliability Scoring
- **High**: ≥20 appeals (sample size sufficient)
- **Medium**: 10-19 appeals (adequate sample)
- **Low**: <10 appeals (monitor for trends)

---

## Dependencies

**Required:**
- pandas
- langchain-anthropic (for Claude assessment)
- langgraph

**Optional (for full NLP):**
```bash
pip install -e ".[nlp]"  # Installs spacy + model
pip install -e ".[nlp,llm]"  # Also installs LLM dependencies
```

**Automatic spaCy model download:**
```bash
python -m spacy download en_core_web_sm
```

---

## Integration Points

### 1. CLI Command
```bash
socrata appeal-tracking --max-rows 500 --include-coaching --output report.json
```

### 2. Scheduled Job (APScheduler)
```python
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
scheduler.add_job(appeal_tracking_workflow, 'cron', day_of_week='mon', hour=8)
```

### 3. Streamlit Dashboard
```python
# In Mission Control views
with st.spinner("Analyzing appeals..."):
    result = workflow.invoke(state)
    st.json(result["final_report"])
```

### 4. API Endpoint (FastAPI)
```python
@router.post("/api/appeal-tracking")
async def analyze_appeals(request: AppealAnalysisRequest):
    workflow = create_appeal_tracking_workflow()
    result = workflow.invoke({...})
    return result
```

---

## Token Cost

**Typical execution:**
- Spacy classification: 0 tokens (deterministic)
- Claude assessment: 350-400 tokens
- **Total**: ~400 tokens per run

**Cost at scale:**
- 100 appeals: ~450 tokens → $0.001
- 1000 appeals: ~450 tokens → $0.001 (same assessment)
- Monthly (weekly runs): ~2K tokens → $0.004

---

## Testing

Run examples:
```bash
python -m socrata_toolkit.analysis.appeal_tracking_example
```

Example outputs:
1. Classifier test on sample texts
2. Synthetic inspector data analysis
3. Workflow structure validation
4. CLI integration patterns
5. Programmatic API examples

---

## Known Limitations

1. **Data availability**: Requires reinspection + dismissal datasets to be current
2. **Text quality**: Classification accuracy depends on decision_notes text completeness
3. **Sample size**: <10 appeals per inspector = low confidence (marked in output)
4. **Trend analysis**: Requires date column for time-series trend detection
5. **Inspector matching**: Must have consistent inspector ID across datasets

---

## Future Enhancements

- [ ] Machine learning classifier (replace spaCy keyword matching)
- [ ] Time-series forecasting for performance trends
- [ ] Root cause analysis (link appeals to violation types)
- [ ] Peer group comparison (percentile ranking)
- [ ] Automated coaching plan scheduling
- [ ] Real-time dashboard with alert thresholds

---

## Support

For questions or issues:
1. Check `appeal_tracking_example.py` for usage patterns
2. Review docstrings in `appeal_classifier.py` and `appeal_tracking_workflow.py`
3. Run with `log_level=DEBUG` for execution trace
4. File issue with sample data for debugging
