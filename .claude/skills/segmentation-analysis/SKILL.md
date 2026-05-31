---
name: segmentation-analysis
description: Customer/user segmentation with actionable insights. Use when identifying distinct customer groups, analyzing segment-specific behavior, profiling high-value segments, or testing segmentation hypotheses.
---

# Segmentation Analysis

# When to use
- The team needs to understand who the best customers are and what distinguishes them
- Marketing wants distinct groups to target with different messages or offers
- Product needs to prioritise features based on high-value user behaviour patterns
- Churn is high and the team needs to identify at-risk users before they leave
- An existing segmentation feels arbitrary and needs data validation or improvement

# Process
1. **Define the segmentation goal** — clarify what decisions the segments will inform (product roadmap, marketing campaigns, retention programs). The goal determines which variables matter and how many segments are useful (typically 3–7). See `references/segmentation_approaches.md`.
2. **Select and prepare variables** — choose 3–7 attributes or behaviours that vary across users and relate to the business outcome. Handle missing values and scale continuous variables. Remove outliers only if they would distort cluster centroids.
3. **Run the segmentation** — for data-driven segmentation, use k-means clustering via `scripts/segmentation_runner.py`. For rule-based segmentation, apply the business logic rules and validate that segments are distinct and non-overlapping.
4. **Profile each segment** — compute the mean and median for each variable by segment, expressed as % above/below the overall average. Identify the 2–3 defining characteristics of each segment and assign a descriptive name.
5. **Validate and interpret** — confirm segments are meaningfully different (silhouette score > 0.3 for clustering) and make business sense. Sanity-check by asking whether you would actually treat each segment differently.
6. **Map to strategy and report** — assign each segment to a recommended strategy (Retain & Expand, Monetise, Activate, Win-Back, Sunset). Produce `assets/segment_profile_template.md` with the profiles and strategic priorities.

# Inputs the skill needs
- User-level data with attributes (demographics, plan type) and behavioural metrics (sessions, revenue, feature usage, recency)
- Business goal the segmentation will serve
- Any existing segmentation to validate or replace
- Minimum of ~100 users per expected segment for clustering to be meaningful

# Output
- `scripts/segmentation_runner.py` — runs k-means clustering, produces elbow and silhouette plots, assigns segment labels
- `references/segmentation_approaches.md` — when to use k-means vs. RFM vs. rule-based; interpretation guide
- `assets/segment_profile_template.md` — filled segment profiles with size, key characteristics, recommended strategy, and tracking plan
