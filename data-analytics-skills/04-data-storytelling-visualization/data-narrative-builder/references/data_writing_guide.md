# Data Writing Guide
## Pyramid Principle, Number Formatting, and Humanising Data for NYC DOT

---

## The Pyramid Principle

Structure every section with the conclusion first, followed by supporting evidence. Never bury the key finding.

### Wrong (inverted pyramid — burying the finding)

> "We analysed inspection records from all five boroughs over the past 90 days. After reviewing completion rates,
> comparing them to prior quarters, and accounting for seasonal variation, we found that Brooklyn showed
> the largest deviation. Brooklyn's ramp completion rate is now 62%."

### Right (pyramid — conclusion first)

> "Brooklyn's ramp completion rate fell to 62% — the largest single-quarter decline in three years.
> This is 12 percentage points below target and 8 points below the next-lowest borough (Queens at 70%)."

### Apply pyramid principle at every level

- Document level: Key finding in the first sentence of the document
- Section level: Key point in the first sentence of each section
- Paragraph level: Topic sentence states the point; the rest provides evidence

---

## Number Formatting Rules

### Use the right precision

| Context | Format | Example |
|---------|--------|---------|
| Completion rates for executives | Round to nearest whole percentage | 67%, not 67.3% |
| Completion rates with confidence intervals | One decimal place | 67.3% (95% CI: 64.1–70.5%) |
| Large counts for executives | Abbreviate | 3.6M permits, not 3,612,847 |
| Row counts for technical audience | Full number | 398,241 inspection records |
| Dollar amounts | Round to nearest $1K or $1M for exec audiences | $2.4M, not $2,412,000 |
| Days / time periods | Spell out for clarity | 14 days, not 0.5 months |

### Always include the comparison

A number without context is meaningless. Include at least one of:
- Change from prior period: "up 23% from Q1"
- Gap from target: "8 percentage points below the 75% target"
- Peer comparison: "lowest of the five boroughs; citywide average is 71%"
- Absolute magnitude: "equivalent to 1,200 additional ramps remaining unfinished"

### Avoid false precision

- Wrong: "The completion rate increased by 12.7432 percentage points."
- Right: "The completion rate increased by approximately 13 percentage points."

---

## Humanising Data

Translate statistics into human impact whenever the audience includes non-technical stakeholders.

### Technique: The concrete equivalent

Take a large number and translate it into something the audience can visualise.

| Raw statistic | Humanised equivalent |
|--------------|---------------------|
| "3,200 ramps remain incomplete" | "3,200 ramps — enough to affect every sidewalk on a 14-block stretch of Fifth Avenue" |
| "Inspection backlog of 8,400 records" | "8,400 uninspected blocks — that's every block between 14th Street and 190th Street in Manhattan, twice over" |
| "SLA breached by 6 days" | "Inspection data went unrefreshed for 6 extra days — the equivalent of missing a full week of field reports" |

### Technique: The affected person

Name a specific role or constituency, not an abstract count.

- Instead of: "47 ramp commitments are incomplete in District 45"
- Try: "47 district residents with mobility challenges are still waiting for the ADA ramp that was promised in the 2024 capital budget"

### Technique: The trend as a trajectory

Show what happens if nothing changes.

- "At the current decline rate, Brooklyn will miss its year-end target by 15 percentage points — the first time the borough has missed its annual target in 5 years."
- "If inspection velocity holds at current levels, the citywide backlog will reach 12,000 records by October — up from 4,200 today."

---

## Pairing Text with Visuals

Each narrative beat should pair with exactly one chart. More than one chart per narrative section creates visual noise.

### Pairing guide for DOT narratives

| Narrative moment | Chart type | Example |
|-----------------|-----------|---------|
| "Here is the trend" | Line chart with annotation | Completion rate last 12 months, with target line |
| "Here is the borough comparison" | Horizontal bar chart, sorted | All 5 boroughs, bars coloured by status (green/amber/red) |
| "Here is the problem concentrated" | Choropleth map | Inspection completion heat map by block group |
| "Here is the distribution" | Box plot or histogram | Violation resolution time by borough |
| "Here is the composition" | Stacked bar (not pie — too many categories) | Violation type breakdown by borough |
| "Here is the correlation" | Scatter plot | Inspection density vs. completion rate by block |

### Chart title rule: state the finding

- Wrong: "Completion rate by borough, Q2 2026"
- Right: "Brooklyn ramp completion is 12 pp below target — lowest in three years"

### Annotation rule: say it on the chart

Every chart shown to a non-technical audience needs:
1. A title that states the finding
2. A data source and as-of date in the footer
3. Any relevant threshold annotated directly (SLA line, target line)
4. The key data point called out (the borough, the month, the anomaly)

---

## Executive Writing Style

### Sentence length

Maximum 25 words per sentence for executive audiences. If a sentence runs longer, split it.

### Avoid these words

| Avoid | Use instead |
|-------|------------|
| "Significant" | Specify: "23% increase" |
| "Notable" | Specify: "third consecutive quarterly decline" |
| "Various" | Name them: "Manhattan, Brooklyn, and Queens" |
| "Leverage" | Use, apply |
| "Utilise" | Use |
| "Synergies" | (eliminate entirely) |
| "Going forward" | "Starting [MONTH]" |

### Active voice

- Passive (weak): "Additional inspectors should be reallocated to Brooklyn."
- Active (strong): "The Brooklyn Borough Manager should reallocate 15 inspectors to ramp-only routes by July 15."

### One ask per close

Never end a document or briefing with three asks. If there are three decisions needed, rank them and ask for the most critical one. Executives act on one clear request; three requests produce no action.
