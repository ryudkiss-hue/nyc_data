---
name: technical-to-business-translator
description: Reframe technical analysis findings in business language. Activate when findings need to reach a non-technical audience, when jargon is obscuring the message, or when a stakeholder needs to understand and act on statistical results without a technical background.
---

# When to use
- Delivering analysis results to a VP, C-suite, or business team without data backgrounds
- A technical report needs a plain-language executive version
- Statistical output (p-values, confidence intervals, model metrics) needs business translation
- A dashboard explanation needs to be written for non-technical users

# Process
1. **Detect and list jargon** — run `scripts/jargon_detector.py` to flag technical terms; score reading level against grade-10 target
2. **Match audience persona** — identify the audience type (executive, product manager, finance, ops) and their known priorities using `references/audience_personas.md`
3. **Apply translation patterns** — replace jargon using `references/translation_patterns.md` (e.g. "statistically significant at p < 0.05" → "we're 95% confident this result is real, not random"); use metaphor bank for complex concepts
4. **Rewrite for business framing** — restructure findings around business outcomes: revenue, cost, risk, customer impact. Lead with the implication, not the method.
5. **Review readability** — re-run `scripts/jargon_detector.py` on the translated version; verify grade-10 readability and no residual jargon
6. **Produce dual output** — generate a plain-language version alongside the original technical version for reference

# Inputs the skill needs
- Required: the technical text, findings, or report to translate
- Required: target audience (role and technical comfort level)
- Optional: business priorities or context of the audience
- Optional: decisions the audience needs to make based on the findings

# Output
- Jargon report with flagged terms and suggested replacements
- Before/after readability scores
- Dual-version document: translated business language + original technical version
