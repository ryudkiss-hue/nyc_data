# Funnel Design Guide

## Defining funnel steps

A well-defined funnel has steps that are:

1. **Sequential** — a user cannot reach step N without passing through step N-1
2. **Mutually exclusive** — each user is counted once per step at a given point in time
3. **Exhaustive within scope** — no meaningful step is omitted that could explain drop-off
4. **Anchored to a denominator** — the first step defines the universe; all conversion rates are relative to it

**Anti-patterns:**
- Steps that can be completed out of order (breaks the funnel assumption)
- Steps defined by page views rather than intentional actions (inflated early steps)
- Mixing session-level and user-level counts across steps

---

## Conversion rate types

**Step-over-step conversion rate**
`users at step N / users at step N-1`
Answers: "Of the users who reached this step, how many continued?"

**Overall conversion rate**
`users at step N / users at step 1`
Answers: "Of everyone who entered the funnel, how many reached this step?"

Use step-over-step to find where the biggest drop happens.
Use overall to communicate the funnel health to stakeholders.

---

## Time window considerations

**Open-ended funnel:** A user can complete later steps at any time. Appropriate for purchase funnels where users shop over days.

**Time-bounded funnel:** A user must complete all steps within a fixed window (e.g., 7 days). Appropriate for onboarding where late completion is not a real conversion.

**Cohort-based funnel:** Group users by start date and track their progression over a fixed observation window. Required for fair period-over-period comparison.

---

## Drop-off prioritisation

**Impact score:** `absolute drop-off × value per user at that step`

A 40% drop-off at step 2 is more impactful than a 40% drop-off at step 5 if step 2 has 10× more users flowing through it.

**Recovery value:** `users lost at step × conversion rate of remaining steps × revenue per conversion`

This gives the maximum revenue recoverable if you eliminated the drop-off entirely — use as an upper bound for effort.

---

## Segment-specific funnels

Always break the funnel by the most relevant segments before drawing conclusions:

- **Acquisition channel** — users from paid ads may have lower intent than organic
- **Device type** — mobile funnels often drop sharply at form-fill steps
- **New vs returning users** — returning users bring prior familiarity; comparing them inflates cohort averages
- **Plan / price point** — high-intent (paid plan) users convert differently from freemium

---

## Funnel quality checklist

- [ ] First step denominator is clearly defined and appropriate
- [ ] Time window is specified and consistent for all steps
- [ ] Users are de-duplicated per step (each user counted once)
- [ ] Drop-off at each step has at least one hypothesis
- [ ] Biggest drop-off step is identified and owns a next action
- [ ] Funnel is broken by at least one key segment
