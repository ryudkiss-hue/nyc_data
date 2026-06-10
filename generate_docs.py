import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import yaml

# Set up path resolution
_src_path = str((Path(__file__).resolve().parent / "src").absolute())
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

def generate_csv_directory():
    """Generates an exhaustive CSV from the current datasets.yaml."""
    print("📂 Generating Dataset Directory CSV...")
    config_path = Path("config/datasets.yaml")
    if not config_path.exists():
        print("❌ config/datasets.yaml not found.")
        return

    with open(config_path) as f:
        full_cfg = yaml.safe_load(f)

    datasets = full_cfg.get("datasets", {})
    rows = []

    for key, info in datasets.items():
        rows.append({
            "Key": key,
            "Official Title": info.get("label", ""),
            "4x4 ID": info.get("fourfour", ""),
            "Browser URL": info.get("url", f"https://data.cityofnewyork.us/d/{info.get('fourfour', '')}"),
            "Last Updated (Unix)": info.get("last_updated", ""),
            "Columns": ", ".join(map(str, info.get("columns", [])))
        })

    df = pd.DataFrame(rows)
    output_path = Path("dataset_directory.csv")
    df.to_csv(output_path, index=False)
    print(f"✅ CSV Generated: {output_path.absolute()}")

def generate_markdown_reference():
    """Generates a formal DATASETS.md reference file."""
    print("📖 Generating DATASETS.md Reference...")
    config_path = Path("config/datasets.yaml")
    with open(config_path) as f:
        full_cfg = yaml.safe_load(f)

    datasets = full_cfg.get("datasets", {})

    md_content = "# 🏛️ NYC DOT SIM Dataset Directory\n\n"
    md_content += f"**Last Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    md_content += "This document serves as the technical reference for all 26 datasets integrated into the Manhattan Mission Control Powerhouse.\n\n"
    md_content += "| # | Official Title | 4x4 ID | Schema Link |\n"
    md_content += "| :--- | :--- | :--- | :--- |\n"

    for i, (key, info) in enumerate(datasets.items(), 1):
        md_content += f"| {i} | **{info.get('label', '')}** | `{info.get('fourfour', '')}` | [View Dataset]({info.get('url', '')}) |\n"

    md_content += "\n---\n\n## 🛠️ Automated Discovery Workflow\n\nTo discover and integrate a new dataset, run the following workflow:\n\n"
    md_content += "```python\npython scripts/discover_socrata.py --id [FOUR-FOUR]\n```\n\n"
    md_content += "This workflow will:\n1. Query Socrata Metadata API.\n2. Extract column names and types.\n3. Validate Four Moments (Integrity Check).\n4. Append to `config/datasets.yaml` and update `DATASETS.md`.\n"

    output_path = Path("DATASETS.md")
    output_path.write_text(md_content, encoding="utf-8")
    print(f"✅ Markdown Generated: {output_path.absolute()}")

if __name__ == "__main__":
    generate_csv_directory()
    generate_markdown_reference()
