import os
import sys
from pathlib import Path
import yaml
import json
import pandas as pd
import requests

# Set up path resolution
_src_path = str((Path(__file__).resolve().parent / "src").absolute())
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

try:
    from socrata_toolkit import SocrataClient, SocrataConfig
    from socrata_toolkit.quality.validator import QualityValidator
except ImportError:
    # Fallback for different envs
    sys.path.insert(0, "C:\\Users\\ryudk\\nyc_data\\src")
    from socrata_toolkit import SocrataClient, SocrataConfig
    from socrata_toolkit.quality.validator import QualityValidator

def run_audit():
    print("🚀 Initializing 360-Degree Data Integrity Scan...")
    
    # 1. Load Dataset Configuration
    config_path = Path("config/datasets.yaml")
    with open(config_path, "r") as f:
        full_cfg = yaml.safe_load(f)
    datasets = full_cfg.get("datasets", {})
    
    audit_results = []
    token = os.getenv("SOCRATA_TOKEN", "")
    client = SocrataClient(SocrataConfig(app_token=token))
    validator = QualityValidator()

    # 2. Iterate and Verify
    for key, info in datasets.items():
        fourfour = info["fourfour"]
        label = info["label"]
        print(f"🔍 Auditing: {label} ({fourfour})...")
        
        status = "OK"
        details = {}
        
        try:
            # A. Existence & Metadata Check
            meta_url = f"https://data.cityofnewyork.us/api/views/{fourfour}.json"
            resp = requests.get(meta_url, timeout=10)
            if resp.status_code != 200:
                status = "FAIL (Not Found)"
                details = {"error": f"Socrata API returned {resp.status_code}"}
            else:
                meta = resp.json()
                details["columns"] = [col["name"] for col in meta.get("columns", [])]
                details["row_count"] = meta.get("numberOfRows", "Unknown")
                details["last_updated"] = meta.get("rowsUpdatedAt", "Unknown")
                
                # B. Integrity Check (Sample Fetch)
                df = client.fetch_dataframe(
                    domain="data.cityofnewyork.us",
                    fourfour=fourfour,
                    max_rows=100
                )
                
                if df.empty:
                    status = "WARN (Empty Sample)"
                else:
                    # Clean DF: Drop columns with dicts/lists for validation
                    clean_df = df.copy()
                    for col in clean_df.columns:
                        if clean_df[col].apply(lambda x: isinstance(x, (dict, list))).any():
                            clean_df = clean_df.drop(columns=[col])

                    # C. Mandate Validation (Four Moments)
                    val_result = validator.validate(clean_df, table_name=key)
                    details["validation"] = {
                        "pass_rate": val_result.pass_rate,
                        "status": val_result.status.value,
                        "failed_expectations": [e.message for e in val_result.failed_expectations]
                    }
        except Exception as e:
            status = "ERROR"
            details = {"error": str(e)}
        
        audit_results.append({
            "key": key,
            "fourfour": fourfour,
            "label": label,
            "status": status,
            "details": details
        })

    # 3. Save Final Audit Report
    report_path = Path("final_comprehensive_scan.json")
    with open(report_path, "w") as f:
        json.dump(audit_results, f, indent=2, default=str)
    
    print(f"✅ Audit Complete. Results saved to {report_path.absolute()}")

if __name__ == "__main__":
    run_audit()
