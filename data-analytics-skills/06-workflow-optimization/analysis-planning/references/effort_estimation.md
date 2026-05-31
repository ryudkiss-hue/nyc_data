# Effort Estimation for Analysis Work

Guidelines for estimating how long analysis tasks will take. Use these as starting points, then adjust based on experience.

---

## Reference Estimates by Task Type

### Data Exploration and Profiling

| Task | Estimate | Notes |
|---|---|---|
| Run EDA on a new dataset (< 20 columns) | 1–2 hours | Using `programmatic-eda` scripts |
| Profile a large table (> 50 columns) | 3–4 hours | Include time for anomaly investigation |
| Understand a new data source (unfamiliar system) | 0.5–1 day | Add time for documentation review and Q&A |

### SQL and Data Extraction

| Task | Estimate | Notes |
|---|---|---|
| Simple aggregation query (1–2 tables) | 30 min | Familiar tables |
| Complex multi-join query (3+ tables) | 2–4 hours | Include test and validation time |
| Query a new/unfamiliar schema | 2× baseline | Add time for schema exploration |
| Build a reusable CTE-based data model | 0.5–1 day | |

### Analysis and Modelling

| Task | Estimate | Notes |
|---|---|---|
| Cohort / retention analysis | 0.5–1 day | |
| A/B test results analysis | 2–4 hours | Assuming clean experiment data |
| Funnel analysis | 3–5 hours | |
| Segmentation / clustering | 0.5–1 day | |
| Predictive model (standard algorithm, clean data) | 1–3 days | |
| Predictive model (new domain, messy data) | 3–5 days | |
| Forecasting (time series) | 1–2 days | |

### Stakeholder Communication

| Task | Estimate | Notes |
|---|---|---|
| Write one-page findings summary | 1–2 hours | |
| Build a slide deck (5–8 slides) | 3–5 hours | |
| Build a dashboard (new, 3–5 charts) | 0.5–1 day | |
| Write a full analysis report | 0.5–1 day | |
| Incorporate stakeholder feedback (1 round) | 1–3 hours | |

---

## Estimation Adjustments

Apply multipliers to the base estimate:

| Condition | Multiplier |
|---|---|
| Familiar data, familiar question type | 1.0× |
| New data source | 1.5× |
| Data quality issues suspected | 1.5–2× |
| Stakeholder hasn't confirmed requirements | 1.5× (risk of rework) |
| First time doing this type of analysis | 2× |
| Collaboration with another analyst | 0.7× (parallel work) |
| Context switch (not your primary focus) | 1.3× |

---

## Buffer Rules

- Always add a **10–15% buffer** for unexpected data issues
- For projects over 3 days: add a **half-day contingency** per week of work
- For any analysis with an external dependency (access request, data delivery): add **1–2 days** for the dependency

---

## Common Under-estimation Patterns

| Trap | Why it happens | Fix |
|---|---|---|
| Forgetting validation time | Analysts plan for the happy path | Add 20% of analysis time for testing and QA |
| Assuming data is ready | It rarely is | Check availability before committing to a date |
| Forgetting stakeholder feedback cycles | One round of feedback = at least 2 hours | Budget for at least one revision round |
| Underestimating unfamiliar tools | Confidence in the method, not the tool | Add ramp-up time for new tools |
| Not accounting for interruptions | Focus time is rare | Treat 6 hours as a full productive day, not 8 |
