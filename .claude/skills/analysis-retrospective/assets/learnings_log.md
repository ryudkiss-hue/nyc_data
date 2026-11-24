# Cumulative Learnings Log

Append an entry each time a retrospective produces a reusable learning. Most recent entry at top.

Format each entry as a fenced block. Do not edit or delete past entries — this is an immutable log.

---

## How to use this log

- Search by `dataset:` tag to find learnings for a specific dataset before starting work on it.
- Search by `category:` to find all reference, template, or checklist updates.
- Before each analysis kickoff, skim entries for the relevant dataset key.

---

## Entry format

```
date:      YYYY-MM-DD
project:   short project name
category:  Template | Reference | Checklist | Norm | Skip
dataset:   dataset key(s) affected, or "general"
learning:  one paragraph describing what was learned and why it matters
action:    what artifact was created or updated (path), or "none" if Norm
status:    DONE | PENDING
```

---

## Log entries

```
date:      2026-06-14
project:   Seed entry — learnings log initialized
category:  Norm
dataset:   general
learning:  Always run `socrata dataset health --key <key>` before starting any analysis,
           even for "routine" pulls. Stale datasets have caused at least two misfiled
           analyses where analysts reported numbers from a dataset that hadn't updated
           in weeks. The health check takes 5 minutes and prevents hours of rework.
action:    none (team norm)
status:    DONE
```

```
date:      2026-06-14
project:   Seed entry — borough code normalization
category:  Reference
dataset:   violations, inspection, ramp_progress
learning:  Borough codes in Socrata data are inconsistent across datasets and even across
           rows within a dataset. Always normalize with upper(trim(borough)) in SOQL
           WHERE clauses. Some rows use full names ("MANHATTAN") while others use codes
           ("MN"). When grouping by borough, apply a CASE statement:
             WHEN upper(borough) IN ('MN','MANHATTAN') THEN 'MN'
             WHEN upper(borough) IN ('BX','BRONX') THEN 'BX'
             WHEN upper(borough) IN ('BK','BROOKLYN') THEN 'BK'
             WHEN upper(borough) IN ('QN','QUEENS') THEN 'QN'
             WHEN upper(borough) IN ('SI','STATEN ISLAND') THEN 'SI'
           This prevents fan-out in GROUP BY queries and silent under-counts.
action:    Add to references/scoping_framework.md under Step 3 Data Dependencies
status:    DONE
```

```
date:      2026-06-14
project:   Seed entry — Wilson CI threshold
category:  Checklist
dataset:   ramp_progress, inspection
learning:  Staten Island consistently produces small sub-samples (n < 30) in borough-
           stratified analyses. Wilson Score CI is always required (n < 1000), but for
           n < 30 the interval is so wide that the rate cannot be reported as a reliable
           point estimate. Flag in output as "insufficient sample" rather than suppress.
           Include n= in every cell of every borough breakdown table.
action:    Add to analysis-qa-checklist skill
status:    PENDING
```

---

<!-- Add new entries above this line -->
