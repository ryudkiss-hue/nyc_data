#!/usr/bin/env python
"""
Search Socrata for all NYC DOT datasets relevant to SIM project managers.

Project Manager Workflows:
- Program managers: ramp completion, budget, scheduling
- Operations managers: inspections, violations, conflicts, SLAs
"""

import sys
sys.path.insert(0, 'src')

import json
import logging
from datetime import datetime

import requests

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def search_socrata_all():
    """Search all datasets on NYC Open Data portal."""

    print("=" * 70)
    print("SEARCHING SOCRATA FOR NYC DOT DATASETS")
    print("=" * 70)

    domain = "data.cityofnewyork.us"
    base_url = f"https://{domain}/api/catalog/v1"

    # Keywords relevant to SIM project managers
    search_terms = [
        "sidewalk",
        "inspection",
        "violation",
        "ramp",
        "accessibility",
        "ADA",
        "curb",
        "street",
        "permit",
        "construction",
        "complaint",
        "311",
        "tree",
        "pothole",
        "pavement",
        "concrete",
        "hazard",
        "DOT",
    ]

    all_datasets = {}

    for term in search_terms:
        print(f"\n[SEARCHING] '{term}'...")

        try:
            url = f"{base_url}/search"
            params = {
                "q": term,
                "domains": domain,
                "limit": 50,
                "offset": 0,
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                print(f"  Error: {response.status_code}")
                continue

            data = response.json()
            results = data.get("results", [])

            print(f"  Found {len(results)} datasets")

            for item in results:
                dataset_id = item.get("resource", {}).get("id")
                name = item.get("resource", {}).get("name")
                description = item.get("resource", {}).get("description", "")
                rows = item.get("resource", {}).get("rowsUpdatedAt")

                if dataset_id and name:
                    if dataset_id not in all_datasets:
                        all_datasets[dataset_id] = {
                            "name": name,
                            "description": description[:200],
                            "search_terms": [term],
                            "last_updated": rows,
                        }
                    else:
                        # Track multiple search terms that match
                        if term not in all_datasets[dataset_id]["search_terms"]:
                            all_datasets[dataset_id]["search_terms"].append(term)

        except Exception as e:
            print(f"  Error: {e}")

    return all_datasets


def categorize_datasets(datasets):
    """Categorize datasets by relevance to project manager workflows."""

    categories = {
        "Inspection & Violations": [],
        "Ramp & Accessibility": [],
        "Permits & Construction": [],
        "Complaints & 311": [],
        "Street Infrastructure": [],
        "Other": [],
    }

    keywords = {
        "Inspection & Violations": ["violation", "inspection", "sim unit"],
        "Ramp & Accessibility": ["ramp", "accessibility", "ada", "curb", "accessible"],
        "Permits & Construction": ["permit", "construction", "street work"],
        "Complaints & 311": ["complaint", "311", "service request"],
        "Street Infrastructure": ["street", "pothole", "pavement", "concrete", "sidewalk"],
    }

    for dataset_id, info in datasets.items():
        name_lower = (info["name"] + " " + info["description"]).lower()

        categorized = False
        for category, kws in keywords.items():
            if any(kw in name_lower for kw in kws):
                categories[category].append((dataset_id, info))
                categorized = True
                break

        if not categorized:
            categories["Other"].append((dataset_id, info))

    return categories


def main():
    datasets = search_socrata_all()

    print("\n" + "=" * 70)
    print(f"TOTAL DATASETS FOUND: {len(datasets)}")
    print("=" * 70)

    # Categorize
    categories = categorize_datasets(datasets)

    # Output organized results
    all_relevant = {}

    for category, items in categories.items():
        if not items:
            continue

        print(f"\n[{category}] - {len(items)} datasets")
        print("-" * 70)

        for dataset_id, info in sorted(items, key=lambda x: x[1]["name"]):
            print(f"\n  📊 {info['name']}")
            print(f"     ID: {dataset_id}")
            print(f"     Terms: {', '.join(info['search_terms'][:3])}")
            if info["description"]:
                print(f"     Desc: {info['description']}")

            all_relevant[dataset_id] = {
                "name": info["name"],
                "category": category,
                "fourfour": dataset_id,
                "search_terms": info["search_terms"],
                "description": info["description"],
            }

    # Save comprehensive list
    output = {
        "timestamp": datetime.now().isoformat(),
        "total_datasets": len(all_relevant),
        "by_category": {
            cat: len([x for x in items if x])
            for cat, items in categories.items()
        },
        "datasets": all_relevant,
    }

    print("\n" + "=" * 70)
    print("SAVING RESULTS TO socrata_datasets.json")
    print("=" * 70)

    with open("socrata_datasets.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"✅ Saved {len(all_relevant)} datasets to socrata_datasets.json")

    return output


if __name__ == "__main__":
    main()
