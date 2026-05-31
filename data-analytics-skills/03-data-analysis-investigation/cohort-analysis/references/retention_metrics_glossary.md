# Retention Metrics Glossary

Definitions for retention metrics used in cohort analysis. Use these as the canonical definitions when writing reports.

---

## Core Retention Metrics

### Day-N / Week-N / Month-N Retention
The percentage of users from a cohort who were active on (or within) period N after joining.

```
N-period Retention = (Users active in period N) / (Cohort size at period 0) × 100
```

**Variants:**
- **Unbounded (on or after):** User is retained if they were active *any time up to period N*
- **Bounded (exactly at N):** User is retained only if they were active *within period N* (the standard definition)

Always specify which variant you're using.

---

### D1 / D7 / D30 Retention (Day-based)
Common benchmarks for consumer apps. Measured using bounded windows.

| Product Category | D1 Target | D7 Target | D30 Target |
|---|---|---|---|
| Top-quartile mobile apps | > 40% | > 20% | > 10% |
| Median mobile apps | ~25% | ~10% | ~5% |
| SaaS / B2B products | > 70% (W1) | > 50% (W4) | — |

*Benchmarks vary widely by product type — use industry-specific sources.*

---

### Rolling Retention
A user is counted as retained in period N if they were active *at any point from period N onwards*.

```
Rolling Retention (N) = Users who returned on period N or later / Cohort size
```

Rolling retention never decreases — it can only stay flat or increase as you extend the window. Useful for showing "did this user ever come back?"

---

### Week-over-Week (WoW) Retention
Percentage of weekly active users from week N who are also active in week N+1.

```
WoW Retention = WAU(this week) who were also WAU(last week) / WAU(last week)
```

---

### Month-over-Month (MoM) Retention
Same concept for monthly active users.

```
MoM Retention = MAU(this month) who were also MAU(last month) / MAU(last month)
```

---

## Revenue Retention Metrics

### Gross Revenue Retention (GRR)
The percentage of recurring revenue retained from existing customers, excluding expansion.

```
GRR = (Starting MRR − Churn MRR − Contraction MRR) / Starting MRR × 100
```
GRR is capped at 100% (cannot exceed starting revenue).

**Best-in-class:** > 90% for SaaS; > 85% for SMB-focused SaaS.

---

### Net Revenue Retention (NRR) / Net Dollar Retention (NDR)
Revenue retained including expansion (upsell/cross-sell), minus churn and contraction.

```
NRR = (Starting MRR − Churn MRR − Contraction MRR + Expansion MRR) / Starting MRR × 100
```
NRR can exceed 100% if expansion outweighs churn.

**Best-in-class:** > 120% for enterprise SaaS; > 100% for any healthy SaaS.

---

### Logo Retention / Customer Retention Rate (CRR)
The percentage of customers (accounts, not revenue) retained over a period.

```
CRR = (Customers at end − New customers acquired) / Customers at start × 100
```

---

## Derived Metrics

### Churn Rate
```
Monthly Churn Rate = Churned customers this month / Customers at start of month × 100
```

Relationship: Monthly Retention Rate + Monthly Churn Rate = 100%

### Expected Lifetime
```
Expected Lifetime (months) = 1 / Monthly Churn Rate
```
Example: 5% monthly churn → 20-month expected lifetime.

### Lifetime Value (LTV) via Retention
```
LTV = ARPU × (1 / Churn Rate)   [for constant churn rate]
```

---

## Period Labels Explained

| Label | Meaning | Example (monthly) |
|---|---|---|
| Period 0 | The cohort's first period — baseline (always 100%) | January cohort in January |
| Period 1 | One period after joining | January cohort in February |
| Period N | N periods after joining | January cohort in month N+1 |

Period 0 should always be 100% unless there is a data quality issue (users who had the retention event before their cohort date).
