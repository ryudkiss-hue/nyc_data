import os
import sys

# Ensure the parent directory is in the path so we can import the toolkit
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from socrata_toolkit.core import SocrataClient


def test_tokens():
    print("--- 1. Testing Environment Variables ---")
    app_token = os.getenv("SOCRATA_APP_TOKEN")
    app_secret = os.getenv("SOCRATA_APP_SECRET")

    if not app_token:
        print("❌ SOCRATA_APP_TOKEN is missing!")
    else:
        print(f"✅ SOCRATA_APP_TOKEN found: {app_token[:5]}...{app_token[-3:]}")

    if not app_secret:
        print("❌ SOCRATA_APP_SECRET is missing!")
    else:
        print(f"✅ SOCRATA_APP_SECRET found: {app_secret[:5]}...{app_secret[-3:]}")

    print("\n--- 2. Testing Socrata API Authentication ---")
    if app_token:
        try:
            # Using the SocrataClient to fetch 1 row to verify authentication
            client = SocrataClient()
            print("Attempting to fetch 1 record from NYC 311 Dataset (erm2-nwe9)...")
            df = client.fetch_dataframe("data.cityofnewyork.us", "erm2-nwe9", max_rows=1)

            if not df.empty:
                print("✅ Success! Authenticated and retrieved data.")
        except Exception as e:
            print(f"❌ Failed to connect using SocrataClient: {e}")
    else:
        print("⚠️ Skipping API test since tokens are missing.")


if __name__ == "__main__":
    test_tokens()
