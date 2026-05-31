# Business Metric Definitions

## Revenue metrics

**MRR (Monthly Recurring Revenue)**
The predictable monthly revenue from active subscriptions. Excludes one-time fees, professional services, and usage overages unless contracted.

Components:
- New MRR — from new customers acquired this month
- Expansion MRR — upgrades, seat additions, upsells from existing customers
- Contraction MRR — downgrades from existing customers
- Churned MRR — lost from customers who cancelled

**ARR (Annual Recurring Revenue)**
MRR × 12. A forward-looking measure of annualised subscription run rate, not a trailing 12-month total.

**ACV (Annual Contract Value)**
Total contract value divided by contract length in years. Used for comparing deal sizes.

---

## Retention and churn metrics

**Logo Churn Rate (monthly)**
`churned customers / customers at start of month`
Measures how many customers you lose, regardless of their size.

**Revenue Churn Rate (monthly)**
`churned MRR / MRR at start of month`
Weights churn by customer value.

**Net Revenue Retention (NRR)**
`(starting MRR + expansion MRR − contraction MRR − churned MRR) / starting MRR`
> 100% means existing customer revenue is growing even without new customer acquisition.
Benchmark: best-in-class SaaS > 120%.

**Gross Revenue Retention (GRR)**
`(starting MRR − contraction MRR − churned MRR) / starting MRR`
Upper-bound 100% (expansion excluded). Measures pure downside.

---

## Unit economics

**LTV (Customer Lifetime Value)**
`ARPU × Gross Margin / Monthly Churn Rate`

Where:
- ARPU = average revenue per user per month
- Gross Margin = (revenue − COGS) / revenue
- Monthly Churn Rate = monthly logo or revenue churn (decimal)

LTV represents the average total gross profit expected from a customer over their lifetime.

**CAC (Customer Acquisition Cost)**
`Total Sales & Marketing Spend / New Customers Acquired`

Typically calculated over the same period (quarter or month). Fully-loaded CAC includes salaries, tools, and overhead attributable to S&M.

**LTV:CAC Ratio**
`LTV / CAC`
- < 1: Destroying value per customer
- 1–3: Marginal; likely unprofitable
- 3–5: Healthy
- > 5: Either very efficient or under-investing in growth

**Payback Period**
`CAC / (ARPU × Gross Margin)` in months

How many months until a new customer repays their acquisition cost. Benchmark: < 12 months for high-growth; < 18 months for enterprise.

---

## Engagement metrics

**DAU / MAU (Daily / Monthly Active Users)**
Active is defined by the product — must be specified explicitly (login, any event, core action).

**DAU/MAU Ratio (Stickiness)**
Proportion of monthly actives who return daily. > 20% is strong for consumer; > 10% is typical for B2B.

**Session metrics**
- Session length — average time per session
- Sessions per user per week — frequency signal
- Depth — pages/actions per session

---

## Growth metrics

**MoM Growth**
`(current month value − prior month value) / prior month value`

**WoW / YoY Growth**
Same formula, different period. YoY removes seasonality effects.

**Quick Ratio**
`(New MRR + Expansion MRR) / (Contraction MRR + Churned MRR)`
Ratio > 4 = high-efficiency growth. Measures "quality" of growth — how much gross adds are offset by losses.
