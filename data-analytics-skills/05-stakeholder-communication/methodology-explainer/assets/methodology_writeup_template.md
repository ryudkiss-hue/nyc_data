# Methodology Write-Up — [Analysis Name]

**Audience tier:** Executive / Analyst / Technical
**Prepared by:** [Name]
**Date:** [YYYY-MM-DD]
**Related analysis:** [Link or file name]

---

## What Question This Answers

[State the business question in one sentence. E.g.: "Which boroughs are at risk of missing the Q4 ADA ramp completion target, and by how much?"]

---

## Data Used

| Dataset | Key | Fourfour | Rows used | Pull date | Last modified |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |

**Filters applied:**
- [e.g. `borough IN ('MN','BX','BK','QN','SI')`]
- [e.g. `inspection_date >= '2025-01-01'`]

---

## Method (Plain Language)

[Write 3–5 sentences in language appropriate for the audience tier. Use the patterns in `references/explanation_patterns.md`. For executive tier: no method names, no formulas. For analyst tier: describe the steps. For technical tier: name the method and cite implementation.]

**Executive version:**
> [Paste plain-language summary here]

**Analyst version (optional — include if audience is operations/manager tier):**
> [Add "How we calculated this" paragraph here]

---

## Key Assumptions

1. [Assumption — state the value assumed and the source]
2. [Assumption]
3. [Assumption]

**Assumption we're least confident in:** [Name it and explain why]

---

## Limitations

What this analysis cannot tell you:

1. [e.g. "Why a particular borough lags — this analysis shows the gap, not the cause"]
2. [e.g. "Whether ramps marked 'complete' in the database have been physically confirmed"]
3. [e.g. "Impact of records with null geometry (N=1,247 excluded from spatial analysis)"]

**What would change the conclusion:**
[e.g. "If the completion date column is systematically mis-recorded for Staten Island, the borough's true rate could be 5–10 pp higher than shown."]

---

## Reproducibility

**Code / query location:** [Path or link]

**To reproduce:**
```bash
# paste exact command or notebook cell here
```

**Dependencies:** [Python packages, dataset versions, DuckDB cache state]

---

## Peer Review Status

- [ ] Logic reviewed by: [Name] on [Date]
- [ ] QA checklist completed (see `analysis-qa-checklist/assets/qa_signoff_template.md`)
- [ ] Assumptions validated with: [SME name / team]
