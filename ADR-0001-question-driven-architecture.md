---
title: Question-Driven Architecture for SIM Division Analytics
status: ACCEPTED
date: 2026-06-19
decision_makers: Claude Code Agent + User
---

# ADR-0001: Question-Driven Architecture for SIM Division Analytics

## Problem

**Analyst context loss:** SIM analysts had to manually navigate between:
- 60+ research questions (from `sim_division_research_operational_questions.md`)
- 309+ KPIs (from `sim_research_questions_to_kpi_mapping.md`)
- 48 datasets (from `sim_dataset_research_question_traceability.md`)
- 10 analysis skills (from `sim_skills_activation_playbook.md`)

**Shallow modules everywhere:** This context was spread across memory files, not code. Each analyst had to copy-paste datasets, manually select skills, and write custom SQL.

**No skill chaining:** When an EDA found outliers, there was no programmatic way to activate root-cause-investigation next.

## Decision

Implement **three deep modules** that centralize this logic:

### 1. QuestionKPIResolver (Deep Module)
- **Input:** Analyst question (text)
- **Output:** QuestionResolution with datasets, KPIs, SQL pattern, primary/secondary skills
- **Locality:** All 60+ question-to-data mappings in one place
- **Test Surface:** Question matching, confidence scoring
- **Implementation:** `src/socrata_toolkit/core/question_resolver.py`

### 2. SkillActivator (Deep Module)
- **Input:** QuestionResolution
- **Output:** SkillContext with pre-populated parameters, datasets, KPI IDs
- **Locality:** All skill routing and chaining rules in one place
- **Test Surface:** Skill selection, chain triggering
- **Implementation:** `src/socrata_toolkit/core/skill_activator.py`

### 3. GlossaryService (Deep Module) [Future]
- **Input:** Metric name
- **Output:** Definition, formula, threshold, data source
- **Locality:** Single source of truth for all terminology
- **Test Surface:** Metric validation against glossary
- **Implementation:** TBD (s/socrata_toolkit/core/glossary_service.py)

## Benefits

### Locality
- **Today (Shallow):** Changes to question/KPI mapping require edits to 5 memory files
- **Tomorrow (Deep):** Changes only affect `question_resolver.py`

### Testability
- Can mock datasets and verify KPI lookup logic
- Can test skill routing without running actual skills
- Can test chaining rules without executing analyses

### Analyst Self-Service
```python
# Question → KPI → Skill in 3 lines
resolver = QuestionKPIResolver()
resolution = resolver.resolve_question("What is the current SCI by borough?")
context = SkillActivator().activate(resolution)
```

### Traceability
Every KPI traces back:
- KPI-001 ← Question A1 ← Dataset violations ← SQL pattern

### Scalability
Adding a new question:
1. Add entry to `QuestionKPIResolver.mappings`
2. Register any new KPIs
3. Done — skill activation and SQL generation work automatically

## Non-Decisions

**What we're NOT doing:**
- Externalizing mappings to YAML yet (hardcoded Python is fine for MVP)
- Building a UI for question selection (CLI first, then dashboard)
- Materializing all 309 KPIs at once (prioritize by frequency of use)

## Consequences

### Positive
- Analysts can ask questions in plain English, get analysis paths back
- Framework scales to 100+ questions without architectural changes
- Skill chains enable progressive analysis (EDA → outliers → root-cause)
- One source of truth for question/KPI/dataset relationships

### Negative
- QuestionKPIResolver is now a bottleneck for question definitions
- Every new question requires editing Python code (not YAML)
- Skill parameters hardcoded by skill type, not per-question (may need flexibility later)

## Implementation Timeline

**Phase 1 (Week 1):** ✅ QuestionKPIResolver + SkillActivator (DONE)

**Phase 2 (Week 2):** GlossaryService + wire into CLI (`socrata question <text>`)

**Phase 3 (Week 3):** Dashboard integration + skill chaining UX

**Phase 4 (Week 4):** Externalize to YAML for non-engineers to add questions

## Alternatives Considered

### Alternative A: Memory Files Only (Rejected)
- **Pros:** No code changes needed
- **Cons:** No programmatic routing, analysts copy-paste, no chaining, no testability
- **Decision:** Rejected — doesn't solve the core problem

### Alternative B: Monolithic AnalysisOrchestrator (Rejected)
- **Pros:** Single class handles everything
- **Cons:** Violates single responsibility; questions/skills/datasets entangled
- **Decision:** Rejected — separating into QuestionKPIResolver + SkillActivator is cleaner

### Alternative C: External Config-Driven (Deferred)
- **Pros:** Analysts can add questions without touching Python
- **Cons:** Overkill for MVP; adds complexity
- **Decision:** Deferred to Phase 4 after we validate the model works

## Related Decisions

- ADR-0002: GlossaryService design (TBD)
- ADR-0003: CLI integration (`socrata question`) (TBD)
- ADR-0004: Dashboard skill activation UX (TBD)

## Open Questions

1. **Skill Parameters:** How to handle per-question overrides? (e.g., Q-A1 wants 10 bins, Q-A2 wants 30 bins)
   - **Answer:** Store in QuestionResolution.notes for now; refactor if pattern emerges

2. **Question Confidence:** How to handle fuzzy matching?
   - **Answer:** Keyword-based fuzzy match with 0.4 threshold; can be tuned

3. **Skill Chaining:** How deeply to chain?
   - **Answer:** Primary → Secondary only (2 skills max) to avoid analysis paralysis

## Sign-Off

**Approved by:** User + Claude Code Architecture Assessment

**Effective Date:** 2026-06-19

**Supersedes:** None (baseline architecture decision)

