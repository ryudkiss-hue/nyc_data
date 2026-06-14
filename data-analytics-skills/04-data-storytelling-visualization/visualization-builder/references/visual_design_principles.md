# Visual Design Principles — NYC DOT

## Hierarchy

Make the most important element visually dominant:

1. **Data first** — chart marks (bars, lines) should be the boldest element.
2. **Labels second** — axis labels and data annotations at medium weight.
3. **Infrastructure last** — gridlines, tick marks, and spines should be subtle (alpha 0.2–0.3).

Remove chart elements that don't earn their place:
- Top and right spines → remove
- Gridlines → keep horizontal only, alpha 0.3
- Legend → only if chart has multiple series; prefer direct labels on lines

## Color

- **One hue per message.** Use a single color for comparison charts. Vary saturation, not hue.
- **Highlight one bar** by making it darker when comparing across groups (e.g., highlight Brooklyn in a borough comparison).
- **Diverging palette** for metrics that go positive and negative (e.g., MoM change): blue for positive, red for negative.
- **Never use red for the best performer** — red reads as warning regardless of context.

## Typography

- Title: 13–14pt, bold
- Axis labels: 10–11pt, regular
- Tick labels: 9pt
- Annotations: 9pt, placed adjacent to the data point
- Caption / source: 7–8pt, gray, bottom-right

## Annotation patterns

```
# Annotating a bar chart peak
ax.annotate(
    "18% above average",
    xy=(peak_x, peak_y),
    xytext=(peak_x, peak_y + 5),
    ha="center", fontsize=9,
    arrowprops=dict(arrowstyle="->", color="gray")
)

# Adding a threshold line
ax.axhline(y=sla_threshold, color="#C60C30", linestyle="--", linewidth=1, label="SLA Threshold")
```

## Export settings

| Output destination | DPI | Format |
|-------------------|-----|--------|
| Executive presentation (PowerPoint) | 150 | PNG |
| Printed report | 300 | PNG or PDF |
| Dashboard (web) | 96–120 | PNG or SVG |
| Email inline | 96 | PNG |

Always test: resize the exported image to its actual display size and confirm the title is legible.

## Accessibility

- All charts must pass greyscale test (print in B&W — still readable?).
- Use the Wong colorblind-safe palette for multi-series charts.
- Add `alt` text when embedding in HTML: describe what the chart shows, not just what it is.
- Minimum font size 9pt for any text on the chart.
