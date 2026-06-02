---
name: technical-to-business-translator
description: Translate technical analysis into business language. Use when explaining statistical concepts to non-analysts, simplifying technical findings, or bridging communication between data teams and business stakeholders.
---

# When to use

When technical output (model results, statistical tests, query findings) needs to be understood by a business audience. Also use to review your own writing before sending — it is easy to slip into jargon without noticing.

# Process

1. **Detect jargon** — run `scripts/jargon_detector.py` on the draft text to flag technical terms that need translation.
2. **Score readability** — run `scripts/readability_scorer.py` to get Flesch-Kincaid grade level and sentence complexity metrics; target ≤ grade 10 for executive audiences.
3. **Identify the audience persona** — use `references/stakeholder_personas.md` to select the persona that best matches your reader; each persona has vocabulary preferences and typical questions.
4. **Apply translation patterns** — use `references/translation_pattern_library.md` to swap technical language for business equivalents (e.g., "p-value < 0.05" → "we're 95% confident this isn't random chance").
5. **Replace with metaphors where needed** — for complex statistical concepts, pick an appropriate metaphor from `references/metaphor_bank.md`.
6. **Draft the translated version** — use `assets/translation_template.md` to produce the parallel technical/business version; keep the original in an appendix for technical reviewers.

# Inputs the skill needs

- Draft technical text or findings
- Target audience role (VP, product manager, operations, finance, etc.)

# Output

- Jargon detection report
- Readability score before/after
- Translated text with original in appendix (`translation_template.md`)
