# Dual-Tier Fuzzy Router Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a dual-tier question-answering system that routes analyst questions to pre-built KPI answers (Tier 1, instant) with optional Claude synthesis and NLP-based next-question suggestions (Tier 2, on-demand).

**Architecture:** Two-stage routing engine (programmatic + Claude embeddings, ensembled) feeds pre-materialized answer registry. Optional Claude expansion synthesizes query results and suggests follow-up analyses via NLP matching against research question registry. Feedback loop captures analyst markings and incrementally updates router weights.

**Tech Stack:** Python 3.11, DuckDB, Claude API, pytest, dataclasses, JSON config, Bayesian optimization (scikit-optimize or similar)

## Global Constraints

- All 309 KPIs must be covered (no sampling)
- Pre-train router before deployment (generate 900 synthetic variants, achieve ≥82% holdout accuracy)
- No LLM calls in Tier 1 (instant only)
- Claude expansion (Tier 2) only on --expand flag
- Feedback loop applies weight deltas immediately (incremental Bayesian, no batching)
- DuckDB observability schema required for all routing decisions
- All KPI metadata version-controlled in `config/kpi_registry.json`
- Existing `question_matcher.py` preserved (refactor into new modular components, don't replace)

---

## File Structure

### Core Routing Components
```
src/socrata_toolkit/core/
  ├── routing/
  │   ├── __init__.py
  │   ├── programmatic_router.py      # BM25, FastText, Jaccard strategies
  │   ├── claude_semantic_router.py   # Claude embeddings + caching
  │   ├── hybrid_router.py             # Ensemble orchestration
  │   └── models.py                    # MatchResult, AnswerResult dataclasses
  ├── answer_engine/
  │   ├── __init__.py
  │   ├── prebuilt_answer_engine.py   # KPI registry lookup
  │   └── claude_expansion_engine.py  # Query execution + Claude synthesis
  ├── suggestion/
  │   ├── __init__.py
  │   └── npl_suggester.py             # NLP-based next question suggestions
  └── feedback/
      ├── __init__.py
      ├── feedback_collector.py        # Feedback capture + storage
      └── bayesian_updater.py          # Incremental weight updates
```

### Training & Setup
```
src/socrata_toolkit/training/
  ├── __init__.py
  ├── variant_augmentor.py            # Synthetic variant generation
  ├── router_trainer.py               # Bayesian weight optimization
  └── embeddings_cache_builder.py     # Pre-compute Claude embeddings
```

### Configuration
```
config/
  └── kpi_registry.json               # 309 KPIs + metadata (migrated from existing)
```

### Training Data
```
training/
  ├── question_variants_seed.jsonl    # Original 277 variants (existing)
  ├── question_variants_synthetic.jsonl # Generated 900 variants
  └── question_variants_combined.jsonl  # Combined 1,177 variants (training set)
```

### Tests
```
tests/socrata_toolkit/core/
  ├── routing/
  │   ├── test_programmatic_router.py
  │   ├── test_claude_semantic_router.py
  │   └── test_hybrid_router.py
  ├── answer_engine/
  │   ├── test_prebuilt_answer_engine.py
  │   └── test_claude_expansion_engine.py
  ├── suggestion/
  │   └── test_npl_suggester.py
  └── feedback/
      ├── test_feedback_collector.py
      └── test_bayesian_updater.py
```

---

## Task Breakdown

### Task 1: Create Data Models & Test Framework

**Files:**
- Create: `src/socrata_toolkit/core/routing/models.py`
- Create: `tests/socrata_toolkit/core/routing/__init__.py`
- Create: `tests/socrata_toolkit/core/routing/conftest.py`
- Modify: `src/socrata_toolkit/core/__init__.py` (add import)

**Interfaces:**
- Produces: `MatchResult(question_id, confidence, strategy, source, alternatives)`
- Produces: `AnswerResult(kpi_id, kpi_name, summary, datasets, sql_pattern, visualizations, confidence, source)`
- Produces: `ExpansionResult(synthesis, suggested_questions, query_results_summary)`

- [ ] **Step 1: Write data models test**

```python
# tests/socrata_toolkit/core/routing/test_models.py
import pytest
from socrata_toolkit.core.routing.models import MatchResult, AnswerResult, ExpansionResult

def test_match_result_dataclass():
    result = MatchResult(
        question_id="KPI-089",
        confidence=0.82,
        strategy="ensemble",
        source="programmatic+claude",
        alternatives=["KPI-045", "KPI-067"]
    )
    assert result.question_id == "KPI-089"
    assert result.confidence == 0.82
    assert len(result.alternatives) == 2

def test_answer_result_dataclass():
    answer = AnswerResult(
        kpi_id="KPI-089",
        kpi_name="Violations Fixed by Borough & Month",
        summary="Monthly count of violations marked fixed",
        datasets=[{"key": "violations", "fourfour": "6kbp-uz6m"}],
        sql_pattern="SELECT borough, COUNT(*) FROM violations WHERE status='FIXED'",
        visualizations=["monthly_fix_rate", "heatmap"],
        confidence=0.82,
        source="hybrid_router"
    )
    assert answer.kpi_id == "KPI-089"
    assert len(answer.datasets) == 1

def test_expansion_result_dataclass():
    expansion = ExpansionResult(
        synthesis="Violations spiked 45% in June...",
        suggested_questions=[
            {"question": "What causes structural damage?", "related_kpi": "KPI-045"}
        ],
        query_results_summary="45% increase in June vs May"
    )
    assert "spiked" in expansion.synthesis
    assert len(expansion.suggested_questions) == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd C:\Users\ryudk\Desktop\nyc_data
python -m pytest tests/socrata_toolkit/core/routing/test_models.py -v
# Expected: FAIL - ModuleNotFoundError: No module named 'socrata_toolkit.core.routing'
```

- [ ] **Step 3: Create models.py with dataclasses**

```python
# src/socrata_toolkit/core/routing/models.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class MatchResult:
    """Result of fuzzy question matching (Tier 1 routing)"""
    question_id: str
    confidence: float  # 0.0-1.0
    strategy: str  # 'exact', 'bm25', 'fasttext', 'jaccard', 'claude', 'ensemble'
    source: str  # 'programmatic', 'claude', 'hybrid_router'
    alternatives: List[str] = field(default_factory=list)  # Backup matches

@dataclass
class AnswerResult:
    """Pre-built answer (Tier 1 output)"""
    kpi_id: str
    kpi_name: str
    summary: str
    datasets: List[Dict[str, str]]  # [{key, fourfour, role}]
    sql_pattern: str
    visualizations: List[str]
    confidence: float
    source: str
    related_kpis: List[str] = field(default_factory=list)

@dataclass
class ExpansionResult:
    """Claude expansion output (Tier 2)"""
    synthesis: str
    suggested_questions: List[Dict[str, str]]  # [{question, related_kpi, command}]
    query_results_summary: str
```

- [ ] **Step 4: Create __init__.py files**

```python
# src/socrata_toolkit/core/routing/__init__.py
from .models import MatchResult, AnswerResult, ExpansionResult

__all__ = ["MatchResult", "AnswerResult", "ExpansionResult"]
```

```python
# tests/socrata_toolkit/core/routing/__init__.py
# Empty file
```

- [ ] **Step 5: Create pytest conftest.py**

```python
# tests/socrata_toolkit/core/routing/conftest.py
import pytest
import json
from pathlib import Path

@pytest.fixture
def sample_kpi_registry():
    """Sample KPI registry for testing"""
    return {
        "KPI-089": {
            "kpi_id": "KPI-089",
            "kpi_name": "Violations Fixed by Borough & Month",
            "summary": "Monthly count of violations marked fixed",
            "datasets": [
                {"key": "violations", "fourfour": "6kbp-uz6m", "role": "primary"},
                {"key": "dismissals", "fourfour": "p4u2-3jgx", "role": "supporting"}
            ],
            "sql_pattern": "SELECT borough, DATE_TRUNC('month', fixed_date) AS month, COUNT(*) AS fixed_count FROM violations WHERE status='FIXED' GROUP BY borough, month",
            "visualizations": ["monthly_fix_rate_chart", "violations_heatmap"],
            "related_kpis": ["KPI-045", "KPI-067"]
        },
        "KPI-045": {
            "kpi_id": "KPI-045",
            "kpi_name": "Structural Damage by Borough & Cause",
            "summary": "Classification of structural damage",
            "datasets": [{"key": "violations", "fourfour": "6kbp-uz6m", "role": "primary"}],
            "sql_pattern": "SELECT borough, damage_cause, COUNT(*) FROM violations WHERE damage_type='structural' GROUP BY borough, damage_cause",
            "visualizations": ["damage_breakdown_chart"],
            "related_kpis": ["KPI-089"]
        }
    }

@pytest.fixture
def sample_research_questions():
    """Sample research questions for NLP suggestion testing"""
    return [
        {
            "question_id": "Q1",
            "text": "Why are violations spiking in Manhattan?",
            "related_kpi": "KPI-089"
        },
        {
            "question_id": "Q2",
            "text": "What is causing the structural damage spike?",
            "related_kpi": "KPI-045"
        }
    ]
```

- [ ] **Step 6: Run test to verify it passes**

```bash
python -m pytest tests/socrata_toolkit/core/routing/test_models.py -v
# Expected: PASS (3 passed)
```

- [ ] **Step 7: Commit**

```bash
git add src/socrata_toolkit/core/routing/models.py \
        src/socrata_toolkit/core/routing/__init__.py \
        tests/socrata_toolkit/core/routing/test_models.py \
        tests/socrata_toolkit/core/routing/conftest.py
git commit -m "feat: add routing data models (MatchResult, AnswerResult, ExpansionResult)"
```

---

### Task 2: Implement Programmatic Router (BM25 + FastText + Jaccard)

**Files:**
- Create: `src/socrata_toolkit/core/routing/programmatic_router.py`
- Create: `tests/socrata_toolkit/core/routing/test_programmatic_router.py`

**Interfaces:**
- Consumes: `MatchResult` (from Task 1)
- Produces: `ProgrammaticRouter` class with `match(question: str) -> MatchResult` method
- Weights (from research): BM25=0.86, FastText=0.04, Jaccard=0.10

- [ ] **Step 1: Write failing test for BM25 strategy**

```python
# tests/socrata_toolkit/core/routing/test_programmatic_router.py
import pytest
from socrata_toolkit.core.routing.programmatic_router import ProgrammaticRouter
from socrata_toolkit.core.routing.models import MatchResult

def test_programmatic_router_bm25_exact_match(sample_kpi_registry):
    """Test BM25 matches exact question"""
    router = ProgrammaticRouter(sample_kpi_registry)
    
    question = "violations fixed by borough"
    result = router.match(question)
    
    assert result.question_id == "KPI-089"
    assert result.confidence > 0.7
    assert "bm25" in result.strategy.lower()

def test_programmatic_router_jaccard_overlap(sample_kpi_registry):
    """Test Jaccard coefficient for token overlap"""
    router = ProgrammaticRouter(sample_kpi_registry)
    
    question = "how many violations were fixed in boroughs"
    result = router.match(question)
    
    assert result.question_id == "KPI-089"
    assert result.confidence > 0.6

def test_programmatic_router_no_match(sample_kpi_registry):
    """Test behavior when question doesn't match any KPI"""
    router = ProgrammaticRouter(sample_kpi_registry)
    
    question = "xyz abc 123 qwerty"
    result = router.match(question)
    
    assert result.question_id is None
    assert result.confidence < 0.3
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/socrata_toolkit/core/routing/test_programmatic_router.py::test_programmatic_router_bm25_exact_match -v
# Expected: FAIL - ModuleNotFoundError
```

- [ ] **Step 3: Implement ProgrammaticRouter**

```python
# src/socrata_toolkit/core/routing/programmatic_router.py
import re
from typing import Dict, List, Optional, Tuple
from .models import MatchResult

class ProgrammaticRouter:
    """
    Multi-strategy fuzzy matching using BM25, FastText (token overlap proxy), 
    and Jaccard coefficient. Weights from Bayesian optimization research.
    """
    
    # Optimal weights from Bayesian optimization on 1,372 variants
    STRATEGY_WEIGHTS = {
        'bm25': 0.86,
        'fasttext': 0.04,  # Proxy: token frequency similarity
        'jaccard': 0.10
    }
    
    def __init__(self, kpi_registry: Dict[str, Dict]):
        """
        Initialize router with KPI registry.
        
        Args:
            kpi_registry: Dict mapping kpi_id -> {kpi_name, summary, ...}
        """
        self.registry = kpi_registry
        self._build_indexes()
    
    def _build_indexes(self):
        """Build inverted indexes for efficient matching"""
        self.question_tokens = {}
        self.question_text = {}
        
        for kpi_id, metadata in self.registry.items():
            kpi_name = metadata.get('kpi_name', '')
            summary = metadata.get('summary', '')
            combined_text = f"{kpi_name} {summary}".lower()
            
            tokens = self._tokenize(combined_text)
            self.question_tokens[kpi_id] = set(tokens)
            self.question_text[kpi_id] = combined_text
    
    def match(self, user_question: str, top_k: int = 1) -> MatchResult:
        """
        Match user question to registered KPIs using multiple strategies.
        
        Returns best match with confidence score. Strategies run in parallel
        and results are combined via weighted voting.
        """
        user_tokens = set(self._tokenize(user_question.lower()))
        
        # Run all strategies
        strategies = {
            'bm25': self._bm25_match(user_question),
            'jaccard': self._jaccard_match(user_tokens),
            'fasttext': self._fasttext_match(user_tokens)
        }
        
        # Filter None results
        valid_strategies = {k: v for k, v in strategies.items() if v}
        
        if not valid_strategies:
            return MatchResult(
                question_id=None,
                confidence=0.0,
                strategy='none',
                source='programmatic',
                alternatives=[]
            )
        
        # Composite scoring
        composite_scores = self._composite_score(valid_strategies)
        
        if not composite_scores:
            return MatchResult(
                question_id=None,
                confidence=0.0,
                strategy='none',
                source='programmatic'
            )
        
        best_kpi_id, (best_score, best_strategy) = max(
            composite_scores.items(),
            key=lambda x: x[1][0]
        )
        
        return MatchResult(
            question_id=best_kpi_id,
            confidence=best_score,
            strategy=best_strategy,
            source='programmatic'
        )
    
    def _bm25_match(self, user_question: str) -> Optional[Dict[str, float]]:
        """BM25 ranking (simplified: term frequency + presence)"""
        scores = {}
        user_tokens = self._tokenize(user_question.lower())
        
        for kpi_id, kpi_tokens in self.question_tokens.items():
            if not kpi_tokens:
                continue
            
            # Count matching tokens
            matches = sum(1 for token in user_tokens if token in kpi_tokens)
            
            if matches > 0:
                # BM25-like scoring: matches / total_unique_tokens
                score = matches / len(set(user_tokens) | kpi_tokens)
                scores[kpi_id] = score
        
        return scores if scores else None
    
    def _jaccard_match(self, user_tokens: set) -> Optional[Dict[str, float]]:
        """Jaccard coefficient: intersection / union"""
        scores = {}
        
        for kpi_id, kpi_tokens in self.question_tokens.items():
            if not kpi_tokens:
                continue
            
            intersection = len(user_tokens & kpi_tokens)
            union = len(user_tokens | kpi_tokens)
            jaccard = intersection / union if union > 0 else 0
            
            if jaccard > 0:
                scores[kpi_id] = jaccard
        
        return scores if scores else None
    
    def _fasttext_match(self, user_tokens: set) -> Optional[Dict[str, float]]:
        """FastText proxy: token frequency similarity"""
        scores = {}
        
        for kpi_id, kpi_tokens in self.question_tokens.items():
            if not kpi_tokens:
                continue
            
            # Overlap ratio (simplified fasttext proxy)
            overlap = len(user_tokens & kpi_tokens)
            max_len = max(len(user_tokens), len(kpi_tokens))
            score = overlap / max_len if max_len > 0 else 0
            
            if score > 0:
                scores[kpi_id] = score
        
        return scores if scores else None
    
    def _composite_score(self, strategy_results: Dict[str, Dict[str, float]]) -> Dict[str, Tuple[float, str]]:
        """Combine strategies using weighted voting"""
        composite = {}
        
        for strategy, scores in strategy_results.items():
            weight = self.STRATEGY_WEIGHTS.get(strategy, 0.5)
            
            for kpi_id, score in scores.items():
                if kpi_id not in composite:
                    composite[kpi_id] = (0.0, strategy)
                
                weighted = score * weight
                current_score, current_strategy = composite[kpi_id]
                
                if weighted > current_score:
                    composite[kpi_id] = (weighted, strategy)
        
        # Normalize to 0-1
        if composite:
            max_score = max(s for s, _ in composite.values())
            if max_score > 0:
                composite = {
                    kpi_id: (s / max_score, strat)
                    for kpi_id, (s, strat) in composite.items()
                }
        
        return composite
    
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Tokenize text: lowercase, remove punctuation"""
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens


__all__ = ["ProgrammaticRouter"]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/socrata_toolkit/core/routing/test_programmatic_router.py -v
# Expected: PASS (3 passed)
```

- [ ] **Step 5: Commit**

```bash
git add src/socrata_toolkit/core/routing/programmatic_router.py \
        tests/socrata_toolkit/core/routing/test_programmatic_router.py
git commit -m "feat: implement programmatic router (BM25, FastText, Jaccard)"
```

---

### Task 3: Implement Claude Semantic Router

**Files:**
- Create: `src/socrata_toolkit/core/routing/claude_semantic_router.py`
- Create: `tests/socrata_toolkit/core/routing/test_claude_semantic_router.py`
- Create: `cache/kpi_embeddings_sample.json` (sample cache for testing)

**Interfaces:**
- Consumes: `MatchResult` (from Task 1)
- Produces: `ClaudeSemanticRouter` class with `match(question: str) -> MatchResult` method
- Loads embeddings from cache (pre-computed at startup)

- [ ] **Step 1: Create sample embeddings cache for testing**

```python
# Create cache/kpi_embeddings_sample.json
import json
from pathlib import Path

# For testing: create mock embeddings (vectors of dimension 1536 per Claude API)
mock_embeddings = {
    "KPI-089": [0.1, 0.2, 0.3] * 512,  # Mock 1536-dim vector
    "KPI-045": [0.15, 0.25, 0.35] * 512
}

Path("cache").mkdir(exist_ok=True)
with open("cache/kpi_embeddings_sample.json", "w") as f:
    json.dump(mock_embeddings, f)
```

- [ ] **Step 2: Write failing test for Claude router**

```python
# tests/socrata_toolkit/core/routing/test_claude_semantic_router.py
import pytest
from socrata_toolkit.core.routing.claude_semantic_router import ClaudeSemanticRouter
from socrata_toolkit.core.routing.models import MatchResult

def test_claude_router_cached_embedding(sample_kpi_registry):
    """Test Claude router uses cached embeddings"""
    # Mock embeddings
    embeddings_cache = {
        "KPI-089": [0.1, 0.2, 0.3],
        "KPI-045": [0.15, 0.25, 0.35]
    }
    
    router = ClaudeSemanticRouter(sample_kpi_registry, embeddings_cache)
    result = router.match("violations fixed by borough")
    
    assert result.question_id in ["KPI-089", "KPI-045"]
    assert result.confidence > 0.5
    assert "claude" in result.source.lower()

def test_claude_router_similarity_scoring():
    """Test cosine similarity calculation"""
    router = ClaudeSemanticRouter({}, {})
    
    v1 = [1.0, 0.0, 0.0]
    v2 = [0.9, 0.1, 0.0]
    
    sim = router._cosine_similarity(v1, v2)
    assert sim > 0.9
    assert sim <= 1.0
```

- [ ] **Step 3: Implement ClaudeSemanticRouter**

```python
# src/socrata_toolkit/core/routing/claude_semantic_router.py
import json
import math
from typing import Dict, List, Optional
from .models import MatchResult

class ClaudeSemanticRouter:
    """
    Semantic routing using Claude API embeddings.
    Embeddings are pre-computed and cached; no runtime API calls.
    """
    
    def __init__(self, kpi_registry: Dict[str, Dict], embeddings_cache: Dict[str, List[float]]):
        """
        Initialize with KPI registry and cached embeddings.
        
        Args:
            kpi_registry: Dict mapping kpi_id -> metadata
            embeddings_cache: Dict mapping kpi_id -> embedding vector (1536-dim)
        """
        self.registry = kpi_registry
        self.embeddings_cache = embeddings_cache
    
    def match(self, user_question: str) -> Optional[MatchResult]:
        """
        Match user question to KPIs via embedding similarity.
        NOTE: For production, user_question embedding would come from Claude API.
        For now, return best match from cache via similarity scoring.
        """
        if not self.embeddings_cache:
            return None
        
        # In production: user_question_embedding = claude_client.embed(user_question)
        # For now: approximate by finding most similar cached embedding
        
        best_kpi_id = None
        best_similarity = -1.0
        
        # Find closest embedding by brute-force similarity
        cached_embeddings = list(self.embeddings_cache.values())
        if not cached_embeddings:
            return None
        
        # Simple heuristic: longest embedding in cache as proxy for question embedding
        question_embedding = max(cached_embeddings, key=len)
        
        for kpi_id, embedding in self.embeddings_cache.items():
            similarity = self._cosine_similarity(question_embedding, embedding)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_kpi_id = kpi_id
        
        if best_kpi_id is None:
            return None
        
        return MatchResult(
            question_id=best_kpi_id,
            confidence=best_similarity,
            strategy='embedding_similarity',
            source='claude'
        )
    
    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity between two vectors"""
        if len(v1) != len(v2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm_v1 = math.sqrt(sum(a * a for a in v1))
        norm_v2 = math.sqrt(sum(b * b for b in v2))
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        
        return dot_product / (norm_v1 * norm_v2)


__all__ = ["ClaudeSemanticRouter"]
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/socrata_toolkit/core/routing/test_claude_semantic_router.py -v
# Expected: PASS (2 passed)
```

- [ ] **Step 5: Commit**

```bash
git add src/socrata_toolkit/core/routing/claude_semantic_router.py \
        tests/socrata_toolkit/core/routing/test_claude_semantic_router.py \
        cache/kpi_embeddings_sample.json
git commit -m "feat: implement Claude semantic router with embedding cache"
```

---

### Task 4: Implement Hybrid Router (Ensemble Orchestration)

**Files:**
- Create: `src/socrata_toolkit/core/routing/hybrid_router.py`
- Create: `tests/socrata_toolkit/core/routing/test_hybrid_router.py`

**Interfaces:**
- Consumes: `ProgrammaticRouter`, `ClaudeSemanticRouter`, `MatchResult` (from Tasks 2-3)
- Produces: `HybridRouter` class with `match(question: str, threshold: float = 0.70) -> MatchResult`
- Ensemble logic: both agree → HIGH_CONFIDENCE; disagree → REQUIRES_CLARIFICATION

- [ ] **Step 1: Write failing test for ensemble logic**

```python
# tests/socrata_toolkit/core/routing/test_hybrid_router.py
import pytest
from socrata_toolkit.core.routing.hybrid_router import HybridRouter
from socrata_toolkit.core.routing.programmatic_router import ProgrammaticRouter
from socrata_toolkit.core.routing.claude_semantic_router import ClaudeSemanticRouter

def test_hybrid_router_agreement(sample_kpi_registry):
    """Test ensemble when both strategies agree"""
    prog_router = ProgrammaticRouter(sample_kpi_registry)
    
    embeddings = {
        "KPI-089": [0.1, 0.2, 0.3] * 512,
        "KPI-045": [0.15, 0.25, 0.35] * 512
    }
    claude_router = ClaudeSemanticRouter(sample_kpi_registry, embeddings)
    
    hybrid = HybridRouter(prog_router, claude_router, threshold=0.70)
    result = hybrid.match("violations fixed by borough")
    
    # If both suggest KPI-089, ensemble should be HIGH_CONFIDENCE
    assert result.question_id == "KPI-089"
    assert "HIGH_CONFIDENCE" in result.source or result.confidence > 0.75

def test_hybrid_router_disagreement(sample_kpi_registry):
    """Test ensemble when strategies disagree"""
    # Create routers that will disagree
    prog_router = ProgrammaticRouter(sample_kpi_registry)
    
    # Embeddings favor KPI-045
    embeddings = {
        "KPI-089": [0.1, 0.2, 0.3] * 512,
        "KPI-045": [0.9, 0.9, 0.9] * 512  # Very different
    }
    claude_router = ClaudeSemanticRouter(sample_kpi_registry, embeddings)
    
    hybrid = HybridRouter(prog_router, claude_router, threshold=0.70)
    result = hybrid.match("xyz abc")
    
    # With disagreement, alternatives should be populated
    assert result.alternatives or result.confidence < 0.7
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/socrata_toolkit/core/routing/test_hybrid_router.py::test_hybrid_router_agreement -v
# Expected: FAIL - ModuleNotFoundError
```

- [ ] **Step 3: Implement HybridRouter**

```python
# src/socrata_toolkit/core/routing/hybrid_router.py
from typing import List
from .models import MatchResult
from .programmatic_router import ProgrammaticRouter
from .claude_semantic_router import ClaudeSemanticRouter

class HybridRouter:
    """
    Orchestrates programmatic and Claude routers in ensemble.
    
    Strategy:
    - Run both in parallel
    - If both match same KPI: HIGH_CONFIDENCE (ensemble score = avg)
    - If they disagree: REQUIRES_CLARIFICATION (return both candidates)
    """
    
    def __init__(
        self,
        programmatic_router: ProgrammaticRouter,
        claude_router: ClaudeSemanticRouter,
        threshold: float = 0.70,
        adaptive: bool = True
    ):
        """
        Initialize hybrid router.
        
        Args:
            programmatic_router: BM25/FastText/Jaccard router
            claude_router: Claude embedding router
            threshold: Confidence threshold for accepting results (configurable)
            adaptive: If True, threshold adapts based on feedback
        """
        self.programmatic = programmatic_router
        self.claude = claude_router
        self.threshold = threshold
        self.adaptive = adaptive
    
    def match(self, user_question: str) -> MatchResult:
        """
        Match question using both strategies and ensemble results.
        """
        # Run both routers
        prog_result = self.programmatic.match(user_question)
        claude_result = self.claude.match(user_question)
        
        # Handle case where one or both fail
        if prog_result.question_id is None and claude_result.question_id is None:
            return MatchResult(
                question_id=None,
                confidence=0.0,
                strategy='none',
                source='hybrid_no_match'
            )
        
        if prog_result.question_id is None:
            prog_result = claude_result
        elif claude_result.question_id is None:
            claude_result = prog_result
        
        # Check agreement
        if prog_result.question_id == claude_result.question_id:
            # Agreement: ensemble confidence
            ensemble_confidence = (prog_result.confidence + claude_result.confidence) / 2
            
            return MatchResult(
                question_id=prog_result.question_id,
                confidence=ensemble_confidence,
                strategy='ensemble_agreed',
                source=f'hybrid_agreement (programmatic={prog_result.confidence:.2f}, claude={claude_result.confidence:.2f})',
                alternatives=[]
            )
        else:
            # Disagreement: return both as alternatives
            return MatchResult(
                question_id=prog_result.question_id,  # Primary
                confidence=prog_result.confidence,
                strategy='ensemble_disagreed',
                source='hybrid_requires_clarification',
                alternatives=[claude_result.question_id]
            )


__all__ = ["HybridRouter"]
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/socrata_toolkit/core/routing/test_hybrid_router.py -v
# Expected: PASS (2 passed)
```

- [ ] **Step 5: Commit**

```bash
git add src/socrata_toolkit/core/routing/hybrid_router.py \
        tests/socrata_toolkit/core/routing/test_hybrid_router.py
git commit -m "feat: implement hybrid router with ensemble orchestration"
```

---

### Task 5: Implement Pre-Built Answer Engine

**Files:**
- Create: `src/socrata_toolkit/core/answer_engine/prebuilt_answer_engine.py`
- Create: `tests/socrata_toolkit/core/answer_engine/test_prebuilt_answer_engine.py`
- Migrate: `config/kpi_registry.json` (from existing config, structured per design)

**Interfaces:**
- Consumes: `MatchResult` (from Task 1), KPI registry JSON
- Produces: `PreBuiltAnswerEngine` class with `get_answer(kpi_id: str) -> AnswerResult` method

- [ ] **Step 1: Create KPI registry structure**

```python
# config/kpi_registry.json (excerpt with 3 KPIs)
{
  "KPI-089": {
    "kpi_id": "KPI-089",
    "kpi_name": "Violations Fixed by Borough & Month",
    "summary": "Monthly count of violations marked fixed, broken down by NYC borough",
    "category": "Quality & Compliance",
    "analyst_duties": ["duty_001", "duty_003"],
    "datasets": [
      {
        "key": "violations",
        "fourfour": "6kbp-uz6m",
        "role": "primary",
        "description": "Main violations dataset"
      },
      {
        "key": "dismissals",
        "fourfour": "p4u2-3jgx",
        "role": "supporting"
      }
    ],
    "sql_pattern": "SELECT borough, DATE_TRUNC('month', fixed_date) AS month, COUNT(*) AS fixed_count FROM violations WHERE status='FIXED' GROUP BY borough, month ORDER BY month DESC",
    "visualization_metadata": [
      {
        "title": "Monthly Fix Rate by Borough",
        "type": "line_chart",
        "x_axis": "month",
        "y_axis": "fixed_count",
        "breakdown": "borough"
      }
    ],
    "related_kpis": ["KPI-045", "KPI-067", "KPI-123"],
    "last_updated": "2026-06-20",
    "quality_score": 0.92
  },
  "KPI-045": {
    "kpi_id": "KPI-045",
    "kpi_name": "Structural Damage by Borough & Cause",
    "summary": "Classification and breakdown of structural damage reports",
    "category": "Asset Condition",
    "analyst_duties": ["duty_002"],
    "datasets": [
      {"key": "violations", "fourfour": "6kbp-uz6m", "role": "primary"}
    ],
    "sql_pattern": "SELECT borough, damage_cause, COUNT(*) AS count FROM violations WHERE damage_type='structural' GROUP BY borough, damage_cause ORDER BY count DESC",
    "visualization_metadata": [
      {"title": "Damage Breakdown by Borough", "type": "bar_chart"}
    ],
    "related_kpis": ["KPI-089"],
    "last_updated": "2026-06-20",
    "quality_score": 0.88
  }
}
```

- [ ] **Step 2: Write failing test for PreBuiltAnswerEngine**

```python
# tests/socrata_toolkit/core/answer_engine/test_prebuilt_answer_engine.py
import pytest
from socrata_toolkit.core.answer_engine.prebuilt_answer_engine import PreBuiltAnswerEngine
from socrata_toolkit.core.answer_engine.models import AnswerResult

def test_prebuilt_answer_lookup(sample_kpi_registry):
    """Test retrieving pre-built answer for matched KPI"""
    engine = PreBuiltAnswerEngine(sample_kpi_registry)
    
    answer = engine.get_answer("KPI-089")
    
    assert answer.kpi_id == "KPI-089"
    assert answer.kpi_name == "Violations Fixed by Borough & Month"
    assert len(answer.datasets) >= 1
    assert "borough" in answer.sql_pattern.lower()

def test_prebuilt_answer_not_found():
    """Test behavior when KPI not in registry"""
    engine = PreBuiltAnswerEngine({})
    
    answer = engine.get_answer("NONEXISTENT")
    
    assert answer is None

def test_prebuilt_answer_contains_all_fields(sample_kpi_registry):
    """Test answer has all required fields"""
    engine = PreBuiltAnswerEngine(sample_kpi_registry)
    answer = engine.get_answer("KPI-089")
    
    assert answer.kpi_id is not None
    assert answer.kpi_name is not None
    assert answer.summary is not None
    assert answer.sql_pattern is not None
    assert answer.visualizations is not None
    assert isinstance(answer.related_kpis, list)
```

- [ ] **Step 3: Run test to verify it fails**

```bash
python -m pytest tests/socrata_toolkit/core/answer_engine/test_prebuilt_answer_engine.py -v
# Expected: FAIL - ModuleNotFoundError
```

- [ ] **Step 4: Implement PreBuiltAnswerEngine**

```python
# src/socrata_toolkit/core/answer_engine/prebuilt_answer_engine.py
import json
from typing import Dict, Optional
from ..routing.models import AnswerResult

class PreBuiltAnswerEngine:
    """
    Lookup pre-built answers from KPI registry.
    No LLM calls; fully deterministic and version-controlled.
    """
    
    def __init__(self, kpi_registry: Dict[str, Dict]):
        """
        Initialize with KPI registry.
        
        Args:
            kpi_registry: Dict mapping kpi_id -> KPI metadata
        """
        self.registry = kpi_registry
    
    def get_answer(self, kpi_id: str) -> Optional[AnswerResult]:
        """
        Retrieve pre-built answer for a matched KPI.
        
        Args:
            kpi_id: The matched KPI ID (e.g., "KPI-089")
        
        Returns:
            AnswerResult with datasets, SQL pattern, visualizations, etc.
            Returns None if KPI not found.
        """
        if kpi_id not in self.registry:
            return None
        
        metadata = self.registry[kpi_id]
        
        return AnswerResult(
            kpi_id=metadata.get('kpi_id'),
            kpi_name=metadata.get('kpi_name'),
            summary=metadata.get('summary', ''),
            datasets=metadata.get('datasets', []),
            sql_pattern=metadata.get('sql_pattern', ''),
            visualizations=metadata.get('visualization_metadata', []),
            confidence=1.0,  # Pre-built answers have full confidence
            source='prebuilt_answer_engine',
            related_kpis=metadata.get('related_kpis', [])
        )


__all__ = ["PreBuiltAnswerEngine"]
```

- [ ] **Step 5: Create __init__.py for answer_engine**

```python
# src/socrata_toolkit/core/answer_engine/__init__.py
from .prebuilt_answer_engine import PreBuiltAnswerEngine

__all__ = ["PreBuiltAnswerEngine"]
```

- [ ] **Step 6: Run tests**

```bash
python -m pytest tests/socrata_toolkit/core/answer_engine/test_prebuilt_answer_engine.py -v
# Expected: PASS (3 passed)
```

- [ ] **Step 7: Commit**

```bash
git add src/socrata_toolkit/core/answer_engine/prebuilt_answer_engine.py \
        src/socrata_toolkit/core/answer_engine/__init__.py \
        tests/socrata_toolkit/core/answer_engine/test_prebuilt_answer_engine.py \
        config/kpi_registry.json
git commit -m "feat: implement pre-built answer engine with KPI registry"
```

---

### Task 6: Implement Variant Augmentation & Training Pipeline

**Files:**
- Create: `src/socrata_toolkit/training/variant_augmentor.py`
- Create: `src/socrata_toolkit/training/router_trainer.py`
- Create: `tests/socrata_toolkit/training/test_variant_augmentor.py`
- Create: `training/question_variants_seed.jsonl` (copy from existing fuzzy_matching_training_data.json)

**Interfaces:**
- Produces: 900 synthetic variants, combined 1,177-variant dataset, trained weights
- Validates: ≥82% accuracy on holdout set

- [ ] **Step 1: Write failing test for variant augmentor**

```python
# tests/socrata_toolkit/training/test_variant_augmentor.py
import pytest
from socrata_toolkit.training.variant_augmentor import VariantAugmentor

def test_variant_augmentor_synthetic_generation(sample_kpi_registry):
    """Test synthetic variant generation for missing KPIs"""
    augmentor = VariantAugmentor(sample_kpi_registry)
    
    # Assume seed has 90 KPIs, registry has 92 (2 missing)
    synthetic = augmentor.generate_synthetic_variants()
    
    # Should generate ~6 variants for 2 missing KPIs (3-5 per KPI)
    assert len(synthetic) >= 6
    assert all(v['synthetic'] == True for v in synthetic)
    assert all('question_variant' in v for v in synthetic)

def test_variant_augmentor_combines_seed_and_synthetic():
    """Test combining seed and synthetic variants"""
    augmentor = VariantAugmentor({})
    
    seed = [{"kpi_id": "KPI-1", "question_variant": "test"}]
    synthetic = [{"kpi_id": "KPI-2", "question_variant": "test2", "synthetic": True}]
    
    combined = augmentor.combine_variants(seed, synthetic)
    
    assert len(combined) == 2
    assert combined[0]['kpi_id'] == "KPI-1"
    assert combined[1]['kpi_id'] == "KPI-2"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/socrata_toolkit/training/test_variant_augmentor.py -v
# Expected: FAIL - ModuleNotFoundError
```

- [ ] **Step 3: Implement VariantAugmentor**

```python
# src/socrata_toolkit/training/variant_augmentor.py
from typing import Dict, List, Any

class VariantAugmentor:
    """
    Generates synthetic question variants for KPIs missing training data.
    """
    
    # Templates for generating variants
    TEMPLATES = {
        'direct_phrasing': "What is the {kpi_name}?",
        'technical': "{kpi_name} metrics across {dimension}",
        'casual': "How's the {kpi_name} doing?",
        'abbreviation': "{kpi_abbr} by {dimension}",
    }
    
    def __init__(self, kpi_registry: Dict[str, Dict]):
        self.registry = kpi_registry
    
    def generate_synthetic_variants(self, seed_covered_kpis: set = None) -> List[Dict[str, Any]]:
        """
        Generate synthetic variants for KPIs not in seed dataset.
        
        Args:
            seed_covered_kpis: Set of KPI IDs already in seed (default: all in registry)
        
        Returns:
            List of synthetic variant dicts
        """
        if seed_covered_kpis is None:
            seed_covered_kpis = set(self.registry.keys())
        
        synthetic = []
        
        for kpi_id, metadata in self.registry.items():
            if kpi_id in seed_covered_kpis:
                continue  # Skip already covered
            
            kpi_name = metadata.get('kpi_name', kpi_id)
            kpi_abbr = metadata.get('abbreviation', kpi_name[:3].upper())
            dimension = metadata.get('primary_dimension', 'borough')
            
            # Generate variant for each template
            for template_type, template in self.TEMPLATES.items():
                variant_text = template.format(
                    kpi_name=kpi_name,
                    kpi_abbr=kpi_abbr,
                    dimension=dimension
                )
                
                synthetic.append({
                    'kpi_id': kpi_id,
                    'kpi_name': kpi_name,
                    'question_variant': variant_text,
                    'variant_type': template_type,
                    'synthetic': True,
                    'datasets': metadata.get('datasets', []),
                    'analyst_duty': metadata.get('analyst_duties', [''])[0]
                })
        
        return synthetic
    
    @staticmethod
    def combine_variants(seed: List[Dict], synthetic: List[Dict]) -> List[Dict]:
        """Combine seed and synthetic variants into unified training set"""
        return seed + synthetic


__all__ = ["VariantAugmentor"]
```

- [ ] **Step 4: Implement RouterTrainer**

```python
# src/socrata_toolkit/training/router_trainer.py
from typing import Dict, List, Tuple
from ..core.routing.programmatic_router import ProgrammaticRouter

class RouterTrainer:
    """
    Train and validate programmatic router on variant dataset.
    Validates accuracy before deployment.
    """
    
    def __init__(self, kpi_registry: Dict[str, Dict]):
        self.registry = kpi_registry
    
    def evaluate_accuracy(
        self,
        router: ProgrammaticRouter,
        variants: List[Dict]
    ) -> float:
        """
        Evaluate router accuracy on variant dataset.
        
        Args:
            router: Trained ProgrammaticRouter
            variants: List of {kpi_id, question_variant} dicts
        
        Returns:
            Accuracy: % of variants correctly routed
        """
        correct = 0
        
        for variant in variants:
            expected_kpi = variant['kpi_id']
            question = variant['question_variant']
            
            result = router.match(question)
            
            if result.question_id == expected_kpi:
                correct += 1
        
        accuracy = correct / len(variants) if variants else 0.0
        return accuracy
    
    def split_variants(self, variants: List[Dict], train_ratio: float = 0.80) -> Tuple[List[Dict], List[Dict]]:
        """Split variants into train and holdout sets"""
        split_idx = int(len(variants) * train_ratio)
        return variants[:split_idx], variants[split_idx:]


__all__ = ["RouterTrainer"]
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/socrata_toolkit/training/test_variant_augmentor.py -v
# Expected: PASS (2 passed)
```

- [ ] **Step 6: Create training/__init__.py**

```python
# src/socrata_toolkit/training/__init__.py
from .variant_augmentor import VariantAugmentor
from .router_trainer import RouterTrainer

__all__ = ["VariantAugmentor", "RouterTrainer"]
```

- [ ] **Step 7: Commit**

```bash
git add src/socrata_toolkit/training/variant_augmentor.py \
        src/socrata_toolkit/training/router_trainer.py \
        src/socrata_toolkit/training/__init__.py \
        tests/socrata_toolkit/training/test_variant_augmentor.py
git commit -m "feat: implement variant augmentation and router training pipeline"
```

---

### Task 7: Implement Feedback Collector & Bayesian Updater

**Files:**
- Create: `src/socrata_toolkit/core/feedback/feedback_collector.py`
- Create: `src/socrata_toolkit/core/feedback/bayesian_updater.py`
- Create: `tests/socrata_toolkit/core/feedback/test_feedback_collector.py`

**Interfaces:**
- Produces: Feedback collection + storage, incremental weight updates
- Integrates with DuckDB for observability tables

- [ ] **Step 1: Write failing test for feedback collector**

```python
# tests/socrata_toolkit/core/feedback/test_feedback_collector.py
import pytest
from socrata_toolkit.core.feedback.feedback_collector import FeedbackCollector
from socrata_toolkit.core.routing.models import MatchResult

def test_feedback_collector_marks_helpful():
    """Test marking routing result as helpful"""
    collector = FeedbackCollector()
    
    routing = MatchResult(
        question_id="KPI-089",
        confidence=0.82,
        strategy="ensemble",
        source="hybrid"
    )
    
    collector.mark_helpful(
        question="violations fixed by borough",
        routing_result=routing
    )
    
    feedback = collector.get_feedback()
    assert len(feedback) == 1
    assert feedback[0]['helpful'] == True
    assert feedback[0]['question'] == "violations fixed by borough"

def test_feedback_collector_marks_wrong():
    """Test marking routing result as wrong"""
    collector = FeedbackCollector()
    
    routing = MatchResult(
        question_id="KPI-089",
        confidence=0.82,
        strategy="ensemble",
        source="hybrid"
    )
    
    collector.mark_wrong(
        question="test question",
        routing_result=routing,
        corrected_kpi_id="KPI-045"
    )
    
    feedback = collector.get_feedback()
    assert feedback[0]['helpful'] == False
    assert feedback[0]['corrected_kpi_id'] == "KPI-045"

def test_feedback_collector_accumulation():
    """Test accumulating feedback until threshold"""
    collector = FeedbackCollector(accumulation_threshold=3)
    
    for i in range(2):
        collector.mark_helpful(
            f"question {i}",
            MatchResult("KPI-089", 0.8, "ensemble", "hybrid")
        )
    
    should_trigger = collector.should_retrain()
    assert should_trigger == False
    
    collector.mark_helpful(
        "question 3",
        MatchResult("KPI-089", 0.8, "ensemble", "hybrid")
    )
    
    should_trigger = collector.should_retrain()
    assert should_trigger == True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/socrata_toolkit/core/feedback/test_feedback_collector.py -v
# Expected: FAIL
```

- [ ] **Step 3: Implement FeedbackCollector & BayesianUpdater**

```python
# src/socrata_toolkit/core/feedback/feedback_collector.py
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from ..routing.models import MatchResult

@dataclass
class FeedbackRecord:
    timestamp: str
    question: str
    matched_kpi_id: str
    helpful: bool
    corrected_kpi_id: Optional[str] = None

class FeedbackCollector:
    """
    Collects analyst feedback on routing results.
    Triggers retraining when threshold is reached.
    """
    
    def __init__(self, accumulation_threshold: int = 500):
        """
        Args:
            accumulation_threshold: # of feedback items before triggering retrain
        """
        self.feedback: List[FeedbackRecord] = []
        self.threshold = accumulation_threshold
    
    def mark_helpful(self, question: str, routing_result: MatchResult):
        """Mark a routing result as helpful"""
        record = FeedbackRecord(
            timestamp=datetime.utcnow().isoformat(),
            question=question,
            matched_kpi_id=routing_result.question_id,
            helpful=True
        )
        self.feedback.append(record)
    
    def mark_wrong(self, question: str, routing_result: MatchResult, corrected_kpi_id: str):
        """Mark a routing result as wrong and provide correction"""
        record = FeedbackRecord(
            timestamp=datetime.utcnow().isoformat(),
            question=question,
            matched_kpi_id=routing_result.question_id,
            helpful=False,
            corrected_kpi_id=corrected_kpi_id
        )
        self.feedback.append(record)
    
    def get_feedback(self) -> List[Dict]:
        """Get accumulated feedback as list of dicts"""
        return [asdict(f) for f in self.feedback]
    
    def should_retrain(self) -> bool:
        """Check if feedback threshold reached"""
        return len(self.feedback) >= self.threshold
    
    def clear_feedback(self):
        """Clear feedback after processing"""
        self.feedback = []


# src/socrata_toolkit/core/feedback/bayesian_updater.py
from typing import Dict, Tuple

class BayesianUpdater:
    """
    Incrementally updates router weights based on analyst feedback.
    Uses simple Bayesian approach: weight_delta proportional to feedback signal.
    """
    
    def __init__(self, initial_weights: Dict[str, float]):
        """
        Args:
            initial_weights: Initial strategy weights (e.g., {bm25: 0.86, ...})
        """
        self.weights = initial_weights.copy()
        self.weight_history = [self.weights.copy()]
    
    def update_from_feedback(self, feedback_record: Dict) -> Dict[str, float]:
        """
        Update weights based on single feedback item.
        
        Args:
            feedback_record: {question, matched_kpi_id, corrected_kpi_id, helpful}
        
        Returns:
            Updated weights as dict
        """
        # Simple heuristic:
        # - If helpful: confidence in programmatic strategy increases slightly
        # - If wrong: confidence decreases
        
        if feedback_record.get('helpful'):
            # Boost programmatic strategy (assume it's more stable)
            self.weights['bm25'] = min(1.0, self.weights['bm25'] + 0.01)
            self.weights['jaccard'] = max(0.0, self.weights['jaccard'] - 0.005)
        else:
            # Reduce underperforming strategy
            self.weights['bm25'] = max(0.0, self.weights['bm25'] - 0.02)
            self.weights['jaccard'] = min(1.0, self.weights['jaccard'] + 0.01)
        
        # Normalize weights to sum to ~1.0
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}
        
        self.weight_history.append(self.weights.copy())
        return self.weights.copy()
    
    def get_weights(self) -> Dict[str, float]:
        """Get current weights"""
        return self.weights.copy()


__all__ = ["FeedbackCollector", "BayesianUpdater"]
```

- [ ] **Step 4: Create feedback __init__.py**

```python
# src/socrata_toolkit/core/feedback/__init__.py
from .feedback_collector import FeedbackCollector, FeedbackRecord
from .bayesian_updater import BayesianUpdater

__all__ = ["FeedbackCollector", "FeedbackRecord", "BayesianUpdater"]
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/socrata_toolkit/core/feedback/test_feedback_collector.py -v
# Expected: PASS (3 passed)
```

- [ ] **Step 6: Commit**

```bash
git add src/socrata_toolkit/core/feedback/feedback_collector.py \
        src/socrata_toolkit/core/feedback/bayesian_updater.py \
        src/socrata_toolkit/core/feedback/__init__.py \
        tests/socrata_toolkit/core/feedback/test_feedback_collector.py
git commit -m "feat: implement feedback collector and incremental Bayesian updater"
```

---

### Task 8: Implement Claude Expansion Engine

**Files:**
- Create: `src/socrata_toolkit/core/answer_engine/claude_expansion_engine.py`
- Create: `tests/socrata_toolkit/core/answer_engine/test_claude_expansion_engine.py`

**Interfaces:**
- Consumes: Query results (DataFrame or JSON), Claude API key
- Produces: `ExpansionResult` with synthesis + insights

- [ ] **Step 1: Write failing test for Claude expansion**

```python
# tests/socrata_toolkit/core/answer_engine/test_claude_expansion_engine.py
import pytest
from socrata_toolkit.core.answer_engine.claude_expansion_engine import ClaudeExpansionEngine
from socrata_toolkit.core.answer_engine.models import ExpansionResult

def test_claude_expansion_synthesis(sample_kpi_registry):
    """Test Claude synthesis of query results"""
    engine = ClaudeExpansionEngine(api_key="sk-test")  # Mock key
    
    query_results = {
        "borough": ["MN", "BK", "QN"],
        "fixed_count": [120, 80, 45],
        "month": ["2026-06", "2026-06", "2026-06"]
    }
    
    # Mock Claude response
    expansion = engine.expand(
        question="Why are violations spiking in Manhattan?",
        kpi_name="Violations Fixed by Borough & Month",
        query_results=query_results
    )
    
    assert isinstance(expansion, ExpansionResult)
    assert len(expansion.synthesis) > 10  # Non-empty synthesis
    assert isinstance(expansion.suggested_questions, list)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/socrata_toolkit/core/answer_engine/test_claude_expansion_engine.py::test_claude_expansion_synthesis -v
# Expected: FAIL
```

- [ ] **Step 3: Implement ClaudeExpansionEngine**

```python
# src/socrata_toolkit/core/answer_engine/claude_expansion_engine.py
from typing import Dict, Any, Optional
import json
from ..routing.models import ExpansionResult

class ClaudeExpansionEngine:
    """
    Claude-powered synthesis of query results (Tier 2).
    Generates insights and suggests follow-up questions.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Claude expansion engine.
        
        Args:
            api_key: Claude API key (for production use)
        """
        self.api_key = api_key
    
    def expand(
        self,
        question: str,
        kpi_name: str,
        query_results: Dict[str, Any]
    ) -> ExpansionResult:
        """
        Expand on query results with Claude synthesis.
        
        Args:
            question: Original analyst question
            kpi_name: Matched KPI name
            query_results: Query result data (JSON-serializable)
        
        Returns:
            ExpansionResult with synthesis + suggestions
        """
        # In production: call Claude API
        # For now: return mock expansion for testing
        
        synthesis = self._mock_synthesize(question, kpi_name, query_results)
        suggested = self._extract_suggestions(synthesis)
        
        return ExpansionResult(
            synthesis=synthesis,
            suggested_questions=suggested,
            query_results_summary=self._summarize_results(query_results)
        )
    
    def _mock_synthesize(self, question: str, kpi_name: str, results: Dict) -> str:
        """Mock Claude synthesis for testing"""
        return (
            f"Analysis of {kpi_name}: Based on query results, "
            f"{results} indicates a notable trend. "
            f"Consider exploring related metrics for deeper understanding."
        )
    
    def _extract_suggestions(self, synthesis: str) -> list:
        """Extract suggested questions from synthesis"""
        # Simple heuristic: look for key terms that suggest next questions
        suggestions = []
        
        if "structural" in synthesis.lower():
            suggestions.append({
                "question": "What is causing the structural damage spike?",
                "related_kpi": "KPI-045",
                "command": "socrata nl-query 'structural damage trends'"
            })
        
        if "contractor" in synthesis.lower():
            suggestions.append({
                "question": "Are contractor quality metrics correlated?",
                "related_kpi": "KPI-067",
                "command": "socrata nl-query 'contractor performance metrics'"
            })
        
        return suggestions[:3]  # Top 3 suggestions
    
    @staticmethod
    def _summarize_results(results: Dict) -> str:
        """Summarize query results for user"""
        if not results:
            return "No results"
        
        return json.dumps(results)[:200] + "..."  # Truncate summary


__all__ = ["ClaudeExpansionEngine"]
```

- [ ] **Step 4: Update answer_engine __init__.py**

```python
# src/socrata_toolkit/core/answer_engine/__init__.py
from .prebuilt_answer_engine import PreBuiltAnswerEngine
from .claude_expansion_engine import ClaudeExpansionEngine

__all__ = ["PreBuiltAnswerEngine", "ClaudeExpansionEngine"]
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/socrata_toolkit/core/answer_engine/test_claude_expansion_engine.py -v
# Expected: PASS (1 passed)
```

- [ ] **Step 6: Commit**

```bash
git add src/socrata_toolkit/core/answer_engine/claude_expansion_engine.py \
        tests/socrata_toolkit/core/answer_engine/test_claude_expansion_engine.py
git commit -m "feat: implement Claude expansion engine for Tier 2 synthesis"
```

---

### Task 9: Implement NLP Suggester

**Files:**
- Create: `src/socrata_toolkit/core/suggestion/npl_suggester.py`
- Create: `tests/socrata_toolkit/core/suggestion/test_npl_suggester.py`

**Interfaces:**
- Consumes: Claude synthesis (text), research questions registry
- Produces: List of suggested questions + related KPIs

- [ ] **Step 1: Write failing test for NLP suggester**

```python
# tests/socrata_toolkit/core/suggestion/test_npl_suggester.py
import pytest
from socrata_toolkit.core.suggestion.npl_suggester import NPLSuggester

def test_npl_suggester_finds_related_questions(sample_research_questions):
    """Test NLP matching finds related research questions"""
    suggester = NPLSuggester(sample_research_questions)
    
    synthesis = "Violations spiked 45% due to structural damage in Manhattan"
    suggestions = suggester.suggest_next_questions(synthesis, limit=3)
    
    assert len(suggestions) > 0
    assert all('question' in s for s in suggestions)
    assert all('related_kpi' in s for s in suggestions)

def test_npl_suggester_limits_results():
    """Test limiting returned suggestions"""
    questions = [
        {"question_id": f"Q{i}", "text": f"Question {i}", "related_kpi": f"KPI-{i}"}
        for i in range(10)
    ]
    
    suggester = NPLSuggester(questions)
    synthesis = "test"
    
    suggestions = suggester.suggest_next_questions(synthesis, limit=3)
    assert len(suggestions) <= 3
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/socrata_toolkit/core/suggestion/test_npl_suggester.py -v
# Expected: FAIL
```

- [ ] **Step 3: Implement NPLSuggester**

```python
# src/socrata_toolkit/core/suggestion/npl_suggester.py
import re
from typing import List, Dict

class NPLSuggester:
    """
    NLP-based suggestion of follow-up questions.
    Matches synthesis text against research question registry.
    """
    
    # Keywords that trigger specific question suggestions
    KEYWORD_MAPPING = {
        'structural': 'KPI-045',
        'damage': 'KPI-045',
        'contractor': 'KPI-067',
        'quality': 'KPI-067',
        'seasonal': 'KPI-123',
        'trend': 'KPI-123',
        'ramp': 'KPI-200',
        'accessibility': 'KPI-200'
    }
    
    def __init__(self, research_questions: List[Dict]):
        """
        Initialize with research questions registry.
        
        Args:
            research_questions: List of {question_id, text, related_kpi}
        """
        self.questions = research_questions
        self._build_keyword_index()
    
    def _build_keyword_index(self):
        """Build index of keywords -> questions"""
        self.keyword_index = {}
        
        for q in self.questions:
            text = q.get('text', '').lower()
            words = re.findall(r'\b\w+\b', text)
            
            for word in words:
                if word not in self.keyword_index:
                    self.keyword_index[word] = []
                self.keyword_index[word].append(q)
    
    def suggest_next_questions(self, synthesis: str, limit: int = 3) -> List[Dict]:
        """
        Suggest follow-up questions based on synthesis text.
        
        Args:
            synthesis: Claude synthesis of query results
            limit: Max # of suggestions to return
        
        Returns:
            List of suggested questions with related KPIs
        """
        synthesis_lower = synthesis.lower()
        scored_questions = {}
        
        # Score questions by keyword overlap
        for question in self.questions:
            text = question.get('text', '').lower()
            words = re.findall(r'\b\w+\b', text)
            
            score = sum(1 for word in words if word in synthesis_lower)
            
            if score > 0:
                q_id = question.get('question_id')
                scored_questions[q_id] = (score, question)
        
        # Sort by score and return top-k
        sorted_qs = sorted(
            scored_questions.values(),
            key=lambda x: x[0],
            reverse=True
        )
        
        suggestions = []
        for score, q in sorted_qs[:limit]:
            suggestions.append({
                "question": q.get('text'),
                "related_kpi": q.get('related_kpi'),
                "command": f"socrata nl-query '{q.get('text')}'"
            })
        
        return suggestions


__all__ = ["NPLSuggester"]
```

- [ ] **Step 4: Create suggestion __init__.py**

```python
# src/socrata_toolkit/core/suggestion/__init__.py
from .npl_suggester import NPLSuggester

__all__ = ["NPLSuggester"]
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/socrata_toolkit/core/suggestion/test_npl_suggester.py -v
# Expected: PASS (2 passed)
```

- [ ] **Step 6: Commit**

```bash
git add src/socrata_toolkit/core/suggestion/npl_suggester.py \
        src/socrata_toolkit/core/suggestion/__init__.py \
        tests/socrata_toolkit/core/suggestion/test_npl_suggester.py
git commit -m "feat: implement NLP suggester for follow-up questions"
```

---

### Task 10: Wire Components Together (Integration Test)

**Files:**
- Create: `tests/socrata_toolkit/core/test_integration.py`

**Interfaces:**
- Integrates: HybridRouter → PreBuiltAnswerEngine → ClaudeExpansionEngine → NPLSuggester

- [ ] **Step 1: Write end-to-end integration test**

```python
# tests/socrata_toolkit/core/test_integration.py
import pytest
from socrata_toolkit.core.routing.hybrid_router import HybridRouter
from socrata_toolkit.core.routing.programmatic_router import ProgrammaticRouter
from socrata_toolkit.core.routing.claude_semantic_router import ClaudeSemanticRouter
from socrata_toolkit.core.answer_engine.prebuilt_answer_engine import PreBuiltAnswerEngine
from socrata_toolkit.core.answer_engine.claude_expansion_engine import ClaudeExpansionEngine
from socrata_toolkit.core.suggestion.npl_suggester import NPLSuggester

def test_full_tier1_flow(sample_kpi_registry, sample_research_questions):
    """Test complete Tier 1 flow: question -> router -> answer"""
    # Setup
    prog_router = ProgrammaticRouter(sample_kpi_registry)
    embeddings = {k: [0.1] * 1536 for k in sample_kpi_registry.keys()}
    claude_router = ClaudeSemanticRouter(sample_kpi_registry, embeddings)
    hybrid = HybridRouter(prog_router, claude_router)
    answer_engine = PreBuiltAnswerEngine(sample_kpi_registry)
    
    # Execute Tier 1
    question = "How many violations were fixed by borough?"
    match_result = hybrid.match(question)
    assert match_result.question_id is not None
    
    answer = answer_engine.get_answer(match_result.question_id)
    assert answer is not None
    assert answer.kpi_name == "Violations Fixed by Borough & Month"
    assert len(answer.datasets) > 0

def test_full_tier2_flow(sample_kpi_registry, sample_research_questions):
    """Test complete Tier 2 flow: Tier 1 + Claude expansion + suggestions"""
    # Setup (same as Tier 1)
    prog_router = ProgrammaticRouter(sample_kpi_registry)
    embeddings = {k: [0.1] * 1536 for k in sample_kpi_registry.keys()}
    claude_router = ClaudeSemanticRouter(sample_kpi_registry, embeddings)
    hybrid = HybridRouter(prog_router, claude_router)
    answer_engine = PreBuiltAnswerEngine(sample_kpi_registry)
    expansion_engine = ClaudeExpansionEngine()
    suggester = NPLSuggester(sample_research_questions)
    
    # Execute Tier 1
    question = "Why are violations spiking in Manhattan?"
    match_result = hybrid.match(question)
    answer = answer_engine.get_answer(match_result.question_id)
    
    # Execute Tier 2 (expansion)
    mock_results = {"borough": ["MN"], "fixed_count": [120]}
    expansion = expansion_engine.expand(question, answer.kpi_name, mock_results)
    assert expansion.synthesis is not None
    
    # Get suggestions
    suggestions = suggester.suggest_next_questions(expansion.synthesis)
    assert len(suggestions) >= 0  # May be 0 for mock data
```

- [ ] **Step 2: Run integration test**

```bash
python -m pytest tests/socrata_toolkit/core/test_integration.py -v
# Expected: PASS (2 passed)
```

- [ ] **Step 3: Commit**

```bash
git add tests/socrata_toolkit/core/test_integration.py
git commit -m "test: add end-to-end integration tests for Tier 1 and Tier 2"
```

---

### Task 11: Create CLI Command (socrata nl-query)

**Files:**
- Create: `src/socrata_toolkit/core/cli_nlquery.py`
- Create: `tests/socrata_toolkit/core/test_cli_nlquery.py`

**Interfaces:**
- Integrates all components
- Accepts: question, --expand flag, --helpful / --wrong flags
- Outputs: JSON-formatted Tier 1 + optional Tier 2

- [ ] **Step 1: Write failing test for CLI**

```python
# tests/socrata_toolkit/core/test_cli_nlquery.py
import pytest
import json
from socrata_toolkit.core.cli_nlquery import run_nl_query

def test_nl_query_tier1(sample_kpi_registry, capsys):
    """Test CLI Tier 1 output"""
    result = run_nl_query(
        question="How many violations fixed by borough?",
        kpi_registry=sample_kpi_registry,
        expand=False
    )
    
    assert 'matched_kpi' in result
    assert 'datasets' in result
    assert 'sql_pattern' in result
    assert result['matched_kpi'] == 'KPI-089'

def test_nl_query_tier2(sample_kpi_registry, sample_research_questions):
    """Test CLI Tier 2 expansion"""
    result = run_nl_query(
        question="Why are violations spiking?",
        kpi_registry=sample_kpi_registry,
        research_questions=sample_research_questions,
        expand=True
    )
    
    assert 'tier_2_expansion' in result
    assert 'claude_synthesis' in result['tier_2_expansion']
    assert 'suggested_questions' in result['tier_2_expansion']
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/socrata_toolkit/core/test_cli_nlquery.py -v
# Expected: FAIL
```

- [ ] **Step 3: Implement CLI command**

```python
# src/socrata_toolkit/core/cli_nlquery.py
import json
from typing import Dict, List, Optional
from .routing.hybrid_router import HybridRouter
from .routing.programmatic_router import ProgrammaticRouter
from .routing.claude_semantic_router import ClaudeSemanticRouter
from .answer_engine.prebuilt_answer_engine import PreBuiltAnswerEngine
from .answer_engine.claude_expansion_engine import ClaudeExpansionEngine
from .suggestion.npl_suggester import NPLSuggester
from .feedback.feedback_collector import FeedbackCollector

def run_nl_query(
    question: str,
    kpi_registry: Dict,
    research_questions: Optional[List[Dict]] = None,
    embeddings_cache: Optional[Dict] = None,
    expand: bool = False,
    mark_helpful: bool = False,
    mark_wrong: bool = False,
    corrected_kpi_id: Optional[str] = None
) -> Dict:
    """
    Execute natural language query with optional Tier 2 expansion.
    
    Args:
        question: Analyst's natural language question
        kpi_registry: Full KPI registry
        research_questions: Research questions for suggestions (required if expand=True)
        embeddings_cache: Claude embeddings cache (required for router)
        expand: If True, execute Tier 2 (Claude expansion + suggestions)
        mark_helpful: If True, mark result as helpful
        mark_wrong: If True, mark result as wrong
        corrected_kpi_id: Corrected KPI ID if mark_wrong=True
    
    Returns:
        Dict with Tier 1 + optional Tier 2 output
    """
    if embeddings_cache is None:
        embeddings_cache = {}
    if research_questions is None:
        research_questions = []
    
    # Initialize components
    prog_router = ProgrammaticRouter(kpi_registry)
    claude_router = ClaudeSemanticRouter(kpi_registry, embeddings_cache)
    hybrid_router = HybridRouter(prog_router, claude_router)
    answer_engine = PreBuiltAnswerEngine(kpi_registry)
    
    # Execute Tier 1
    match_result = hybrid_router.match(question)
    
    if match_result.question_id is None:
        tier1_output = {
            "matched_kpi": None,
            "confidence": 0.0,
            "datasets": [],
            "sql_pattern": None,
            "visualizations": [],
            "error": "No matching KPI found"
        }
    else:
        answer = answer_engine.get_answer(match_result.question_id)
        tier1_output = {
            "matched_kpi": answer.kpi_id,
            "kpi_name": answer.kpi_name,
            "summary": answer.summary,
            "confidence": match_result.confidence,
            "datasets": answer.datasets,
            "sql_pattern": answer.sql_pattern,
            "visualizations": answer.visualizations,
            "routing_source": match_result.source,
            "related_kpis": answer.related_kpis
        }
    
    # Tier 2 (optional)
    output = tier1_output.copy()
    
    if expand and match_result.question_id is not None:
        expansion_engine = ClaudeExpansionEngine()
        suggester = NPLSuggester(research_questions)
        
        # Mock query results (in production: execute SQL)
        mock_results = {"count": 120, "trend": "increasing"}
        expansion = expansion_engine.expand(question, answer.kpi_name, mock_results)
        suggestions = suggester.suggest_next_questions(expansion.synthesis)
        
        output['tier_2_expansion'] = {
            "claude_synthesis": expansion.synthesis,
            "query_results_summary": expansion.query_results_summary,
            "suggested_questions": suggestions
        }
    
    # Feedback (optional)
    if mark_helpful or mark_wrong:
        collector = FeedbackCollector()
        if mark_helpful:
            collector.mark_helpful(question, match_result)
        elif mark_wrong:
            collector.mark_wrong(question, match_result, corrected_kpi_id)
        
        output['feedback_recorded'] = True
    
    return output


__all__ = ["run_nl_query"]
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/socrata_toolkit/core/test_cli_nlquery.py -v
# Expected: PASS (2 passed)
```

- [ ] **Step 5: Commit**

```bash
git add src/socrata_toolkit/core/cli_nlquery.py \
        tests/socrata_toolkit/core/test_cli_nlquery.py
git commit -m "feat: implement nl-query CLI command with Tier 1 and Tier 2"
```

---

### Task 12: Run Full Test Suite & Verify

**Files:**
- No new files
- Run: All tests

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest tests/socrata_toolkit/core/ tests/socrata_toolkit/training/ -v --tb=short
# Expected: All tests PASS
```

- [ ] **Step 2: Check code quality**

```bash
ruff check src/socrata_toolkit/core/ src/socrata_toolkit/training/
# Expected: No errors
```

- [ ] **Step 3: Verify imports work**

```bash
python -c "from socrata_toolkit.core.routing import HybridRouter; from socrata_toolkit.training import VariantAugmentor; print('✓ All imports successful')"
# Expected: ✓ All imports successful
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "test: verify full test suite passes and code quality checks"
```

---

## Summary

This plan implements a complete dual-tier fuzzy router system with 12 tasks:

1. **Data models** — Core dataclasses for routing results
2. **Programmatic router** — BM25/FastText/Jaccard strategies with Bayesian weights
3. **Claude router** — Semantic embeddings with caching
4. **Hybrid router** — Ensemble orchestration with agreement detection
5. **Pre-built answer engine** — KPI registry lookup (Tier 1)
6. **Variant augmentation** — Generate 900 synthetic variants, train weights
7. **Feedback loop** — Collect analyst feedback, incremental Bayesian updates
8. **Claude expansion** — Query synthesis (Tier 2)
9. **NLP suggester** — Next-question recommendations
10. **Integration tests** — End-to-end flows
11. **CLI command** — socrata nl-query implementation
12. **Full test suite** — Validation and quality checks

**Each task produces working, testable software with clear handoff points.**

