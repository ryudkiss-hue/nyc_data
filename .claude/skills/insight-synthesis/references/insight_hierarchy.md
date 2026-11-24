# Insight Hierarchy — NYC DOT Framework

## The four levels

### Level 1: Observation
*What the data shows.* No interpretation.

> "There were 4,821 open violations in Brooklyn in May 2026."

**Test:** Can you read this directly off a table? → It's an observation.

---

### Level 2: Pattern
*A relationship, trend, or comparison across time, geography, or category.*

> "Brooklyn has had the highest open violation count of any borough for 6 consecutive months."

**Test:** Does it require comparing two or more data points? → It's a pattern.

---

### Level 3: Insight
*The pattern interpreted in business/operational context — the "so what."*

> "Brooklyn's persistently high violation backlog suggests the current inspection-to-crew ratio is insufficient for the borough's sidewalk density — not a temporary spike but a structural capacity gap."

**Test:** Would a field manager nod and say "yes, that explains something we've been experiencing"? → It's an insight.

---

### Level 4: Recommendation
*A specific action derived from the insight.*

> "Reallocate 2 FTE inspection crews from Staten Island (lowest backlog) to Brooklyn for Q3 2026, targeting a 15% reduction in open violations within 60 days."

**Test:** Does it name who should do what by when, with a measurable outcome? → It's a recommendation.

---

## Common level-collapse errors

| Error | Example | Fix |
|-------|---------|-----|
| Presenting observations as insights | "The completion rate is 62%." | Add context: vs. what target? vs. last period? vs. other boroughs? |
| Recommendations without insight | "We should hire more inspectors." | State the evidence first: "The BK closure rate fell 12pp in May. Crew records show..." |
| Insight without data support | "Brooklyn is underperforming because of resource issues." | Link to specific numbers before drawing the causal conclusion |

---

## Confidence levels

Always attach a confidence rating to each insight before presenting it.

| Level | Meaning | Appropriate language |
|-------|---------|---------------------|
| **High** | Multiple corroborating data sources; root cause confirmed | "The data shows...", "Analysis confirms..." |
| **Medium** | Pattern is clear but cause is inferred | "This suggests...", "Evidence points to..." |
| **Low** | Hypothesis; directional signal, not confirmed | "One possible explanation...", "Further investigation needed to confirm..." |

---

## NYC DOT insight examples by level

| Dataset | Observation | Pattern | Insight |
|---------|-------------|---------|---------|
| violations | 4,821 open in BK | BK has been highest for 6 months | Structural capacity gap, not spike |
| ramp_progress | 62% completion rate in SI | SI trailing all boroughs since Q1 | Contractor performance issue vs. permit delays (TBD) |
| inspection | 18% null on `defect_type` | Null rate higher on Fridays | End-of-week data entry fatigue — field workflow issue |
