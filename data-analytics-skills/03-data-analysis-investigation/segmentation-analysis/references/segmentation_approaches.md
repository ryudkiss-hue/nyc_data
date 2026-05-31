# Segmentation Approaches

## Pre-defined vs data-driven segmentation

**Pre-defined segmentation:** Segments are defined by business rules before analysis.
- Examples: pricing plan, geography, acquisition channel, industry vertical
- Advantages: immediately actionable, stable over time, explainable to stakeholders
- Disadvantages: may not reflect natural groupings in the data

**Data-driven segmentation (clustering):** Segments are derived from patterns in the data.
- Examples: k-means on behavioural features, RFM (Recency, Frequency, Monetary) quartiles
- Advantages: uncovers non-obvious groups
- Disadvantages: requires interpretation; segments change as data changes

**For most business analyses, start with pre-defined segments.** Use data-driven approaches when the goal is to discover segments, not confirm existing ones.

---

## RFM segmentation

Recency, Frequency, and Monetary value — a standard customer segmentation for transactional businesses.

| Dimension | Definition |
|---|---|
| Recency | Days since last purchase |
| Frequency | Number of purchases in a period |
| Monetary | Total or average spend |

Score each dimension on a 1–5 scale (5 = best). Champions are 5-5-5; At Risk are 1-1-1.

Standard RFM segments:

| Segment | RFM pattern |
|---|---|
| Champions | High R, F, M |
| Loyal customers | High F, medium M |
| Potential loyalists | Recent, low F |
| At risk | Low R, formerly high F/M |
| Hibernating | Low R, low F |
| Lost | Very low R, low everything |

---

## Index scoring

Index = `segment metric / overall metric × 100`

Interpretation:
- 100 = in line with average
- 120+ = over-indexing (20% above average)
- 80 or below = under-indexing (20% below average)

Index scores normalise for segment size and allow comparison across metrics of different scales.

---

## Segmentation pitfalls

**Simpson's paradox:** A trend in the aggregate can reverse within every segment. Always break down before concluding.

**Over-segmentation:** Too many small segments produce noise, not signal. Segments with < 30 observations are generally not reliable.

**Confounding with size:** A segment that is 80% of total volume will always explain most of the movement. Look at rate changes, not just absolute contributions.

**Survivorship bias:** Analysing only active or paying customers ignores the population that churned or never converted.

---

## Segment profile template structure

For each segment, document:

1. **Label** — a business-meaningful name (not "cluster 3")
2. **Size** — N and % of total
3. **Key characteristics** — 3–5 metrics where this segment differs from the average
4. **Index scores** — for primary metrics
5. **Hypothesised need or behaviour** — why this segment behaves differently
6. **Recommended action** — what product, marketing, or CS intervention makes sense
