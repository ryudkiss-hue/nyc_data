from typing import Any, Dict, List


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
