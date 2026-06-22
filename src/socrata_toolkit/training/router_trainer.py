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

    def split_variants(
        self,
        variants: List[Dict],
        train_ratio: float = 0.80
    ) -> Tuple[List[Dict], List[Dict]]:
        """Split variants into train and holdout sets"""
        split_idx = int(len(variants) * train_ratio)
        return variants[:split_idx], variants[split_idx:]


__all__ = ["RouterTrainer"]
