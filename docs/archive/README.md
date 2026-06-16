# Archived Documentation

This directory contains outdated documentation that is no longer actively maintained but preserved for historical reference.

## Directory Structure

### `/phases/` — Implementation Phase Planning (14 docs)

Historical planning documents from project phases 1–3. These describe the original implementation strategy and lessons learned.

**Note:** Current development is tracked in the active documentation in the parent `/docs/` directory and git commit history.

**Contains:**
- Phase 1 (GIS pilot, design, implementation)
- Phase 2 (integration, architecture strategy)
- Phase 3 (completion, integration guide)
- Related reports and checklists

**When to use:**
- Understanding historical architectural decisions
- Learning from past project phases
- Tracing how features were originally planned vs. current implementation

### `/deprecated/` — Outdated Implementations (4 docs)

Documentation for superseded implementations, old versions, or approaches that are no longer used.

**Contains:**
- `DEPLOYMENT_GUIDE_v0.5.0.md` — Old version (current: DEPLOYMENT_GUIDE.md)
- `IMPLEMENTATION_SUMMARY_5METHODS.md` — Old 5-methods proposal (superseded by current architecture)
- `TESTING_REPORT_5METHODS.md` — Old testing approach report
- `UI_INTEGRATION_PLAN_5METHODS.md` — Old UI plan (superseded by Dash-primary architecture)

**When to use:**
- Comparing old vs. current implementation approaches
- Reviewing deprecated feature proposals

### `/reports/` — Project Completion Reports (12 docs)

Final reports and assessments from completed project milestones.

**Contains:**
- Architectural assessments
- Comprehensive verification reports
- Post-implementation reviews
- Dataverse architecture documentation
- Completion summaries

**When to use:**
- Reviewing completed project work
- Understanding architecture decisions made
- Post-mortems and lessons learned

---

## Migration History

**Current Documentation:** All active user-facing docs are in the parent `/docs/` directory:
- `QUICKSTART.md` — Getting started
- `DEPLOYMENT_GUIDE.md` — Deployment instructions
- `COMMAND_REFERENCE.md` — CLI commands
- `CI.md` — CI/CD architecture
- `MISSION_CONTROL.md` — Dashboard reference
- And 170+ more in active use

**Archive Date:** 2026-06-16

**Reason:** Consolidating documentation structure, removing outdated phase planning docs, and clarifying which docs are current vs. historical.

---

## Accessing Archived Docs

If you need to reference an archived document:

1. **Browse this directory** — Use `README.md` files in subdirectories for categorized listings
2. **Check git history** — All archived docs remain in git; use `git log --all -- docs/archive/` to see when they were moved
3. **Search by filename** — Use `find docs/archive -name "*.md" -type f` to locate files

---

## Adding to Archive

When archiving a document:

1. **Create or use appropriate subdirectory** (`phases/`, `deprecated/`, `reports/`, etc.)
2. **Move the file** — `mv docs/OLD_DOC.md docs/archive/deprecated/`
3. **Update this README** — Add entry to relevant section
4. **Commit the move** — `git add docs/archive && git commit -m "archive: Move OLD_DOC to deprecated"`

---

## Current (Active) Documentation Locations

For current, maintained documentation, see:

| Topic | File | Location |
|-------|------|----------|
| Quick start | QUICKSTART.md | `/docs/` |
| Deployment | DEPLOYMENT_GUIDE.md | `/docs/` |
| Dashboard reference | MISSION_CONTROL.md | `/docs/` |
| CLI reference | COMMAND_REFERENCE.md | `/docs/` |
| CI/CD architecture | CI.md | `/docs/` |
| Data analysis components | ANALYSIS_MODULES.md | `/docs/` |
| Project instructions | CLAUDE.md | `/` (repo root) |
