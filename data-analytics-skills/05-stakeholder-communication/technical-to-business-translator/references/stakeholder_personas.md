# Stakeholder Personas

Profiles of common business audiences. Use these to calibrate vocabulary, depth, and framing before writing or presenting analysis.

---

## Persona 1: The Executive (C-Suite / VP)

**Role:** Sets strategy, approves budgets, makes irreversible decisions  
**Available attention:** 2–5 minutes for a written output; 10 minutes for a presentation  
**Technical comfort:** Comfortable with percentages, ratios, and trends; uncomfortable with statistical notation  
**What they want:** Bottom line upfront, confidence level, recommended action, risk if wrong  
**What they don't want:** Methodology, caveats that don't change the decision, multiple charts of the same thing  

**Writing style for this persona:**
- Lead with the finding, not the process
- One key number per slide
- Use "$" and "%" rather than statistical scores
- Active voice: "Customers in X segment churn 40% less" not "A 40% reduction in churn was observed"

**Vocabulary to avoid:** p-value, confidence interval, regression, model accuracy, feature, pipeline

---

## Persona 2: The Product Manager

**Role:** Defines product roadmap; runs experiments; owns user metrics  
**Available attention:** 10–20 minutes for a written analysis  
**Technical comfort:** Comfortable with A/B test concepts, funnel metrics, cohort analysis; variable on statistics  
**What they want:** User behaviour insight, experiment results, segment breakdowns, actionable recommendations  
**What they don't want:** Deep statistical proofs; database-level detail  

**Writing style for this persona:**
- Metrics by user segment and lifecycle stage
- "Statistical significance" is OK; "p-value" less so
- Include a "what this means for the roadmap" paragraph
- Charts preferred over tables

**Vocabulary bridge:** "The test was significant" is fine; "p=0.03" replace with "we're 97% confident"

---

## Persona 3: The Finance / Business Analyst

**Role:** Models business performance; owns P&L or cost centre  
**Available attention:** 30–60 minutes for a full report  
**Technical comfort:** High for numbers and formulas; low for ML/statistics terminology  
**What they want:** Defensible numbers, clear assumptions, ability to stress-test the model  
**What they don't want:** Black-box outputs; vague ranges without methodology  

**Writing style for this persona:**
- Show the formula or calculation, not just the output
- Provide an assumption log they can adjust
- Include a sensitivity table
- Excel-friendly output formats where possible

**Vocabulary bridge:** "The model predicts" → "Based on the formula: [X] × [Y] = [result]"

---

## Persona 4: The Operations Lead

**Role:** Manages day-to-day team or process performance  
**Available attention:** 5 minutes; acts on dashboards and alerts  
**Technical comfort:** Comfortable with operational KPIs; low comfort with analytical methodology  
**What they want:** Clear signal on what to act on today; ranked lists; thresholds and alerts  
**What they don't want:** Historical analysis without a present-day action; uncertainty ranges that prevent action  

**Writing style for this persona:**
- "Here are the 10 accounts to contact today, ranked by risk"
- Traffic-light status (red/amber/green) over percentages
- Avoid preamble — get to the list or the action quickly

**Vocabulary bridge:** All technical terms → outcome + action

---

## Persona 5: The Marketing Lead

**Role:** Owns acquisition, retention, and brand performance  
**Available attention:** 15–30 minutes for a report  
**Technical comfort:** Comfortable with conversion metrics, attribution, and campaign KPIs; variable on statistics  
**What they want:** Which channels/segments perform, ROI by tactic, customer behaviour insights  
**What they don't want:** SQL-level detail; extensive caveats about data quality  

**Writing style for this persona:**
- Compare against benchmarks (last period, industry)
- Include chart with trend over time
- Frame in terms of campaign impact, not model performance
- Acknowledge attribution limitations briefly, then move on

**Vocabulary bridge:** "Lift" is fine; "ROAS" fine; "regression coefficient" → "the relationship between spend and revenue"
