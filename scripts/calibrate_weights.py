#!/usr/bin/env python3
import json
import pickle
from pathlib import Path

import numpy as np
from scipy.optimize import minimize


def tokenize(text):
    return text.lower().split()

def _jaro_similarity(s1: str, s2: str) -> float:
    if len(s1) == 0 and len(s2) == 0:
        return 1.0
    if len(s1) == 0 or len(s2) == 0:
        return 0.0

    match_distance = max(len(s1), len(s2)) // 2 - 1
    if match_distance < 0:
        match_distance = 0

    s1_matches = [False] * len(s1)
    s2_matches = [False] * len(s2)

    matches = 0
    transpositions = 0

    for i in range(len(s1)):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len(s2))

        for j in range(start, end):
            if s2_matches[j] or s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    k = 0
    for i in range(len(s1)):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    return (matches / len(s1) + matches / len(s2) + (matches - transpositions / 2) / matches) / 3

def calculate_jaro_winkler(s1: str, s2: str) -> float:
    s1_norm = s1.lower()
    s2_norm = s2.lower()
    jaro = _jaro_similarity(s1_norm, s2_norm)
    if jaro < 0.7:
        return jaro

    prefix = 0
    for i in range(min(len(s1_norm), len(s2_norm), 4)):
        if s1_norm[i] == s2_norm[i]:
            prefix += 1
        else:
            break

    return jaro + (prefix * 0.1 * (1 - jaro))

def calculate_bm25(query_terms, doc_terms, kpi_names, k1=1.5, b=0.75):
    if not doc_terms:
        return 0.0

    score = 0.0
    doc_len = len(doc_terms)
    avg_doc_len = sum(len(tokenize(name)) for name in kpi_names) / len(kpi_names)

    for term in query_terms:
        term_freq = doc_terms.count(term)
        if term_freq == 0:
            continue

        docs_with_term = sum(1 for name in kpi_names if term in tokenize(name))
        idf = len(kpi_names) / (docs_with_term + 1)

        numerator = term_freq * (k1 + 1)
        denominator = term_freq + k1 * (1 - b + b * (doc_len / avg_doc_len))
        score += idf * (numerator / denominator)

    return min(score / max(len(query_terms), 1), 1.0)

def calculate_jaccard(query_tokens, doc_tokens):
    if not query_tokens or not doc_tokens:
        return 0.0
    intersection = len(query_tokens & doc_tokens)
    union = len(query_tokens | doc_tokens)
    return intersection / union if union > 0 else 0.0

def main():
    print("=" * 80)
    print("Advanced Weight Calibration (BM25 + Token Overlap + Jaro-Winkler)")
    print("=" * 80)

    desktop_dir = Path("C:/Users/ryudk/Desktop")
    training_file = desktop_dir / "fuzzy_matching_training_data_extended.json"

    if not training_file.exists():
        print(f"Error: extended training file not found at {training_file}")
        return

    with open(training_file, encoding="utf-8") as f:
        data = json.load(f)

    questions = data["labeled_questions"]
    print(f"Loaded {len(questions)} labeled question variants.")

    kpi_map = {}
    for q in questions:
        kpi_map[q["kpi_id"]] = q["kpi_name"]

    kpi_ids = sorted(list(kpi_map.keys()))
    kpi_names = [kpi_map[kid] for kid in kpi_ids]
    kpi_tokens = [set(tokenize(name)) for name in kpi_names]
    kpi_terms = [tokenize(name) for name in kpi_names]

    num_qs = len(questions)
    num_kpis = len(kpi_ids)

    bm25_matrix = np.zeros((num_qs, num_kpis))
    fasttext_matrix = np.zeros((num_qs, num_kpis))
    jaccard_matrix = np.zeros((num_qs, num_kpis))

    print("Pre-computing similarity matrices (BM25, Token Jaccard, Jaro-Winkler)...")
    for q_idx, q in enumerate(questions):
        q_text = q["question_variant"]
        q_terms = tokenize(q_text)
        q_tokens = set(q_terms)

        for k_idx in range(num_kpis):
            # 1. BM25
            bm25_matrix[q_idx, k_idx] = calculate_bm25(q_terms, kpi_terms[k_idx], kpi_names)
            # 2. FastText (token Jaccard)
            fasttext_matrix[q_idx, k_idx] = calculate_jaccard(q_tokens, kpi_tokens[k_idx])
            # 3. Jaccard (character Jaro-Winkler)
            jaccard_matrix[q_idx, k_idx] = calculate_jaro_winkler(q_text, kpi_names[k_idx])

    # Cache features to Desktop
    features_cache_path = desktop_dir / "fuzzy_matching_features.pkl"
    metadata_cache_path = desktop_dir / "fuzzy_matching_metadata.json"

    with open(features_cache_path, "wb") as f:
        pickle.dump({
            "bm25": bm25_matrix,
            "fasttext": fasttext_matrix,
            "jaccard": jaccard_matrix
        }, f)

    with open(metadata_cache_path, "w", encoding="utf-8") as f:
        json.dump({
            "kpi_ids": kpi_ids,
            "kpi_names": kpi_names,
            "questions": [{
                "text": q["question_variant"],
                "kpi_id": q["kpi_id"],
                "variant_type": q["variant_type"]
            } for q in questions]
        }, f, indent=2)

    print(f"Cached feature matrix to: {features_cache_path}")

    true_indices = np.array([kpi_ids.index(q["kpi_id"]) for q in questions])

    def evaluate_accuracy(weights):
        w_bm25, w_ft, w_jac = weights
        composite_scores = w_bm25 * bm25_matrix + w_ft * fasttext_matrix + w_jac * jaccard_matrix
        predictions = np.argmax(composite_scores, axis=1)
        return np.mean(predictions == true_indices)

    baseline_weights = [0.80, 0.15, 0.05]
    baseline_acc = evaluate_accuracy(baseline_weights)
    print(f"\nBaseline Accuracy (80/15/5): {baseline_acc * 100:.2f}%")

    # Run optimization search
    best_acc = baseline_acc
    best_weights = baseline_weights[:]

    # Grid search or random search since it's 3D and bounded
    # BM25: [0.5, 0.95], FastText: [0.02, 0.45], Jaccard: [0.01, 0.1]
    print("\nRunning grid search for optimal weights...")
    for w_bm25 in np.linspace(0.50, 0.95, 46):
        for w_ft in np.linspace(0.02, 0.45, 44):
            w_jac = 1.0 - w_bm25 - w_ft
            if w_jac >= 0.01 and w_jac <= 0.10:
                acc = evaluate_accuracy([w_bm25, w_ft, w_jac])
                if acc > best_acc:
                    best_acc = acc
                    best_weights = [w_bm25, w_ft, w_jac]

    print("\n" + "=" * 50)
    print("OPTIMIZATION RESULTS")
    print("=" * 50)
    print(f"Optimal BM25 Weight:      {best_weights[0]:.4f} (baseline: 0.8000)")
    print(f"Optimal FastText Weight:  {best_weights[1]:.4f} (baseline: 0.1500)")
    print(f"Optimal Jaccard Weight:   {best_weights[2]:.4f} (baseline: 0.0500)")
    print("-" * 50)
    print(f"Baseline Accuracy:  {baseline_acc * 100:.2f}%")
    print(f"Optimized Accuracy: {best_acc * 100:.2f}%")
    print(f"Improvement:        +{(best_acc - baseline_acc) * 100:.2f} percentage points")
    print("=" * 50)

    variant_types = sorted(list(set(q["variant_type"] for q in questions)))
    accuracy_by_type = {}

    for v_type in variant_types:
        indices = [idx for idx, q in enumerate(questions) if q["variant_type"] == v_type]
        if not indices:
            continue
        v_true = true_indices[indices]
        v_composite = best_weights[0] * bm25_matrix[indices] + best_weights[1] * fasttext_matrix[indices] + best_weights[2] * jaccard_matrix[indices]
        v_pred = np.argmax(v_composite, axis=1)
        v_acc = np.mean(v_pred == v_true)
        accuracy_by_type[v_type] = {
            "accuracy": v_acc,
            "count": len(indices)
        }

    print("\nAccuracy by Variant Type:")
    for v_type, info in accuracy_by_type.items():
        print(f"  • {v_type.replace('_', ' ').capitalize()}: {info['accuracy'] * 100:.1f}% ({info['count']} samples)")

    calibration_logs_dir = Path("C:/Users/ryudk/Desktop/.calibration_logs")
    calibration_logs_dir.mkdir(parents=True, exist_ok=True)

    results_json = {
        "bm25": best_weights[0],
        "fasttext": best_weights[1],
        "jaccard": best_weights[2],
        "baseline_accuracy": baseline_acc,
        "optimized_accuracy": best_acc,
        "variants_tested": num_qs,
        "accuracy_by_variant_type": {k: v["accuracy"] for k, v in accuracy_by_type.items()},
        "counts_by_variant_type": {k: v["count"] for k, v in accuracy_by_type.items()}
    }

    with open(calibration_logs_dir / "optimal_weights.json", "w", encoding="utf-8") as f:
        json.dump(results_json, f, indent=2)

    print(f"\nCalibration metrics saved successfully to: {calibration_logs_dir / 'optimal_weights.json'}")

if __name__ == "__main__":
    main()
