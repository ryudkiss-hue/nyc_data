# Visualization Specification

**Chart title:** [State the finding, not the variables]
**Created:** YYYY-MM-DD
**Analyst:** [Name]
**Deliverable:** [ ] Slide  [ ] Report  [ ] Dashboard  [ ] Email

---

## Message

> [One sentence: what should the reader understand in 5 seconds?]
>
> Example: "Brooklyn accounts for 38% of open violations despite having only 24% of SIM units."

## Data

| Field | Value |
|-------|-------|
| Source dataset | [e.g., violations — 6kbp-uz6m] |
| Fourfour | |
| Date range | YYYY-MM-DD → YYYY-MM-DD |
| Row count | |
| Aggregation | [e.g., GROUP BY borough, SUM(count)] |
| Filters applied | [e.g., status = 'OPEN', borough IS NOT NULL] |

## Chart specification

| Field | Value |
|-------|-------|
| Chart type | bar / line / scatter / histogram / stacked_bar / choropleth |
| X-axis | column name + unit |
| Y-axis | column name + unit |
| Color by | column name (or "single color") |
| Sort order | descending by Y / chronological / geographic |

## Visual design

| Element | Choice |
|---------|--------|
| Primary color | #003087 (NYC Blue) |
| Highlight color | #FF6319 (NYC Orange) — used for: ___ |
| Alert color | #C60C30 (NYC Red) — used for: ___ |
| Reference line | [e.g., SLA threshold at 14 days] |
| Annotations | [key data points to label directly] |

## Axes

| Axis | Label | Unit | Scale | Start at zero? |
|------|-------|------|-------|---------------|
| X | | | linear / log / time | Y / N / N/A |
| Y | | | linear / log | Y / N |

## Export

| Field | Value |
|-------|-------|
| Output format | PNG / SVG / PDF |
| DPI | 150 / 300 |
| Final dimensions | width × height px |
| Filename | |

## Validation checklist

- [ ] Title states the finding (not the variables)
- [ ] All axes labeled with units
- [ ] Data source and date in footer
- [ ] Passes greyscale test
- [ ] Key data point annotated directly on chart
- [ ] 5-second legibility test passed
