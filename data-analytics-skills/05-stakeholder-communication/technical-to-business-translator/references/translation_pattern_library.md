# Translation Pattern Library

Ready-to-use translations for common technical concepts. Apply these when rewriting analysis for business audiences.

---

## Statistical Concepts

| Technical | Business translation | Notes |
|---|---|---|
| "p-value of 0.03" | "We're 97% confident this result isn't random chance" | Invert the p-value for intuitive framing |
| "statistically significant at α=0.05" | "The difference is large enough that we're confident it's real" | Drop the alpha entirely for executive audiences |
| "95% confidence interval: [12, 18]" | "We estimate the true value is between 12 and 18" | Keep the range; drop "confidence interval" |
| "not statistically significant" | "The data doesn't give us enough evidence to draw a conclusion" | Avoid "failed to reject the null" entirely |
| "effect size of 0.4 (medium)" | "A meaningful difference — visible in practice, not just in data" | Cohen's d in business terms |
| "standard deviation of 15" | "Results typically vary by about 15 [units] from the average" | Replace with units |
| "correlation of 0.72" | "These two things tend to move together strongly" | Add direction: "when X goes up, Y tends to go up too" |
| "multiple regression" | "A formula that accounts for multiple factors simultaneously" | Use "formula" not "model" for executive audiences |
| "overfitting" | "The model learned the historical data too well and won't work reliably on new data" | |
| "cross-validation score of 0.83" | "When we tested the model on data it hadn't seen, it was correct 83% of the time" | |

---

## Machine Learning

| Technical | Business translation |
|---|---|
| "model accuracy of 85%" | "The model gets the right answer 85% of the time" |
| "precision: 0.90, recall: 0.75" | "When it flags something, it's right 90% of the time; it catches 75% of the cases we care about" |
| "AUC of 0.84" | "The model is meaningfully better than random (a perfect model scores 1.0; random guessing scores 0.5)" |
| "feature importance: account_age ranks first" | "How long a customer has been with us is the strongest signal the model uses" |
| "the model needs retraining" | "The patterns in the data have shifted enough that the model's predictions are less reliable now" |
| "training / test split" | "We built the model on older data and tested it on recent data it hadn't seen before" |

---

## Data Engineering

| Technical | Business translation |
|---|---|
| "the ETL pipeline failed" | "The automated process that moves data from [source] to [destination] stopped working" |
| "data latency of 3 hours" | "The data in this report is up to 3 hours behind real time" |
| "schema change broke the report" | "A change to the underlying data structure caused the report to stop updating correctly" |
| "null values in the column" | "Missing data — those records don't have a value for [field]" |
| "cardinality is too high" | "There are too many unique values to group or filter on this field effectively" |
| "query timeout" | "The data request was too large or complex to complete in the allowed time" |

---

## A/B Testing

| Technical | Business translation |
|---|---|
| "treatment group" | "Users who received the change" |
| "control group" | "Users who saw the current version" |
| "holdout group" | "Users kept on the old version so we could measure the impact of the change" |
| "minimum detectable effect" | "The smallest improvement we would be able to detect given our sample size" |
| "underpowered test" | "We don't have enough data to draw a reliable conclusion yet" |
| "novelty effect" | "The initial boost may fade as users get used to the change" |
| "CUPED / variance reduction" | "A technique that makes our experiment results more precise without changing what we're testing" |

---

## Rewriting Patterns

**Replace passive voice with active:**
- Before: "Revenue was found to be negatively correlated with churn."
- After: "Customers with higher revenue churn less."

**Replace hedged jargon with direct claims:**
- Before: "The analysis suggests a potential uplift opportunity may exist in this segment."
- After: "We estimate $X in additional revenue is achievable in this segment."

**Replace technical process with outcome:**
- Before: "After applying SMOTE to address class imbalance and tuning hyperparameters via grid search..."
- After: "We built a model that reliably identifies at-risk customers even though they're a small fraction of our base."
