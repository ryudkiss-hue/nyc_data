"""
Unified Schema Documentation Generator.
Queries Socrata for the definitive schema of all 37 datasets and updates DATASETS.md.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml

# Set up path resolution
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from socrata_toolkit.core.client import SocrataClient, SocrataConfig


def fetch_full_metadata(domain: str, fourfour: str) -> dict[str, Any]:
    """Queries Socrata for full view metadata including column descriptions and types."""
    url = f"https://{domain}/api/views/{fourfour}.json"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.json()

def generate_schema_markdown(dataset_key: str, meta: dict[str, Any]) -> str:
    """Generates a Markdown table for a dataset's schema."""
    name = meta.get("name", dataset_key)
    description = meta.get("description", "No description provided.")
    cols = meta.get("columns", [])

    md = f"### {name} (`{dataset_key}`)\n\n"
    md += f"> {description}\n\n"
    md += "| Field Name | API Name | Data Type | Description |\n"
    md += "| :--- | :--- | :--- | :--- |\n"

    for col in cols:
        fname = col.get("name", "N/A")
        aname = col.get("fieldName", "N/A")
        dtype = col.get("dataTypeName", "N/A")
        desc = col.get("description", "").replace("\n", " ").strip()
        md += f"| **{fname}** | `{aname}` | `{dtype}` | {desc} |\n"

    md += "\n---\n"
    return md

def update_datasets_md(registry: dict[str, Any]):
    """Generates the full DATASETS.md file."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    md_header = "# 🏛️ NYC DOT Socrata Toolkit Dataset Directory\n\n"
    md_header += f"**Last Generated:** {now}\n\n"
    md_header += "This document serves as the definitive technical reference for all 37 datasets integrated into the toolkit.\n\n"
    md_header += "| # | Official Title | 4x4 ID | Category | Link |\n"
    md_header += "| :--- | :--- | :--- | :--- | :--- |\n"

    schema_details = "\n## 📂 Detailed Schemas\n\n"

    count = 1
    for key, info in registry.items():
        domain = info.get("domain", "data.cityofnewyork.us")
        fourfour = info["fourfour"]
        label = info.get("label", key)
        group = info.get("group", "General")

        print(f"📡 Fetching schema for {label} [{fourfour}]...")
        try:
            full_meta = fetch_full_metadata(domain, fourfour)
            md_header += f"| {count} | **{label}** | `{fourfour}` | {group} | [Jump to Schema](#{key}) |\n"
            schema_details += generate_schema_markdown(key, full_meta)
            count += 1
        except Exception as e:
            print(f"❌ Failed to fetch meta for {key}: {e}")
            md_header += f"| {count} | **{label}** | `{fourfour}` | {group} | *Fetch Failed* |\n"

    footer = "\n---\n\n## 🛠️ Automated Discovery Workflow\n\nTo discover and integrate a new dataset, run:\n```bash\npython scripts/discover_socrata.py --id [FOUR-FOUR]\n```\n"

    dest = _REPO_ROOT / "DATASETS.md"
    with open(dest, "w", encoding="utf-8") as f:
        f.write(md_header + schema_details + footer)
    print(f"✅ DATASETS.md updated at {dest}")

if __name__ == "__main__":
    datasets_path = _REPO_ROOT / "config" / "datasets.yaml"
    with open(datasets_path) as f:
        config = yaml.safe_load(f)

    registry = config.get("datasets", {})
    update_datasets_md(registry)

