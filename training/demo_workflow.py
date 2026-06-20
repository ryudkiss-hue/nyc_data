"""
End-to-end demo showing dual-tier fuzzy router in action.
Demonstrates: question → Tier 1 routing → optional Tier 2 expansion → feedback.
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, 'src')

from socrata_toolkit.core.cli_nlquery import run_nl_query
from socrata_toolkit.core.config import get_config


def run_demo():
    """Run interactive demo workflow"""
    config = get_config()
    kpi_registry = config.load_kpi_registry()
    research_questions = config.load_research_questions()
    embeddings_cache = config.load_embeddings_cache()
    
    demo_questions = [
        ("violations fixed by borough", False),
        ("Why are violations increasing?", True),
        ("ramp completion rate", False),
    ]
    
    print("\n" + "="*60)
    print("NYC DOT SIM Dual-Tier Fuzzy Router - DEMO")
    print("="*60)
    
    for i, (question, expand) in enumerate(demo_questions, 1):
        print(f"\n[Question {i}] {question}")
        print(f"  Mode: {'Tier 2 (expansion enabled)' if expand else 'Tier 1 (instant)'}")
        
        result = run_nl_query(
            question=question,
            kpi_registry=kpi_registry,
            research_questions=research_questions,
            embeddings_cache=embeddings_cache,
            expand=expand
        )
        
        if result.get('matched_kpi'):
            print(f"  Matched KPI: {result['kpi_name']} ({result['matched_kpi']})")
            print(f"  Confidence: {result['confidence']:.0%}")
            print(f"  Datasets: {', '.join(ds['key'] for ds in result['datasets'])}")
            
            if expand and 'tier_2_expansion' in result:
                synthesis = result['tier_2_expansion'].get('claude_synthesis', '')
                print(f"  Claude Synthesis: {synthesis[:100]}...")
        else:
            print(f"  Result: No match found")
    
    print("\n" + "="*60)
    print("Demo complete. System ready for production use.")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_demo()
