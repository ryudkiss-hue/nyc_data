# EDA Findings Summary: [Dataset Name]

**Date:** [YYYY-MM-DD]  
**Analyst:** [Name]  
**Full report:** `assets/eda_report_template.md`

---

## Dataset at a Glance

[Dataset name] contains [N] rows representing [grain — e.g. "one row per user session"]. The analysis covers [date range]. Overall data quality is [Good / Acceptable / Poor — one sentence why].

---

## Top Quality Issues

List the 3–5 most significant findings in priority order. Each should answer: what is the issue, how bad is it, and what should happen next.

### Issue 1: [Short title]
- **What:** [Specific column or pattern — e.g. "`revenue` has 12% nulls"]
- **Impact:** [How this affects downstream analysis or business decisions]
- **Recommended action:** [Fix in pipeline / impute / exclude column / accept risk]
- **Owner:** [Data engineering / Analyst / Business stakeholder]

### Issue 2: [Short title]
- **What:**
- **Impact:**
- **Recommended action:**
- **Owner:**

### Issue 3: [Short title]
- **What:**
- **Impact:**
- **Recommended action:**
- **Owner:**

---

## What Looks Good

- [Column X is 100% complete and within expected range.]
- [No full-row duplicates detected.]
- [Date coverage is continuous from [start] to [end] with no gaps.]

---

## Next Step

[ ] Data is ready for analysis — proceed to [next skill / analysis type]  
[ ] Data fix required before proceeding — ticket created: [link]  
[ ] Further investigation needed: [specific question]
