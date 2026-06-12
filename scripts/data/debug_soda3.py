import os

import requests
from dotenv import load_dotenv

from socrata_toolkit.core.client import SocrataClient, SocrataConfig

load_dotenv()

def debug_soda3():
    token = os.getenv("SOCRATA_APP_TOKEN")
    client = SocrataClient(SocrataConfig(app_token=token))

    # Try fetching a small batch from 'built' (ugc8-s3f6)
    fourfour = "ugc8-s3f6"
    domain = "data.cityofnewyork.us"
    url = f"https://{domain}/api/v3/views/{fourfour}/query.json"

    soql = "SELECT * LIMIT 100 OFFSET 0"
    payload = {
        "query": soql
    }

    headers = {
        "Content-Type": "application/json",
        "X-App-Token": token
    }

    print(f"Testing SODA3 POST to {url}")

    resp = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {resp.status_code}")
    try:
        data = resp.json()
        if data:
            all_keys = set()
            for row in data:
                all_keys.update(row.keys())
            print(f"All Keys across 100 records: {sorted(list(all_keys))}")
        else:
            print("No data returned.")
    except:
        print(f"Raw Response: {resp.text}")

if __name__ == "__main__":
    debug_soda3()
