# Impact Quantification Framework

Structured approach to sizing business impact. Use this before running any impact script to ensure the right model and inputs are chosen.

---

## Step 1: Classify the Impact Type

| Type | Definition | Example |
|---|---|---|
| **Revenue growth** | Additional revenue that would not exist without the change | Improved checkout conversion adds orders |
| **Cost reduction** | Lower spend on existing operations | Automation reduces manual review hours |
| **Risk reduction** | Reduced probability or cost of a bad outcome | Better fraud detection reduces chargeback losses |
| **Efficiency gain** | Same output with fewer inputs (not always monetised directly) | Faster pipeline reduces analyst waiting time |

---

## Step 2: Identify the Impact Formula

### Revenue Growth

```
Incremental revenue = Affected volume × Lift % × Value per unit × Time horizon
```
Use `scripts/revenue_impact.py --model conversion_lift`

### Retention / Churn Prevention

```
LTV impact = Saved customers × Average LTV
```
Use `scripts/revenue_impact.py --model retention_improvement`

### Upsell / Expansion Revenue

```
Expansion revenue = Eligible base × Take rate × Incremental ARPU × Time horizon
```
Use `scripts/revenue_impact.py --model upsell`

### Cost Reduction (Headcount)

```
Savings = Hours saved per person × Hourly fully-loaded cost × Headcount × Periods
```
Use `scripts/cost_savings.py --model headcount_efficiency`

### Cost Reduction (Error/Rework)

```
Savings = (Error rate before − Error rate after) × Volume × Cost per error × Periods
```
Use `scripts/cost_savings.py --model error_reduction`

### Infrastructure / Vendor Cost

```
Savings = Current cost × Reduction % × Periods
```
Use `scripts/cost_savings.py --model infrastructure`

---

## Step 3: Assign a Confidence Level

Based on how well each input is known:

| Level | When to use | Range |
|---|---|---|
| **High** | All inputs measured directly; method validated | ±20% around base |
| **Medium** | 1–2 inputs are estimated; method is approximate | −40% / +60% |
| **Low** | Multiple inputs estimated; novel scenario | −70% / +150% |

Use `scripts/confidence_interval.py` to produce the range.

---

## Step 4: Document Every Assumption

For each input, record:
- **Source** (measured / estimated / benchmarked / assumed)
- **Value used**
- **Sensitivity**: what happens to the output if this input is 50% wrong?

High-sensitivity inputs need explicit acknowledgement in the estimate.

---

## Estimation Pitfalls

**Optimism bias** — people systematically overestimate lift and underestimate cost. Apply a 20–30% discount to first-cut estimates unless they are based on measured experiments.

**Attribution double-counting** — if two teams both claim credit for the same metric improvement, the total claimed impact exceeds the real impact. Always check: is this the same pool of customers/events?

**Ignoring cannibalisation** — upselling customers on a premium tier reduces revenue from existing contracts if they would have renewed at the same rate. Model the net change, not the gross.

**Confusing one-time and recurring impact** — a data migration saves headcount once; a process improvement saves headcount every month. Label clearly.
