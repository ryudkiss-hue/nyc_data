# Dashboard Design Principles

## The single question test

Every dashboard should answer one primary question. If you cannot complete the sentence "This dashboard tells me ___," the scope is too broad. A dashboard that tries to answer five questions answers none of them well.

---

## Information hierarchy

**Level 1 — KPIs:** The 2–4 metrics that matter most. Always visible above the fold. No interaction required to see them.

**Level 2 — Context:** Trend lines, period comparisons, variance from target. Explains whether KPIs are good or bad.

**Level 3 — Diagnostic:** Breakdowns by segment, time, or dimension. Used to investigate anomalies.

Resist the urge to put level 3 content at level 1. Executives need level 1; analysts need all three.

---

## Layout principles

**F-pattern reading:** Eyes scan left to right, then down. Place the most important metric top-left. Put totals before breakdowns.

**Proximity:** Related charts should be adjacent. Group by topic, not by chart type.

**White space:** A crowded dashboard forces every chart to compete for attention. Remove or collapse anything that is not regularly used.

**Consistent scales:** Charts on the same page comparing the same metric should use the same axis scale. Inconsistent scales mislead.

---

## Chart selection summary

| Data type | Recommended chart |
|---|---|
| Trend over time | Line |
| Category comparison (≤7) | Bar (vertical) |
| Category comparison (8+, long labels) | Bar (horizontal) |
| Part of whole (≤4 segments) | Donut |
| Part of whole (5+ segments) | Stacked bar |
| Distribution | Histogram or box plot |
| Two-variable relationship | Scatter |
| Sequential drop-off | Funnel |

---

## Colour usage

- Use a single colour for a single series. Reserve multiple colours for multiple series.
- Use colour to encode meaning, not decoration. Red = bad, green = good, grey = context/background.
- Limit to 3–5 distinct colours. More colours require a legend; legends require eye movement.
- Ensure accessibility: avoid red-green combinations that are indistinguishable to colour-blind users. Use blue-orange as the primary contrast pair.

---

## Anti-patterns to avoid

| Anti-pattern | Problem |
|---|---|
| Dual y-axis charts | Creates the illusion of correlation between unrelated metrics |
| 3D charts | Distorts relative sizes; never adds information |
| Pie charts with > 5 slices | Slices < 5% are unreadable |
| Truncated y-axis | Exaggerates differences; misleads at a glance |
| Too many decimal places | Creates false precision; rounds to 2 significant figures |
| Unlabelled axes | Forces the viewer to infer what is being shown |
| Missing time zone / period label | Makes the data unverifiable |

---

## Mobile-first considerations

If the dashboard will be viewed on mobile:

- Limit to 3 charts per page
- Single-column layout
- KPI cards instead of charts where possible
- No hover interactions (use tap-to-expand)
- Minimum 16px font size
