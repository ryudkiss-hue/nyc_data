# NYC DOT Program Metric Definitions
**Adapted from:** business-metrics-calculator skill (public-sector operational model)  
**Authority:** NYC DOT Sidewalk Inspection & Management Program  
**Version:** 2026-06-02

---

## Model Type: Public-Sector Operational Program

NYC DOT SIM is not a SaaS subscription business. Standard SaaS metrics (MRR, churn, LTV)
do not apply. This document defines the equivalent operational KPIs and their benchmark
thresholds for each DOT program area.

---

## ADA Ramp Construction Program

### Completion Rate
**Definition:** (Constructed + Complex Constructed corners) ÷ Total corners in corpus × 100  
**Unit:** %  
**Source:** `e7gc-ub6z` → `construc_2` field  
**Frequency:** Updated as construction is recorded  
**Benchmark thresholds:**
| Grade | Threshold |
|-------|-----------|
| ✅ Good | ≥ 75% |
| 🟡 Acceptable | 50–74% |
| 🔴 Poor | < 50% |
**Current value:** 36.9% — 🔴 Poor  
**Notes:** DOT mandate is 100% ADA compliance citywide. 36.9% reflects program-in-progress status; not a failure state.

### Not-Assigned Rate
**Definition:** Corners with status = "Not Assigned" ÷ Total corners × 100  
**Unit:** % (lower is better)  
**What it measures:** Eligible corners with no work order — a scheduling gap, not a construction gap  
**Benchmark thresholds:**
| Grade | Threshold |
|-------|-----------|
| ✅ Good | ≤ 5% |
| 🟡 Acceptable | 5–15% |
| 🔴 Poor | > 15% |
**Current value:** 15.8% — 🔴 Poor  
**Action:** Run borough-stratified work order assignment to close unassigned queue

### Borough Completion Rate
**Definition:** (Constructed + Complex Constructed in borough) ÷ Total borough corners × 100  
**Caveat:** Small-n boroughs (MN, SI) require full-corpus pull for reliability  
**Current values:**
- Bronx: 80% ✅ | Brooklyn: 78% ✅ | Queens: 77% ✅
- Manhattan: 44% 🔴 | Staten Island: 45% 🔴

---

## Violation Resolution Program

### Certification Rate
**Definition:** Violations with non-null `certi_date` ÷ Total violations × 100  
**Unit:** %  
**Source:** `6kbp-uz6m` → `certi_date`  
**What it means:** DOT signed off that the violation was corrected by the property owner  
**Benchmark thresholds:**
| Grade | Threshold |
|-------|-----------|
| ✅ Good | ≥ 85% |
| 🟡 Acceptable | 70–84% |
| 🔴 Poor | < 70% |
**Current value:** 71.4% — 🟡 Acceptable

### Grace Period (Median Days)
**Definition:** Median value of the `grace_pd` field across all violations (calendar days)  
**Unit:** days (lower is better — faster resolution)  
**Standard policy:** 45-day correction window from issuance  
**Benchmark thresholds:**
| Grade | Threshold |
|-------|-----------|
| ✅ Good | ≤ 45 days |
| 🟡 Acceptable | 46–60 days |
| 🔴 Poor | > 60 days |
**Current value:** 45.0 days — ✅ Good (consistent with policy)

### BBL Conflict Rate (Sample-Based)
**Definition:** BBLs appearing on 2+ violations ÷ Unique BBLs in sample × 100  
**Unit:** % (lower is better)  
**Note:** This metric is sample-size sensitive. Full-corpus detection (via CLI `conflict-detect`)
is required for accurate conflict counts.  
**Full-corpus result (21,936 rows):** 1,926 conflicted BBLs / ~10,000 unique BBLs ≈ ~8.8%  
**2,000-row sample result:** 20 conflicted BBLs / 1,980 unique BBLs = 1.0%  
**Benchmark thresholds:**
| Grade | Threshold (full corpus) |
|-------|------------------------|
| ✅ Good | ≤ 5% |
| 🟡 Acceptable | 5–10% |
| 🔴 Poor | > 10% |
**Use full-corpus rate for this metric; sample rate is not meaningful.**

---

## Resurfacing Program

### Paving/Milling Mix
**Definition:** PAVING jobs ÷ Total scheduled jobs × 100  
**Typical target:** 60/40 PAVING/MILLING ratio reflects standard resurfacing workflow  
**Current value:** 61.0% PAVING — within normal range

### Manhattan Share of Weekly Jobs
**Definition:** Manhattan jobs ÷ Total citywide jobs × 100  
**Expected share:** ~20% (proportional to lane-miles)  
**Current value:** 7.2% — ⚠️ Significantly below expected share  
**Note:** Investigate whether this reflects a planned outer-borough rotation or a systematic gap

---

## Data Quality Metrics (Toolkit Health)

### Dataset Availability Rate
**Definition:** Datasets returning non-empty responses ÷ Total datasets in registry × 100  
**Current value:** 23/26 = 88.5% (3 empty/timeout)

### CI Pass Rate
**Definition:** PRs with all checks passing ÷ Total open PRs × 100  
**Current value:** 5/5 = 100%

### Synthetic Data Exposure Rate
**Definition:** Fraction of API calls that could route to synthetic data  
**Current value:** 0% (demo mode hard-disabled)  
**Target:** 0%

---

## Dataset Governance Compliance

### LL251 Inventory Compliance
**Definition:** Datasets confirmed in NYC DOT LL251 inventory ÷ DOT-operated datasets in registry × 100  
**Unit:** % (higher is better)  
**Source:** `5tqd-u88y` (LL251 Data Asset Inventory)  
**What it measures:** Alignment between operational registry and official DOT inventory; signals governance maturity and audit readiness  
**Benchmark thresholds:**
| Grade | Threshold |
|-------|-----------|
| ✅ Good | ≥ 90% |
| 🟡 Acceptable | 85–89% |
| 🔴 Poor | < 85% |
**Current value:** 88.5% (23/26 confirmed) — 🟡 Acceptable  
**Notes:** 3 non-DOT datasets (vfx9-tbb6, 64uk-42ks, erm2-nwe9) excluded by agency; all DOT-operated datasets registered.

### Automation Rate
**Definition:** Datasets with automatic (system-managed) updates ÷ Total datasets in registry × 100  
**Unit:** % (higher is better)  
**What it measures:** Degree to which data updates are scheduled/automated vs. manual; signals operational scalability  
**Source:** `5tqd-u88y` → `update_automation` field  
**Benchmark thresholds:**
| Grade | Threshold |
|-------|-----------|
| ✅ Good | ≥ 80% |
| 🟡 Acceptable | 70–79% |
| 🔴 Poor | < 70% |
**Current value:** 65.4% (17/26 automated) — 🔴 Poor  
**Candidates for improvement:** i642-2fxq (Lot Info), jvk9-k4re (Capital Blocks), u9au-h79y (Step Streets), fwpa-qxaf (Pedestrian Demand)

### Removed Records Flag
**Definition:** Datasets with records marked as deleted/removed in live updates ÷ Total datasets × 100  
**Unit:** % (lower is better)  
**What it measures:** Data quality concern; indicates whether datasets support historical retention and audit trails  
**Source:** `5tqd-u88y` → `legislativecompliance_removedrecords` field  
**Benchmark thresholds:**
| Grade | Threshold |
|-------|-----------|
| ✅ Good | < 10% |
| 🟡 Acceptable | 10–20% |
| 🔴 Poor | > 20% |
**Current value:** 23.1% (6/26 flagged) — 🔴 Poor  
**Flagged datasets:** 6kbp-uz6m (Violations), j6v2-6uxq (Tree Damage), jagj-gttd (Ramp Complaints), 97nd-ff3i (Capital Reconstruction), ffaf-8mrv (In-house Resurfacing), plus 1 other  
**Action:** Review data retention policy; determine whether historical versions should be archived vs. purged for each flagged dataset.

### Update Frequency Compliance
**Definition:** Datasets with update_frequency matching operational needs (Daily for active programs, Monthly/Quarterly for static references)  
**Unit:** Categorical (Daily, Weekly, Monthly, Quarterly, Annual)  
**What it measures:** Alignment between data refresh cadence and program operational cycles  
**Source:** `5tqd-u88y` → `update_updatefrequency` field  
**Current distribution:**
- Daily: 16/26 (62%) — Active operational datasets
- Weekly: 2/26 (8%) — Permit/construction coordination
- Monthly: 3/26 (11%) — Summary/reference layers
- Quarterly: 3/26 (11%) — Reference/overlay layers
- Annual: 1/26 (4%) — Static inventory

**Notes:** Daily updates dominate operational datasets (Violations, Inspections, Permits); aligned with DOT program velocity. Reference layers (MapPLUTO, Planimetric) follow source-system update cadences (Quarterly).
