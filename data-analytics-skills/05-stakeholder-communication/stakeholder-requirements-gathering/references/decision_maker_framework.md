# Decision-Maker Framework

Use this to calibrate the rigour, format, and speed of an analysis based on the type of decision it will inform.

---

## Decision Types

### Strategic Decision
**Definition:** Sets long-term direction, allocates significant resources, or is difficult to reverse.  
**Examples:** Entering a new market, choosing a pricing model, major product roadmap pivot  
**Required rigour:** High — statistical validity, sensitivity analysis, documented assumptions  
**Required speed:** Low urgency — take the time to do it right  
**Typical audience tier:** Executive (C-suite, Board)  
**Format:** Formal report or presentation with full methodology section  

### Operational Decision
**Definition:** Optimises how existing processes run; moderate reversibility.  
**Examples:** Setting SLA thresholds, adjusting a marketing budget allocation, changing a workflow  
**Required rigour:** Medium — directionally correct is sufficient; perfect is the enemy of good  
**Required speed:** Medium urgency — days, not weeks  
**Typical audience tier:** Business analyst / domain lead  
**Format:** One-page summary + supporting data  

### Tactical Decision
**Definition:** Day-to-day execution; highly reversible.  
**Examples:** Which customer to prioritise in the CS queue, whether to send a specific campaign today  
**Required rigour:** Low — fast is more valuable than thorough  
**Required speed:** High urgency — hours, not days  
**Typical audience tier:** Operational team  
**Format:** Dashboard metric or single answer  

---

## Calibration Matrix

| Decision type | Acceptable uncertainty | Audience | Format | Turnaround |
|---|---|---|---|---|
| Strategic | Low (< 10%) | Executive | Report / slide deck | 1–2 weeks |
| Operational | Medium (20–30%) | Business lead | One-pager + data | 1–3 days |
| Tactical | High (±50% OK) | Operator | Number / flag | Hours |

---

## Stakeholder Role Map

Understanding which role plays which part in a decision:

| Role | What they need from you |
|---|---|
| **Decider** | Bottom-line recommendation, confidence level, key risk |
| **Approver** | Enough detail to validate; needs to understand method |
| **Influencer** | Findings relevant to their domain; may shape the decision |
| **Implementer** | Specific, actionable outputs; granular data they can act on |
| **Reviewer** | Technical validity; reproducibility; comparison to prior work |

Ask at the start: "Who is the decider? Who needs to approve? Who will implement?"

---

## Questions to Ask for Each Decision Type

**For strategic decisions:**
- What is the irreversible part of this decision?
- What would cause you to reverse course 6 months from now?
- What's the cost of being wrong?
- Who else needs to sign off?

**For operational decisions:**
- How often will this decision be revisited?
- What's good enough for you to act?
- Who owns the implementation?

**For tactical decisions:**
- What is the single number or flag you need?
- How will this be consumed (dashboard, alert, report)?
- What's the tolerance for being directionally right vs. precisely right?

---

## Mismatched Rigour Costs

| Mismatch | Consequence |
|---|---|
| Over-rigorous for tactical decision | Wasted time; answer arrives too late to matter |
| Under-rigorous for strategic decision | Decision based on insufficient evidence; costly reversal |
| Wrong audience for the format | Executive confused by detail; analyst can't validate from summary |
