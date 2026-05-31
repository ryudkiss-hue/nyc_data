---
name: context-packager
description: Efficiently package context for AI-assisted analysis. Use when preparing to work with Claude on analysis, organizing context documents, or structuring prompts for complex analytical tasks.
---

# When to use

Before starting an AI-assisted analysis session when the task requires more than a single prompt — complex investigations, multi-step analyses, or work that depends on project-specific knowledge. A well-packaged context bundle reduces back-and-forth and produces better first responses.

# Process

1. **Identify required context layers** — use `references/context_layering_guide.md` to decide which layers are needed: task definition, business context, data schema, prior findings, constraints, and output format.
2. **Collect and deduplicate sources** — run `scripts/context_bundler.py` to merge multiple context files into a single structured bundle; it deduplicates and applies the layering order.
3. **Check token budget** — run `scripts/token_counter.py` on the bundle to estimate token count; trim lower-priority layers if over budget (see `references/context_layering_guide.md` for trimming priority).
4. **Score context quality** — evaluate the bundle against `references/context_quality_rubric.md`; a good bundle scores ≥ 7/10 on completeness, clarity, and relevance.
5. **Write the prompt header** — prepend a clear task statement to the bundle: what you need, what output format you expect, and any hard constraints.
6. **Save the package** — store the bundle using `assets/context_package_template.md` so it can be reused or updated for follow-up sessions.

# Inputs the skill needs

- Task description (what you want the AI to do)
- List of context source files or snippets (schema docs, prior reports, business definitions)
- Token budget (default: 100k tokens)

# Output

- Merged context bundle (single text file)
- Token count estimate
- Context quality score
- Ready-to-use prompt with task header (`context_package_template.md`)
