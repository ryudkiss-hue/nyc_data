# Technical-to-Business Translation Glossary — NYC DOT

## Statistical terms

| Technical term | Business language | NYC DOT example |
|---------------|------------------|-----------------|
| **p-value** | "Confidence that the result isn't random chance" | "We're 95% confident the Brooklyn increase isn't just noise in the data." |
| **Statistical significance** | "The result is reliably real, not a fluke" | "The 12-point drop in closure rate is statistically reliable — it's not just random variation." |
| **Confidence interval** | "The realistic range for the true answer" | "The completion rate is 66%, but the true rate is likely between 59% and 73%." |
| **Standard deviation** | "How much values typically vary from average" | "On average, violations take 14 days to close, but individual cases range from 2 to 45 days." |
| **Correlation (r)** | "How closely two things move together" | "Boroughs with more inspectors close violations faster — the relationship is strong." |
| **R² (R-squared)** | "How much of the outcome is explained by this factor" | "Inspector count explains 78% of the variation in closure speed across boroughs." |
| **IQR** | "The middle 50% range" | "Most closures happen in 5 to 21 days — that's the typical range." |
| **Outlier** | "An unusually extreme case" | "312 violations took more than 45 days to close — well outside the normal range." |
| **Distribution** | "The pattern of how values are spread out" | "Most violations are closed quickly, but a long tail of cases drags the average up." |
| **Mean vs. median** | "Average vs. typical" | "The average closure time is 18 days, but the typical case closes in 12 — a few slow cases pull the average up." |

## Data quality terms

| Technical term | Business language | NYC DOT example |
|---------------|------------------|-----------------|
| **Null / missing value** | "Missing data" | "14% of records are missing the defect type — we can't use those for defect-level analysis." |
| **Schema drift** | "The data format changed unexpectedly" | "The Socrata API changed how borough codes are formatted, which broke our pipeline last week." |
| **Data latency / lag** | "The data is delayed" | "Closures are recorded in the system 24–72 hours after they happen, so today's data isn't fully current." |
| **Duplicate records** | "The same thing counted twice" | "We found 87 violations logged twice — we removed duplicates before counting." |
| **Data lineage** | "Where the data came from and how it was processed" | "This figure came from Socrata, was filtered for open violations only, and was last refreshed on June 12." |
| **SLA** | "Deadline for updating data" | "This dataset is supposed to refresh daily — it hasn't been updated in 3 days, which may affect the numbers." |

## Analysis / modelling terms

| Technical term | Business language | NYC DOT example |
|---------------|------------------|-----------------|
| **K-means clustering** | "Grouping similar cases together automatically" | "We used the data to group sidewalk units into 4 risk tiers, based on inspection history and defect rates." |
| **Linear regression** | "Fitting a trend line to see where things are headed" | "Based on the trend, open violations are growing by about 42 per month." |
| **ADF test (stationarity)** | "Testing whether a trend is real or just random" | "The test confirms the upward trend in violations is statistically real, not just noise." |
| **ARIMA forecast** | "A prediction model that accounts for past patterns and seasonality" | "Our model predicts 5,900 open violations by August, assuming current closure rates hold." |
| **Silhouette score** | "How well-separated the groups are (0–1 scale)" | "The 4-group segmentation scored 0.52 — the groups are reasonably distinct." |

## Formatting rules for translated output

1. **Lead with the business implication**, not the method: "Violation rates are rising" before "linear regression shows β=+42."
2. **State uncertainty in plain terms**: "The true rate is likely between 59% and 73%" — not "95% CI [0.59, 0.73]."
3. **Avoid acronyms without expansion** in the first use: "IQR (the middle 50% range)."
4. **Numbers to one decimal place** in executive output — false precision undermines trust.
5. **Prefer comparisons to anchors** stakeholders already know: "2× the Manhattan rate" rather than "0.24 vs. 0.12."
