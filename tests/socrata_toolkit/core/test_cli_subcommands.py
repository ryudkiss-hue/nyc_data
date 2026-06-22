import pytest


def test_cli_subcommand_evaluate_exists():
    """Test evaluate subcommand is available"""
    from socrata_toolkit.training.evaluate_router import evaluate_router
    assert callable(evaluate_router)

def test_cli_subcommand_train_exists():
    """Test train subcommand is available"""
    from socrata_toolkit.training.train_router_weights import train_router_weights
    assert callable(train_router_weights)

def test_cli_subcommand_demo_exists():
    """Test demo subcommand is available"""
    import sys
    sys.path.insert(0, 'src')
    from training.demo_workflow import run_demo
    assert callable(run_demo)
