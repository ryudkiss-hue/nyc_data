# Audience Depth Guide

How to calibrate methodology explanations for different reader types. Match the depth to who will read it, not to how proud you are of the method.

---

## Tier 1: Executive / Decision-Maker

**Who:** C-suite, VP, Board, senior business leaders  
**What they care about:** Can I trust this? What's the conclusion? What should I do?  
**What they don't want:** Methodological detail, statistical terms, caveats that don't change the decision  

**Write this much:** 1 paragraph maximum  
**Include:** Data source, time period, method in one plain sentence, single most important limitation  
**Omit:** Formula, model parameters, sample sizes (unless very small), confidence intervals (unless the decision depends on them)  

**Test:** Could a smart 10-year-old follow the logic? If yes, it's right for this audience.

---

## Tier 2: Business Analyst / Domain Expert

**Who:** Product managers, finance analysts, operations leads, marketing strategists  
**What they care about:** Is the method appropriate? Did we account for [known issue]? Can I replicate or extend this?  
**What they don't want:** Dense statistical notation, code, heavy academic framing  

**Write this much:** 3–5 paragraphs or 1 structured writeup section  
**Include:** Data sources and joins, time period and filters, method logic in plain English, assumptions, key limitations  
**Omit:** Code, mathematical notation, model internals beyond "how it works at a high level"  

**Test:** Could a product manager on the team follow the logic and explain it to their skip-level?

---

## Tier 3: Technical Peer / Data Scientist

**Who:** Other analysts, data scientists, data engineers reviewing the work  
**What they care about:** Correctness, reproducibility, statistical validity, code quality  
**What they don't want:** Oversimplification that hides important choices  

**Write this much:** Full technical appendix or inline code documentation  
**Include:** Exact SQL or code, model hyperparameters, feature engineering choices, train/test split details, validation approach, assumptions with quantified sensitivity  
**Omit:** Nothing — this is the audience that needs the full picture  

---

## Common Calibration Mistakes

| Mistake | Consequence | Fix |
|---|---|---|
| Using Tier 3 language for Tier 1 audience | Executive stops reading; decision delayed | Rewrite the summary section using the translation table |
| Using Tier 1 depth for Tier 2 audience | Business analyst can't validate; asks repeated questions | Add a data + method section |
| Writing only for Tier 1 and having Tier 3 in the same doc | Technical reviewers can't verify; executives get overwhelmed by appendix | Use layered structure: summary → detail → appendix |
| No limitations section for any tier | Stakeholder over-trusts the output | Every methodology explanation needs at least one limitation |

---

## Quick Calibration Checklist

Before finalising a methodology explanation:

- [ ] I know who will read this (name the primary audience tier)
- [ ] The depth matches that tier
- [ ] Statistical terms are translated for Tier 1 and Tier 2 audiences
- [ ] At least one limitation is explicitly stated
- [ ] The "how we got here" is short enough that it doesn't compete with "what we found"
