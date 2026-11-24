---
name: context-packager
description: Package and compress the context needed for an AI-assisted analysis session. Use when starting a complex analysis with Claude to minimise token usage, reduce repetition, and establish shared understanding upfront.
---

# When to use
- Starting a multi-turn AI analysis session where context will be referenced repeatedly
- Restarting a conversation and need to rebuild context efficiently
- Sharing context with a collaborator who will continue an AI-assisted analysis
- When an AI session keeps losing context and producing inconsistent results

# Process
1. **Identify context layers** — use `references/context_layering_guide.md` to determine what layers are needed: business context, data schema, metric definitions, analytical constraints, and output format preferences
2. **Consolidate sources** — use `scripts/context_bundler.py` to merge schema docs, metric definitions, and business rules into a single structured file
3. **Verify token budget** — estimate token count; trim to fit within budget while preserving the highest-signal context
4. **Assess quality** — score the package against `references/context_quality_rubric.md`; ensure it covers the minimum viable context for the analysis
5. **Craft the task statement** — write a clear opening prompt that references the packaged context and states the analytical goal
6. **Save for reuse** — store the package for future sessions on the same dataset or analysis area

# Inputs the skill needs
- Required: description of the analytical goal
- Required: source materials (schema docs, metric definitions, reports, data samples)
- Required: token budget ceiling

# Output
- Unified context file (structured markdown)
- Token estimate
- Context quality score
- Formatted prompt ready for use with Claude
