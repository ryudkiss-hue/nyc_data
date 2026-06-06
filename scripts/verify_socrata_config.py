#!/usr/bin/env python3
"""Verify Socrata API token configuration and live data connectivity.

This script checks:
1. SOCRATA_APP_TOKEN environment variable
2. Live connectivity to NYC Open Data
3. Dataset metadata retrieval
4. Ability to fetch live data
"""

import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from socrata_toolkit.core.client import SocrataClient, SocrataConfig


def print_status(status: str, message: str):
    """Print a status message."""
    icon = "✓" if status == "ok" else "✗" if status == "error" else "⚠"
    print(f"{icon} {message}")


def check_token():
    """Check if Socrata token is configured."""
    token = os.getenv("SOCRATA_APP_TOKEN")

    if not token:
        print_status("warning", "SOCRATA_APP_TOKEN not set")
        print("  → Public data access available (limited rate limits)")
        print("  → To enable full-corpus fetches, set SOCRATA_APP_TOKEN in .env")
        return False

    if token == "your-socrata-app-token-here":
        print_status("warning", "SOCRATA_APP_TOKEN is a placeholder")
        print("  → Public data access available (limited rate limits)")
        print("  → To enable full-corpus fetches, replace with real token")
        return False

    print_status("ok", f"SOCRATA_APP_TOKEN configured: {token[:15]}...")
    return True


def check_connectivity():
    """Check connectivity to Socrata API."""
    try:
        client = SocrataClient(SocrataConfig())

        # Try to search for datasets
        results = client.search("sidewalk", limit=1)
        print_status("ok", "Connected to Socrata API (NYC Open Data)")
        return True
    except Exception as e:
        print_status("error", f"Failed to connect to Socrata API: {e}")
        return False


def check_dataset_access():
    """Check if we can access dataset metadata and sample data."""
    try:
        client = SocrataClient(SocrataConfig())
        domain = "data.cityofnewyork.us"

        # Test with ramp progress dataset (fourfour: e7gc-ub6z)
        fourfour = "e7gc-ub6z"
        print(f"\n  Testing dataset access (fourfour: {fourfour})...")

        # Get metadata
        meta = client.get_metadata(domain, fourfour)
        name = meta.name if hasattr(meta, 'name') and callable(meta.name) else meta.name if hasattr(meta, 'name') else "Unknown"
        cols = meta.num_columns if hasattr(meta, 'num_columns') and callable(meta.num_columns) else len(meta.columns) if hasattr(meta, 'columns') else "Unknown"
        rows = meta.num_rows if hasattr(meta, 'num_rows') and callable(meta.num_rows) else meta.rows if hasattr(meta, 'rows') else "Unknown"
        print_status("ok", f"Retrieved metadata for dataset: {name}")
        print(f"    → Columns: {cols}")
        print(f"    → Rows: {rows}")

        # Try to fetch sample data
        df = client.fetch_dataframe(domain, fourfour, max_rows=5)
        print_status("ok", f"Fetched {len(df)} sample rows")
        print(f"    → Last update: {datetime.utcnow().isoformat()}")

        return True
    except Exception as e:
        print_status("error", f"Failed to access dataset: {e}")
        return False


def check_cache():
    """Check if DuckDB cache is available."""
    try:
        import duckdb
        cache_dir = os.getenv("SOCRATA_CACHE_DIR", "/tmp/socrata_cache")
        os.makedirs(cache_dir, exist_ok=True)

        test_db = os.path.join(cache_dir, "test.duckdb")
        conn = duckdb.connect(test_db)
        conn.execute("SELECT 1")
        conn.close()

        if os.path.exists(test_db):
            os.remove(test_db)

        print_status("ok", f"DuckDB cache available: {cache_dir}")
        return True
    except Exception as e:
        print_status("error", f"Failed to initialize cache: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Socrata Configuration & Connectivity Verification")
    print("=" * 60)

    print("\n1. Token Configuration:")
    token_ok = check_token()

    print("\n2. API Connectivity:")
    conn_ok = check_connectivity()

    print("\n3. Dataset Access:")
    data_ok = check_dataset_access()

    print("\n4. Cache System:")
    cache_ok = check_cache()

    print("\n" + "=" * 60)
    if token_ok and conn_ok and data_ok and cache_ok:
        print("✓ All checks passed! System is ready for production.")
        return 0
    elif conn_ok and data_ok and cache_ok:
        print("⚠ System is functional with public data access.")
        print("  To enable full-corpus dataset fetches, configure SOCRATA_APP_TOKEN")
        return 0
    else:
        print("✗ Configuration incomplete. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
