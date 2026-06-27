# Claude ↔ Gemini Memory Sync Protocol

**Purpose:** Maintain memory consistency across Claude Code and Gemini CLI runtimes  
**Direction:** Bidirectional (Claude → Gemini before calibration, Gemini → Claude after completion)  
**Sync Type:** File-based (JSON/Markdown)  

---

## Source of Truth Locations

### Claude Code Memory (SOURCE)
```
C:\Users\ryudk\.claude\projects\C--Users-ryudk\memory\
├── MEMORY.md (index, 68 lines)
├── fuzzy_matching_hybrid_algorithm_research.md (core research)
├── sim_research_questions_to_kpi_mapping.md (309 KPIs)
├── sim_research_question_methodology_matrix.md (frameworks)
├── sim_skills_activation_playbook.md (skill routing)
├── memora_integration_plan.md (memora strategy)
└── [8 other project memory files]
```

### Gemini Sync Working Directory (STAGING)
```
C:\Users\ryudk\Desktop\claude_memory_sync\
├── MEMORY.md (synced index)
├── fuzzy_matching_hybrid_algorithm_research.md (synced)
├── [all Claude memory files copied]
└── _sync_metadata.json (tracks what was synced)
```

### Memora SQLite (INTEGRATION TARGET)
```
C:\Users\ryudk\.claude\projects\C--Users-ryudk\memory\.memora\
├── db.sqlite (memora database)
└── embeddings.pkl (cached embeddings)
```

---

## Phase 0: Initial Sync (Claude → Gemini)

**Before Gemini CLI starts:** Copy all Claude memory files to Desktop staging area.

### Files to Sync

| File | Purpose | Size | Priority |
|------|---------|------|----------|
| MEMORY.md | Index of all memories | 3KB | CRITICAL |
| fuzzy_matching_hybrid_algorithm_research.md | Core research findings | 8KB | CRITICAL |
| sim_research_questions_to_kpi_mapping.md | 309 KPI definitions | 15KB | CRITICAL |
| sim_research_question_methodology_matrix.md | Research frameworks | 12KB | HIGH |
| sim_skills_activation_playbook.md | Skill routing logic | 10KB | HIGH |
| memora_integration_plan.md | Memora strategy | 8KB | HIGH |
| sim_division_research_operational_questions.md | Research context | 10KB | MEDIUM |
| sim_infrastructure_glossary.md | Domain glossary | 12KB | MEDIUM |
| [6 other project files] | Supporting context | 30KB | MEDIUM |

**Total:** ~110KB (easily portable)

### Sync Manifest

**File:** `C:\Users\ryudk\Desktop\_sync_manifest.json`

```json
{
  "sync_version": "1.0",
  "sync_date": "2026-06-19T21:47:00Z",
  "direction": "Claude → Gemini (initial)",
  "source": "C:\\Users\\ryudk\\.claude\\projects\\C--Users-ryudk\\memory",
  "staging": "C:\\Users\\ryudk\\Desktop\\claude_memory_sync",
  "files": [
    {
      "name": "MEMORY.md",
      "size": 3450,
      "hash": "sha256:abc123...",
      "priority": "CRITICAL",
      "requires_parsing": false
    },
    {
      "name": "fuzzy_matching_hybrid_algorithm_research.md",
      "size": 8120,
      "hash": "sha256:def456...",
      "priority": "CRITICAL",
      "requires_parsing": true,
      "frontmatter_keys": ["name", "description", "metadata"]
    },
    {
      "name": "sim_research_questions_to_kpi_mapping.md",
      "size": 15340,
      "hash": "sha256:ghi789...",
      "priority": "CRITICAL",
      "requires_parsing": true,
      "section_count": 8
    }
  ],
  "total_files": 12,
  "total_size_bytes": 112340,
  "checksum": "sha256:jkl012..."
}
```

**How to use:**
```bash
# Gemini CLI reads this manifest
gemini-cli memory sync \
  --manifest-file _sync_manifest.json \
  --source C:\Users\ryudk\Desktop\claude_memory_sync \
  --target /gemini/memory \
  --direction "read" \
  --verify-checksums
```

---

## Phase 1-5: Memory Updates (Gemini Modifies)

**During calibration:** Gemini CLI creates/modifies:

### New Files Created by Gemini

```
C:\Users\ryudk\Desktop\
├── fuzzy_matching_training_data_extended.json (1,200+ variants)
├── .embeddings_cache/ (cached embeddings)
│   ├── index.json
│   ├── kpi_embeddings.pkl
│   └── question_vectors.pkl
├── .calibration_logs/
│   ├── optimal_weights.json
│   ├── accuracy_metrics.json
│   └── calibration_history.json
└── CALIBRATION_REPORT_2026-06-19.md (results)
```

### Files Modified by Gemini

**File:** `C:\Users\ryudk\Desktop\claude_memory_sync\fuzzy_matching_hybrid_algorithm_research.md`

**Gemini updates the "Status" section:**
```markdown
## Status

Research COMPLETE (2026-06-19).  
Weight calibration COMPLETE (2026-06-19 by Gemini CLI).

### Calibration Results
- **Baseline accuracy:** 72%
- **Optimized accuracy:** 87%
- **Training dataset:** 1,200+ variants
- **Optimal weights:** BM25=0.78, FastText=0.16, Jaccard=0.06

[Full calibration details...]
```

**File:** `C:\Users\ryudk\Desktop\claude_memory_sync\MEMORY.md`

**Gemini updates relevant entries:**
```markdown
- [Fuzzy Matching Hybrid Algorithm Research](fuzzy_matching_hybrid_algorithm_research.md) — ⭐⭐⭐⭐⭐ CALIBRATION COMPLETE (2026-06-19). Weights optimized: BM25=0.78, FastText=0.16, Jaccard=0.06. Achieved 87% routing accuracy on 1,200 labeled variants. Embeddings cached to Desktop. Ready for production deployment.
```

---

## Phase 6: Reverse Sync (Gemini → Claude)

**After calibration completes:** Gemini creates sync package for Claude Code to pull back.

### Reverse Sync Manifest

**File:** `C:\Users\ryudk\Desktop\_reverse_sync_manifest.json`

```json
{
  "sync_version": "1.0",
  "sync_date": "2026-06-19T00:47:00Z",
  "direction": "Gemini → Claude (calibration results)",
  "source": "C:\\Users\\ryudk\\Desktop",
  "target": "C:\\Users\\ryudk\\.claude\\projects\\C--Users-ryudk\\memory",
  "files_to_push": [
    {
      "filename": "fuzzy_matching_hybrid_algorithm_research.md",
      "source_path": "C:\\Users\\ryudk\\Desktop\\claude_memory_sync\\fuzzy_matching_hybrid_algorithm_research.md",
      "target_path": "C:\\Users\\ryudk\\.claude\\projects\\C--Users-ryudk\\memory\\fuzzy_matching_hybrid_algorithm_research.md",
      "operation": "OVERWRITE",
      "priority": "CRITICAL"
    },
    {
      "filename": "MEMORY.md",
      "source_path": "C:\\Users\\ryudk\\Desktop\\claude_memory_sync\\MEMORY.md",
      "target_path": "C:\\Users\\ryudk\\.claude\\projects\\C--Users-ryudk\\memory\\MEMORY.md",
      "operation": "OVERWRITE",
      "priority": "CRITICAL"
    }
  ],
  "files_to_import": [
    {
      "filename": "optimal_weights.json",
      "source_path": "C:\\Users\\ryudk\\Desktop\\.calibration_logs\\optimal_weights.json",
      "target_location": "EMBEDDINGS_CACHE (memora)",
      "operation": "IMPORT_TO_MEMORA",
      "priority": "CRITICAL"
    },
    {
      "filename": "CALIBRATION_REPORT_2026-06-19.md",
      "source_path": "C:\\Users\\ryudk\\Desktop\\CALIBRATION_REPORT_2026-06-19.md",
      "target_location": "docs/",
      "operation": "ARCHIVE",
      "priority": "MEDIUM"
    }
  ],
  "memora_edges_to_create": [
    {
      "from_node": "fuzzy-matching-hybrid-algorithm-research",
      "to_node": "sim-architecture-implementation-phase1",
      "edge_type": "calibrated_weight_for",
      "metadata": {
        "weights": {"bm25": 0.78, "fasttext": 0.16, "jaccard": 0.06},
        "accuracy": 0.87
      }
    }
  ],
  "total_files": 4,
  "estimated_import_time": "2 minutes"
}
```

**How Claude Code will pull back:**
```bash
# Claude Code reads reverse manifest after Gemini completes
claude-code memory sync \
  --manifest-file C:\Users\ryudk\Desktop\_reverse_sync_manifest.json \
  --direction "write" \
  --target C:\Users\ryudk\.claude\projects\C--Users-ryudk\memory \
  --memora-integration \
  --verify-checksums
```

---

## Conflict Resolution

**If both runtimes modify same file:**

1. **Timestamp-based:** Later write wins
2. **Section-based:** Merge if modifications are in different sections
3. **Manual review:** If conflicts are semantic, flag for user review

**Example conflict:**
- Claude modifies: "Status" section in fuzzy_matching_hybrid_algorithm_research.md
- Gemini modifies: Same "Status" section
- **Resolution:** Gemini's version is newer → use Gemini's version (has calibration results)
- **Log:** Record merge in `_sync_metadata.json`

---

## Sync Metadata Tracking

**File:** `C:\Users\ryudk\Desktop\_sync_metadata.json`

```json
{
  "last_sync_claude_to_gemini": {
    "timestamp": "2026-06-19T21:47:00Z",
    "files_synced": 12,
    "total_bytes": 112340,
    "status": "SUCCESS",
    "checksums_verified": true
  },
  "last_sync_gemini_to_claude": {
    "timestamp": "2026-06-19T01:47:00Z",
    "files_synced": 4,
    "total_bytes": 45320,
    "status": "PENDING",
    "memora_edges_created": 1,
    "conflicts": []
  },
  "file_sync_history": [
    {
      "filename": "fuzzy_matching_hybrid_algorithm_research.md",
      "last_modified_by": "Gemini",
      "last_modified": "2026-06-19T01:45:00Z",
      "size": 8540,
      "hash": "sha256:new_hash..."
    }
  ]
}
```

---

## Automated Sync Schedule (Optional)

**After Phase 6, if setting up continuous sync:**

```bash
# Every 30 minutes, check for memory updates
gemini-cli memory sync \
  --manifest-file _sync_manifest.json \
  --schedule "*/30 * * * *" \
  --direction "bidirectional" \
  --conflict-resolution "timestamp"
```

---

## Manual Sync Commands (for user)

### Copy Claude memory to Desktop (preparation)
```bash
cp -r C:\Users\ryudk\.claude\projects\C--Users-ryudk\memory C:\Users\ryudk\Desktop\claude_memory_sync
```

### Start Gemini with memory context
```bash
cd C:\Users\ryudk\Desktop
gemini-cli start \
  --memory-dir claude_memory_sync \
  --handoff-manifest GEMINI_HANDOFF_MANIFEST.md
```

### After Gemini completes, sync back to Claude
```bash
# Claude Code picks up results
claude-code memory sync \
  --source C:\Users\ryudk\Desktop\claude_memory_sync \
  --target C:\Users\ryudk\.claude\projects\C--Users-ryudk\memory \
  --memora-integration true
```

---

## Verification Checklist

**After sync completes:**

- [ ] MEMORY.md index updated with calibration results
- [ ] fuzzy_matching_hybrid_algorithm_research.md has "Status: CALIBRATION COMPLETE"
- [ ] Optimal weights stored in memora (.memora/db.sqlite)
- [ ] Embeddings cached to Desktop (.embeddings_cache/)
- [ ] Calibration report generated (CALIBRATION_REPORT_2026-06-19.md)
- [ ] Checksums match in _sync_metadata.json
- [ ] No conflicts recorded
- [ ] Claude Code can read weights for deployment

---

## Summary

| Phase | Direction | Files | Size | Time |
|-------|-----------|-------|------|------|
| **0: Initial** | Claude → Gemini | 12 memory files | 110KB | <1min |
| **1-5: Calibration** | Gemini modifies | 4 new + 2 updated | 45KB | 3-4h |
| **6: Reverse** | Gemini → Claude | 4 results files | 45KB | <1min |
| **Post-sync** | Bidirectional (optional) | All files | 155KB | Ongoing |

**Status:** Sync protocol ready. Gemini has all necessary context from Claude memory. After calibration, Claude Code will pull results back to memora.
