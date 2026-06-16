# Plan 006: Fix three SKILL.md inaccuracies in the data-analytics-skills library

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**:
> ```bash
> git diff --stat 0c716b2..HEAD -- \
>   data-analytics-skills/03-data-analysis-investigation/segmentation-analysis/SKILL.md \
>   data-analytics-skills/04-data-storytelling-visualization/visualization-builder/SKILL.md \
>   data-analytics-skills/05-stakeholder-communication/methodology-explainer/SKILL.md
> ```
> If any of these files changed since `0c716b2`, compare the "Current state"
> excerpts below against the live code before proceeding.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: docs
- **Planned at**: commit `0c716b2`, 2026-06-14

## Why this matters

Three SKILL.md files contain inaccuracies found during the verify/improve pass.
Each one would cause an analyst to either look for a non-existent script, fail
to find CLI usage docs, or misunderstand what inputs the skill requires. These
are pure documentation fixes — no Python code changes.

## Current state

### Fix 1 — segmentation-analysis/SKILL.md references a non-existent script

File: `data-analytics-skills/03-data-analysis-investigation/segmentation-analysis/SKILL.md`

Line 17 reads:
```
4. **Profile each segment** — calculate mean/median metrics per segment as % deviation from overall average; use `scripts/segment_profiler.py`
```

There is no `segment_profiler.py`. The actual scripts in that directory are:
- `scripts/segmentation_engine.py` — k-means or rule-based segmentation
- `scripts/segment_builder.py` — segment profiling and reporting

Line 29 reads:
```
- `scripts/segmentation_engine.py` — k-means or rule-based segmentation with validation
```
This is correct but incomplete — `scripts/segment_builder.py` is not mentioned.

### Fix 2 — visualization-builder/SKILL.md missing CLI usage docs

File: `data-analytics-skills/04-data-storytelling-visualization/visualization-builder/SKILL.md`

The SKILL.md describes the visualization-builder skill but gives no CLI example
for `scripts/chart_builder.py`. The script requires `--input CSV` (no demo mode
exists), so an analyst following the skill with no CSV would be stuck. The
SKILL.md should include a usage example showing the key flags.

To verify what the script accepts:
```bash
python3 data-analytics-skills/04-data-storytelling-visualization/visualization-builder/scripts/chart_builder.py --help
```
Expected output shows:
```
usage: chart_builder.py [-h] --input INPUT [--recommend] [--chart {bar,line,histogram,scatter}]
                        [--x X_COL] [--y Y_COL] [--target-col TARGET_COL] [--out OUT]
```

### Fix 3 — methodology-explainer/SKILL.md "Inputs" section is misleading

File: `data-analytics-skills/05-stakeholder-communication/methodology-explainer/SKILL.md`

Lines 21–24:
```
# Inputs the skill needs
- Required: description of the analysis method used
- Required: target audience tier (executive / analyst / technical)
- Optional: known concerns or questions the audience is likely to raise
```

This implies analysts must write their own method description. In practice,
`scripts/explain_method.py` works with a fixed menu of 5 built-in methods
(`wilson_score`, `iqr_outlier`, `z_score`, `linear_regression`, `kmeans`).
"Target audience tier" in the script is `--audience` with choices
`field_staff | manager | council | public` — not the tiers listed in the
SKILL.md. The mismatch causes confusion about what to prepare before running
the script vs. what the script can generate on its own.

The SKILL.md is intentionally broader (it covers _how_ to explain methodology
in general), but the "Inputs" section that describes what to pass to the
_script_ should accurately reflect the CLI.

## Steps

### Step 1 — Fix segmentation-analysis/SKILL.md

Open `data-analytics-skills/03-data-analysis-investigation/segmentation-analysis/SKILL.md`.

Replace line 17:
```
4. **Profile each segment** — calculate mean/median metrics per segment as % deviation from overall average; use `scripts/segment_profiler.py`
```
With:
```
4. **Profile each segment** — calculate mean/median metrics per segment as % deviation from overall average; use `scripts/segment_builder.py`
```

Also update the Output section (line 29 onwards). Change:
```
- `scripts/segmentation_engine.py` — k-means or rule-based segmentation with validation
```
To:
```
- `scripts/segmentation_engine.py` — k-means or rule-based segmentation with validation
- `scripts/segment_builder.py` — per-segment profiling: mean/median metrics and top borough per segment
```

**Verification:**
```bash
grep "segment_profiler" data-analytics-skills/03-data-analysis-investigation/segmentation-analysis/SKILL.md
```
Expected: no output (empty).

```bash
grep "segment_builder" data-analytics-skills/03-data-analysis-investigation/segmentation-analysis/SKILL.md
```
Expected: 2 lines (step 4 and the Output section).

### Step 2 — Fix visualization-builder/SKILL.md CLI usage

Open `data-analytics-skills/04-data-storytelling-visualization/visualization-builder/SKILL.md`.

Find the step that mentions `scripts/chart_builder.py` (around step 3 of the
process). After the step description, add a Usage block:

```markdown
  **CLI usage:**
  ```bash
  # See chart recommendations for your data:
  python3 scripts/chart_builder.py --input your_data.csv --recommend

  # Build a bar chart:
  python3 scripts/chart_builder.py --input your_data.csv --chart bar --x borough --y defect_count --out chart.png

  # Build a line trend:
  python3 scripts/chart_builder.py --input your_data.csv --chart line --x inspection_date --y count --out trend.png
  ```
  Note: `--input` is required. For chart types: `bar | line | histogram | scatter`.
```

**Verification:**
```bash
grep -n "\-\-input\|\-\-recommend\|\-\-chart" \
  data-analytics-skills/04-data-storytelling-visualization/visualization-builder/SKILL.md
```
Expected: at least 3 lines containing the flag examples.

### Step 3 — Fix methodology-explainer/SKILL.md Inputs section

Open `data-analytics-skills/05-stakeholder-communication/methodology-explainer/SKILL.md`.

Replace the "Inputs the skill needs" section:
```
# Inputs the skill needs
- Required: description of the analysis method used
- Required: target audience tier (executive / analyst / technical)
- Optional: known concerns or questions the audience is likely to raise
```

With:
```
# Inputs the skill needs
- Required: the method to explain — choose from the built-in list:
  `wilson_score`, `iqr_outlier`, `z_score`, `linear_regression`, `kmeans`
- Required: target audience — `field_staff | manager | council | public`
- Optional: known concerns or questions the audience is likely to raise

**Quick start (script):**
```bash
python3 scripts/explain_method.py --method wilson_score --audience manager
python3 scripts/explain_method.py --method z_score --audience council
```
The script prints the formula, plain-language explanation, an NYC DOT example,
and the audience-tailored phrasing. No external data required.
```

**Verification:**
```bash
python3 data-analytics-skills/05-stakeholder-communication/methodology-explainer/scripts/explain_method.py \
  --method iqr_outlier --audience field_staff
```
Expected: prints formula, plain language section, NYC DOT example, and audience version for `FIELD STAFF`. Exit 0.

```bash
grep "wilson_score\|iqr_outlier" \
  data-analytics-skills/05-stakeholder-communication/methodology-explainer/SKILL.md
```
Expected: at least 1 line listing available methods.

### Step 4 — Update plans/README.md

Mark this plan as `DONE` in `plans/README.md`.

## STOP conditions

- If the SKILL.md files are structured significantly differently from the
  excerpts above (e.g. the sections have been reorganized), do not guess —
  stop and report the current structure so the plan can be updated.

## Done criteria

All three checks pass:
```bash
# 1. No references to non-existent script
grep "segment_profiler" data-analytics-skills/03-data-analysis-investigation/segmentation-analysis/SKILL.md
# Expected: empty

# 2. chart_builder CLI flags documented
grep "\-\-input" data-analytics-skills/04-data-storytelling-visualization/visualization-builder/SKILL.md
# Expected: at least 1 line

# 3. methodology-explainer lists built-in methods
grep "wilson_score" data-analytics-skills/05-stakeholder-communication/methodology-explainer/SKILL.md
# Expected: at least 1 line
```
