# Metaphor Bank

Concrete analogies for abstract technical concepts. Use when a translation table entry isn't enough and the audience needs an intuitive mental model.

---

## Statistical Testing

**P-value / statistical significance**
> "Imagine flipping a coin 20 times and getting 15 heads. You'd suspect the coin is rigged — and you'd be right to. Statistical significance is our way of measuring how 'suspicious' our result is. A p-value of 0.03 means: if nothing had really changed, we'd only see a result this extreme 3% of the time."

**Confidence interval**
> "Think of it like a weather forecast. We don't say 'it will be exactly 22°C tomorrow.' We say 'between 19° and 24°.' A confidence interval is the same idea — we know the true value is in a range, not a single point."

**Type I vs Type II error**
> "Type I is a false alarm — the smoke detector goes off but there's no fire. Type II is a missed threat — there's a fire but the detector didn't go off. We tune the detector (and the analysis) depending on which error costs more."

---

## Machine Learning

**Model training**
> "Teaching the model is like training a new employee by showing them thousands of past examples — 'here's a customer who churned, here's one who didn't.' After enough examples, they develop an intuition for the pattern."

**Overfitting**
> "Imagine a student who memorised the practice exam answers instead of understanding the subject. They'd ace the practice test but struggle on the real one. Overfitting is the same — the model memorised the training data instead of learning the underlying pattern."

**Feature importance**
> "Like asking a doctor 'what's the most important thing you look at to decide if a patient is at risk?' — feature importance tells us which data points the model relies on most."

**Model accuracy vs. precision/recall tradeoff**
> "A spam filter set to 'aggressive' catches more spam (high recall) but also blocks legitimate emails (low precision). Setting it to 'conservative' lets spam through (low recall) but rarely blocks real mail (high precision). It's a dial, not a switch — and the right setting depends on what you care about more."

---

## Data Quality

**Data freshness / latency**
> "Think of it like a newspaper. A morning paper has yesterday's news. If you need real-time prices, you need a live feed. Each data source has a 'publication delay' — the question is whether that delay matters for your decision."

**Data lineage**
> "Every number in this report has a paper trail — like tracing a recipe back to the farm where the ingredients came from. If a number looks wrong, we can follow the trail upstream to find where the error was introduced."

**Null / missing data**
> "It's the difference between answering 'zero' and leaving a blank on a form. A zero is a real answer; a blank means we don't know. Both look the same in a total unless we're careful."

---

## A/B Testing

**Randomised experiment**
> "It's the same idea as a clinical trial. Half the patients get the new drug, half get a placebo. Neither group knows which they got. After enough time, we compare outcomes. The randomisation is what lets us say the drug caused the improvement — not some other difference between the groups."

**Minimum sample size**
> "To reliably detect a 1mm change in height, you'd need a very precise ruler. To detect a tiny conversion rate lift, you need a lot of users. Small improvements require large samples to be measurable."

---

## Forecasting

**Forecast uncertainty**
> "A weather forecast for tomorrow is much more reliable than one for next month. The further out we forecast, the wider the cone of uncertainty. We show a range instead of a single number to be honest about this."

**Seasonality**
> "Like a retailer who knows Q4 is always their busiest quarter — not because something changed, but because it always has been. We strip out these predictable cycles to see what's actually new."
