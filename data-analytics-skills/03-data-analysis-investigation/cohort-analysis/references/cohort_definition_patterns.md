# Cohort Definition Patterns

Guidance for choosing how to define cohorts and how to interpret common retention patterns.

---

## Cohort Grouping Strategies

| Strategy | When to use | Example |
|---|---|---|
| **Signup date** | Default — group by when users joined the product | January 2024 signup cohort |
| **First purchase date** | E-commerce / marketplace — focus on buying behaviour | First purchase in Q1 |
| **First activation event** | Products with an "aha moment" — group by when users first got value | First project created |
| **Acquisition channel** | Marketing attribution — compare channel quality | Organic vs. Paid cohort |
| **Plan tier at signup** | B2B SaaS — compare free vs. paid cohort behaviour | Free trial cohort |
| **Feature adoption** | Measure impact of a specific feature | Users who used Feature X in month 1 |
| **Assigned segment** | Geographic or demographic segmentation | Enterprise accounts cohort |

---

## Retention Event Definitions

Retention means different things in different products. Choose the right event:

| Product type | Good retention event | Avoid |
|---|---|---|
| Consumer app | Login, session start, core action | Generic page view |
| E-commerce | Repeat purchase within N days | Browsing without purchase |
| SaaS / B2B | Seat usage, feature use, API call | Passive SSO login |
| Marketplace | Listing a product, making a sale | Account creation only |
| Content platform | Content consumed ≥ N minutes | App open with 0 engagement |

**Best practice:** define "active" with the data team and at least one product stakeholder before running analysis. A wrong retention event produces correct-looking but misleading retention curves.

---

## Common Retention Patterns and What They Mean

### 1. Smile / Bathtub Curve
```
100% ─────
         \
          ─────── ──────────── (flattens to 20-30%)
```
Healthy product. High early churn (users who don't find value), but a stable retained core.

**Signal:** Focus acquisition on users more likely to be in the "retained core" population.

---

### 2. Continuous Decline (no flattening)
```
100% ─\
       \─
         \─
           \──────────────── (approaches 0%)
```
Product has not achieved product-market fit for this segment. No user cohort finds lasting value.

**Signal:** Retention is a product problem, not a marketing problem. Investigate why users leave.

---

### 3. Improving Cohorts (newer cohorts retain better)
```
[2023-01] ──── 20%
[2023-06] ────── 35%
[2024-01] ──────── 45%
```
Product improvements are working. Validate by correlating retention improvement with specific releases.

---

### 4. Declining Cohorts (newer cohorts retain worse)
```
[2023-01] ──────── 45%
[2023-06] ────── 30%
[2024-01] ──── 20%
```
Product quality has degraded, acquisition channels are bringing lower-quality users, or product is becoming less relevant.

**Signal:** Investigate what changed (product, acquisition mix, market).

---

### 5. Step-change at a specific period
```
100% ──────────────────── ─── ───
                        |
                        Drops suddenly at period 6
```
There may be a contract end date, a free trial expiry, or a competitor event at period N.

**Signal:** Intervene proactively before period N (e.g. renewal outreach before month 6).

---

## Cohort Analysis Pitfalls

### 1. Immature cohorts
Recent cohorts have fewer periods of data. Don't compare period-12 retention of a January cohort against a November cohort that only has 3 periods.

**Fix:** Only compare cohorts at the same period number; highlight which cells are incomplete.

### 2. Survivorship bias in averages
Averaging retention across all cohorts is dominated by the largest cohorts. Report retention per cohort, not just an overall average.

### 3. Small cohort noise
A 20-person cohort showing 80% retention at period 6 means 4 people were active. Statistical noise is high.

**Fix:** Set a minimum cohort size threshold (e.g. ≥ 100) and exclude or grey out smaller cohorts.

### 4. Conflating user retention with revenue retention
A user may be retained but spend less — or a user may churn but be on an annual plan with revenue recognised. Run separate analyses for user retention and net revenue retention (NRR).

### 5. Multiple retention events inflating retention
If a user can generate 10 events per day, filtering to "any event" will show near-100% retention even if the product has problems.

**Fix:** Deduplicate to one active/inactive signal per user per period.
