#!/usr/bin/env python
"""Quick test runner for domain_rules tests."""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_domain_rules.py", "-v", "--tb=short"],
    cwd="C:\\Users\\ryudk\\nyc_data"
)
sys.exit(result.returncode)
