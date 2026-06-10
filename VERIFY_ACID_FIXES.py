#!/usr/bin/env python3
"""
Verification script for ACID reliability fixes.
Run this to validate all fixes are working correctly.
"""

import sys
import subprocess
from pathlib import Path

def run_command(cmd: list[str], description: str) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    print("\n" + "="*70)
    print("Testing: " + description)
    print("Command: " + " ".join(cmd))
    print("="*70)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8',
            errors='replace'
        )

        if result.returncode == 0:
            print("[PASS] " + description)
            return True, result.stdout + result.stderr
        else:
            print("[FAIL] " + description)
            print("STDOUT:", result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
            print("STDERR:", result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
            return False, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        print("[TIMEOUT] " + description)
        return False, "Test timed out"
    except Exception as e:
        print("[ERROR] " + description)
        print("Error: " + str(e))
        return False, str(e)

def main():
    """Run all verification tests."""
    print("\n" + "="*70)
    print("NYC DOT Socrata Toolkit - ACID Reliability Fixes Verification")
    print("="*70)

    results = []

    # Test 1: ACID Tests
    success, output = run_command(
        [sys.executable, "-m", "pytest", "tests/test_acid_fixes.py", "-v", "--tb=short"],
        "ACID Reliability Tests (17 tests)"
    )
    results.append(("ACID Tests", success))

    # Test 2: Cache Manager Tests
    success, output = run_command(
        [sys.executable, "-m", "pytest", "tests/test_cache_manager.py", "-v", "--tb=short"],
        "Cache Manager Tests (regression)"
    )
    results.append(("Cache Manager Tests", success))

    # Test 3: DuckDB Store Tests (only our new tests)
    success, output = run_command(
        [
            sys.executable, "-m", "pytest",
            "tests/test_duckdb_store_coverage.py::TestDuckDBManagerConnection",
            "-v", "--tb=short"
        ],
        "DuckDB Connection Tests (regression)"
    )
    results.append(("DuckDB Connection Tests", success))

    # Summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)

    for test_name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(status + " " + test_name)

    all_passed = all(success for _, success in results)

    print("\n" + "="*70)
    if all_passed:
        print("[SUCCESS] ALL ACID FIXES VERIFIED SUCCESSFULLY")
        print("\nThe following fixes are working correctly:")
        print("  1. DuckDB Connection Pooling (RLock for thread safety)")
        print("  2. Transactional Write Boundaries (BEGIN/COMMIT with rollback)")
        print("  3. Session State Persistence (DuckDB-backed storage)")
        print("  4. Manifest File Locking (fcntl/msvcrt for atomic updates)")
        print("\nReady for production deployment.")
    else:
        print("[FAILURE] SOME VERIFICATION TESTS FAILED")
        print("\nPlease review the output above for details.")
        sys.exit(1)

    print("="*70 + "\n")

if __name__ == "__main__":
    main()
