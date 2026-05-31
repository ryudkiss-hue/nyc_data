# Business Rule Patterns for Data Validation

Reusable validation patterns for common data types. Use these as the starting point when defining rules for `value_range_validator.py`.

---

## Numeric Rules

| Column type | Min | Max | Notes |
|---|---|---|---|
| Revenue / amount | 0 | [business cap] | Negative values only valid if refunds are modelled |
| Price / unit cost | 0.01 | [reasonable cap] | Zero price is usually a data error unless free tier |
| Discount percentage | 0 | 100 | Or 0–1 if stored as a ratio |
| Quantity / count | 0 | [reasonable cap] | Fractions only if the unit supports it |
| Age (years) | 0 | 120 | |
| Age (days) | 0 | 43800 | |
| Score / rating | 1 | 5 | Adjust for your rating scale |
| Probability / confidence | 0 | 1 | |
| Latitude | -90 | 90 | |
| Longitude | -180 | 180 | |

---

## Date / Timestamp Rules

| Column type | Min | Max | Notes |
|---|---|---|---|
| `created_at` | [system launch date] | now + 1 day | Future dates indicate a clock error |
| `updated_at` | [system launch date] | now + 1 day | Must be ≥ created_at |
| `event_date` | [earliest historical load] | now | |
| `birth_date` | 1900-01-01 | 18 years ago | If users must be adults |
| `subscription_start` | [product launch date] | now | |
| `subscription_end` | `subscription_start` | now + 10 years | Future end date is valid for active contracts |

**Cross-field rules:**
- `end_date >= start_date`
- `updated_at >= created_at`
- `shipped_at >= ordered_at`
- `resolved_at >= opened_at`

---

## Categorical / Enum Rules

Define the complete allowed set for columns with a fixed value list.

```json
{
  "status":           {"allowed": ["active", "trial", "churned", "paused", "deleted"]},
  "plan_tier":        {"allowed": ["free", "starter", "pro", "enterprise"]},
  "payment_method":   {"allowed": ["card", "ach", "wire", "invoice", "crypto"]},
  "country_code":     {"allowed": ["US", "GB", "DE", "FR", "CA"]},  // expand as needed
  "currency":         {"allowed": ["USD", "EUR", "GBP", "JPY", "CAD"]},
  "event_type":       {"allowed": ["signup", "login", "purchase", "refund", "support_ticket"]}
}
```

---

## String / Format Rules (implement with regex)

| Column type | Pattern | Example valid value |
|---|---|---|
| Email | `.+@.+\..+` | user@company.com |
| UUID | `[0-9a-f-]{36}` | 550e8400-e29b-41d4-a716-446655440000 |
| US phone | `\+1[2-9]\d{9}` | +12125551234 |
| ISO date | `\d{4}-\d{2}-\d{2}` | 2024-01-15 |
| Postal code (US) | `\d{5}(-\d{4})?` | 10001 or 10001-1234 |
| SKU / product code | `[A-Z]{2,4}-\d{4,8}` | PRD-00123 |

---

## Financial Consistency Rules

Cross-column rules that should hold for every row:

1. `gross_profit = revenue - cost_of_goods_sold`
2. `net_revenue = gross_revenue - refunds - discounts`
3. `ltv_estimate ≥ 0` and `ltv_estimate ≤ revenue * 20` (sanity cap)
4. `commission_amount = order_amount * commission_rate` (within 1 cent rounding)
5. If `payment_status = 'paid'` then `payment_date IS NOT NULL`
6. If `order_status = 'shipped'` then `shipped_at IS NOT NULL AND tracking_number IS NOT NULL`

---

## Referential Integrity Patterns

Standard FK relationships to validate:

| Child table | FK column | Parent table | PK column |
|---|---|---|---|
| orders | customer_id | customers | id |
| order_items | order_id | orders | id |
| order_items | product_id | products | id |
| sessions | user_id | users | id |
| events | session_id | sessions | id |
| subscriptions | account_id | accounts | id |
| invoices | subscription_id | subscriptions | id |

---

## Null Rules by Column Role

| Column role | Null policy |
|---|---|
| Primary key | Never null |
| Foreign key | Null allowed if relationship is optional |
| Mandatory attribute | Never null (e.g. email, status, created_at) |
| Optional attribute | Null acceptable; document expected null rate |
| Derived / computed | Null indicates calculation failed — investigate |
| Enrichment (geo, third-party) | Null acceptable; document enrichment rate |
