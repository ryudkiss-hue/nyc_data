# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A library of 31 reusable analytical skill definitions for Claude, organized into 6 categories. Skills are Markdown-based instruction sets with optional Python utilities. This is a documentation + reference library, not a deployable application.

## Validation

```bash
python validate_skills.py
```

Checks every skill directory for: presence of `SKILL.md`, valid YAML frontmatter (`name:`, `description:`), and required sections (`## When to use`, `## Process`, `## Inputs the skill needs`, `## Output`). Run after adding or modifying any `SKILL.md`.

## Running Python utility scripts

Each skill's `scripts/` folder contains standalone CLI tools. All accept `--input` or similar flags; most run with synthetic demo data when called without args.

```bash
python 01-data-quality-validation/programmatic-eda/scripts/data_overview.py --input data.csv
python 03-data-analysis-investigation/ab-test-analysis/scripts/ab_test_analyzer.py --control-n 5000 --control-conv 480 --treatment-n 5100 --treatment-conv 530
```

## Architecture

### Skill structure (every skill follows this pattern)

```
<NN-category>/<skill-name>/
├── SKILL.md          # Required. YAML frontmatter + 4 mandatory sections
├── scripts/          # Optional. Standalone Python CLI utilities
├── references/       # Optional. Frameworks, glossaries, anti-patterns
└── assets/           # Optional. Output templates (Markdown, YAML, HTML)
```

### Category organization

| # | Category | Skills |
|---|---|---|
| 01 | data-quality-validation | programmatic-eda, data-quality-audit, query-validation, schema-mapper, metric-reconciliation |
| 02 | documentation-knowledge | semantic-model-builder, analysis-documentation, data-catalog-entry, sql-to-business-logic, analysis-assumptions-log |
| 03 | data-analysis-investigation | cohort-analysis, segmentation-analysis, funnel-analysis, time-series-analysis, root-cause-investigation, ab-test-analysis, business-metrics-calculator |
| 04 | data-storytelling-visualization | insight-synthesis, visualization-builder, executive-summary-generator, dashboard-specification, data-narrative-builder |
| 05 | stakeholder-communication | technical-to-business-translator, stakeholder-requirements-gathering, analysis-qa-checklist, methodology-explainer, impact-quantification |
| 06 | workflow-optimization | analysis-planning, context-packager, peer-review-template, analysis-retrospective |

### Common skill chains

- **New dataset**: `programmatic-eda` → `data-quality-audit` → analysis skills
- **Metric definition**: `semantic-model-builder` → `analysis-documentation`
- **Delivering findings**: `insight-synthesis` → `technical-to-business-translator` → `executive-summary-generator`
- **Any analysis**: `analysis-qa-checklist` + `analysis-assumptions-log` as quality gates

## Conventions

### SKILL.md format

```markdown
---
name: skill-name
description: One-line description
---

## When to use
## Process
## Inputs the skill needs
## Output
```

The Process section uses numbered steps (typically 6–7). All four sections are mandatory.

### Python scripts

- Standalone CLI tools using `argparse`; no frameworks
- Dependencies: only `pandas`, `numpy`, and stdlib (`re`, `json`, `math`, `argparse`)
- Pattern: core function(s) + `main()` that runs a demo when called without real args
- Input: CSV/Parquet/Excel. Output: formatted stdout + optional file save
- No scipy, scikit-learn, or external stats packages — implement statistical tests directly

### Asset templates

- Markdown templates use `[REQUIRED]` and `[OPTIONAL]` placeholders
- YAML definitions follow dbt Semantic Layer conventions (see `02-documentation-knowledge/semantic-model-builder/assets/metric_definition.yaml`)
- HTML templates: self-contained with inline styles (used for heatmaps)

### Naming

- Category dirs: `NN-category-name/` (numeric prefix preserves order)
- Skill dirs and files: `kebab-case` for dirs, `snake_case.py` / `snake_case.md` for files

## Exemplar skill

`01-data-quality-validation/programmatic-eda/` is the most complete skill — read it first to understand the expected depth and structure for scripts, references, and assets.
