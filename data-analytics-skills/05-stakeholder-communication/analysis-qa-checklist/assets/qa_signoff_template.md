# Analysis QA Sign-Off

Complete this form before delivering any analysis to stakeholders.
File alongside the analysis output in the project folder.

---

## Identification

| Field | Value |
|---|---|
| Analysis title | |
| Output file(s) | |
| Original question / brief | |
| Analyst | |
| Reviewer | |
| Intended audience | |
| Delivery date | |
| Data pull date | |

---

## Dataset References

| Dataset key | Fourfour | Row count used | Last modified | Within SLA? |
|---|---|---|---|---|
| | | | | Yes / No |
| | | | | Yes / No |

---

## Checklist Results

| Section | Result | Notes |
|---|---|---|
| 1. Question framing | Pass / Fail / N/A | |
| 2. Data sourcing & freshness | Pass / Fail / N/A | |
| 3. Transformations & logic | Pass / Fail / N/A | |
| 4. Statistical validity | Pass / Fail / N/A | |
| 5. Finding statements | Pass / Fail / N/A | |
| 6. Presentation quality | Pass / Fail / N/A | |
| 7. Assumptions & caveats | Pass / Fail / N/A | |
| 8. Recommendations | Pass / Fail / N/A | |

---

## Automated QA Runner Output

Paste the output of `scripts/qa_runner.py` below:

```
(paste qa_runner.py output here)
```

Flags raised: ___ | Flags resolved: ___ | Flags accepted with explanation: ___

---

## Issues Found & Resolutions

| # | Issue | Severity | Resolution | Resolved by |
|---|---|---|---|---|
| 1 | | High / Med / Low | | |
| 2 | | High / Med / Low | | |

---

## Accepted Risks

List any flags that were reviewed and accepted (not fixed), with justification:

1.
2.

---

## Delivery Decision

- [ ] **APPROVED FOR DELIVERY** — all sections pass; any accepted risks are documented above
- [ ] **HOLD — revisions required** — see issues table above; re-review after fixes
- [ ] **ESCALATE** — issue cannot be resolved at analyst level; flagging to [manager / data owner]

**Reviewer signature / initials:** ______________________

**Date of sign-off:** ______________________

---

## Notes for Next Analyst

Document anything that would help someone picking up this analysis later:

- Data quirks discovered:
- Filters applied that aren't obvious from the output:
- Follow-up questions raised but not addressed in this analysis:
