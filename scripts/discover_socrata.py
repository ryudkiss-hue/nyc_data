import os
import sys
import yaml
import requests
import pandas as pd
from pathlib import Path
from typing import Dict, Any

# Set up path resolution
_src_path = str((Path(__file__).resolve().parent.parent / "src").absolute())
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

try:
    from socrata_toolkit import SocrataClient, SocrataConfig
    from socrata_toolkit.quality.validator import QualityValidator
except ImportError:
    sys.path.insert(0, "C:\\Users\\ryudk\\nyc_data\\src")
    from socrata_toolkit import SocrataClient, SocrataConfig
    from socrata_toolkit.quality.validator import QualityValidator

def discover_dataset(fourfour: str, label: str = None) -> Dict[str, Any]:
    """
    Automated agential discovery of a new Socrata dataset.
    Queries metadata, extracts columns, and validates integrity.
    """
    print(f"🕵️  Discovering Metadata for {fourfour}...")
    meta_url = f"https://data.cityofnewyork.us/api/views/{fourfour}.json"
    
    resp = requests.get(meta_url, timeout=15)
    resp.raise_for_status()
    meta = resp.json()
    
    # Official metadata
    official_label = label or meta.get("name", "Unknown Dataset")
    columns = [col["name"] for col in meta.get("columns", [])]
    last_updated = meta.get("rowsUpdatedAt", 0)
    
    # Integrity Check (Real Sample Fetch)
    client = SocrataClient(SocrataConfig(app_token=os.getenv("SOCRATA_TOKEN", "")))
    df = client.fetch_dataframe("data.cityofnewyork.us", fourfour, max_rows=100)
    
    status = "OK"
    if not df.empty:
        validator = QualityValidator()
        # Filter for validation
        clean_df = df.copy()
        for col in clean_df.columns:
            if clean_df[col].apply(lambda x: isinstance(x, (dict, list))).any():
                clean_df = clean_df.drop(columns=[col])
        
        val_result = validator.validate(clean_df, table_name=fourfour)
        status = val_result.status.value
    
    return {
        "fourfour": fourfour,
        "label": official_label,
        "url": f"https://data.cityofnewyork.us/d/{fourfour}",
        "columns": columns,
        "last_updated": last_updated,
        "integrity_status": status
    }

def update_registry(dataset_info: Dict[str, Any], key: str):
    """Appends the discovered info to datasets.yaml."""
    config_path = Path("config/datasets.yaml")
    with open(config_path, "r") as f:
        full_cfg = yaml.safe_load(f)
    
    if "datasets" not in full_cfg:
        full_cfg["datasets"] = {}
        
    full_cfg["datasets"][key] = {
        "fourfour": dataset_info["fourfour"],
        "label": dataset_info["label"],
        "url": dataset_info["url"],
        "columns": dataset_info["columns"],
        "last_updated": dataset_info["last_updated"]
    }
    
    with open(config_path, "w") as f:
        yaml.dump(full_cfg, f, sort_keys=False)
    print(f"📝 Registry Updated: {key} added to datasets.yaml")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Automated Socrata Discovery")
    parser.add_argument("--id", required=True, help="The 4x4 Socrata ID (e.g., kpav-sd4t)")
    parser.add_argument("--key", required=True, help="The internal key name (e.g., new_sidewalk_data)")
    
    args = parser.parse_args()
    try:
        info = discover_dataset(args.id)
        update_registry(info, args.key)
    except Exception as e:
        print(f"❌ Discovery Failed: {e}")
