# Risks and Dependencies in Analysis Planning

How to identify, document, and mitigate things that could delay or invalidate an analysis before they cause problems.

---

## Dependency Types

### Data Dependencies

| Dependency | Example | How to resolve |
|---|---|---|
| Data access not yet granted | Need access to a vendor's export | Raise access request immediately; don't start the analysis until confirmed |
| Data doesn't exist | Metric was never tracked | Scope out or use a proxy; document the limitation |
| Data is unreliable / known quality issues | A known ETL bug affects the column | Document the issue; decide whether to proceed with caveated results or wait for the fix |
| Data is too fresh (not enough history) | New feature only 2 weeks old | Narrow the question or set a longer timeline |

### People Dependencies

| Dependency | Example | How to resolve |
|---|---|---|
| SME input required | Need product manager to confirm event definition | Schedule immediately; flag as a blocker if unresolved |
| Stakeholder needs to confirm scope | Requirements not yet signed off | Do not start until sign-off; treat as day 0 |
| Another analyst is needed | Two people needed for parallel work | Confirm availability before committing the timeline |

### Tool / System Dependencies

| Dependency | Example | How to resolve |
|---|---|---|
| Warehouse quota / cost approval | Large query needs DBA sign-off | Get approval before running |
| Dashboard tool access | Need a BI tool licence | Request early; use an alternative format as fallback |
| Third-party data delivery | Vendor sends a file on the 5th of the month | Build the timeline around the delivery date |

---

## Risk Register

For each identified risk, record:

| Field | What to capture |
|---|---|
| **Risk** | Brief description of what could go wrong |
| **Probability** | High / Medium / Low |
| **Impact on timeline** | Hours / days it would add |
| **Mitigation** | Action taken before the risk materialises |
| **Contingency** | What to do if the risk materialises anyway |

---

## Common Analysis Risks

| Risk | Probability | Typical impact | Mitigation |
|---|---|---|---|
| Data quality issue discovered mid-analysis | Medium | +0.5–1 day | Run EDA on data before committing to approach |
| Scope expands after requirements sign-off | High | +0.5–2 days | Document scope boundaries explicitly; get written sign-off |
| Stakeholder unavailable for feedback | Medium | +1–3 days | Book feedback slot in advance; set a response deadline |
| Key assumption turns out to be wrong | Medium | Restart sub-questions | Make assumptions explicit early; validate before building on them |
| Approach doesn't work on the actual data | Low–Medium | +0.5–1 day | Run a proof-of-concept before full implementation |
| External data delivery delayed | Low–Medium | +1–5 days | Identify alternative or contingency approach |

---

## Escalation Trigger

Escalate to the requestor when:
- A dependency will cause the delivery date to slip by more than 20%
- A key assumption is found to be incorrect and changes the conclusion
- The data needed for a must-have requirement doesn't exist
- A risk materialises and changes the feasibility of the plan

**Escalate early.** A stakeholder told on day 1 that the delivery will be late has options. A stakeholder told on the eve of the delivery has none.
