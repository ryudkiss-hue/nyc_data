import pytest

from socrata_toolkit.core.routing.programmatic_router import ProgrammaticRouter
from socrata_toolkit.training.router_trainer import RouterTrainer
from socrata_toolkit.training.variant_augmentor import VariantAugmentor


@pytest.fixture
def sample_kpi_registry():
    """Sample KPI registry for testing"""
    return {
        "KPI-089": {
            "kpi_id": "KPI-089",
            "kpi_name": "Violations Fixed by Borough & Month",
            "summary": "Monthly count of violations marked fixed",
            "datasets": [{"key": "violations", "fourfour": "6kbp-uz6m"}],
            "sql_pattern": "SELECT * FROM violations",
            "visualization_metadata": [],
            "related_kpis": []
        }
    }

def test_variant_augmentor_generates_synthetic(sample_kpi_registry):
    """Test synthetic variant generation"""
    augmentor = VariantAugmentor(sample_kpi_registry)

    synthetic = augmentor.generate_synthetic_variants(seed_covered_kpis=set())

    # Should generate 4 variants (one per template)
    assert len(synthetic) >= 4
    assert all(v['synthetic'] for v in synthetic)
    assert all('question_variant' in v for v in synthetic)

def test_variant_augmentor_respects_seed_covered(sample_kpi_registry):
    """Test that augmentor skips seed-covered KPIs"""
    augmentor = VariantAugmentor(sample_kpi_registry)

    synthetic = augmentor.generate_synthetic_variants(seed_covered_kpis={"KPI-089"})

    # Should generate no variants since KPI-089 is marked as covered
    assert len(synthetic) == 0

def test_router_trainer_evaluate_accuracy(sample_kpi_registry):
    """Test router accuracy evaluation"""
    router = ProgrammaticRouter(sample_kpi_registry)
    trainer = RouterTrainer(sample_kpi_registry)

    variants = [
        {
            "kpi_id": "KPI-089",
            "question_variant": "violations fixed by borough"
        },
        {
            "kpi_id": "KPI-089",
            "question_variant": "how many violations fixed"
        }
    ]

    accuracy = trainer.evaluate_accuracy(router, variants)

    assert accuracy >= 0.0
    assert accuracy <= 1.0

def test_router_trainer_split_variants(sample_kpi_registry):
    """Test variant splitting"""
    trainer = RouterTrainer(sample_kpi_registry)

    variants = [{"kpi_id": f"KPI-{i}", "question_variant": f"q{i}"} for i in range(100)]

    train, holdout = trainer.split_variants(variants, train_ratio=0.80)

    assert len(train) == 80
    assert len(holdout) == 20
    assert len(train) + len(holdout) == 100
