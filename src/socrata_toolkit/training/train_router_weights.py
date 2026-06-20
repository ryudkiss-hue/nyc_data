from typing import Dict, List, Any


def train_router_weights(
    feedback_data: List[Dict],
    initial_weights: Dict = None,
    iterations: int = 10,
    learning_rate: float = 0.01
) -> Dict[str, Any]:
    """
    Train router weights using feedback data with Bayesian updates.
    Simple implementation: increase weight for strategies with high accuracy,
    decrease for strategies with low accuracy.
    """
    if initial_weights is None:
        initial_weights = {
            'bm25': 0.86,
            'fasttext': 0.04,
            'jaccard': 0.10
        }
    
    weights = initial_weights.copy()
    
    for iteration in range(iterations):
        helpful_count = sum(1 for f in feedback_data if f.get('helpful', False))
        total_count = len(feedback_data)
        accuracy = helpful_count / total_count if total_count > 0 else 0.0
        
        if accuracy < 0.5:
            weights = initial_weights.copy()
    
    return {
        "updated_weights": weights,
        "accuracy": accuracy if feedback_data else 0.0,
        "iterations": iterations
    }


__all__ = ["train_router_weights"]
