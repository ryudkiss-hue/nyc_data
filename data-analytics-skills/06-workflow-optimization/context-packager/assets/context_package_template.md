# Context Package

**Session / task name:** [short descriptive title]  
**Created:** [YYYY-MM-DD]  
**Token estimate:** [~X,000 tokens]  
**Quality score:** [X / 10]  
**Model target:** [claude-3-sonnet / gpt-4o / other]

---

## TASK

[What you need the AI to do. Be specific: what to analyse, what output you need, any hard constraints.]

Example:
> Analyse the churn data in `prod.subscriptions` and identify the top 3 factors that distinguish customers who churned within 90 days of signup from those who stayed. Produce a ranked list of factors with supporting evidence. Use only data from 2024-01-01 onwards. Output as a Markdown table followed by a short narrative summary.

---

## BUSINESS CONTEXT

[Company/product context, how key metrics are defined, relevant business rules.]

**Key metric definitions:**
- **Churned:** [definition — e.g. subscription cancelled or not renewed within 90 days of expiry]
- **Active:** [definition]
- **MRR:** [definition]

**Business context:**
[2–3 sentences about the product, customer base, and anything relevant to interpreting the data.]

---

## DATA SCHEMA

[Tables and columns relevant to the task. Include only what's needed.]

```sql
-- prod.subscriptions
CREATE TABLE prod.subscriptions (
    subscription_id   VARCHAR,
    customer_id       VARCHAR,
    plan_tier         VARCHAR,   -- free, starter, pro, enterprise
    status            VARCHAR,   -- active, cancelled, expired
    created_at        TIMESTAMP,
    cancelled_at      TIMESTAMP, -- null if not cancelled
    mrr               DECIMAL
);

-- prod.customers
CREATE TABLE prod.customers (
    customer_id       VARCHAR,
    industry          VARCHAR,
    company_size      VARCHAR,   -- SMB, Mid-Market, Enterprise
    signup_source     VARCHAR,
    created_at        TIMESTAMP
);
```

---

## PRIOR FINDINGS

[Results from previous analyses relevant to this task. Summarise — don't paste full reports.]

- [e.g. Last quarter's churn analysis found SMB had 2× the churn rate of Enterprise — focus there]
- [e.g. "Onboarding completion" was identified as a leading indicator of 90-day retention]

---

## CONSTRAINTS

- [e.g. Only use data from 2024-01-01 onwards — earlier data has schema inconsistencies]
- [e.g. Exclude free-tier accounts — they are not revenue-bearing]
- [e.g. Do not make causal claims — this is observational data]

---

## OUTPUT FORMAT

[How you want the response structured.]

- Format: [Markdown table + narrative / SQL query / bullet points / slide outline]
- Length: [Concise — under 500 words / detailed — as needed]
- Terminology: [Use "customer" not "user"; use "$" not "USD"]

---

*Bundle built with `scripts/context_bundler.py`. Token count verified with `scripts/token_counter.py`.*
