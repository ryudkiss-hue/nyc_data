---
name: segmentation-analysis
description: Identify distinct customer or user segments based on behavior, attributes, or value. Activate when you need to answer "who are our best customers?" or "what distinct groups exist in our user base?" and need data-driven profiles to inform strategy.
---

# When to use
- Marketing needs audience segments for targeted campaigns
- Product team needs user profiles to prioritise features
- Understanding which customer groups are most at risk of churn
- An existing segmentation feels arbitrary and needs data validation
- Personalisation requires meaningful, stable user groupings

# Process
1. **Define segmentation goal** — clarify which business decision the segments will support; this determines variable selection and acceptable segment count (typically 3–7)
2. **Select segmentation variables** — choose 3–7 attributes or behaviours with meaningful variation; prepare data (scale numeric variables, encode categoricals, handle nulls)
3. **Run segmentation** — use `scripts/segmentation_engine.py` supporting k-means clustering (for numeric behavioural data) or rule-based segmentation (for business-defined groups); validate with silhouette score > 0.3 for clustering
4. **Profile each segment** — calculate mean/median metrics per segment as % deviation from overall average; use `scripts/segment_profiler.py`
5. **Name and describe segments** — assign descriptive names based on 2–3 defining characteristics; reference `references/segment_naming_conventions.md`
6. **Produce recommendations** — for each segment, recommend a strategic action: Retain & Expand, Monetise, Activate, Win-Back, or Sunset; fill `assets/segment_profiles_template.md`

# Inputs the skill needs
- Required: customer/user dataset with attributes or behavioural metrics
- Required: segmentation goal — what decision will this support?
- Optional: preferred number of segments or business-defined segment rules
- Optional: minimum segment size threshold
- Note: minimum ~100 users per expected segment for clustering to be meaningful

# Output
- `scripts/segmentation_engine.py` — k-means or rule-based segmentation with validation
- `references/segment_naming_conventions.md` — naming patterns and anti-patterns
- `assets/segment_profiles_template.md` (filled) — per-segment profiles with size, defining metrics, and strategic recommendations
