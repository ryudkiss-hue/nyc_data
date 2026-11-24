# Data Analytics Skills for Claude

**31 portable AI-powered skills that turn Claude into a hands-on analytics partner**

*No setup required · Works for any company or industry*

---

## What's in this repo?

A structured library of **skills** (reusable instruction sets) that Claude activates on demand to help with every stage of the analyst workflow: from data quality checks and deep-dive analysis, through documentation and dashboards, all the way to stakeholder communication.

---

## Why these skills are different

| Traditional approach | These skills |
|---------------------|--------------|
| Needs prep before use | Zero setup required |
| Breaks when business rules change | Adapts naturally |
| Company-specific, hard to share | Portable across any org |
| Silent on assumptions | Teaches you what context matters |

Each skill asks targeted questions to gather exactly what it needs, then executes a complete, structured workflow.

---

## Skill Categories

**01 · Data Quality & Validation** — 5 skills
- programmatic-eda, data-quality-audit, query-validation, schema-mapper, metric-reconciliation

**02 · Documentation & Knowledge** — 5 skills
- semantic-model-builder, analysis-documentation, data-catalog-entry, sql-to-business-logic, analysis-assumptions-log

**03 · Data Analysis & Investigation** — 7 skills
- cohort-analysis, segmentation-analysis, funnel-analysis, time-series-analysis, root-cause-investigation, ab-test-analysis, business-metrics-calculator

**04 · Data Storytelling & Visualization** — 5 skills
- insight-synthesis, visualization-builder, executive-summary-generator, dashboard-specification, data-narrative-builder

**05 · Stakeholder Communication** — 5 skills
- technical-to-business-translator, stakeholder-requirements-gathering, analysis-qa-checklist, methodology-explainer, impact-quantification

**06 · Workflow Optimization** — 4 skills
- analysis-planning, context-packager, peer-review-template, analysis-retrospective

---

## Quick Start

Describe your task to Claude naturally — it selects and activates the right skill automatically.

| You need to... | Start here |
|---------------|-----------|
| Explore an unfamiliar dataset | `programmatic-eda` → `data-quality-audit` |
| Write or review SQL | `query-validation` + `schema-mapper` |
| Understand a metric drop/spike | `root-cause-investigation` |
| Analyze experiment results | `ab-test-analysis` |
| Build a dashboard | `dashboard-specification` + `visualization-builder` |
| Present to leadership | `executive-summary-generator` + `insight-synthesis` |
| Document your methodology | `analysis-documentation` + `analysis-assumptions-log` |
| Start a complex analysis | `analysis-planning` first, always |

---

## How skills work

1. **Request minimum viable context** — Claude asks only what's essential to start
2. **Execute the workflow** — structured, step-by-step analytical process
3. **Surface assumptions** — anything uncertain is flagged, not silently assumed
4. **Deliver a consistent output** — templated result you can share or iterate on

Skills degrade gracefully: if you can't provide everything, Claude states what it's assuming and proceeds.

---

## Customization

Add a `references/` folder inside any skill with company-specific context:
```
skill-name/
├── SKILL.md
└── references/
    ├── company-schema.md
    ├── metric-definitions.md
    └── business-rules.md
```

**Version:** 1.1.0 · **Maintainer:** Nimrod Fisher · **Last Updated:** April 2026
