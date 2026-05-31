---
name: metric-reconciliation
description: Cross-source metric validation and discrepancy investigation. Use when metrics from different sources don't match, investigating data quality issues between systems, or validating data migration accuracy.
---

# Metric Reconciliation

## Quick Start

Systematically compare metrics across different data sources, identify discrepancies, investigate root causes, and produce reconciliation reports with actionable fixes.

## Context Requirements

Before reconciling metrics, I need:

1. **Data Sources**: The 2+ systems/datasets to compare
2. **Metric Definitions**: How each source calculates the metric
3. **Expected Variance**: What difference is acceptable vs. concerning
4. **Time Period**: What date range to reconcile
5. **Join Keys**: How to match records across sources

## Context Gathering

### For Data Sources:
"I need access to the data from each source. Please provide:

**Source 1** (e.g., Production Database):
- Connection details OR CSV export OR SQL query to fetch data
- System name: 'Postgres Production DB'
- What metric: 'Total Revenue'

**Source 2** (e.g., Analytics Warehouse):
- Connection details OR CSV export OR SQL query to fetch data  
- System name: 'Snowflake Analytics'
- What metric: 'Total Revenue'

**Additional Sources** (if comparing 3+ systems):
- Same information for each additional source

Can you provide data exports or connection details for each source?"

### For Metric Definitions:
"To understand why metrics might differ, I need:

**How is the metric calculated in each source?**

Example for 'Total Revenue':
- **Source 1 (Production)**: `SUM(orders.total_amount) WHERE status = 'completed'`
- **Source 2 (Analytics)**: `SUM(daily_revenue.amount) WHERE type = 'sale'`

**Known calculation differences:**
- Does Source 1 include refunds? (yes/no)
- Does Source 2 exclude certain transaction types? (which ones?)
- Different time zones? (UTC vs EST)
- Different granularity? (transaction-level vs daily aggregates)

Understanding these helps identify expected vs. unexpected differences."

### For Expected Variance:
"What variance is acceptable before we investigate?

**Common Thresholds:**
- **Financial metrics** (revenue, payments): <0.1% variance acceptable
- **User metrics** (signups, sessions): <2% variance acceptable  
- **Behavioral metrics** (clicks, views): <5% variance acceptable

For your metric, what % difference would trigger investigation?

Also:
- Are some time periods expected to differ? (recent data still syncing?)
- Known lag between sources? (e.g., data warehouse updates daily)"

### For Time Period:
"What time range should I reconcile?

**Options:**
- **Specific dates**: '2024-12-01' to '2024-12-31'
- **Last N days**: Last 7 days, last 30 days
- **Relative period**: Last month, last quarter
- **All time**: Full historical comparison

Note: Longer periods may take more time but show trends in variance."

### For Join Keys:
"How should I match records between sources?

**Common Join Strategies:**

1. **Aggregate Comparison** (simplest):
   - Compare totals only
   - Example: Total revenue Source 1 vs Source 2

2. **Time-Based Comparison**:
   - Match by date/hour/minute
   - Example: Daily revenue Source 1 vs Source 2

3. **Entity-Based Comparison**:
   - Match by transaction ID, order ID, customer ID
   - Example: Order #12345 in both systems

4. **Multi-Key Comparison**:
   - Match by date + entity
   - Example: Customer X's revenue on 2024-12-15

Which approach makes sense for your use case?"

## Workflow

### Step 1: Load Data from Each Source

```python
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Load Source 1
if source1_type == 'database':
    source1_df = pd.read_sql(source1_query, source1_connection)
elif source1_type == 'csv':
    source1_df = pd.read_csv(source1_file)

# Load Source 2
if source2_type == 'database':
    source2_df = pd.read_sql(source2_query, source2_connection)
elif source2_type == 'csv':
    source2_df = pd.read_csv(source2_file)

print(f"📊 Data Loaded:")
print(f"  Source 1 ({source1_name}): {len(source1_df):,} records")
print(f"  Source 2 ({source2_name}): {len(source2_df):,} records")
```

**Checkpoint**: "Data loaded successfully. Record counts look reasonable?"

### Step 2: Standardize Data Formats

```python
def standardize_data(df, date_col, metric_col, source_name):
    """Standardize data format for comparison"""
    
    # Convert dates to datetime
    df[date_col] = pd.to_datetime(df[date_col])
    
    # Ensure metric is numeric
    df[metric_col] = pd.to_numeric(df[metric_col], errors='coerce')
    
    # Remove nulls
    original_count = len(df)
    df = df.dropna(subset=[date_col, metric_col])
    dropped = original_count - len(df)
    
    if dropped > 0:
        print(f"⚠️  {source_name}: Dropped {dropped} records with null date/metric")
    
    # Add source identifier
    df['source'] = source_name
    
    return df

source1_df = standardize_data(source1_df, 'date', 'revenue', 'Source1')
source2_df = standardize_data(source2_df, 'date', 'revenue', 'Source2')
```

### Step 3: Aggregate at Comparison Level

```python
# Aggregate by date (or whatever join key you're using)
source1_agg = source1_df.groupby('date')['revenue'].sum().reset_index()
source1_agg.columns = ['date', 'source1_revenue']

source2_agg = source2_df.groupby('date')['revenue'].sum().reset_index()
source2_agg.columns = ['date', 'source2_revenue']

print(f"\n📈 Aggregated Data:")
print(f"  Source 1: {len(source1_agg)} date periods")
print(f"  Source 2: {len(source2_agg)} date periods")
```

### Step 4: Join and Compare

```python
# Full outer join to catch records in one source but not the other
comparison = source1_agg.merge(source2_agg, on='date', how='outer')

# Fill NaN with 0 for missing dates
comparison['source1_revenue'] = comparison['source1_revenue'].fillna(0)
comparison['source2_revenue'] = comparison['source2_revenue'].fillna(0)

# Calculate differences
comparison['difference'] = comparison['source1_revenue'] - comparison['source2_revenue']
comparison['abs_difference'] = comparison['difference'].abs()
comparison['pct_difference'] = (
    (comparison['difference'] / comparison['source1_revenue'].replace(0, np.nan)) * 100
).fillna(0)

# Sort by date
comparison = comparison.sort_values('date')

print(f"\n🔍 Comparison Summary:")
print(f"  Total periods compared: {len(comparison)}")
print(f"  Perfect matches: {(comparison['difference'] == 0).sum()}")
print(f"  Discrepancies: {(comparison['difference'] != 0).sum()}")
```

### Step 5: Analyze Discrepancies

```python
def analyze_discrepancies(comparison, threshold_pct=2.0):
    """Identify and categorize discrepancies"""
    
    # Categorize by severity
    comparison['status'] = 'MATCH'
    comparison.loc[comparison['abs_difference'] > 0, 'status'] = 'MINOR'
    comparison.loc[comparison['pct_difference'].abs() > threshold_pct, 'status'] = 'SIGNIFICANT'
    
    # Statistics
    stats = {
        'total_source1': comparison['source1_revenue'].sum(),
        'total_source2': comparison['source2_revenue'].sum(),
        'total_difference': comparison['difference'].sum(),
        'total_pct_diff': (comparison['difference'].sum() / 
                          comparison['source1_revenue'].sum() * 100),
        'periods_matched': (comparison['status'] == 'MATCH').sum(),
        'periods_minor': (comparison['status'] == 'MINOR').sum(),
        'periods_significant': (comparison['status'] == 'SIGNIFICANT').sum(),
        'max_abs_diff': comparison['abs_difference'].max(),
        'avg_abs_diff': comparison['abs_difference'].mean()
    }
    
    return stats

stats = analyze_discrepancies(comparison, threshold_pct=2.0)

print(f"\n📊 Reconciliation Statistics:")
print(f"  Source 1 Total: ${stats['total_source1']:,.2f}")
print(f"  Source 2 Total: ${stats['total_source2']:,.2f}")
print(f"  Difference: ${stats['total_difference']:,.2f} ({stats['total_pct_diff']:.2f}%)")
print(f"\n  Perfect Matches: {stats['periods_matched']}")
print(f"  Minor Variances: {stats['periods_minor']}")
print(f"  Significant Variances: {stats['periods_significant']}")
```

### Step 6: Investigate Root Causes

```python
# Find the worst discrepancies
worst_discrepancies = comparison.nlargest(10, 'abs_difference')

print(f"\n🔍 Top 10 Largest Discrepancies:")
for _, row in worst_discrepancies.iterrows():
    print(f"\n  Date: {row['date'].strftime('%Y-%m-%d')}")
    print(f"    Source 1: ${row['source1_revenue']:,.2f}")
    print(f"    Source 2: ${row['source2_revenue']:,.2f}")
    print(f"    Difference: ${row['difference']:,.2f} ({row['pct_difference']:.1f}%)")

# Investigate patterns
print(f"\n📈 Patterns:")

# Check if discrepancy trends over time
comparison['month'] = pd.to_datetime(comparison['date']).dt.to_period('M')
monthly_variance = comparison.groupby('month')['pct_difference'].mean()

improving = monthly_variance.iloc[-3:].mean() < monthly_variance.iloc[:3].mean()
print(f"  Variance trend: {'Improving' if improving else 'Worsening'}")

# Check for systematic bias
bias = "Source 1 consistently higher" if stats['total_difference'] > 0 else "Source 2 consistently higher"
print(f"  Systematic bias: {bias}")

# Check for specific days of week
comparison['day_of_week'] = pd.to_datetime(comparison['date']).dt.day_name()
dow_variance = comparison.groupby('day_of_week')['abs_difference'].mean()
worst_day = dow_variance.idxmax()
print(f"  Worst day of week: {worst_day}")
```

### Step 7: Drill Down on Specific Discrepancies

```python
def investigate_specific_date(date, source1_df, source2_df):
    """Drill into a specific date's discrepancy"""
    
    # Filter to that date
    s1_detail = source1_df[source1_df['date'] == date]
    s2_detail = source2_df[source2_df['date'] == date]
    
    print(f"\n🔬 Detailed Investigation: {date}")
    print(f"\n  Source 1:")
    print(f"    Records: {len(s1_detail)}")
    print(f"    Total: ${s1_detail['revenue'].sum():,.2f}")
    print(f"    Sample transactions:")
    print(s1_detail[['transaction_id', 'revenue', 'status']].head())
    
    print(f"\n  Source 2:")
    print(f"    Records: {len(s2_detail)}")
    print(f"    Total: ${s2_detail['revenue'].sum():,.2f}")
    print(f"    Sample transactions:")
    print(s2_detail[['transaction_id', 'revenue', 'status']].head())
    
    # Find missing transactions
    s1_ids = set(s1_detail['transaction_id'])
    s2_ids = set(s2_detail['transaction_id'])
    
    missing_in_s2 = s1_ids - s2_ids
    missing_in_s1 = s2_ids - s1_ids
    
    if missing_in_s2:
        print(f"\n  ⚠️  In Source 1 but not Source 2: {len(missing_in_s2)} transactions")
        print(f"    Total value: ${s1_detail[s1_detail['transaction_id'].isin(missing_in_s2)]['revenue'].sum():,.2f}")
    
    if missing_in_s1:
        print(f"\n  ⚠️  In Source 2 but not Source 1: {len(missing_in_s1)} transactions")
        print(f"    Total value: ${s2_detail[s2_detail['transaction_id'].isin(missing_in_s1)]['revenue'].sum():,.2f}")

# Investigate worst discrepancy
worst_date = worst_discrepancies.iloc[0]['date']
investigate_specific_date(worst_date, source1_df, source2_df)
```

### Step 8: Generate Reconciliation Report

```python
def generate_reconciliation_report(comparison, stats):
    """Create comprehensive reconciliation report"""
    
    report = []
    report.append("=" * 60)
    report.append("METRIC RECONCILIATION REPORT")
    report.append("=" * 60)
    report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Period: {comparison['date'].min()} to {comparison['date'].max()}")
    report.append(f"\n{'Source 1':20} ${stats['total_source1']:>15,.2f}")
    report.append(f"{'Source 2':20} ${stats['total_source2']:>15,.2f}")
    report.append(f"{'-'*40}")
    report.append(f"{'Difference':20} ${stats['total_difference']:>15,.2f}")
    report.append(f"{'Variance %':20} {stats['total_pct_diff']:>14.2f}%")
    
    report.append(f"\n{'='*60}")
    report.append("SUMMARY")
    report.append("=" * 60)
    report.append(f"  Perfect Matches: {stats['periods_matched']}")
    report.append(f"  Minor Variances: {stats['periods_minor']}")
    report.append(f"  Significant Variances: {stats['periods_significant']}")
    report.append(f"  Average Daily Variance: ${stats['avg_abs_diff']:,.2f}")
    report.append(f"  Maximum Daily Variance: ${stats['max_abs_diff']:,.2f}")
    
    report.append(f"\n{'='*60}")
    report.append("TOP DISCREPANCIES")
    report.append("=" * 60)
    
    top_10 = comparison.nlargest(10, 'abs_difference')
    for i, row in top_10.iterrows():
        report.append(f"\n{row['date'].strftime('%Y-%m-%d')}:")
        report.append(f"  Source 1: ${row['source1_revenue']:>12,.2f}")
        report.append(f"  Source 2: ${row['source2_revenue']:>12,.2f}")
        report.append(f"  Diff: ${row['difference']:>12,.2f} ({row['pct_difference']:>6.1f}%)")
    
    return "\n".join(report)

report = generate_reconciliation_report(comparison, stats)
print(report)

# Save report
with open('reconciliation_report.txt', 'w') as f:
    f.write(report)

# Save detailed comparison to CSV
comparison.to_csv('detailed_comparison.csv', index=False)
```

## Context Validation

Before proceeding, verify:
- [ ] Have access to data from all sources being compared
- [ ] Metric definitions are clear and documented
- [ ] Know what variance is acceptable vs concerning
- [ ] Time periods align between sources
- [ ] Have unique identifiers to match records (if doing detailed reconciliation)

## Output Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
METRIC RECONCILIATION REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Metric: Total Revenue
Period: 2024-12-01 to 2024-12-31
Generated: 2025-01-11 15:30:00

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Production DB        $1,234,567.89
Analytics DW         $1,229,123.45
────────────────────────────────
Difference           $    5,444.44
Variance %                  0.44%

Status: ✅ WITHIN THRESHOLD (< 2%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BREAKDOWN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Days Compared: 31
  ✅ Perfect Matches: 23 days (74%)
  ⚠️  Minor Variances: 6 days (19%)
  🔴 Significant Variances: 2 days (7%)

Average Daily Variance: $175.63
Maximum Daily Variance: $2,345.67

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOP 5 DISCREPANCIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 2024-12-15
   Production: $45,678.90
   Analytics:  $43,333.23
   Difference: $2,345.67 (5.1%)
   
2. 2024-12-22
   Production: $38,901.23
   Analytics:  $37,123.45
   Difference: $1,777.78 (4.6%)

[... continues ...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROOT CAUSE ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Pattern: Source 1 consistently higher
Likely Causes:
1. Timing: Production DB updated real-time,
   Analytics DW has 2-hour delay
2. Refunds: Production includes, Analytics excludes
3. Missing Data: 15 transactions on 2024-12-15
   present in Production but not in Analytics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMMEDIATE:
1. Investigate 2024-12-15 missing transactions
2. Document refund handling difference

ONGOING:
3. Set up daily reconciliation alerts
4. Standardize metric definitions across systems

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FILES GENERATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ reconciliation_report.txt
✓ detailed_comparison.csv (daily breakdown)
✓ discrepancies_only.csv (issues for investigation)
```

## Common Scenarios

### Scenario 1: "Daily revenue doesn't match between systems"
→ Compare aggregated daily revenue
→ Identify which days have discrepancies
→ Drill into specific days to find missing/extra transactions
→ Document known timing differences

### Scenario 2: "Migration validation - old system vs new system"
→ Compare same metric across systems for overlapping period
→ Match by transaction ID to find missing/changed records
→ Validate calculation logic produces same results
→ Create mapping for known differences

### Scenario 3: "Financial reconciliation for month-end close"
→ Compare general ledger to data warehouse
→ Strict threshold (< 0.1% variance)
→ Investigate every discrepancy
→ Produce audit trail documentation

### Scenario 4: "Why does dashboard show different number than report?"
→ Compare underlying queries from each
→ Identify filter differences, timing differences
→ Document which number is "correct" and why
→ Fix or annotate the incorrect source

### Scenario 5: "Quarterly business review - validate all KPIs"
→ Reconcile multiple metrics systematically
→ Create reconciliation matrix (metric × source)
→ Flag metrics that need definition alignment
→ Prioritize fixes by business impact

## Handling Missing Context

**User says "numbers don't match" without specifics:**
"Let me help reconcile. I need:
1. What's the metric? (revenue, user count, etc.)
2. What are the two numbers you're seeing?
3. Where is each number coming from? (system, report, dashboard)
4. What time period?"

**User doesn't know metric definitions:**
"No problem. I'll extract the underlying queries/data from each source and reverse-engineer how they're calculating the metric. Then we can see where they diverge."

**User doesn't have direct data access:**
"Can you export the data to CSV from each source? Or screenshot the summary numbers? I can work with whatever you have access to."

**No transaction-level data available:**
"We'll do aggregate comparison only. This will show the magnitude of the difference but won't pinpoint specific missing transactions."

## Advanced Options

After basic reconciliation, offer:

**Automated Monitoring**:
"Want me to create a script that runs this reconciliation daily and alerts you when variance exceeds threshold?"

**Multi-Source Reconciliation**:
"If you have 3+ sources to compare, I can create a reconciliation matrix showing all pairwise comparisons."

**Trend Analysis**:
"I can track reconciliation over time to show if data quality is improving or degrading."

**Root Cause Classification**:
"I can categorize discrepancies by likely cause (timing lag, missing data, calculation difference, etc.) to prioritize fixes."

**Documentation Generation**:
"I can create formal documentation of known differences between sources for your team's reference."
