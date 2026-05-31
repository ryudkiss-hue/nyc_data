# Chart Selection Guide

## Decision tree

1. **What relationship are you showing?**
   - Change over time → Line or area chart
   - Comparing categories → Bar chart
   - Part of a whole → Pie, donut, or stacked bar
   - Distribution of values → Histogram or box plot
   - Relationship between two variables → Scatter plot
   - Sequential process with drop-off → Funnel

2. **How many categories?**
   - ≤ 7: Vertical bar
   - 8–15: Horizontal bar
   - > 15: Needs filtering or aggregation first

3. **Is the time dimension continuous or discrete?**
   - Continuous (daily/weekly/monthly): Line
   - Discrete (Q1/Q2/Q3/Q4, year over year): Bar

---

## Chart-by-chart guidance

### Line chart
**Use for:** Continuous time series, multi-metric trends
**Not for:** Unordered categories (implies continuity that doesn't exist)
**Best practices:**
- Direct label series at the end of the line (no legend required)
- Maximum 4 lines before the chart becomes unreadable
- Y-axis should start at 0 for absolute values; can be non-zero for showing rate of change

### Bar chart (vertical)
**Use for:** Comparing discrete categories
**Not for:** Time series with many periods (use line)
**Best practices:**
- Sort by value unless the x-axis has a natural order (e.g., age groups)
- One colour for one series; use accent colour to highlight the key bar
- Gap between bars should be ~50% of bar width

### Bar chart (horizontal)
**Use for:** Long category labels, many categories
**Best practices:**
- Sort descending (longest bar at top)
- Label values at the end of bars

### Scatter plot
**Use for:** Showing correlation, outliers, distributions across two dimensions
**Best practices:**
- Add a trend line if showing correlation
- Label only notable outliers, not all points
- Ensure axes start at meaningful values (not always 0)

### Histogram
**Use for:** Distribution of a continuous variable
**Best practices:**
- Choose bin width based on data range; too few bins hides the shape
- Add a reference line for mean or median
- Use to check normality before applying statistical tests

### Box plot
**Use for:** Comparing distributions across groups
**Best practices:**
- Explain the components (box = IQR, whiskers = 1.5×IQR, dots = outliers) when the audience is non-technical
- Overlay a strip plot (individual points) for small samples (n < 50)

### Funnel chart
**Use for:** Sequential processes with volume drop-off
**Best practices:**
- Label both the absolute count and the conversion rate for each step
- Order steps from top to bottom in process sequence
- Highlight the step with the largest absolute drop-off

---

## What to avoid

| Chart type | Problem |
|---|---|
| 3D bar / pie | Depth distorts relative sizes |
| Dual y-axis | Creates false correlation impression |
| Bubble chart (without explanation) | Third dimension (size) is hard to read accurately |
| Radar / spider chart | Comparisons between axes are meaningless |
| Area chart with multiple overlapping series | Series overlap creates confusion |
