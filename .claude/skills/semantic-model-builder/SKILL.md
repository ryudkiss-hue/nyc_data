---
name: semantic-model-builder
description: Create a structured semantic layer definition for a metric, dimension, or entity. Use when you need a canonical, shareable definition that can feed dbt Semantic Layer, a data catalog, or a BI tool's metric store.
---

# When to use
- A stakeholder or team needs a canonical definition for a business metric
- Multiple teams are using different SQL to calculate the same KPI
- Implementing or extending a dbt Semantic Layer
- Building data catalog entries that need machine-readable metric definitions
- Onboarding a new analyst who needs to understand how key metrics are calculated

# Process
1. **Identify the object type** — determine whether you're defining a metric (a numeric aggregation), a dimension (a groupable attribute), or an entity (a primary object like customer or order)
2. **Gather definition inputs** — collect from the data owner: calculation logic (SQL or formula), grain, dimensions it can be sliced by, filters that always apply, and known edge cases
3. **Generate YAML scaffolding** — use `scripts/semantic_model_generator.py` to produce a structured YAML definition with required fields, validation rules, and dbt-compatible syntax
4. **Validate the output** — run `scripts/definition_validator.py` to check required fields, type constraints, and reference integrity across definitions
5. **Add dbt context** — if the target is dbt Semantic Layer, add `model`, `label`, and `meta` blocks; reference the dbt integration guide in `references/dbt_semantic_layer_guide.md`

# Inputs the skill needs
- Required: metric or model name
- Required: calculation logic (SQL snippet, formula, or plain-language description)
- Required: business context — what decision does this metric inform? What does "good" look like?
- Optional: source tables and column names
- Optional: target framework (dbt Semantic Layer, LookML, Cube, plain YAML)

# Output
- `assets/metric_definition.yaml` — structured metric definition with calculation, grain, dimensions, and filters
- `assets/dimension_definition.yaml` — dimension definitions referenced by metrics
- `assets/entity_definition.yaml` — entity definitions (primary objects)
- Validation report confirming required fields and reference integrity
