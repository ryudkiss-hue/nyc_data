# Peer Review Framework

How to structure and run an effective peer review of analytical work. Applies to notebooks, reports, dashboards, and SQL.

---

## When to Require Peer Review

| Situation | Review required? |
|---|---|
| Analysis drives a major strategic decision (> $100K impact or irreversible) | Yes — mandatory |
| Analysis goes into a stakeholder-facing dashboard | Yes — mandatory |
| A/B test conclusions that will change product or pricing | Yes — mandatory |
| Ad-hoc analysis for a recurring report | Yes — recommended |
| One-off exploratory analysis (internal only) | Optional |
| Quick sanity check / spot query | Not required |

---

## Types of Review

### Full Review
**Scope:** Logic, data, code, and communication  
**Time:** 60–90 minutes  
**When:** Strategic decisions, external reporting, production dashboards

### Logic Review
**Scope:** Is the question answered correctly? Are the conclusions supported?  
**Time:** 20–30 minutes  
**When:** Most analytical deliverables

### Code Review
**Scope:** SQL/Python correctness, reproducibility, performance  
**Time:** 20–40 minutes  
**When:** Scripts going into production, shared models, reusable pipelines

### Sanity Check
**Scope:** Does the output look plausible? Are the numbers in the right ballpark?  
**Time:** 5–10 minutes  
**When:** Any analysis before the full review; quick gut-check

---

## Reviewer Responsibilities

1. **Read the brief first** — understand what the analysis was trying to answer before evaluating whether it succeeded.
2. **Review against the question, not your preferences** — the right analysis for the stated question may not be the analysis you would have done.
3. **Be specific** — "this is unclear" is not actionable. Cite the specific line, number, or claim.
4. **Distinguish blockers from suggestions** — clearly separate must-fix issues from nice-to-have improvements.
5. **Be timely** — return the review within the agreed window; a delayed review is a delivery blocker.

---

## Author Responsibilities

1. **Provide context** — share the brief or requirements doc with the reviewer; don't make them guess the question.
2. **Flag known issues** — tell the reviewer upfront what you're unsure about. "I'm not confident the join is right" saves everyone time.
3. **Respond to every comment** — even if you disagree; explain why. "Won't fix — the denominator is correct because..." is a valid response.
4. **Don't take feedback personally** — a good peer review is a gift that improves the quality of your work.

---

## Review Etiquette

| Do | Don't |
|---|---|
| Ask "why" when you don't understand a choice | Assume it's wrong |
| Suggest an alternative | Just say "this is wrong" |
| Acknowledge what's done well | Only write critical comments |
| Categorise your feedback (must-fix / should-fix / minor) | Leave priority ambiguous |
| Review promptly | Let a review sit for days |
