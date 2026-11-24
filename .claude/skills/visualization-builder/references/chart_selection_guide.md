# Chart Selection Guide — NYC DOT

## Decision tree

```
What is the key message?
│
├── Compare values across categories
│   └── BAR CHART (horizontal if labels are long; vertical if ≤7 categories)
│       Example: violations by borough, completion rate by defect type
│
├── Show change over time
│   └── LINE CHART (one line per series; max 4–5 lines)
│       Example: daily inspections trend, rolling 7-day violation rate
│
├── Show part of a whole
│   ├── STACKED BAR (for 2–4 categories — readable)
│   └── PIE (only for 2 categories — "pass/fail", "open/closed")
│       Example: open vs. closed violations by borough
│
├── Show distribution of a single variable
│   ├── HISTOGRAM (continuous numeric: defect depth, days to closure)
│   └── BOX PLOT (compare distributions across groups: days-to-close by borough)
│
├── Show relationship between two numeric variables
│   └── SCATTER (correlation: inspection frequency vs. violation rate)
│
└── Show geographic patterns
    └── CHOROPLETH (borough-level metric map)
        Example: ramp completion rate shaded by borough
```

## Common chart mistakes (and fixes)

| Mistake | Fix |
|---------|-----|
| **Pie chart with 6 slices** | Use a horizontal bar chart — humans can't compare angles accurately |
| **Dual y-axis** | Split into two charts — dual axes mislead on scale relationship |
| **3D bars / exploded pie** | Never — 3D distorts magnitude perception |
| **Title = variable names** ("Violations by Borough") | Title = the finding ("Brooklyn has 2× the violations of SI") |
| **Rainbow color palette** | Use a single hue + saturation gradient, or NYC DOT blues |
| **No data source** | Always add "Source: NYC Open Data [fourfour] / as of YYYY-MM-DD" |
| **Truncated y-axis** | Start y-axis at 0 for bar charts; document if you must truncate |

## NYC DOT color palette

| Use | Hex | Name |
|-----|-----|------|
| Primary data | `#003087` | NYC DOT Blue |
| Accent / highlight | `#FF6319` | NYC Orange |
| Negative / alert | `#C60C30` | NYC Red |
| Neutral | `#888888` | Gray |
| Background | `#FFFFFF` | White |

Colorblind-safe alternative: use `#0072B2` (blue) and `#D55E00` (orange) from the Wong palette.

## Annotation checklist

- [ ] Title states the finding (not the variables)
- [ ] Axes labeled with units (count, %, days, USD)
- [ ] Data source and date in footer
- [ ] Key data points annotated directly on chart (not in legend only)
- [ ] Reference lines for SLA thresholds, targets, or averages
- [ ] Chart passes the 5-second test: key message legible without reading labels
