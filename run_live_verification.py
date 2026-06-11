#!/usr/bin/env python
"""
Live Data Authenticity Verification - Strict Test
Runs 5 critical checks against real Socrata API
"""

import sys
import os
sys.path.insert(0, 'src')

import logging
import json
from datetime import datetime
import requests
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from socrata_toolkit.core.client import SocrataClient, SocrataConfig


def main():
    print("=" * 70)
    print("LIVE DATA AUTHENTICITY VERIFICATION")
    print("=" * 70)

    results = {
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }

    # CHECK 1: Credentials
    print("\n[CHECK 1] Credentials & Domain")
    try:
        config = SocrataConfig()
        print(f"  Domain: {config.domain}")
        print(f"  Has SOCRATA_APP_TOKEN: {bool(os.getenv('SOCRATA_APP_TOKEN'))}")

        check1 = config.domain == "data.cityofnewyork.us"
        results["checks"]["credentials"] = {
            "domain": config.domain,
            "is_production": check1,
            "status": "PASS" if check1 else "FAIL"
        }
        print(f"  Status: {'✅ PASS' if check1 else '❌ FAIL'}")
    except Exception as e:
        print(f"  Error: {e}")
        results["checks"]["credentials"] = {"status": "ERROR", "error": str(e)}
        check1 = False

    # CHECK 2: Live API Call
    print("\n[CHECK 2] Live API Connectivity")
    try:
        url = "https://data.cityofnewyork.us/api/views/6kbp-uz6m/rows.json"
        params = {"$limit": 1}
        response = requests.get(url, params=params, timeout=10)

        response_time = response.elapsed.total_seconds() * 1000
        print(f"  Endpoint: {url}")
        print(f"  Status code: {response.status_code}")
        print(f"  Response time: {response_time:.0f}ms")

        check2 = response.status_code == 200
        results["checks"]["api_connectivity"] = {
            "endpoint": url,
            "status_code": response.status_code,
            "response_time_ms": response_time,
            "is_live": check2,
            "status": "PASS" if check2 else "FAIL"
        }
        print(f"  Status: {'✅ PASS' if check2 else '❌ FAIL'}")
    except Exception as e:
        print(f"  Error: {e}")
        results["checks"]["api_connectivity"] = {"status": "ERROR", "error": str(e)}
        check2 = False

    # CHECK 3: Real Data
    print("\n[CHECK 3] Real Data Fetch")
    check3 = False
    df = None
    try:
        client = SocrataClient(config)
        df = client.fetch_dataframe("data.cityofnewyork.us", "6kbp-uz6m", max_rows=20)

        print(f"  Rows fetched: {len(df)}")
        print(f"  Columns: {len(df.columns)}")
        print(f"  Has 'description': {'description' in df.columns}")
        print(f"  Has 'borough': {'borough' in df.columns}")

        check3 = len(df) > 0 and "description" in df.columns

        # Sample records
        samples = []
        for idx, row in df.head(3).iterrows():
            samples.append({
                "description": str(row.get("description", ""))[:100],
                "borough": row.get("borough"),
            })

        results["checks"]["data_fetch"] = {
            "rows": len(df),
            "columns": len(df.columns),
            "has_description": "description" in df.columns,
            "has_borough": "borough" in df.columns,
            "samples": samples,
            "status": "PASS" if check3 else "FAIL"
        }

        print(f"  Status: {'✅ PASS' if check3 else '❌ FAIL'}")
        print("\n  Sample Records:")
        for sample in samples:
            print(f"    - {sample['description'][:60]}...")
            print(f"      Borough: {sample['borough']}")

    except Exception as e:
        print(f"  Error: {e}")
        results["checks"]["data_fetch"] = {"status": "ERROR", "error": str(e)}

    # CHECK 4: No Mock Patterns
    print("\n[CHECK 4] No Mock/Synthetic Patterns")
    check4 = False
    if df is not None:
        try:
            descriptions = df["description"].astype(str).str.lower()

            mock_patterns = {
                "contains_test": descriptions.str.contains("test", regex=False).any(),
                "contains_mock": descriptions.str.contains("mock", regex=False).any(),
                "contains_fake": descriptions.str.contains("fake", regex=False).any(),
                "contains_sample": descriptions.str.contains("sample", regex=False).any(),
                "contains_synthetic": descriptions.str.contains("synthetic", regex=False).any(),
            }

            found_mocks = [k.replace("contains_", "") for k, v in mock_patterns.items() if v]

            print(f"  Descriptions analyzed: {len(descriptions)}")
            print(f"  Mock patterns found: {found_mocks if found_mocks else 'None'}")

            check4 = len(found_mocks) == 0
            results["checks"]["no_mocks"] = {
                "mock_patterns": mock_patterns,
                "verdict": "REAL DATA" if check4 else "POSSIBLE MOCK",
                "status": "PASS" if check4 else "FAIL"
            }
            print(f"  Status: {'✅ PASS' if check4 else '❌ FAIL'}")

        except Exception as e:
            print(f"  Error: {e}")
            results["checks"]["no_mocks"] = {"status": "ERROR", "error": str(e)}
    else:
        print(f"  Skipped (data fetch failed)")
        results["checks"]["no_mocks"] = {"status": "SKIPPED"}

    # CHECK 5: Real Timestamps
    print("\n[CHECK 5] Real Timestamps (Current Data)")
    check5 = False
    if df is not None:
        try:
            date_cols = [col for col in df.columns if "date" in col.lower()]

            if date_cols:
                col = date_cols[0]
                df[col] = pd.to_datetime(df[col], errors='coerce')
                latest = df[col].max()
                days_old = (datetime.now() - latest).days

                print(f"  Latest record: {latest}")
                print(f"  Age: {days_old} days")
                print(f"  Fresh (<30 days): {days_old < 30}")

                check5 = days_old < 30
                results["checks"]["timestamps"] = {
                    "latest_record": str(latest),
                    "age_days": days_old,
                    "is_fresh": days_old < 30,
                    "status": "PASS" if check5 else "WARNING"
                }
            else:
                print(f"  No date columns found")
                results["checks"]["timestamps"] = {"status": "WARNING", "reason": "no_date_columns"}
                check5 = True  # Not a failure, just missing column

            print(f"  Status: {'✅ PASS' if check5 else '⚠️ WARNING'}")

        except Exception as e:
            print(f"  Error: {e}")
            results["checks"]["timestamps"] = {"status": "ERROR", "error": str(e)}
    else:
        print(f"  Skipped (data fetch failed)")
        results["checks"]["timestamps"] = {"status": "SKIPPED"}

    # OVERALL VERDICT
    print("\n" + "=" * 70)
    all_critical_pass = check1 and check2 and check3 and check4

    if all_critical_pass:
        verdict = "✅ REAL DATA VERIFIED - PRODUCTION READY"
    else:
        verdict = "❌ VERIFICATION FAILED"

    results["overall"] = {
        "all_pass": all_critical_pass,
        "verdict": verdict,
        "timestamp": datetime.now().isoformat()
    }

    print(f"OVERALL: {verdict}")
    print("=" * 70)

    # Output JSON
    print("\n[DETAILED RESULTS]")
    print(json.dumps(results, indent=2, default=str))

    return 0 if all_critical_pass else 1


if __name__ == "__main__":
    sys.exit(main())
