---
name: methodology-explainer
description: Create a clear, transparent explanation of analytical methodology for any audience level. Activate when you deliver findings that require the audience to trust the method — A/B tests, attribution models, forecasts, statistical analyses, or anything where "how did you get that?" is a likely question.
---

# When to use
- Delivering A/B test results where the statistical method needs justification
- Presenting a forecast or model where assumptions must be communicated
- Documenting methodology for reproducibility and audit
- Onboarding a stakeholder who needs to understand and trust a recurring analysis
- Any analysis where "how did you get that?" is a likely question

# Process
1. **Determine audience tier** — classify as executive (decision-maker, no stats background), analyst (technically literate peer), or technical peer (will scrutinise the method). Tier determines depth and format.
2. **Select explanation pattern** — choose: narrative (for executives), layered technical (for analysts — plain first, then detail on request), or Q&A format (for peer review). See `references/explanation_patterns.md`.
3. **Draft the core explanation** — cover: what question the analysis answers, what data was used, what method was applied, what assumptions were made, and what the key limitations are
4. **Simplify statistical language** — replace p-values with confidence statements, model metrics with error margins, technical method names with purpose descriptions. See `references/stats_plain_language.md`.
5. **Add a limitations section** — every methodology explanation must include what the analysis cannot conclude and what would change the findings
6. **Produce deliverables** — fill `assets/methodology_writeup_template.md` or `assets/methodology_slide_template.md` depending on format

# Inputs the skill needs
- Required: the method to explain — choose from the built-in list:
  `wilson_score`, `iqr_outlier`, `z_score`, `linear_regression`, `kmeans`
- Required: target audience — `field_staff | manager | council | public`
- Optional: known concerns or questions the audience is likely to raise
- Optional: format requirements (slide, written doc, email)

**Quick start (script — no external data required):**
```bash
python3 scripts/explain_method.py --method wilson_score --audience manager
python3 scripts/explain_method.py --method z_score --audience council
```
The script prints the formula, plain-language explanation, an NYC DOT example,
and the audience-tailored phrasing. For custom methods not in the list, use the
templates in `assets/` directly.

# Output
- Plain-language methodology write-up
- Limitations paragraph
- `assets/methodology_writeup_template.md` or `assets/methodology_slide_template.md` (filled)
