#!/usr/bin/env python3
"""Quick JSON verification script for config files."""
import json
import sys

files = [
    'data/dataset_config.json',
    'data/analytics_config.json'
]

all_valid = True
for filepath in files:
    try:
        with open(filepath) as f:
            data = json.load(f)
        print(f"✓ {filepath}: Valid JSON ({len(data)} top-level keys)")
    except Exception as e:
        print(f"✗ {filepath}: Invalid JSON - {e}")
        all_valid = False

if all_valid:
    print("\nAll config files are valid JSON!")
    sys.exit(0)
else:
    sys.exit(1)
