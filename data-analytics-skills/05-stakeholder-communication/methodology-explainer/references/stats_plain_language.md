# Statistical Terms — Plain Language Translations

NYC DOT-specific reference for converting technical statistical language into plain English
for executive and operations audiences.

---

## Core Translations

| Technical term | Plain language version | NYC DOT example |
|---|---|---|
| p-value < 0.05 | "We're 95% confident this result is real, not random chance" | "The difference in closure rates between boroughs is real — 95% confident" |
| Confidence interval | "Margin of error" or "likely range" | "74% ramp completion, ±3 pp margin of error" |
| Statistically significant | "This difference is real, not noise" | "Brooklyn's improvement is real, not a data blip" |
| Statistical power | "How sensitive our test is to detecting a real difference" | Avoid — say "we had enough data to detect a meaningful change" |
| Sample size | "Number of records we analyzed" | "Based on 12,847 violation records" |
| Null hypothesis | Do not use | Describe what you tested instead: "We tested whether closure rates differ by borough" |
| Regression | "A model that predicts one thing from another" | "A formula that predicts how long a violation stays open based on type and borough" |
| Correlation | "These two things move together" | "More inspections per block tends to go with fewer open violations — though one doesn't necessarily cause the other" |
| Variance / standard deviation | "How spread out the values are" | "Completion rates range widely across inspection districts" |
| Outlier | "Unusually high or low value" | "Three inspection districts have unusually high violation rates" |
| Median | "The middle value" | "Half of violations are closed within 14 days; half take longer" |
| Distribution | "The pattern of how values are spread" | "Most violations are closed quickly, but a small number stay open for months" |
| Bayesian | "We used prior knowledge to sharpen our estimate" | "We combined past completion rates with new data to produce a more stable forecast" |
| CUSUM / control chart | "A running alarm system for when a trend changes" | "We track whether violation rates are trending in a new direction week over week" |
| KMeans clustering | "Grouping similar inspection sites together automatically" | "We grouped all 1,200 inspection districts into 4 types based on violation patterns" |
| Moran's I | "A measure of whether nearby places are more similar than distant ones" | "Violations cluster geographically — fixing one block often means the neighboring blocks also need attention" |
| Survival analysis | "Tracking how long before an event happens" | "We measured how long violations typically stay open before being resolved" |
| Wilson Score CI | "A more accurate margin of error for small samples" | (avoid; just say "margin of error, adjusted for small sample size") |
| AUC / ROC | "How accurate our prediction is overall" | Avoid; say "the model correctly identifies [X]% of [outcome]" |
| R-squared | "How much of the variation is explained by the model" | Avoid; say "the model explains most of the differences we see" |

---

## Confidence Statement Templates

Use these when reporting any rate, percentage, or comparison:

**For a single rate:**
> "[X]% of [population] [metric], based on [N] records. We estimate the true rate is between [low]% and [high]% (95% confidence)."

**For a comparison between groups:**
> "Borough A's rate ([X]%) is [higher/lower] than Borough B's ([Y]%). We're 95% confident this difference is real and not due to sample variation."

**For a trend:**
> "The violation closure rate has [risen/fallen] by [X] percentage points over the past [period]. This trend is consistent across [N] weeks of data."

**For a forecast:**
> "At the current rate, we project [X]% completion by [date]. This projection has a ±[Y] pp uncertainty range — the true value will likely fall between [low]% and [high]%."

---

## Phrases to Avoid in Non-Technical Deliverables

These phrases trigger confusion or distrust in non-technical audiences:

| Avoid | Reason |
|---|---|
| "The algorithm determined..." | Sounds like a black box; use "our analysis found..." |
| "Statistically speaking..." | Signals hedging; just state the finding |
| "The model predicts with 87% accuracy..." | What does 13% error mean operationally? State that instead |
| "After controlling for covariates..." | Jargon; say "after accounting for borough size differences..." |
| "The null hypothesis was rejected..." | Meaningless to non-statisticians; state what was found |
| "Data is heteroskedastic..." | Always translate; e.g. "the spread of violation rates varies a lot by district" |
| "We ran a logistic regression..." | Name the purpose: "we built a model to predict which violations are likely to miss their deadline" |

---

## Borough-Specific Framing Notes

When reporting borough comparisons, frame for equity sensitivity:

- Avoid: "Staten Island has the worst performance"
- Prefer: "Staten Island currently lags on ramp completions; this may reflect lower baseline infrastructure density rather than operational gaps"

- Avoid: "The Bronx data is an outlier"
- Prefer: "The Bronx shows a different pattern — worth understanding why before drawing conclusions"
