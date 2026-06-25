# Data Analytics Skills Integration — Implementation Plan

**Date:** 2026-06-18  
**Duration:** 6 weeks  
**Team Size:** 2 FTE engineers  
**Total Effort:** 216 hours (124 with parallelization ≈ 5.2 weeks wall time)  
**Status:** Ready for execution

---

## Executive Summary

This plan translates the approved 3-phase design into 38 concrete, executable tasks across all three phases:

- **Phase 1 (Weeks 1-2):** Config Consolidation — 37 hours
- **Phase 2 (Weeks 3-4):** Skill Registry & Auto-Chaining — 39 hours
- **Phase 3 (Weeks 5-6):** Discovery & Workflow Templates — 48 hours

**Success Criteria:** All 31 skills integrated, zero context loss, full audit compliance, discovery 80%+ accurate, 5-6 workflows operational.

---

## Phase 1: Config Consolidation (Weeks 1-2)

**Goal:** Create unified configuration system. All 31 skills read from config instead of hardcoding context.

### Phase 1A: Config File Creation (Week 1 - Days 1-3) — 15 hours

#### P1A-1: Create datasets.json (4 hours)
- Convert 57 datasets from `config/datasets.yaml` and SQL queries into standardized JSON format
- Fields: key, fourfour_id, name, row_count, primary_key, freshness_sla (HIGH/MEDIUM/LOW), required_columns[], quality_score
- Success criteria: All 57 datasets documented, no missing fourfours or primary keys, JSON validates against schema

#### P1A-2: Create business_rules.json (3 hours)
- Codify NYC DOT operational rules: borough abbreviations, SLA tiers, quality weights
- Fields: boroughs (MN, BX, BK, QN, SI), sla_definitions (HIGH=14d, MEDIUM=30d, LOW=60d), quality_weights (35% completeness, 25% validity, 25% consistency, 15% freshness), stakeholder_personas
- Success criteria: 5 boroughs with consistent abbreviations, quality weights sum to 100%, all personas defined, Pydantic validation passes

#### P1A-3: Create metrics.json (5 hours)
- Document all 51 Metric definitions with formulas, source datasets, borough aggregation rules
- Fields: metric_id, name, formula, source_datasets[], borough_level, quality_tier, ownership
- Data source: Extract from existing skill references and Metric documentation
- Success criteria: All 51 Metrics documented with formulas, each Metric references valid source dataset(s), borough aggregation specified, all formulas syntactically valid

#### P1A-4: Create quality_gates.json (3 hours)
- Define validation rules for data quality checks
- Fields: gate_id, rule_description, severity (CRITICAL/MAJOR/MINOR), applies_to_datasets[], sql_check, threshold
- Success criteria: Minimum 12 gates defined (one per dataset category + general gates), 3+ CRITICAL, 4+ MAJOR, 5+ MINOR, all SQL checks valid

### Phase 1B: Config Loader Module Development (Week 1 - Days 3-5) — 9 hours

#### P1B-1: Implement ConfigSystem class (6 hours)
- Build Python module to load, validate, and provide access to all configs
- Location: `src/config_system.py`
- Key methods:
  - `__init__()` — loads all 4 JSON files, validates schemas
  - `get_dataset(key: str) -> Dict`
  - `get_borough_list() -> List[str]`
  - `get_metric_formula(metric_id: str) -> str`
  - `get_quality_gates(dataset_key: str = None) -> List[Dict]`
  - `validate_dataset_exists(key: str) -> bool`
  - `validate_analysis_context(datasets_used, quality_gates) -> Tuple[bool, List[str]]`
- Success criteria: All methods tested, lazy-loads configs (singleton pattern), schema validation on load, <100ms load time, 100% method coverage

#### P1B-2: Create Pydantic models for config validation (3 hours)
- Define strict type checking for all config structures
- Location: `src/config_models.py`
- Models: Dataset, BusinessRules, Metric, QualityGate, ConfigSchema
- Success criteria: All 4 config JSON files validate successfully, custom validators for business logic, helpful error messages, used by ConfigSystem

### Phase 1C: Skills Integration (Week 2 - Days 1-4) — 33 hours (parallelizable)

For each skill category, refactor to use ConfigSystem instead of hardcoded thresholds:

#### P1C-1: Update programmatic-eda skill (2 hours)
- Import ConfigSystem, read borough list from config, use quality_weights from config, reference dataset metadata from config
- Success criteria: No hardcoded borough names, no hardcoded quality thresholds, skill still produces same outputs, 2+ test cases pass

#### P1C-2: Update data-quality-audit skill (2 hours)
- Same refactoring pattern as P1C-1
- Success criteria: Same as P1C-1

#### P1C-3: Update 4 remaining data-quality skills (6 hours, parallelizable)
- Batch update: query-validation, schema-mapper, metric-reconciliation, (one more)
- Success criteria: All 6 data-quality skills reading from ConfigSystem

#### P1C-4: Update all 7 documentation & knowledge skills (7 hours, parallelizable)
- semantic-model-builder, analysis-documentation, data-catalog-entry, sql-to-business-logic, analysis-assumptions-log, (2 more from knowledge category)
- Success criteria: All 7 skills reading from ConfigSystem

#### P1C-5: Update all 7 data-analysis-investigation skills (7 hours, parallelizable)
- cohort-analysis, segmentation-analysis, funnel-analysis, time-series-analysis, root-cause-investigation, ab-test-analysis, business-metrics-calculator
- Success criteria: All 7 analysis skills reading from ConfigSystem

#### P1C-6: Update all 5 data-storytelling-visualization skills (5 hours, parallelizable)
- insight-synthesis, visualization-builder, executive-summary-generator, dashboard-specification, data-narrative-builder
- Success criteria: All 5 visualization skills reading from ConfigSystem

#### P1C-7: Update all 5 stakeholder-communication skills (5 hours, parallelizable)
- technical-to-business-translator, stakeholder-requirements-gathering, analysis-qa-checklist, methodology-explainer, impact-quantification
- Success criteria: All 5 communication skills reading from ConfigSystem

#### P1C-8: Update all 4 workflow-optimization skills (4 hours, parallelizable)
- analysis-planning, context-packager, peer-review-template, analysis-retrospective
- Success criteria: All 4 workflow skills reading from ConfigSystem

### Phase 1D: Testing & Verification (Week 2 - Days 4-5) — 11 hours

#### P1D-1: Write test_config_consistency.py (5 hours)
- Location: `tests/test_config_consistency.py`
- Test cases:
  1. All 57 datasets have valid fourfour IDs and primary keys
  2. No conflicting borough definitions across configs
  3. All 51 Metrics reference valid datasets
  4. Quality gates reference valid datasets
  5. Quality weights sum to 100%
  6. ConfigSystem loads all files without errors
  7. No hardcoded values in skill code (grep verification)
  8. All 31 skills import ConfigSystem successfully
  9. Configs pass Pydantic validation
  10. Cross-references consistent (dataset→metric→gate)
- Success criteria: 10/10 tests passing

#### P1D-2: Manual skill verification (4 hours)
- Test each of 31 skills manually with sample data
- Process: run skill with `--test` flag, verify output references config (not hardcoded values), check logs confirm ConfigSystem loaded, spot-check 3 random skills in detail
- Success criteria: 31/31 skills load ConfigSystem, 0 hardcoded context errors

#### P1D-3: Performance baseline (2 hours)
- Benchmark ConfigSystem load time and config access latency
- Metrics:
  - ConfigSystem init time: target <100ms
  - get_dataset() call: target <1ms
  - get_borough_list(): target <1ms
  - Full skill execution with config overhead: target <5% slowdown
- Success criteria: All metrics meet targets

**Phase 1 Deliverables:**
- Four consolidated JSON config files
- `src/config_system.py` loader module
- `src/config_models.py` Pydantic models
- All 31 skills updated to use ConfigSystem
- `test_config_consistency.py` verification test
- `PHASE1_VERIFICATION_REPORT.md`
- `PHASE1_PERFORMANCE_BASELINE.md`

---

## Phase 2: Skill Registry & Auto-Chaining (Weeks 3-4)

**Goal:** Skills know about each other. Outputs feed into next skill automatically.

### Phase 2A: Skill Registry Creation (Week 3 - Days 1-3) — 14 hours

#### P2A-1: Document skill input/output declarations (8 hours)
- For each of 31 skills, explicitly declare:
  - Input requirements (data types, minimum rows, required columns)
  - Output capabilities (what files/data it produces, format, size estimates)
  - Chaining rules (which skills can follow this one)
- Process: Read skill SKILL.md, review skill scripts, test skill execution to capture real output schema, document in structured format
- Success criteria: All 31 skills have complete declarations, declarations match actual skill behavior, 5+ logical chaining sequences identified

#### P2A-2: Create skill_registry.json (6 hours)
- Location: `/config/skill_registry.json`
- For each skill:
  ```json
  {
    "skill_id": "programmatic-eda",
    "name": "Programmatic EDA",
    "category": "data-quality-validation",
    "description": "...",
    "inputs_required": {
      "dataset": {"type": "dataframe|file_path", "min_rows": 1000},
      "dataset_key": {"type": "string"}
    },
    "inputs_optional": {...},
    "outputs": {
      "quality_report": {"type": "markdown", "file_pattern": "eda_report_*.md"},
      "findings_summary": {"type": "markdown"},
      "quality_score": {"type": "number", "range": [0, 100]}
    },
    "can_chain_to": ["data-quality-audit", "cohort-analysis", ...],
    "estimated_execution_time_seconds": 120,
    "required_config_access": ["datasets", "quality_gates"],
    "conflicts_with": []
  }
  ```
- Success criteria: All 31 skills documented, JSON validates against schema, no circular dependencies, ≥50% of skills have 2+ downstream skills

### Phase 2B: Orchestrator & Validation Module (Week 3 - Days 3-5) — 14 hours

#### P2B-1: Implement SkillOrchestrator class (8 hours)
- Location: `src/skill_orchestrator.py`
- Key methods:
  - `get_next_skills(skill_id, execution_output) -> List[str]` — returns list of compatible downstream skills
  - `validate_chain(skill_sequence) -> (bool, List[str])` — validates skill sequence, returns is_valid and list_of_errors
  - `execute_chain(skill_sequence, initial_data, analyst_context) -> (result, audit_logs)` — executes chain step-by-step
  - `find_skill_path(start_skill, goal) -> List[str]` — graph search for shortest path
- Success criteria: validate_chain() correctly identifies incompatible sequences, get_next_skills() returns only valid downstream skills, execute_chain() passes outputs to next skill inputs, <5ms validation overhead per skill

#### P2B-2: Implement output→input adapter patterns (6 hours)
- Location: `src/skill_adapters.py`
- For each major chaining sequence, create adapter:
  ```python
  class ProgrammaticEDAToDataQualityAuditAdapter:
      @staticmethod
      def transform(eda_output: Dict) -> Dict:
          return {
              'quality_issues': eda_output['findings_summary'],
              'quality_score': eda_output['quality_score'],
              'dataset_key': eda_output.get('dataset_key')
          }
  ```
- Success criteria: Adapters for 10+ primary chaining sequences, adapter tests verify data loss <5%, all adapters preserve metadata

### Phase 2C: Audit Logging Layer (Week 4 - Days 1-2) — 9 hours

#### P2C-1: Implement AuditLogger class (6 hours)
- Location: `src/audit_logger.py`
- Key methods:
  - `__init__(analysis_id: str)`
  - `log_skill_execution(skill_id, inputs_used, outputs_produced, context, execution_time_seconds)`
  - `save_audit_trail(filepath = None) -> str` — saves to JSON, returns path
  - `get_analysis_summary() -> Dict`
  - `verify_context_consistency() -> List[str]` — returns list of context inconsistencies
- Success criteria: Logs all executions with metadata, audit file size <100KB per analysis, logging overhead <50ms per skill, can reconstruct full workflow from audit log

#### P2C-2: Create audit_logger test fixtures (3 hours)
- Location: `tests/fixtures/audit_logs/`
- Fixtures: sample single-skill, 3-skill chain, 5-skill workflow audit logs
- Success criteria: All fixtures valid, parseable JSON, can reconstruct workflow from each

### Phase 2D: Integration & Testing (Week 4 - Days 2-5) — 18 hours

#### P2D-1: Build sample 2-skill chain execution test (4 hours)
- Location: `tests/test_chaining_basic_2skill.py`
- Test: programmatic-eda → data-quality-audit
- Flow: validate chain → execute EDA → capture outputs → validate adapter → execute audit → verify audit logs
- Success criteria: Test passes end-to-end, zero context loss, audit log shows both executions, execution time matches estimate ±20%

#### P2D-2: Build 3-skill chain test (5 hours)
- Location: `tests/test_chaining_3skill.py`
- Test: programmatic-eda → data-quality-audit → root-cause-investigation
- Success criteria: All 3 skills execute in sequence, outputs flow correctly, audit trail shows all 3 executions

#### P2D-3: Write test_chaining_compatibility.py (6 hours)
- Location: `tests/test_chaining_compatibility.py`
- Test cases:
  1. All declared chains are valid (no output→input mismatches)
  2. No circular dependencies
  3. validate_chain() rejects incompatible sequences
  4. validate_chain() accepts all valid sequences
  5. Execution time predictions accurate (±20%)
  6. No skills have conflicting outputs
  7. Registry consistency (no orphaned skills)
  8. Adapters preserve all critical metadata
  9. Audit logs complete and correct
  10. Error handling in orchestrator graceful
- Success criteria: 10/10 tests passing

#### P2D-4: Verify orchestrator performance (3 hours)
- Benchmark orchestrator overhead
- Metrics:
  - validate_chain() time: target <5ms per skill
  - get_next_skills() time: target <1ms
  - execute_chain() overhead: target <10% total execution time
  - Audit logging overhead: target <50ms per skill
- Success criteria: All metrics meet targets

**Phase 2 Deliverables:**
- `config/skill_registry.json` — Metadata for all 31 skills
- `src/skill_orchestrator.py` — Chaining orchestrator
- `src/skill_adapters.py` — Output→input adapters
- `src/audit_logger.py` — Audit system
- All 31 skills updated with input/output declarations
- `test_chaining_basic_2skill.py`, `test_chaining_3skill.py`, `test_chaining_compatibility.py`
- `PHASE2_PERFORMANCE_BASELINE.md`

---

## Phase 3: Discovery & Workflow Templates (Weeks 5-6)

**Goal:** System recommends what to do next AND provides pre-built workflows.

### Phase 3A: Discovery Engine (Week 5 - Days 1-3) — 13 hours

#### P3A-1: Implement DiscoveryEngine class (8 hours)
- Location: `src/discovery_engine.py`
- Key methods:
  - `recommend_next_skill(current_state) -> List[Recommendation]`
    - current_state = {current_skill, current_outputs, analyst_goal, data_used}
    - Returns: List of (skill_id, score, reason) sorted by score descending
  - `list_workflows(goal=None, time_budget_minutes=None) -> List[Workflow]`
  - `score_recommendation(candidate_skill, context) -> float` (0-100)
  - `search_skills(keyword) -> List[Skill]`
- Scoring logic:
  - Goal relevance (40%) — keyword matching + embedding similarity
  - Data suitability (30%) — dataset quality, completeness checks
  - Natural flow (20%) — chaining compatibility
  - Analyst context (10%) — role, recent usage patterns
- Success criteria: Recommendations rank-ordered by relevance, average recommendation relevance >80%, <100ms to generate recommendations, graceful fallback if goal is vague

#### P3A-2: Build discovery recommendation tests (5 hours)
- Location: `tests/test_discovery_accuracy.py`
- Test scenarios:
  1. Goal: "understand data quality" → should recommend data-quality-audit, programmatic-eda
  2. Goal: "investigate metric changes" → should recommend root-cause-investigation
  3. Goal: "present findings to executives" → should recommend insight-synthesis, technical-to-business-translator
  4. Goal: "assess borough differences" → should recommend segmentation-analysis, cohort-analysis
  5. Goal: "build documentation" → should recommend data-catalog-entry, analysis-documentation
  6. Vague goal: "analyze the data" → should suggest top 3-5 broadly applicable skills
- Scoring: Goal match accuracy ≥80% (recommendations in top 3 match goal)
- Success criteria: 5/6 scenarios pass (≥80% accuracy threshold)

### Phase 3B: Workflow Templates (Week 5 - Days 3-5) — 6 hours

#### P3B-1: Define 5-6 pre-built workflow templates (6 hours)
- Location: `/config/workflow_templates.json`
- **Workflow 1: New Dataset Assessment (25 min)**
  - Step 1: programmatic-eda (8 min)
  - Step 2: data-quality-audit (10 min)
  - Step 3: data-catalog-entry (7 min)
  - Success: Catalog entry created, quality gates defined

- **Workflow 2: Metric Investigation & Report (70 min)**
  - Step 1: root-cause-investigation (15 min)
  - Step 2: time-series-analysis (20 min)
  - Step 3: insight-synthesis (15 min)
  - Step 4: technical-to-business-translator (10 min)
  - Step 5: executive-summary-generator (10 min)
  - Success: Executive summary ready for leadership

- **Workflow 3: Borough Performance Analysis (60 min)**
  - Step 1: programmatic-eda (10 min)
  - Step 2: segmentation-analysis (15 min) [with borough as segment]
  - Step 3: business-metrics-calculator (15 min)
  - Step 4: visualization-builder (10 min)
  - Step 5: impact-quantification (10 min)
  - Success: Borough comparison chart + impact metrics

- **Workflow 4: Data Quality Remediation (45 min)**
  - Step 1: programmatic-eda (8 min)
  - Step 2: data-quality-audit (15 min)
  - Step 3: analysis-planning (12 min)
  - Step 4: analysis-qa-checklist (10 min)
  - Success: Remediation plan approved

- **Workflow 5: Cohort-Based Retention Study (90 min)**
  - Step 1: programmatic-eda (10 min)
  - Step 2: cohort-analysis (25 min)
  - Step 3: segmentation-analysis (15 min)
  - Step 4: business-metrics-calculator (15 min)
  - Step 5: visualization-builder (15 min)
  - Step 6: dashboard-specification (10 min)
  - Success: Dashboard design spec delivered

- **Workflow 6: Analysis Quality Assurance (30 min)**
  - Step 1: [previous analysis skill]
  - Step 2: analysis-qa-checklist (12 min)
  - Step 3: analysis-assumptions-log (8 min)
  - Step 4: peer-review-template (10 min)
  - Success: Analysis approved for delivery

- Structure per workflow:
  ```json
  {
    "workflow_id": "new_dataset_assessment",
    "name": "New Dataset Assessment",
    "description": "...",
    "goal": "Evaluate data quality and create catalog entry",
    "time_estimate_minutes": 25,
    "required_analyst_skill": "intermediate",
    "steps": [
      {
        "sequence": 1,
        "skill_id": "programmatic-eda",
        "time_estimate_minutes": 8,
        "inputs": {...},
        "outputs_to_next": [...]
      }
    ],
    "success_criteria": "Catalog entry created with quality gates defined",
    "potential_next_workflows": ["data_quality_remediation"],
    "frequency": "every_new_dataset"
  }
  ```
- Success criteria: 6 workflows defined, all use valid skill sequences, time estimates provided, clear success criteria

### Phase 3C: Workflow Executor (Week 6 - Days 1-2) — 12 hours

#### P3C-1: Implement WorkflowExecutor class (8 hours)
- Location: `src/workflow_executor.py`
- Key methods:
  - `list_workflows(goal=None, time_budget_minutes=None) -> List[Workflow]`
  - `execute_workflow(workflow_id, initial_data, analyst_context) -> (result, audit_trail)`
  - `pause_workflow(workflow_id)` — pause execution
  - `resume_workflow(workflow_id)` — resume paused workflow
  - `estimate_completion_time(workflow_id, current_step) -> int` — remaining time in minutes
- Features:
  - Automatic context passing between steps
  - Validation gates before each step
  - Recovery from skill failures (skip step or retry)
  - Real-time progress tracking
  - Detailed audit trail with timestamps
- Success criteria: Can execute all 6 workflows end-to-end, pause/resume works, time estimates accurate ±20%, audit trail complete, <10s overhead per workflow

#### P3C-2: Implement workflow error handling (4 hours)
- Location: Add to `src/workflow_executor.py`
- Strategies:
  - Skill fails → Skip and note, continue to next step
  - Invalid input → Prompt analyst for clarification
  - Context missing → Use defaults from config
  - Timeout → Kill skill after 5x estimated time, skip
- Success criteria: Workflows continue despite single skill failure, analyst informed of failures, audit trail notes all failures, recovery success rate >95%

### Phase 3D: User Experience & Templates (Week 6 - Days 2-3) — 7 hours

#### P3D-1: Create CLI/notebook interface examples (4 hours)
- Location: `docs/discovery_and_workflows_user_guide.md`
- Examples:
  ```python
  # Example 1: Get recommendations
  from discovery_engine import DiscoveryEngine
  engine = DiscoveryEngine()
  recs = engine.recommend_next_skill({...})
  
  # Example 2: List workflows
  executor = WorkflowExecutor()
  workflows = executor.list_workflows(goal="assess borough performance", time_budget_minutes=60)
  
  # Example 3: Run workflow
  result = executor.execute_workflow(workflow_id='borough_performance_analysis', ...)
  ```
- Includes: 5-10 worked examples, common workflows, troubleshooting guide, best practices
- Success criteria: Examples are copy-paste ready, all tested and working, covers 80% of expected use cases

#### P3D-2: Build notebook templates (3 hours)
- Location: `docs/notebooks/`
- Templates:
  - `workflow_new_dataset_assessment.ipynb`
  - `workflow_metric_investigation.ipynb`
  - `workflow_borough_analysis.ipynb`
- Each template: pre-filled imports, step-by-step markdown, executable cells, visualization of results, customization notes
- Success criteria: 3+ templates created, each runs end-to-end without errors, beginner-friendly with explanations

### Phase 3E: Testing & Verification (Week 6 - Days 3-5) — 20 hours

#### P3E-1: Write comprehensive workflow execution tests (6 hours)
- Location: `tests/test_workflows_execution.py`
- Test cases: One for each workflow
  - new_dataset_assessment
  - metric_investigation_and_report
  - borough_performance_analysis
  - data_quality_remediation
  - cohort_retention_study
  - analysis_quality_assurance
- For each: validate steps compatible → execute with sample data → verify all outputs → check audit trail → verify time estimate accuracy (±20%)
- Success criteria: 6/6 workflows execute successfully

#### P3E-2: Build discovery recommendation accuracy tests (5 hours)
- Location: `tests/test_discovery_recommendations.py`
- Test data: 20 test scenarios with explicit goals, expert-provided expected recommendations
- Metrics:
  - Top-1 accuracy: recommended skill matches goal 60%+
  - Top-3 accuracy: recommended skill in top 3 matches 80%+
  - Relevance score: average recommendation score >75
- Success criteria: All metrics above thresholds

#### P3E-3: Performance & stress testing (4 hours)
- Benchmarks:
  - Single skill execution: <500ms orchestration overhead
  - Discovery recommendations: <100ms for 31 skills
  - Workflow execution: <10s overhead for 6-skill workflow
  - Audit logging: <50ms per skill
  - Config loading: <100ms cold start
- Stress test: Execute 10 workflows in parallel, target <2x latency degradation
- Success criteria: All benchmarks met, stress test <2x degradation

#### P3E-4: Integration verification and final tests (5 hours)
- Location: `tests/test_integration_final.py`
- Test coverage:
  - Phase 1: All 31 skills load config
  - Phase 2: All skill chains execute
  - Phase 3: All workflows execute
  - End-to-end: Complete workflow with discovery + execution + audit
  - Compliance: Audit trails complete and correct
  - Context: No context loss between any steps
- Success criteria: All tests passing

**Phase 3 Deliverables:**
- `config/workflow_templates.json` — 5-6 pre-built workflows
- `src/discovery_engine.py` — Recommendation engine
- `src/workflow_executor.py` — Workflow runner
- `docs/discovery_and_workflows_user_guide.md` — User guide
- Jupyter notebook templates in `docs/notebooks/`
- `tests/test_workflows_execution.py`, `test_discovery_accuracy.py`, etc.
- `PHASE3_PERFORMANCE_REPORT.md`

---

## Dependency Map & Critical Path

### Critical Path (Tasks that block others)

```
P1A-1,2,3,4 (Config creation, 15h)
    ↓
P1B-1,2 (ConfigSystem, 9h)
    ↓
P1C-1 through P1C-8 (Skills integration, 33h)
    ↓
P1D-1, P1D-2, P1D-3 (Testing, 11h)
    ↓
P2A-1,2 (Registry creation, 14h)
    ↓
P2B-1,2 (Orchestrator, 14h)
    ↓
P2C-1,2 (Audit logging, 9h)
    ↓
P2D-1,2,3,4 (Chaining tests, 18h)
    ↓
P3A-1,2 (Discovery, 13h)
    ↓
P3B-1 (Workflow templates, 6h)
    ↓
P3C-1,2 (Executor, 12h)
    ↓
P3D-1,2 (UX, 7h)
    ↓
P3E-1,2,3,4 (Final testing, 20h)
```

**Critical Path Duration:** ~180 hours (excluding parallelizable tasks)

### Parallelizable Work

**Phase 1C (Skills Integration):** Tasks P1C-3 through P1C-8 can run in parallel
- P1C-3: 5 data-quality skills (6h)
- P1C-4: 7 documentation skills (7h)
- P1C-5: 7 analysis skills (7h)
- P1C-6: 5 visualization skills (5h)
- P1C-7: 5 communication skills (5h)
- P1C-8: 4 workflow skills (4h)
- **Parallelized Duration:** 7h (longest task) vs 33h sequential

**Actual Wall Time with Parallelization:**

| Phase | Sequential | With Parallelization |
|-------|---|---|
| Phase 1 | 68h | 37h |
| Phase 2 | 55h | 39h |
| Phase 3 | 58h | 48h |
| **TOTAL** | **181h** | **124h (≈5.2 weeks)** |

---

## Weekly Breakdown (6 weeks, 2 FTE)

| Week | Phase | Tasks | Effort | Allocation | Milestones |
|------|-------|-------|--------|-----------|-----------|
| 1 | 1A-1B | P1A-1,2,3,4, P1B-1,2 | 37h | 18.5h each | Configs created, ConfigSystem working |
| 2 | 1C-1D | P1C-1–P1D-3 | 44h | 22h each | All 31 skills integrated, Phase 1 gate passed |
| 3 | 2A-2B | P2A-1,2, P2B-1,2 | 36h | 18h each | Registry complete, orchestrator working |
| 4 | 2C-2D | P2C-1,2, P2D-1–4 | 27h | 13.5h each | Audit system working, chaining tests passing, Phase 2 gate passed |
| 5 | 3A-3C | P3A-1,2, P3B-1, P3C-1,2 | 35h | 17.5h each | Discovery working, workflows defined and executable |
| 6 | 3D-3E | P3D-1,2, P3E-1–4 | 37h | 18.5h each | UX complete, all tests passing, Phase 3 gate passed, system ready |

---

## Testing & Verification Plan

### Phase 1 Verification Gate

**Exit Criteria (Must pass before moving to Phase 2):**
1. `test_config_consistency.py`: 10/10 tests passing
2. All 31 skills load ConfigSystem without errors
3. Zero hardcoded context found in skill code (grep verification)
4. ConfigSystem latency <100ms cold start, <1ms warm
5. PHASE1_VERIFICATION_REPORT.md signed off
6. Manual spot-check: 5 random skills tested with sample data

**Failure Plan:**
- If config consistency fails: Fix config files, re-run tests
- If skill integration fails: Review skill code, update ConfigSystem, re-test
- If performance fails: Profile, optimize hot paths, retest
- **Rollback:** Revert config files, reset skills to original hardcoded state

### Phase 2 Verification Gate

**Exit Criteria:**
1. `test_chaining_compatibility.py`: 10/10 tests passing
2. 3-skill chain (programmatic-eda → data-quality-audit → root-cause-investigation) executes end-to-end
3. Audit logs complete and correct for all executions
4. Output→input adapters preserve 95%+ of data
5. Orchestrator validation <5ms per skill
6. PHASE2_PERFORMANCE_BASELINE.md signed off

**Failure Plan:**
- If chaining fails: Review adapter logic, fix output→input mapping
- If audit logs incomplete: Add missing logging calls, retest
- If performance fails: Profile orchestrator, optimize bottlenecks
- **Rollback:** Disable orchestrator, use Phase 1 configs only

### Phase 3 Verification Gate

**Exit Criteria:**
1. `test_workflows_execution.py`: 6/6 workflows executing successfully
2. `test_discovery_accuracy.py`: ≥80% recommendation accuracy
3. `test_discovery_recommendations.py`: Top-3 accuracy ≥80%
4. `test_integration_final.py`: All end-to-end tests passing
5. Workflow time estimates accurate ±20%
6. All notebooks in docs/notebooks/ execute without errors
7. PHASE3_PERFORMANCE_REPORT.md signed off
8. User guide reviewed and approved by analyst

**Failure Plan:**
- If workflow execution fails: Debug skill sequence, check adapters
- If discovery accuracy poor: Refine scoring algorithm, add training data
- If performance fails: Profile workflows, optimize hot paths
- **Rollback:** Disable discovery & templates, use Phase 2 orchestration only

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Config divergence | Medium | High | Automated verification test with every change. Schema validation on load. |
| Incomplete skill registry | Medium | High | Code review checklist. Spot-check by running chaining validation. |
| Discovery misses goals | Low-Medium | Medium | Start with keyword matching. Refine with feedback. Manual override always available. |
| Audit logging slows execution | Low | Medium | Async logging. Profile in Phase 2. |
| Complex workflows hard to debug | Low | Medium | Clear step-by-step logging. Pause between steps. Workflow versioning. |

### Risk Mitigation Tasks

**Risk 1: Config Divergence**
- Task R1-1: Config validation test automation (2h) — automated test runs with every config change
- Task R1-2: Schema enforcement with Pydantic (2h) — strict type checking + custom validators

**Risk 2: Incomplete Skill Registry**
- Task R2-1: Input/output declaration audit (3h) — verify declarations match actual behavior
- Task R2-2: Chaining compatibility checklist (2h) — code review checklist
- Task R2-3: Spot-check validation (1h) — run actual chains and verify

**Risk 3: Discovery Accuracy**
- Task R3-1: Simple discovery algorithm v0 (2h) — start with keyword matching
- Task R3-2: Feedback loop refinement (3h) — gather feedback, iterate on scoring
- Task R3-3: Manual override documentation (1h) — ensure override always available
- Task R3-4: Monitoring & alerting (2h) — track recommendation acceptance rate

**Risk 4: Audit Logging Overhead**
- Task R4-1: Async audit logging (2h) — don't block skill execution
- Task R4-2: Performance profiling (2h) — measure actual overhead

**Risk 5: Workflow Debugging**
- Task R5-1: Step-by-step logging (2h) — log detailed state at each step
- Task R5-2: Pause/resume capability (2h) — allow inspection of intermediate outputs
- Task R5-3: Workflow versioning (2h) — track versions for reproducibility

---

## Success Criteria Summary

### Context Integrity (Phase 1)
- ✅ All 31 skills use identical borough definitions
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
- ✅ Pre-built workflows available for 5+ common tasks
- ✅ Workflows save 30-50% time vs. manual skill chaining
- ✅ New analysts can run sophisticated workflows with guidance

### Overall
- ✅ Analysts save 20-30% of time on context setup
- ✅ Zero context loss between analysis steps
- ✅ Full compliance audit trail for regulatory requirements
- ✅ New analysts can navigate skill menu without training

---

## Key Files & Deliverables

**Config Files (Phase 1):**
- `/config/datasets.json`
- `/config/business_rules.json`
- `/config/metrics.json`
- `/config/quality_gates.json`

**Python Modules:**
- `src/config_system.py`
- `src/config_models.py`
- `src/skill_orchestrator.py`
- `src/skill_adapters.py`
- `src/audit_logger.py`
- `src/discovery_engine.py`
- `src/workflow_executor.py`

**Config Files (Phase 2-3):**
- `/config/skill_registry.json`
- `/config/workflow_templates.json`

**Test Files:**
- `tests/test_config_consistency.py`
- `tests/test_chaining_basic_2skill.py`
- `tests/test_chaining_3skill.py`
- `tests/test_chaining_compatibility.py`
- `tests/test_workflows_execution.py`
- `tests/test_discovery_accuracy.py`
- `tests/test_discovery_recommendations.py`
- `tests/test_integration_final.py`

**Documentation:**
- `docs/discovery_and_workflows_user_guide.md`
- `docs/notebooks/workflow_new_dataset_assessment.ipynb`
- `docs/notebooks/workflow_metric_investigation.ipynb`
- `docs/notebooks/workflow_borough_analysis.ipynb`
- `PHASE1_VERIFICATION_REPORT.md`
- `PHASE1_PERFORMANCE_BASELINE.md`
- `PHASE2_PERFORMANCE_BASELINE.md`
- `PHASE3_PERFORMANCE_REPORT.md`

---

## Next Steps

1. **Assign team** — 2 FTE engineers (can be different skill levels)
2. **Set up environment** — Python 3.9+, Pydantic 2.0+, pytest
3. **Create git branch** — isolate work from main
4. **Start Phase 1A** — config file creation
5. **Run verification gates** — pass each phase before proceeding to next

**Ready to execute. Proceed with Phase 1A when approved.**
