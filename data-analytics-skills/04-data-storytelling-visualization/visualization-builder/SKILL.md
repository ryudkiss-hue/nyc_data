---
name: visualization-builder
description: Create effective, publication-ready data visualizations. Use when choosing chart types, designing presentation visuals, building dashboard charts, or applying visual design best practices to data output.
---

# Visualization Builder

# When to use
- Choosing the right chart type for a specific analytical message
- A chart exists but is cluttered, misleading, or failing to make the point
- Building a chart for an executive presentation that must work without verbal explanation
- Producing consistent, branded visualisations across a report or dashboard
- Creating accessible charts that work for colorblind viewers or screen readers

# Process
1. **Identify the message type** — classify the chart's purpose: comparison (bar), trend over time (line), composition / part-of-whole (stacked bar, pie only for 2–3 categories), distribution (histogram, box plot), or relationship (scatter). The message type determines the chart type. See `references/chart_selection_guide.md`.
2. **Select and load the data** — confirm the data is at the right grain for the chart. Aggregations (e.g., groupby month) should happen before plotting, not inside the chart library.
3. **Build the base chart** — use `scripts/chart_builder.py` with pre-set professional styling (whitegrid, sans-serif, accessible color palette). Set axes, ticks, and scale deliberately — default settings are often wrong.
4. **Apply visual hierarchy** — make the most important data element visually dominant (bolder line, darker bar, distinct color). De-emphasise secondary series. Remove every element that doesn't contribute to the message (gridlines at 0.2 alpha, no top/right spines). See `references/visual_design_principles.md`.
5. **Annotate for the reader** — add a descriptive title that states the finding ("Mobile churn is 2× desktop"), not the variable names ("Churn by device type"). Annotate key data points, thresholds, and reference lines directly on the chart. Add a data source and date.
6. **Export and validate** — export at 300 DPI for print or 150 DPI for web. View the chart at the intended display size. Check: is the key message legible in under 5 seconds? Does it work in greyscale? Complete `assets/viz_spec_template.md` if the chart is part of a larger deliverable.

# Inputs the skill needs
- The data to be visualised (at the correct aggregation grain)
- The single key message the chart must communicate
- The audience (technical or executive) and the display context (presentation slide, report, dashboard, email)
- Brand colors or style guidelines if applicable
- Any accessibility requirements (colorblind palette, alt text)

# Output
- `scripts/chart_builder.py` — creates professional matplotlib/seaborn charts with pre-set styling, annotation helpers, and export settings
- `references/chart_selection_guide.md` — which chart type for which message; common chart mistakes and how to fix them
- `references/visual_design_principles.md` — color, typography, hierarchy, annotation, and accessibility principles
- `assets/viz_spec_template.md` — spec template for a chart: message, data source, chart type, annotations, export requirements
