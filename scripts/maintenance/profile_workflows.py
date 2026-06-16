import cProfile
import pstats
import io
import os
import sys
from pathlib import Path
import pandas as pd
import time

# Ensure project root is in path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.analytics import run_all_workflows

def generate_mock_data(rows=10000):
    """Generate synthetic municipal data for profiling."""
    return pd.DataFrame({
        "id": range(rows),
        "val": range(rows),
        "category": ["A", "B", "C", "D"] * (rows // 4),
        "bbl": [str(1000000000 + i) for i in range(rows)],
        "date": pd.date_range("2023-01-01", periods=rows, freq="H")
    })

def main():
    print("🚀 Initializing Performance Profiling for NYC DOT Socrata Toolkit...")
    
    # Setup test frames
    frames = {
        "lot_info": generate_mock_data(5000),
        "mappluto": generate_mock_data(5000),
        "complaints_311": generate_mock_data(10000),
        "weekly_construction": generate_mock_data(2000),
        "street_permits": generate_mock_data(3000),
        "capital_blocks": generate_mock_data(1000),
        "violations": generate_mock_data(5000),
        "tree_damage": generate_mock_data(2000),
        "built": generate_mock_data(4000),
        "ramp_progress": generate_mock_data(2000),
    }

    # CPU Profiling
    pr = cProfile.Profile()
    pr.enable()
    
    start_time = time.perf_counter()
    results = run_all_workflows(frames)
    end_time = time.perf_counter()
    
    pr.disable()
    
    print(f"\n✅ Workflows completed in {end_time - start_time:.4f} seconds")
    
    # Analysis
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(30)  # Top 30 functions
    
    print("\n" + "="*80)
    print("TOP CUMULATIVE TIME FUNCTIONS")
    print("="*80)
    print(s.getvalue())
    
if __name__ == "__main__":
    main()
