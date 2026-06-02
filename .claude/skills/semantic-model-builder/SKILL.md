---
name: semantic-model-builder
description: Build structured semantic layer documentation for metrics, dimensions, and entities. Activate when you need to define a business metric, document a data model, or create YAML definitions compatible with dbt Semantic Layer or similar frameworks.
---

# When to use
- A stakeholder asks "how is [metric] calculated?" and no canonical definition exists
- You're setting up dbt Semantic Layer and need YAML metric/dimension/entity definitions
- Multiple teams are using different SQL queries for the same metric — you need to codify the one true definition
- You're building a data catalog entry for a core model and need structured metadata

# Process
1. **Identify the object type** — decide whether you're documenting a metric, a dimension, or an entity. Use the frameworks in `references/metric_definition_framework.md` for metrics and `references/dimension_hierarchy_patterns.md` for dimensions.
2. **Gather the definition inputs** — collect: calculation logic (SQL or formula), business context, data source(s), grain, edge cases, and known gotchas. Ask the data owner if anything is unclear.
3. **Generate the YAML template** — run `scripts/metric_template_generator.py` to scaffold the initial YAML structure for the object type. Fill in the generated template.
4. **Validate the YAML** — run `scripts/model_yaml_validator.py` to check required fields, type constraints, and reference integrity (referenced dimensions exist in the same file).
5. **Add dbt context** — if this will be deployed to dbt Semantic Layer, consult `references/dbt_semantic_layer_guide.md` for the exact field names and constraints for your dbt version.
6. **Save final definitions** — save metrics to `assets/metric_definition.yaml`, dimensions to `assets/dimension_definition.yaml`, entities to `assets/entity_definition.yaml`.

# Inputs the skill needs
- Required: the metric name or model name to document
- Required: calculation logic — SQL snippet, formula, or plain-English steps
- Required: business context — who uses it, what decision it informs, what a "good" value looks like
- Optional: data source table(s) and column names
- Optional: target semantic layer framework (dbt Semantic Layer, Cube.js, LookML, etc.)
- Optional: existing YAML to validate

# Output
- `assets/metric_definition.yaml` — filled metric YAML definition(s)
- `assets/dimension_definition.yaml` — filled dimension YAML definition(s)
- `assets/entity_definition.yaml` — filled entity YAML definition(s)
- Validation report from `scripts/model_yaml_validator.py` (inline output)
