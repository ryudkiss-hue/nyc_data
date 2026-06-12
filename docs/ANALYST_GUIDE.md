# KPI Dives Analyst Guide

**For NYC DOT Data Analysts & Program Managers**

---

## Quick Start

Each KPI Dive shows **40+ statistical metrics** across **5 NYC boroughs**. This guide helps you understand what each metric means and when to act on it.

### The 10 Summary Cards (Top of Every Dive)

| Card | Metric | What It Means | When to Worry |
|------|--------|---------------|---------------|
| **1. Mean** (Blue) | Average value | Typical KPI level across borough | Significantly below benchmark |
| **2. Median** (Green) | Middle value | Central tendency, robust to outliers | Different from mean (suggests outliers) |
| **3. Std Dev** (Purple) | Spread around mean | How much variation exists | > 30% of mean = high volatility |
| **4. CV** (Orange) | Std Dev ÷ Mean × 100 | **Relative volatility** (unit-free) | CV > 30% = unstable, hard to forecast |
| **5. Skewness** (Red) | Tail asymmetry | Is data left or right-skewed? | \|Skewness\| > 0.5 = asymmetric (outliers on one side) |
| **6. Kurtosis** (Indigo) | Peak sharpness | Are there extreme values? | Kurtosis > 1 = sharp peak with tail risk |
| **7. Outliers** (Yellow) | Count > 3σ | Extreme anomalies | Any value here = investigate data quality |
| **8. Risk %** (Red) | % exceeding threshold | How many at-risk items? | > 20% = escalate |
| **9. IQR** (Teal) | Q3 − Q1 | Middle 50% spread | Used in box plot (whiskers = 1.5 × IQR) |
| **10. Z-Score** (Gray) | Standardized ranking | Borough rank vs. city average | Negative = below average; positive = above |

---

## The 16-Column Statistics Table

Each row is one borough (MN, BK, BX, QN, SI). Columns show:

| # | Column | Definition | How to Use |
|---|--------|-----------|-----------|
| 1 | **Borough** | NYC borough code | Filter/sort by this |
| 2 | **n** | Sample size | n < 30? Results less reliable |
| 3 | **Mean** | Average value | Compare to benchmark |
| 4 | **Median** | Middle value | If ≠ mean, outliers present |
| 5 | **Q1** | 25th percentile | Lower bound of typical values |
| 6 | **Q3** | 75th percentile | Upper bound of typical values |
| 7 | **Min** | Minimum value | Absolute worst case |
| 8 | **Max** | Maximum value | Absolute best case |
| 9 | **σ** | Std Dev | Typical deviation from mean |
| 10 | **CV%** | Coeff of Variation | Volatility in % terms |
| 11 | **Skew** | Skewness | >0 = right tail, <0 = left tail |
| 12 | **Kurt** | Kurtosis | Extreme value risk |
| 13 | **Outliers** | Count > 3σ | Data quality issues |
| 14 | **% vs Bench** | % diff from benchmark | Green if +10%, Red if -10% |
| 15 | **Risk Status** | Action indicator | 🟢 On Target, 🟡 At Risk, 🔴 Critical |
| 16 | **Trend** | Direction | ↑ Improving, ↓ Worsening, → Stable |

---

## Reading the Charts

### 1. Box Plot (with Whiskers)

```
        ← Max (outliers beyond whiskers)
        │
   ┌────┼────┐
   │    │    │  ← Q3 (75th percentile)
   │ ■■■┼■■■ │  ← Median (50th percentile, solid line)
   │    │    │  ← Q1 (25th percentile)
   └────┼────┘
        │
        ← Min (outliers beyond whiskers)
```

- **Box** = middle 50% (IQR)
- **Line in box** = median
- **Whiskers** = ±1.5 × IQR (typical range)
- **Points outside** = outliers (individual anomalies)

**When to Act:**
- Whiskers very wide → high variability
- Outliers visible → data quality concern
- Median off-center in box → skewed distribution

### 2. Trend Line (with 95% Confidence Band)

```
     Actual Trend ──────╱
                       ╱
     Upper CI ........╱
     Lower CI ✗✗✗✗✗✗✗
     
     ← Improving (slope negative)
     → Worsening (slope positive)
```

- **Line** = actual trend (linear slope)
- **Shaded band** = 95% confidence interval (uncertainty)
- **Wide band** = uncertain forecast; **Narrow band** = confident forecast

**When to Act:**
- Slope up + confidence band narrow → confirmed worsening
- Slope up + confidence band wide → unclear if real trend

### 3. Risk Histogram

Shows distribution of values relative to risk threshold.

```
█████            ← Values at/above threshold (red zone)
    ██████       ← Borderline (yellow zone)
        ████████ ← Safe (green zone)
```

**When to Act:**
- Heavy left side (many in red) → escalate
- Heavy right side (mostly green) → stable

### 4. Z-Score Ranking (Color-Coded Table)

Each borough's value standardized against city average.

```
Z-Score  │ Interpretation
━━━━━━━━━┼─────────────────
  > +2   │ 🟢 Well above average (top performer)
  +1 to  │ 🟡 Slightly above average
   +2    │
   -1 to │ 🟡 Slightly below average
   +1    │
  < -2   │ 🔴 Well below average (needs support)
```

**When to Act:**
- Borough consistently < -2 → resource allocation issue
- Borough consistently > +2 → best practice to replicate

---

## Risk Status Color Guide

Every Dive card is color-coded:

| Status | Color | Meaning | Action |
|--------|-------|---------|--------|
| **On Target** | 🟢 Green | Within benchmark ±10% | Monitor, no action |
| **At Risk** | 🟡 Yellow | Approaching threshold or low confidence | Review, plan intervention |
| **Critical** | 🔴 Red | Exceeding threshold or very high risk | Escalate immediately |

---

## Metric Interpretation Cheat Sheet

### Coefficient of Variation (CV)

| CV % | Volatility | Meaning |
|------|-----------|---------|
| < 10% | Very Low | Stable, predictable, reliable |
| 10–30% | Moderate | Normal operational variation |
| > 30% | High | Unstable, hard to forecast |
| > 100% | Extreme | Possible data quality issue |

### Skewness

| Value | Shape | Meaning |
|-------|-------|---------|
| ≈ 0 | Symmetric | Data balanced, no tail bias |
| > 0.5 | Right-skewed | Tail on right, outliers on high end |
| < -0.5 | Left-skewed | Tail on left, outliers on low end |

### Kurtosis (Excess)

| Value | Shape | Meaning |
|-------|-------|---------|
| ≈ 0 | Normal | Standard bell curve |
| > 1 | Leptokurtic | Sharp peak, heavy tails (extreme values) |
| < -1 | Platykurtic | Flat distribution (no strong mode) |

### Outlier Rules

**3-Sigma Rule:**
- Values > 3 std devs from mean (~0.3% of normal data)
- Extreme anomalies only
- Red flag: any values here

**IQR Rule (Tukey Fence):**
- Values < Q1 − 1.5×IQR or > Q3 + 1.5×IQR
- Includes mild + extreme outliers
- Yellow flag: investigate if > 5% of data

---

## Decision Tree: "What Should I Do?"

### Card Shows Red (Critical Risk)

1. **Check Risk % card** → If > 20% of values exceed threshold
   - **Yes?** → Escalate to manager, draft intervention plan
   - **No?** → Maybe one very extreme outlier; investigate

2. **Check Trend card** → Is it worsening or improving?
   - **Worsening** → Urgent; allocate resources
   - **Improving** → Let current action continue; monitor

3. **Check Outliers card** → Any anomalies detected?
   - **Yes** → Isolate & investigate root cause (data error? real anomaly?)
   - **No** → Systemic issue, not isolated

### Card Shows Yellow (At Risk)

1. **Check Trend card** → What's the direction?
   - **Improving** → No action; current approach working
   - **Stable** → Plan for next quarter
   - **Worsening** → Start intervention plan

2. **Check CV card** → Is volatility high?
   - **CV > 30%** → Underlying instability; address root causes
   - **CV < 30%** → Normal variation; accept

3. **Check Confidence card** → How sure are we?
   - **High confidence (narrow CI)** → Trust the signal, act
   - **Low confidence (wide CI)** → Collect more data before acting

### Card Shows Green (On Target)

**No immediate action required.** But check:

1. **Outlier card** → Any anomalies?
   - **Yes** → Minor issue; document & monitor
   - **No** → All good

2. **Trend card** → Direction of change?
   - **Improving** → Reinforce what's working
   - **Worsening** → Plan preventative action
   - **Stable** → Continue current approach

---

## Common Questions

**Q: "My KPI is at 75. Benchmark is 80. Is that bad?"**

A: Look at the Risk Status card. If it's green, you're within acceptable range (±10%). Yellow means it's borderline. Red means action needed.

**Q: "Mean is 75 but Median is 65. What does this mean?"**

A: High outliers are pulling the mean up. The typical value is actually lower (median). Check the box plot—you'll see outliers on the right.

**Q: "CV is 40%. Is that a problem?"**

A: Above 30% = high volatility. This KPI is unstable. Check the Outliers card and Skewness card to understand why. If skewness is high, outliers are driving it.

**Q: "Standard Deviation is 10. Is that high?"**

A: Depends on the unit. A Std Dev of 10 for a KPI measured in thousands is tiny. A Std Dev of 10 for a 0–100 scale is enormous. Check CV% instead—it's unit-free and comparable.

**Q: "Trend is improving but Confidence band is very wide. Should I celebrate?"**

A: Not yet. The wide confidence band means we're not sure if the trend is real or just noise. Collect more data or wait for the band to narrow before declaring success.

**Q: "One borough has 20 outliers, others have 0. What's happening?"**

A: That borough either has a data quality issue (check with source team) or a genuine operational difference. Either way, investigate separately—don't combine boroughs in analysis.

---

## Advanced: When Sample Size Matters

- **n < 30**: Results less reliable. Median more trustworthy than mean. Confidence intervals very wide.
- **30 ≤ n < 100**: Okay. Most statistics reliable.
- **n ≥ 100**: Excellent. Trust even small differences.

Check the **n** column in the statistics table. If it's tiny, take conclusions lightly and collect more data.

---

## Exporting Your Findings

Each Dive supports exports:

- **PNG**: Save chart for presentations
- **CSV**: Download statistics table for Excel analysis
- **JSON**: Raw data for custom analysis
- **MotherDuck Share Link**: Collaborate with teammates (share live Dive)

---

## Need Help?

- **"I don't understand this metric"** → See the Metric Interpretation Cheat Sheet above
- **"What should I do about this?"** → Follow the Decision Tree
- **"This looks wrong"** → Check the Outliers card and Review the Anomaly section. If data looks corrupt, contact the data team.

---

## Summary

Each KPI Dive gives you 40+ metrics to understand your data deeply:
- **Summary cards** (top) = quick health check
- **Charts** = visual patterns
- **Statistics table** = detailed numbers per borough
- **Risk status** = traffic light for action

Read top-to-bottom: summary → chart → table → decision.

