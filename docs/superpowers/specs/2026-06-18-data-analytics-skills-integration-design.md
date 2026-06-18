# Data Analytics Skills Integration Design

**Date:** 2026-06-18  
**Project:** NYC DOT Data Analytics Skills Optimization & Integration  
**Scope:** All 31 skills across 6 categories  
**Timeline:** 6 weeks (3 phases)  
**Owner:** Analytics Engineering Team  

---

## Executive Summary

This design addresses five integration bottlenecks in the 31 data analytics skills:
1. **Context loss** — NYC DOT context (boroughs, datasets, metrics) inconsistent across skills
2. **Discovery gap** — Analysts don't know which skill to use for their task
3. **Activation gap** — Skills require manual context injection
4. **Chaining gap** — Outputs don't feed into next skill automatically
5. **Compliance gap** — No audit trail of what context was applied

**Solution:** Configuration-driven integration system deployed in 3 phases:
- **Phase 1 (Weeks 1-2):** Unified config system — single source of truth for NYC DOT context
- **Phase 2 (Weeks 3-4):** Skill registry & auto-chaining — outputs feed into inputs automatically
- **Phase 3 (Weeks 5-6):** Discovery & templates — automatic recommendations + pre-built workflows

**Result:** Analysts can run sophisticated multi-skill workflows with zero context loss, full audit compliance, and automatic guidance on what to do next.

---

## Problem Statement

### Current State (Before)

**31 skills exist independently:**
- Each has own hardcoded assumptions about borough names, dataset IDs, metric definitions
- Outputs require manual copy/paste to feed into next skill
- No systematic way to know which skill to use next
- NYC DOT context scattered across YAML files, Python scripts, template comments
- No audit trail of what context was applied to each analysis

**Example workflow breakdown:**
```
1. Run programmatic-eda
   → Produces: quality_report.md, findings_summary.md

2. Manually copy findings_summary into data-quality-audit
   → Context loss: SLA thresholds might be different, borough naming might be inconsistent
   
3. Analyst thinks "what do I do next?"
   → No recommendation system

4. Discovery: no audit trail of what context was used
   → Can't reproduce analysis with different contexts
```

**Impact:**
- ❌ Analysts spend 20-30% of time on context setup, not analysis
- ❌ Context inconsistencies lead to contradictory findings
- ❌ No compliance audit trail for regulatory requirements
- ❌ New analysts struggle to understand which skill to use when

### Desired State (After)

**Unified, integrated system:**
- ✅ Single source of truth for all NYC DOT context
- ✅ Skills automatically pull context at runtime
- ✅ Outputs feed into next skill with zero manual intervention
- ✅ System recommends what skill to use next
- ✅ Pre-built workflows for common tasks (new dataset assessment, metric investigation, borough comparison)
- ✅ Full audit trail of every analysis run

**Example workflow (optimized):**
```
1. Run programmatic-eda
   → Automatically uses NYC DOT context from config
   → Produces: quality_report.md, findings_summary.md

2. System suggests: "Next you could run: data-quality-audit, cohort-analysis, or semantic-model-builder"
   → Analyst chooses data-quality-audit
   → Outputs from EDA automatically fed as inputs

3. Run data-quality-audit
   → Uses same context, same borough definitions, same metrics
   → Produces: audit_scorecard.md, remediation_plan.md

4. System logs entire workflow with full context audit trail
   → "Analysis ID: xyz | Skills: [programmatic-eda → data-quality-audit] | Context: {datasets: [inspection], boroughs: [MN, BX, BK, QN, SI], quality_weights: {...}}"
```

**Impact:**
- ✅ Analysts save 20-30% of time on context setup
- ✅ Zero context inconsistencies
- ✅ Full compliance audit trail for every analysis
- ✅ New analysts have guided, recommended skill sequences

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│         UNIFIED CONFIG SYSTEM (Single Source)           │
├─────────────────────────────────────────────────────────┤
│ • config/datasets.json (57 datasets)                    │
│ • config/business_rules.json (NYC DOT context)          │
│ • config/kpis.json (51 KPIs)                            │
│ • config/quality_gates.json (validation rules)          │
│ • config/skill_registry.json (Phase 2 - skill metadata) │
│ • config/workflow_templates.json (Phase 3 - workflows)  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│    SKILLS INTEGRATION API (Phases 2-3)                  │
├─────────────────────────────────────────────────────────┤
│ • config_loader (reads + validates)                     │
│ • skill_validator (ensures context available)           │
│ • chain_orchestrator (auto-wires outputs→inputs)        │
│ • discovery_engine (recommends next skill)              │
│ • workflow_executor (runs pre-built sequences)          │
│ • audit_logger (full compliance trail)                  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│         31 SKILLS (Consuming from Config)               │
├─────────────────────────────────────────────────────────┤
│ ✓ NYC DOT context injected automatically                │
│ ✓ Know what data is available without code reading      │
│ ✓ Validate against quality gates before analysis        │
│ ✓ Logged for audit compliance                           │
└─────────────────────────────────────────────────────────┘
```

**Key principle:** Config is the single source of truth. Skills are consumers, not guardians of context.

---

## Phase 1: Config Consolidation (Weeks 1-2)

**Goal:** Create unified configuration system. All skills read from config instead of hardcoding context.

### Phase 1a: Config Files

Create `/config/` directory with four JSON files:

**`config/datasets.json` (57 datasets)**
- Dataset key, fourfour ID, row count, primary key
- Freshness SLA (HIGH=14d, MEDIUM=30d, LOW=60d)
- Known issues and quality scores
- Required columns for each dataset

Example structure:
```json
{
  "datasets": [
    {
      "key": "inspection",
      "fourfour": "dntt-gqwq",
      "name": "Sidewalk Inspection Records",
      "rows_approx": 398000,
      "primary_key": "objectid",
      "freshness_sla": "HIGH",
      "required_columns": ["objectid", "borough", "status", "inspection_date"],
      "quality_score": 85
    }
  ]
}
```

**`config/business_rules.json` (NYC DOT operational rules)**
- Borough abbreviations and full names (MN, BX, BK, QN, SI)
- SLA tier definitions (HIGH/MEDIUM/LOW days)
- Quality scoring weights (35% completeness, 25% validity, 25% consistency, 15% freshness)
- Stakeholder personas (Commissioner, Deputy Commissioner, Analyst)

**`config/kpis.json` (51 KPI definitions)**
- KPI ID, name, formula
- Source dataset for each KPI
- Borough-level aggregation capability
- Quality tier and ownership

**`config/quality_gates.json` (Validation rules)**
- Gate ID and rule description
- Severity level (CRITICAL / MAJOR / MINOR)
- Which datasets each gate applies to

### Phase 1b: Config Loader Module

Create `src/config_system.py`:
```python
class ConfigSystem:
    def __init__(self):
        self.datasets = load_json('config/datasets.json')
        self.business_rules = load_json('config/business_rules.json')
        self.kpis = load_json('config/kpis.json')
        self.quality_gates = load_json('config/quality_gates.json')
    
    def get_dataset(self, key) → Dataset
    def get_borough_list() → List[str]
    def get_kpi_formula(self, kpi_id) → str
    def validate_analysis_context(self, datasets_used, output_format) → (bool, List[str])
```

All 31 skills import ConfigSystem and use it at initialization.

### Phase 1c: Skills Integration

Each skill's initialization:
```python
from config_system import ConfigSystem

class ProgrammaticEDASkill:
    def __init__(self):
        self.config = ConfigSystem()
        self.required_columns = self.config.get_dataset('inspection')['required_columns']
        self.boroughs = self.config.get_borough_list()
        self.quality_weights = self.config.business_rules['quality_weights']
```

**No more hardcoding borough names, dataset IDs, or metric definitions.**

### Phase 1d: Success Metrics

- ✅ All 31 skills read from config (zero hardcoded context)
- ✅ No conflicting definitions between skills
- ✅ Adding new dataset requires only JSON update, not code changes
- ✅ Verification test passes: `test_config_consistency.py`

### Phase 1e: Deliverables

- `config/datasets.json` — All 57 datasets
- `config/business_rules.json` — NYC DOT rules
- `config/kpis.json` — All 51 KPIs
- `config/quality_gates.json` — Validation rules
- `src/config_system.py` — Config loader
- All 31 skills updated to use ConfigSystem
- `test_config_consistency.py` — Verification test

---

## Phase 2: Skill Registry & Auto-Chaining (Weeks 3-4)

**Goal:** Skills know about each other. Outputs feed into next skill automatically.

### Phase 2a: Skill Metadata Registry

Create `config/skill_registry.json` — Each of 31 skills declares:
- Input requirements (what data/context it needs)
- Output capabilities (what it produces)
- Chaining rules (which skills can follow this one)

Example entry:
```json
{
  "skill_id": "programmatic-eda",
  "name": "Programmatic EDA",
  "inputs_required": {
    "dataset": {"type": "dataframe", "min_rows": 1000},
    "dataset_key": {"type": "string"}
  },
  "outputs": {
    "quality_report": {"type": "markdown", "file": "eda_report_template.md"},
    "findings_summary": {"type": "markdown", "file": "findings_summary.md"},
    "quality_score": {"type": "number", "range": [0, 100]}
  },
  "can_chain_to": ["data-quality-audit", "semantic-model-builder", "cohort-analysis"]
}
```

### Phase 2b: Orchestrator Module

Create `src/skill_orchestrator.py`:
```python
class SkillOrchestrator:
    def get_next_skills(self, current_skill_id, current_output) → List[str]
    def validate_chain(self, skill_sequence) → (bool, List[str])
    def execute_chain(self, skill_sequence, initial_data) → (result, audit_log)
```

**Validates chaining before execution.** Fails fast if skills are incompatible.

### Phase 2c: Audit/Logging Layer

Create `src/audit_logger.py`:
```python
class AuditLogger:
    def log_skill_execution(self, skill_id, inputs_used, outputs_produced, context)
    def save_audit_trail(self) → JSON file
    def get_analysis_summary() → dict
```

**Every skill execution is logged with full context.**

### Phase 2d: How It Works

Analyst workflow:
1. Run programmatic-eda
2. System suggests next skills: "data-quality-audit, cohort-analysis, semantic-model-builder"
3. Analyst chooses "data-quality-audit"
4. System auto-passes EDA outputs → audit inputs
5. Execution logged: `skill_chain=[programmatic-eda → data-quality-audit] | context={datasets, boroughs, quality_weights}`

### Phase 2e: Success Metrics

- ✅ Can execute 2-3 skill sequences without manual data transfer
- ✅ Zero context loss between chained skills
- ✅ Every analysis has audit trail
- ✅ Chaining validation prevents incompatible sequences
- ✅ Verification test passes: `test_chaining_compatibility.py`

### Phase 2f: Deliverables

- `config/skill_registry.json` — Metadata for all 31 skills
- `src/skill_orchestrator.py` — Chaining orchestrator
- `src/audit_logger.py` — Audit system
- All 31 skills updated with input/output declarations
- `test_chaining_compatibility.py` — Verification test

---

## Phase 3: Discovery & Workflow Templates (Weeks 5-6)

**Goal:** System recommends what to do next AND provides pre-built workflows.

### Phase 3a: Discovery Engine

Create `src/discovery_engine.py`:
```python
class DiscoveryEngine:
    def recommend_next_skill(self, current_state) → List[recommendation]
    def list_workflows(self, analyst_goal=None) → List[workflow]
```

**Scores recommendations by:**
- Goal relevance (does this skill help the analyst's stated goal?)
- Data suitability (does the dataset have the right quality/structure?)
- Natural workflow flow (does it make sense after current skill?)

### Phase 3b: Workflow Templates

Create `config/workflow_templates.json` — Pre-built sequences for common tasks:

**Example workflows (5-6 total):**
1. **New Dataset Assessment** (25 min) — EDA → quality audit → catalog entry
2. **Metric Investigation & Report** (70 min) — Root cause → time-series → insight synthesis → translation → executive summary
3. **Borough Performance Analysis** (60 min) — EDA → segmentation → metrics → visualization → impact quantification
4. **Data Quality Remediation** (45 min) — EDA → audit → analysis planning → implementation
5. **Cohort-Based Retention Study** (90 min) — EDA → cohort analysis → segmentation → business metrics → visualization

Each workflow defines:
- Skill sequence (steps 1-5)
- Time estimates per step
- Required context inputs
- Produced outputs
- Success criteria

### Phase 3c: Workflow Executor

Create `src/workflow_executor.py`:
```python
class WorkflowExecutor:
    def list_workflows(self, analyst_goal=None) → List[workflow]
    def execute_workflow(self, workflow_id, initial_data, analyst_context) → (result, audit_trail)
```

**Executes workflows step-by-step, automatically:**
- Validating context at each step
- Passing outputs to next step as inputs
- Logging everything for audit

### Phase 3d: User Experience

Analysts interact via CLI/notebook:

```python
# Example: Get recommendations
from discovery_engine import DiscoveryEngine

engine = DiscoveryEngine()
recommendations = engine.recommend_next_skill({
    'current_skill': 'programmatic-eda',
    'current_outputs': {'quality_score': 78},
    'analyst_goal': 'find borough differences in closure rates'
})

# Example: Run pre-built workflow
from workflow_executor import WorkflowExecutor

executor = WorkflowExecutor()
result = executor.execute_workflow(
    workflow_id='metric_investigation',
    initial_data={'dataset': df},
    analyst_context={'analyst_name': 'Jane', 'dataset_key': 'violations'}
)
```

### Phase 3e: Success Metrics

- ✅ Analysts can run 5-skill workflows in 70 minutes with zero context loss
- ✅ Discovery recommendations match analyst goal 80%+ of the time
- ✅ Pre-built workflows save 30-50% time on common tasks
- ✅ Every workflow execution produces audit trail
- ✅ Verification test passes: `test_discovery_accuracy.py`

### Phase 3f: Deliverables

- `config/workflow_templates.json` — 5-6 pre-built workflows
- `src/discovery_engine.py` — Recommendation engine
- `src/workflow_executor.py` — Workflow runner
- CLI/notebook interface examples
- `test_discovery_accuracy.py` — Verification test

---

## Data Flow & Integration Points

### Phase 1: Config → Skills

```
config/datasets.json
       ↓
ConfigSystem.get_dataset('inspection')
       ↓
[programmatic-eda skill]
       ↓
Uses: fourfour, primary_key, required_columns, freshness_sla
```

### Phase 2: Skills → Skills (Chaining)

```
programmatic-eda output: {quality_score, findings_summary}
       ↓
SkillOrchestrator.validate_chain(['programmatic-eda', 'data-quality-audit'])
       ↓
SkillOrchestrator.execute_chain() passes output → input
       ↓
data-quality-audit receives {quality_score, findings_summary}
       ↓
AuditLogger records: skill_chain, context, timestamp
```

### Phase 3: Discovery & Templates

```
analyst_goal="understand borough differences"
       ↓
DiscoveryEngine.recommend_next_skill()
       ↓
Recommends: segmentation-analysis (rank 1), cohort-analysis (rank 2)
       ↓
OR analyst chooses pre-built workflow: borough_performance_analysis
       ↓
WorkflowExecutor.execute_workflow() runs all steps with auto-chaining
       ↓
Produces: borough_metrics_table, comparison_chart, business_impact_summary
```

---

## Testing & Verification

### Phase 1 Verification
- `test_config_consistency.py` — No contradictions in datasets, KPIs, metrics
- Manual check: All 31 skills import ConfigSystem successfully
- Runtime test: ConfigSystem loads all 4 JSON files without errors

### Phase 2 Verification
- `test_chaining_compatibility.py` — All declared chains are valid (output schema matches input schema)
- Runtime test: Execute sample 2-3 skill sequences end-to-end
- Audit log test: Verify audit trails are written correctly

### Phase 3 Verification
- `test_discovery_accuracy.py` — Discovery recommendations match goal (80%+ accuracy on test scenarios)
- Runtime test: Execute all 5-6 pre-built workflows end-to-end
- Workflow time estimate test: Actual execution time ≤ estimate + 20%

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Config divergence (JSON out of sync with reality) | Medium | High | Automated verification test runs with every config change. Schema validation on load. |
| Skill registry declarations incomplete | Medium | High | Code review checklist: verify each skill declares all inputs/outputs. Spot-check by running chaining validation. |
| Discovery recommendations miss analyst goal | Low-Medium | Medium | Start with simple keyword matching. Refine with feedback. Manual override always available. |
| Audit logging slows down analysis execution | Low | Medium | Async logging to separate file. Profile performance in Phase 2. |
| Complex multi-step workflows too hard to debug | Low | Medium | Clear logging at each step. Analyst can pause between steps. Workflow versioning for reproducibility. |

---

## Success Criteria (All Phases)

### Context Integrity (Phase 1)
- ✅ All 31 skills use identical borough definitions (MN, BX, BK, QN, SI)
- ✅ All skills use identical metric formulas
- ✅ All skills apply same quality thresholds
- ✅ Zero contradictions between skills

### Chaining (Phase 2)
- ✅ 2-3 skill sequences execute without manual intervention
- ✅ Zero data loss between chained skills
- ✅ Incompatible chains rejected before execution
- ✅ Full audit trail of every execution

### Discovery & Templates (Phase 3)
- ✅ System recommends next skill with 80%+ relevance to stated goal
- ✅ Pre-built workflows available for 5+ common analyst tasks
- ✅ Workflows save 30-50% time vs. manual skill chaining
- ✅ New analysts can run sophisticated workflows with guidance

### Overall
- ✅ Analysts save 20-30% of time on context setup
- ✅ Zero context loss between analysis steps
- ✅ Full compliance audit trail for regulatory requirements
- ✅ New analysts can navigate skill menu without training

---

## Timeline & Milestones

| Week | Phase | Milestone |
|------|-------|-----------|
| 1-2 | Phase 1 | Config consolidation complete. All 31 skills reading from config. Verification test passes. |
| 3-4 | Phase 2 | Skill registry complete. Chaining orchestrator working. Sample workflows execute end-to-end. |
| 5-6 | Phase 3 | Discovery engine scoring accurately. Pre-built workflow templates defined. System ready for analyst use. |

---

## Assumptions

1. **Scope is correct** — Focus on all 5 bottlenecks (context, discovery, activation, chaining, compliance)
2. **Config-driven is optimal** — File-based JSON config with API wrapper is the right architecture
3. **Pre-analysis config** — Analysts set up context once, before analysis starts (not runtime updates)
4. **31 skills scope is stable** — No major new skills will be added during implementation
5. **NYC DOT context is canonical** — Once defined in config, all skills defer to it (no local overrides)

---

## Out of Scope

- **Skill modifications beyond integration** — We're not rewriting skill logic, just wiring them together
- **New skill creation** — This design integrates existing 31 skills only
- **Advanced machine learning for discovery** — Start with keyword/goal matching; iterate based on feedback
- **Cloud deployment** — This design is local-first. Cloud deployment is future work.
- **Real-time monitoring** — Audit logs are written post-analysis. Real-time dashboarding is future work.

---

## Next Steps

1. **Write design doc** (this document) ✅
2. **User review & approval** → Awaiting feedback
3. **Invoke writing-plans skill** → Create detailed implementation plan with task breakdown

