# Plan 007: Add --demo modes to run_audit.py and chart_builder.py

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**:
> ```bash
> git diff --stat 0c716b2..HEAD -- \
>   data-analytics-skills/01-data-quality-validation/data-quality-audit/scripts/run_audit.py \
>   data-analytics-skills/04-data-storytelling-visualization/visualization-builder/scripts/chart_builder.py
> ```
> If either file changed since `0c716b2`, compare the "Current state" excerpts
> against the live code before proceeding. On a mismatch, treat it as a STOP.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: dx
- **Planned at**: commit `0c716b2`, 2026-06-14

## Why this matters

Both scripts require external resources that aren't always available:

- `run_audit.py` requires `--key <dataset>` which triggers a live Socrata API
  fetch. Without `SOCRATA_APP_TOKEN` and network access, the script fails
  immediately. Analysts cannot test or demo the quality audit logic in isolation.
- `chart_builder.py` requires `--input CSV` (marked `required=True`). Even the
  `--recommend` mode (which produces zero charts) reads the CSV first. An
  analyst wanting to understand the tool must produce a test CSV first.

Adding `--demo` to both scripts follows the pattern already established in
`saas_metrics.py`, `funnel_analyzer.py`, `cohort_builder.py`, and
`drilldown_analyzer.py`. The fix is entirely additive — no existing code paths
change.

**Convention to match (existing exemplar):**
```python
# From: data-analytics-skills/03-data-analysis-investigation/business-metrics-calculator/scripts/saas_metrics.py
parser.add_argument("--demo", action="store_true", help="Run with built-in demo data")
# ...
if args.demo:
    df = generate_demo_data()
    print("Running with demo data (12 months, July 2025 – June 2026)\n")
elif args.input:
    df = pd.read_csv(args.input)
else:
    print("ERROR: provide --input FILE or --demo")
    sys.exit(1)
```

## Current state

### run_audit.py (lines 190–198)

File: `data-analytics-skills/01-data-quality-validation/data-quality-audit/scripts/run_audit.py`

```python
def main():
    parser = argparse.ArgumentParser(description="NYC DOT data quality audit")
    parser.add_argument("--key", required=True, choices=list(DATASET_KEYS), help="Dataset key")
    parser.add_argument("--rows", type=int, default=5000, help="Rows to sample (default: 5000)")
    parser.add_argument("--output", default=None, help="Output file path (.md or .html)")
    parser.add_argument("--html", action="store_true", help="Output HTML report")
    args = parser.parse_args()

    df = fetch_data(args.key, args.rows)
    required = REQUIRED_FIELDS.get(args.key, [])
```

The data the script expects per dataset is defined in `REQUIRED_FIELDS` (lines
41–48) and `VALID_BOROUGHS` (lines 50–61). The audit checks: completeness of
required fields, duplicate objectid/unique_key rows, borough validity, and
date range rules.

Demo data for the `inspection` dataset key needs these columns:
`objectid`, `borough`, `status`, `inspection_date` (the required fields for
`inspection` per `REQUIRED_FIELDS`). The script also calls
`check_borough_validity(df)` which looks for a `borough` column and validates
it against `VALID_BOROUGHS`.

### chart_builder.py (lines 177–204)

File: `data-analytics-skills/04-data-storytelling-visualization/visualization-builder/scripts/chart_builder.py`

```python
def main():
    parser = argparse.ArgumentParser(description="Recommend or build charts for NYC DOT data.")
    parser.add_argument("--input", required=True, help="Path to CSV")
    ...
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    for col in df.columns:
        if "date" in col.lower() or "time" in col.lower():
            df[col] = pd.to_datetime(df[col], errors="coerce")
```

The recommend logic (`recommend_charts()` at line 49) uses: datetime cols,
numeric cols, category cols. The chart logic uses `groupby` on `x_col` with
sum/count for `bar`, `sort_values` for `line`, `.hist()` for histogram, and
`.scatter()` for scatter. Demo data should have all four column types.

## Steps

### Step 1 — Add generate_demo_data() and --demo to run_audit.py

Open `data-analytics-skills/01-data-quality-validation/data-quality-audit/scripts/run_audit.py`.

**1a.** Add a `generate_demo_data()` function after the `fetch_data()` function
(after line 70, before `check_completeness`). Insert this function:

```python
def generate_demo_data() -> pd.DataFrame:
    """Synthetic NYC DOT inspection records for demo/offline use."""
    import random
    from datetime import date, timedelta

    random.seed(42)
    boroughs = ["MN", "BX", "BK", "QN", "SI", "INVALID_B"]  # 1 invalid for testing
    statuses = ["OPEN", "CLOSED", "PENDING", "DISMISSED"]
    rows = []
    base = date(2025, 1, 1)
    for i in range(200):
        d = base + timedelta(days=random.randint(0, 500))
        rows.append({
            "objectid": i if i != 5 else 5,  # one duplicate for dup check
            "borough": random.choices(boroughs, weights=[20, 20, 20, 20, 18, 2])[0],
            "status": random.choice(statuses),
            "inspection_date": str(d),
            "defect_count": random.randint(0, 15),
            "days_to_close": random.randint(1, 90) if random.random() > 0.2 else None,
        })
    return pd.DataFrame(rows)
```

**1b.** Change `--key` from `required=True` to optional, and add `--demo`.
Replace the `main()` function's argparse block:

```python
def main():
    parser = argparse.ArgumentParser(description="NYC DOT data quality audit")
    parser.add_argument(
        "--key",
        choices=list(DATASET_KEYS),
        help="Dataset key (required unless --demo is used)",
    )
    parser.add_argument("--demo", action="store_true", help="Run with synthetic demo data (no API)")
    parser.add_argument("--rows", type=int, default=5000, help="Rows to sample (default: 5000)")
    parser.add_argument("--output", default=None, help="Output file path (.md or .html)")
    parser.add_argument("--html", action="store_true", help="Output HTML report")
    args = parser.parse_args()

    if args.demo:
        df = generate_demo_data()
        key = "inspection"  # demo data matches inspection schema
        print("[INFO] Running with synthetic demo data (200 rows, inspection schema)")
    elif args.key:
        df = fetch_data(args.key, args.rows)
        key = args.key
    else:
        parser.error("--key or --demo is required")

    required = REQUIRED_FIELDS.get(key, [])
```

Then update the rest of `main()` to use `key` instead of `args.key`:
- Line that calls `render_markdown(args.key, ...)` → change to `render_markdown(key, ...)`

**Verification:**
```bash
python3 data-analytics-skills/01-data-quality-validation/data-quality-audit/scripts/run_audit.py --demo
```
Expected: prints a Markdown quality audit report with completeness table,
duplicate check, borough check, and scoring. Exit 0. No Socrata import error.

```bash
python3 data-analytics-skills/01-data-quality-validation/data-quality-audit/scripts/run_audit.py --demo --output /tmp/test_audit.md
```
Expected: same plus "Report written to /tmp/test_audit.md". Exit 0.

```bash
python3 -m ruff check data-analytics-skills/01-data-quality-validation/data-quality-audit/scripts/run_audit.py
```
Expected: "All checks passed!"

### Step 2 — Add generate_demo_data() and --demo to chart_builder.py

Open `data-analytics-skills/04-data-storytelling-visualization/visualization-builder/scripts/chart_builder.py`.

**2a.** Add a `generate_demo_data()` function after the imports (after the
`MESSAGE_TYPE_MAP` dict, before `infer_message_type()`). Insert:

```python
def generate_demo_data() -> pd.DataFrame:
    """Synthetic NYC DOT inspection records for demo/testing."""
    import random
    from datetime import date, timedelta

    random.seed(42)
    boroughs = ["MN", "BX", "BK", "QN", "SI"]
    rows = []
    base = date(2026, 1, 1)
    for i in range(120):
        d = base + timedelta(days=i // 4)
        rows.append({
            "inspection_date": str(d),
            "borough": boroughs[i % 5],
            "defect_count": random.randint(0, 20),
            "days_to_close": random.randint(1, 60),
            "violation_rate": round(random.uniform(0, 1), 3),
            "count": random.randint(50, 200),
        })
    return pd.DataFrame(rows)
```

**2b.** In `main()`, change `--input` from `required=True` to optional and add
`--demo`. Replace the argparse setup and CSV load:

```python
def main():
    parser = argparse.ArgumentParser(description="Recommend or build charts for NYC DOT data.")
    parser.add_argument("--input", help="Path to CSV (required unless --demo)")
    parser.add_argument("--demo", action="store_true", help="Use built-in synthetic demo data")
    parser.add_argument(
        "--recommend", action="store_true", help="Print chart recommendations and exit"
    )
    parser.add_argument(
        "--chart", choices=["bar", "line", "histogram", "scatter"], help="Chart type to build"
    )
    parser.add_argument("--x", dest="x_col", help="X-axis column")
    parser.add_argument("--y", dest="y_col", help="Y-axis column (not needed for histogram)")
    parser.add_argument("--target-col", help="Column of interest for recommendations")
    parser.add_argument("--out", default="chart.png", help="Output file (.png)")
    args = parser.parse_args()

    if args.demo:
        df = generate_demo_data()
        print("[INFO] Using built-in demo data (120 rows, NYC DOT inspection schema)")
        for col in df.columns:
            if "date" in col.lower():
                df[col] = pd.to_datetime(df[col], errors="coerce")
    elif args.input:
        df = pd.read_csv(args.input)
        for col in df.columns:
            if "date" in col.lower() or "time" in col.lower():
                df[col] = pd.to_datetime(df[col], errors="coerce")
    else:
        parser.error("--input or --demo is required")

    if args.recommend:
        recommend_charts(df, target_col=args.target_col)
        return

    if not args.chart or not args.x_col:
        parser.error("--chart and --x are required when not using --recommend")

    build_chart(df, args.chart, args.x_col, args.y_col, args.out)
```

**Verification:**
```bash
python3 data-analytics-skills/04-data-storytelling-visualization/visualization-builder/scripts/chart_builder.py --demo --recommend
```
Expected: prints chart recommendations showing LINE CHART, BAR CHART, SCATTER,
and HISTOGRAM suggestions. No deprecation warnings. Exit 0.

```bash
python3 -m ruff check data-analytics-skills/04-data-storytelling-visualization/visualization-builder/scripts/chart_builder.py
```
Expected: "All checks passed!"

### Step 3 — Syntax check both files

```bash
python3 -c "import ast; ast.parse(open('data-analytics-skills/01-data-quality-validation/data-quality-audit/scripts/run_audit.py').read()); print('OK: run_audit.py')"
python3 -c "import ast; ast.parse(open('data-analytics-skills/04-data-storytelling-visualization/visualization-builder/scripts/chart_builder.py').read()); print('OK: chart_builder.py')"
```
Expected: both print "OK: <filename>".

### Step 4 — Update plans/README.md

Mark this plan as `DONE` in `plans/README.md`.

## STOP conditions

- If `render_markdown` is called with positional argument `args.key` more than
  once in `run_audit.py` (e.g. a helper you didn't see), stop and map all
  call sites before changing.
- If `chart_builder.py` has a different structure than described (e.g. the
  `main()` block was already refactored), compare carefully — the logic is
  additive; only add the `--demo` path without removing anything.

## Out of scope

- Do not add `--demo` to any other script in this plan.
- Do not modify the `fetch_data()` function or any live-data code paths.
- Do not add matplotlib-based chart generation to the demo path — `--demo
  --recommend` is sufficient; `--demo --chart bar` can work if matplotlib is
  installed but is not required to pass the done criteria.

## Done criteria

```bash
# 1. run_audit demo mode works offline
python3 data-analytics-skills/01-data-quality-validation/data-quality-audit/scripts/run_audit.py --demo
# Expected: prints Markdown report, exit 0

# 2. chart_builder demo recommend works offline
python3 data-analytics-skills/04-data-storytelling-visualization/visualization-builder/scripts/chart_builder.py --demo --recommend
# Expected: prints chart recommendations, exit 0

# 3. Ruff clean
python3 -m ruff check \
  data-analytics-skills/01-data-quality-validation/data-quality-audit/scripts/run_audit.py \
  data-analytics-skills/04-data-storytelling-visualization/visualization-builder/scripts/chart_builder.py
# Expected: All checks passed!

# 4. No LLM imports added
grep -rn "anthropic\|openai\|langchain" \
  data-analytics-skills/01-data-quality-validation/data-quality-audit/scripts/run_audit.py \
  data-analytics-skills/04-data-storytelling-visualization/visualization-builder/scripts/chart_builder.py
# Expected: no output
```
