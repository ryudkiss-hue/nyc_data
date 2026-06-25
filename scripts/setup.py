"""
Interactive setup script for NYC DOT SIM Fuzzy Router.
Installs dependencies, initializes config, validates deployment.
"""
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run shell command with error handling"""
    print(f"\n[SETUP] {description}...")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"ERROR: {description} failed")
        sys.exit(1)


def main():
    print("\n" + "="*60)
    print("NYC DOT SIM Fuzzy Router - Setup")
    print("="*60)
    
    run_command("pip install -e '.[dev,mission]'", "Installing package")
    run_command("python3 training/precompute_embeddings.py config/metric_registry_full.json", 
                "Precomputing embeddings")
    run_command("python3 training/validate_deployment.py", "Validating deployment")
    run_command("pytest tests/socrata_toolkit/core tests/socrata_toolkit/training -q", 
                "Running tests")
    run_command("python3 training/demo_workflow.py", "Running demo")
    
    print("\n" + "="*60)
    print("SETUP COMPLETE")
    print("You can now use: socrata-nlquery 'your question here'")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
