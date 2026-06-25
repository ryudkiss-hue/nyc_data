# Dual-Tier Fuzzy Router & Question-Answering System Design

**Date:** 2026-06-20  
**Status:** Design Complete (Ready for Implementation)  
**Scope:** NYC DOT SIM Analyst CLI Question Router + Pre-Built Answer Engine + Claude Expansion

---

## Executive Summary

This design specifies a **two-tier question-answering system** for the NYC DOT SIM analyst CLI (`socrata nl-query`). The system routes natural language questions to pre-materialized Metrics, datasets, and visualizations (Tier 1 — instant, governed), with optional Claude-powered synthesis and NLP-driven next-question suggestions (Tier 2 — on-demand, exploratory).

**Key outcomes:**
- Analysts get instant answers without LLM latency (Tier 1)
- Optional deeper synthesis and exploration (Tier 2)
- Pre-trained router with 1,000 variants before deployment
- Continuous learning via analyst feedback (incremental Bayesian updates)
- Both Claude and future LLM providers supported (abstracted interface)

---

## 1. Problem Statement

**Current State:**
- 309+ Metrics exist across the NYC DOT SIM domain
- 60+ research questions documented
- 51 Metrics materialized in production pipeline
- Analysts have no discovery mechanism — must manually search docs/code for relevant datasets and Metrics
- Result: 30+ minutes lost to "which dataset?" phase before analysis starts

**Desired State:**
- Analyst asks natural language question: `socrata nl-query "Why are violations spiking in Manhattan?"`
- System instantly routes to relevant Metric, datasets, SQL pattern, and visualization
- Analyst can use pre-built assets immediately (5-minute time-to-productivity)
- Optional: analyst can ask for deeper synthesis ("Tell me more") → Claude expands on the answer with insights and suggests follow-up analyses

---

## 2. Architecture

### 2.1 System Overview

```
┌──────────────────────────────────────────────────────────┐
│ CLI: socrata nl-query "Why are violations spiking in MN?"│
└─────────────────────┬──────────────────────────────────┘
                      │
        ┌─────────────▼──────────────┐
        │  HybridRouter              │
        │  (ensemble: programmatic   │
        │   + Claude embeddings)     │
        └─────────────┬──────────────┘
                      │
      ┌───────────────┼───────────────┐
      │               │               │
 ┌────▼────┐    ┌────▼──────┐   ┌────▼───────┐
 │Programmatic│    │Claude     │   │Observability│
 │Router     │    │Embeddings │   │Logger      │
 │(BM25,    │    │(Tier-2)   │   │            │
 │FastText, │    │(cached)   │   │            │
 │Jaccard)  │    │           │   │            │
 └────┬────┘    └────┬──────┘   └────┬───────┘
      │              │               │
      └──────────────┼───────────────┘
                     │
      ┌──────────────▼──────────────┐
      │ Ensemble Decision           │
      │ (both agree/disagree?)      │
      └──────────────┬──────────────┘
                     │
      ┌──────────────▼──────────────────────┐
      │ ★ TIER 1: PRE-BUILT ANSWER         │
      │ (instant, governed, no LLM)        │
      │ - Matched Metric + summary            │
      │ - Datasets + SQL pattern           │
      │ - Pre-built visualization metadata │
      │ - Confidence + router source       │
      └──────────────┬──────────────────────┘
                     │
          ┌──────────▼──────────┐
          │ Analyst satisfied?  │
          └──────────┬──────────┘
               │          │
              YES        NO (--expand flag)
               │          │
               │      ┌───▼──────────────────┐
               │      │ ★ TIER 2: CLAUDE     │
               │      │ EXPANSION            │
               │      │ (on-demand, LLM)     │
               │      │ - Execute SQL query  │
               │      │ - Claude synthesizes │
               │      │ - NLP suggests next  │
               │      │   questions          │
               │      └───┬──────────────────┘
               │          │
               └──────────┴──────┐
                          │
                  ┌───────▼────────────┐
                  │ FeedbackCollector  │
                  │ + Incremental      │
                  │ Bayesian Update    │
                  └────────────────────┘
```

### 2.2 Data Flow: Two Execution Paths

#### **Path 1: Fast (Default, Tier 1 Only)**

```
1. Analyst: socrata nl-query "How many violations fixed by borough?"
2. Router: Run BM25 + FastText + Jaccard (parallel, ~100ms)
           Run Claude embeddings (cached, ~200ms)
           Ensemble: Both suggest METRIC-089? Confidence = avg(0.82, 0.80) = 0.81
3. PreBuiltAnswer Engine: Lookup METRIC-089 in registry
                          Fetch datasets, SQL, visualization, summary
                          Return JSON (no query execution yet)
4. CLI Output: 
   {
     "matched_metric": "METRIC-089",
     "metric_name": "Violations Fixed by Borough & Month",
     "summary": "Monthly count of violations marked fixed, by borough",
     "datasets": ["violations", "dismissals"],
     "sql_pattern": "SELECT borough, DATE_TRUNC('month', fixed_date) AS month, COUNT(*) AS fixed_count...",
     "visualization": "monthly_fix_rate_chart",
     "confidence": 0.81,
     "routing_source": "ensemble (programmatic=0.82, claude=0.80)"
   }
5. Time: 200ms total

Analyst then:
  - Executes SQL manually or loads visualization
  - Runs their own analysis on the data
```

#### **Path 2: Deep (On-Demand, Tier 1 + Tier 2)**

```
1. Analyst: socrata nl-query "Why are violations spiking?" --expand
2. [Same as Path 1 through step 3]
3. Query Executor: Execute pre-built SQL
                   Results: Borough MN saw 45% increase in June vs May
4. Claude Synthesis:
   Input: Question + SQL results + Metric context
   Output: "Violations spiked 45% in Manhattan in June. Analysis shows
            this correlates with structural damage reports in neighborhoods
            X, Y, Z. Historical trend indicates seasonal pattern, but this
            year is 2.3x higher than same period in 2025. Recommend
            investigating contractor quality metrics."
5. NLP Matcher: Parse Claude insights
                Match against 60+ research questions registry
                Find related Metrics: METRIC-045 (structural damage), 
                                   METRIC-067 (contractor metrics),
                                   METRIC-123 (seasonal patterns)
6. CLI Output:
   {
     [Same as Path 1...]
     "tier_2_expansion": {
       "query_results_summary": "45% increase in June vs May",
       "claude_synthesis": "Violations spiked 45%...[full insight]",
       "suggested_next_questions": [
         {
           "question": "What is causing the structural damage spike?",
           "related_metric": "METRIC-045",
           "command": "socrata nl-query 'structural damage trends in MN'"
         },
         {
           "question": "Are contractor quality metrics correlated?",
           "related_metric": "METRIC-067",
           "command": "socrata nl-query 'contractor performance metrics'"
         }
       ]
     }
   }
7. Time: ~5 seconds (query execution + Claude + NLP)

Analyst can:
  - Accept synthesis as-is
  - Click through to suggested questions (auto-routes to new Metrics)
  - Diverge with follow-up questions
```

---

## 3. Core Components

### 3.1 Fuzzy Router (Dual-Engine Ensemble)

**Component:** `src/socrata_toolkit/core/hybrid_router.py`

**Responsibilities:**
- Orchestrate two routing strategies in parallel
- Ensemble scoring (agreement vs disagreement detection)
- Configurable + adaptive thresholds (default 0.70)
- Return MatchResult with source attribution

**Tier 1: ProgrammaticRouter**
- File: `src/socrata_toolkit/core/programmatic_router.py`
- Strategies: BM25, FastText, Jaccard
- Weights: Derived from Bayesian optimization on 1,000 variants
  - BM25: 0.86 (highest trust)
  - FastText: 0.04 (fast but less reliable)
  - Jaccard: 0.10 (token overlap, simple)
- Latency: ~100ms per question
- Deterministic (no network calls)

**Tier 2: Claude Embeddings**
- File: `src/socrata_toolkit/core/claude_semantic_router.py`
- Strategy: Vector similarity (cached embeddings)
- Cache: Pre-computed embeddings for 309 Metrics (loaded at startup)
- Latency: ~200ms (cache lookup + cosine similarity)
- Provider abstraction: Can swap Claude for Gemini/others via config

**Ensemble Logic:**
```python
# Run both in parallel
t1_result = programmatic_router.match(question)  # {qid, confidence=0.82}
t2_result = claude_router.match(question)        # {qid, confidence=0.80}

if t1_result.qid == t2_result.qid:
    # Agreement: high confidence
    ensemble_confidence = (t1_result.confidence + t2_result.confidence) / 2
    ensemble_status = "HIGH_CONFIDENCE"
else:
    # Disagreement: requires clarification
    ensemble_status = "REQUIRES_CLARIFICATION"
    return [t1_result, t2_result]  # Both candidates
```

### 3.2 Pre-Built Answer Engine (Tier 1)

**Component:** `src/socrata_toolkit/core/prebuilt_answer_engine.py`

**Responsibilities:**
- Lookup matched Metric in registry
- Fetch datasets, SQL pattern, visualization metadata, summary
- Return structured AnswerResult (no execution, no LLM)
- Fully deterministic and auditable

**Registry Source:** `config/metric_registry.json` (version-controlled)

**Registry Structure:**
```json
{
  "metric_id": "METRIC-089",
  "metric_name": "Violations Fixed by Borough & Month",
  "summary": "Monthly count of violations marked fixed, by NYC borough",
  "category": "Quality & Compliance",
  "analyst_duties": ["duty_001", "duty_003"],
  "datasets": [
    {
      "key": "violations",
      "fourfour": "6kbp-uz6m",
      "role": "primary"
    },
    {
      "key": "dismissals",
      "fourfour": "p4u2-3jgx",
      "role": "supporting"
    }
  ],
  "sql_pattern": "SELECT borough, DATE_TRUNC('month', fixed_date) AS month, COUNT(*) AS fixed_count FROM violations WHERE status='FIXED' GROUP BY borough, month ORDER BY month DESC, fixed_count DESC",
  "visualization_metadata": [
    {
      "title": "Monthly Fix Rate by Borough",
      "type": "line_chart",
      "x_axis": "month",
      "y_axis": "fixed_count",
      "breakdown": "borough"
    },
    {
      "title": "Violations Heatmap",
      "type": "heatmap",
      "rows": "borough",
      "columns": "month",
      "values": "fixed_count"
    }
  ],
  "related_metrics": ["METRIC-045", "METRIC-067", "METRIC-123"],
  "last_updated": "2026-06-20",
  "quality_score": 0.92
}
```

### 3.3 Claude Expansion Engine (Tier 2)

**Component:** `src/socrata_toolkit/core/claude_expansion_engine.py`

**Responsibilities:**
- Execute SQL query (uses DuckDB or MotherDuck)
- Pass results to Claude for synthesis
- Parse Claude output for insights
- Return ExpandedAnswerResult

**Prompt Template:**
```
You are a NYC DOT data analyst.
Question: {user_question}
Metric: {metric_name}
Query Results: {query_results_json}

Provide a 2-3 sentence synthesis explaining:
1. What the data shows
2. Why it matters
3. Any anomalies or trends

Be specific with numbers and borough/category names.
```

**Output:** String synthesis (analyst-facing text)

### 3.4 NLP Suggestion Engine

**Component:** `src/socrata_toolkit/core/npl_suggester.py`

**Responsibilities:**
- Parse Claude synthesis for key terms/insights
- Match against 60+ research questions registry
- Rank by relevance
- Map to related Metrics

**Process:**
```python
# 1. Extract key terms from Claude synthesis
insights = claude_expansion_engine.synthesize(results)
# → "violations spiked, structural damage, neighborhoods X Y Z"

# 2. Fuzzy match against research questions
matching_questions = research_question_registry.find_similar(insights)
# → [
#      "What is causing the structural damage spike?",
#      "Are contractor quality metrics correlated?",
#      "Historical seasonal patterns?"
#    ]

# 3. Map to Metrics
suggestions = [
  {
    "question": q,
    "related_metric": research_registry.question_to_metric(q),
    "command": f"socrata nl-query '{q}'"
  }
  for q in matching_questions[:3]  # Top 3
]
```

### 3.5 Feedback Collector & Incremental Bayesian Update

**Component:** `src/socrata_toolkit/core/feedback_collector.py`

**Responsibilities:**
- Capture analyst markings (--helpful / --wrong)
- Store in DuckDB: `routing_feedback(question, matched_metric_id, actual_metric_id, timestamp, helpful)`
- Accumulate feedback
- Trigger incremental weight updates

**Incremental Bayesian Update:**
- After each feedback item: compute weight delta
- Apply delta immediately to router weights
- No batch waiting (continuous adaptation)
- Every 500 items: full re-optimization run + commit weights to git

**Observability Tables:**
```sql
-- routing_decisions: Every routing event
CREATE TABLE routing_decisions (
  id UUID PRIMARY KEY,
  question TEXT,
  matched_metric_id VARCHAR,
  confidence FLOAT,
  ensemble_status VARCHAR,  -- HIGH_CONFIDENCE or REQUIRES_CLARIFICATION
  latency_ms INT,
  router_source VARCHAR,    -- programmatic or claude or ensemble
  created_at TIMESTAMP
);

-- routing_feedback: Analyst corrections
CREATE TABLE routing_feedback (
  id UUID PRIMARY KEY,
  routing_decision_id UUID REFERENCES routing_decisions(id),
  analyst_marked_helpful BOOLEAN,
  corrected_metric_id VARCHAR,
  feedback_text TEXT,
  created_at TIMESTAMP
);

-- weight_history: Router weight evolution
CREATE TABLE weight_history (
  id UUID PRIMARY KEY,
  timestamp TIMESTAMP,
  strategy VARCHAR,  -- BM25, FastText, Jaccard
  weight FLOAT,
  source VARCHAR,   -- initial or feedback_delta or re_optimization
  feedback_count INT
);
```

---

## 4. Variant Training & Pre-Deployment Setup

### 4.1 Variant Augmentation Strategy

**Current State:**
- 277 seed variants (from existing fuzzy_matching_training_data.json)
- 90 Metrics covered
- 3.1 variants per Metric on average

**Goal:**
- Cover all 309 Metrics
- ~3-5 variants per Metric
- Total: 1,000 variants

**Process:**

**Step 1: Extract Phasing Templates from Seed (277 variants)**
```python
seed_variants = load_json("fuzzy_matching_training_data.json")

# Group by variant type
direct_phrasing = [v for v in seed_variants if v['variant_type'] == 'direct_phrasing']
technical = [v for v in seed_variants if v['variant_type'] == 'technical']
casual = [v for v in seed_variants if v['variant_type'] == 'casual']

# Extract patterns (templating)
templates = {
  'direct_phrasing': "What is the {metric_name}?",
  'technical': "{metric_name} metrics across {dimension}",
  'casual': "How's the {metric_name} doing?",
  'abbreviation': "{metric_abbr} by {dimension}",
}
```

**Step 2: Generate Synthetic Variants for 219 Missing Metrics**
```python
registry = load_metric_registry()  # 309 Metrics
covered_metrics = {v['metric_id'] for v in seed_variants}
missing_metrics = [k for k in registry.keys() if k not in covered_metrics]  # ~219

synthetic = []
for metric in missing_metrics:
    for template_name, template in templates.items():
        variant = template.format(
            metric_name=metric.name,
            metric_abbr=metric.abbreviation,
            dimension=metric.primary_dimension
        )
        synthetic.append({
            'metric_id': metric.id,
            'metric_name': metric.name,
            'question_variant': variant,
            'variant_type': template_name,
            'synthetic': True,
            'datasets': metric.datasets,
            'analyst_duty': metric.duties[0]
        })

# ~900 synthetic variants generated
```

**Step 3: Validate Synthetic Variant Quality**
```python
# Holdout validation on seed
seed_holdout = random_sample(seed_variants, 0.20)  # ~55 variants
seed_train = seed_variants - seed_holdout           # ~222 variants

# Train router on seed_train
router = train_router(seed_train)

# Test on seed_holdout
seed_accuracy = router.evaluate(seed_holdout)  # Should be ≥82%

# Test on synthetic
synthetic_accuracy = router.evaluate(synthetic)  # Should be ≥80%

if synthetic_accuracy < 0.80:
    # Regenerate with richer synonyms/domain context
    raise ValidationError("Synthetic variants too weak")
```

**Step 4: Combine & Train Final Weights**
```python
all_variants = seed_variants + synthetic  # ~1,277 variants
train_set = random_sample(all_variants, 0.80)  # ~1,021
holdout_set = all_variants - train_set    # ~256

# Bayesian optimization on train_set
optimal_weights = bayesian_optimize(
    train_set,
    strategies=['BM25', 'FastText', 'Jaccard'],
    iterations=100
)
# → BM25=0.86, FastText=0.04, Jaccard=0.10 (validates prior research)

# Evaluate on holdout
final_accuracy = evaluate(holdout_set, optimal_weights)  # Expected ≥82%
```

**Step 5: Pre-Cache Claude Embeddings**
```python
# For all 309 Metrics, pre-compute embeddings
embeddings_cache = {}
for metric in registry:
    text = f"{metric.name}. {metric.summary}"
    embedding = claude_client.embed(text)  # ~100 Metrics takes ~30 seconds
    embeddings_cache[metric.id] = embedding

# Save to file, load at startup
save_json(embeddings_cache, "cache/metric_embeddings.json")
```

### 4.2 Pre-Deployment Checklist

- [ ] Generate 900 synthetic variants
- [ ] Validate synthetic quality (≥80% accuracy)
- [ ] Combine 277 seed + 900 synthetic = 1,177 variants
- [ ] Train and optimize weights on 1,177 variants
- [ ] Validate final accuracy on holdout (≥82%)
- [ ] Pre-cache Claude embeddings for 309 Metrics
- [ ] Build DuckDB observability schema
- [ ] Deploy with trained router

---

## 5. CLI Interface

### 5.1 Tier 1 (Fast Path)

```bash
$ socrata nl-query "How many violations fixed by borough?"

✓ MATCHED: METRIC-089 (Violations Fixed by Borough & Month)
  Confidence: 0.81 | Source: ensemble (programmatic=0.82, claude=0.80)

📊 DATASETS:
  - violations (6kbp-uz6m)
  - dismissals (p4u2-3jgx)

💾 SQL PATTERN:
  SELECT borough, DATE_TRUNC('month', fixed_date) AS month, 
         COUNT(*) AS fixed_count
  FROM violations
  WHERE status='FIXED'
  GROUP BY borough, month
  ORDER BY month DESC, fixed_count DESC;

📈 VISUALIZATIONS:
  - monthly_fix_rate_chart
  - violations_heatmap

ℹ️  SUMMARY:
  Monthly count of violations marked fixed, by NYC borough.
  Use to track repair completion rates and identify slow boroughs.

💡 TIP: Run with --expand to get deeper analysis
       Run with --helpful to mark this result
```

### 5.2 Tier 2 (Deep Path)

```bash
$ socrata nl-query "Why are violations spiking?" --expand

[Same as above, plus:]

🔍 TIER 2 EXPANSION (Claude Analysis):

Violations spiked 45% in Manhattan in June vs May. Analysis of
query results shows this correlates with structural damage reports
in neighborhoods X (123 reports), Y (98 reports), Z (67 reports).
Historical trend indicates seasonal pattern (avg June sees 15%
increase), but this year is 2.3x higher than same period in 2025.
Recommend investigating contractor quality metrics and material
sourcing changes in Q2 2026.

🔗 SUGGESTED NEXT QUESTIONS:
   [1] "What is causing the structural damage spike?"
       → METRIC-045: Structural Damage by Borough & Cause
       Command: socrata nl-query 'structural damage trends MN'
       
   [2] "Are contractor quality metrics correlated?"
       → METRIC-067: Contractor Performance Metrics
       Command: socrata nl-query 'contractor performance by region'
       
   [3] "Historical seasonal patterns?"
       → METRIC-123: Violations Seasonal Decomposition
       Command: socrata nl-query 'seasonal trends violations'

👍 Mark helpful with: socrata nl-query <question> --helpful
👎 Mark wrong with:   socrata nl-query <question> --wrong --correct-metric METRIC-XXX
```

---

## 6. Deployment Sequence

| Week | Phase | Deliverables |
|------|-------|--------------|
| **W1** | Prepare | Generate 900 synthetic variants, validate, train weights, cache embeddings, build observability schema |
| **W2** | Deploy Tier 1 | Ship router + pre-built answer engine, monitor first 100 live routings, validate ≥80% accuracy |
| **W3** | Add Tier 2 | Integrate Claude expansion engine + NLP suggester |
| **W4+** | Feedback Loop | Collect analyst markings, incremental Bayesian updates, monthly re-optimization |

---

## 7. Success Metrics

| Metric | Target | How to Measure |
|--------|--------|-----------------|
| **Router accuracy (holdout)** | ≥82% | % of 256 holdout variants correctly routed |
| **Live routing accuracy** | ≥80% | % of analyst --helpful markings (first 100 routings) |
| **Ensemble agreement rate** | ≥70% | % of routings where T1 & T2 match |
| **Tier 1 latency** | <200ms | P95 latency for pre-built answer lookup |
| **Tier 2 latency** | <5sec | P95 latency for query execution + Claude synthesis |
| **Analyst satisfaction** | ≥85% | % helpful markings / total markings |
| **Feedback loop velocity** | <1hr | Time from marking to weight delta applied |

---

## 8. Out of Scope (Future Work)

- Multi-language support (English only for v1)
- Real-time dashboard of routing decisions (batch weekly reports only)
- Gemini support (abstracted but not wired in v1; Claude only)
- Richer context in Tier 2 (current question + results only; could add conversation history)

---

## 9. Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Synthetic variants are low quality | Router accuracy < 80% | Validate synthetic quality before training (Step 3) |
| Claude embeddings stale | Tier 2 misses updates to Metrics | Re-cache embeddings weekly; monitor embedding drift |
| Feedback loop too slow | Weight updates lag behind live issues | Use incremental updates (not batch); apply delta immediately |
| Ensemble disagreement high | Analyst confused by two suggestions | Set threshold to >90% for "requires clarification" case; document handling |
| Tier 2 latency too high (>5sec) | Analysts don't use --expand | Use cached embeddings; optimize Claude prompt for speed |

---

## 10. Approval & Next Steps

**Design Status:** ✓ Complete  
**User Approval:** [Pending]

**Next:** Once approved, invoke `writing-plans` skill to create detailed implementation plan with specific files, functions, and testing strategy.

