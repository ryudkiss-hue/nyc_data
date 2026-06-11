#!/usr/bin/env python
"""
Analyze job descriptions from cityjobs.nyc.gov to identify key datasets
and workflows for each project analyst position.
"""

import sys
sys.path.insert(0, 'src')

import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

# Job URLs provided by user
JOB_URLS = [
    "https://cityjobs.nyc.gov/job/project-analyst-sw-in-manhattan-jid-35715",
    "https://cityjobs.nyc.gov/job/sw-project-analyst-in-manhattan-jid-42159",
]

# Map keywords from job descriptions to datasets and workflows
KEYWORD_TO_DATASETS = {
    "ramp": ["ramp_progress", "ramp_complaints", "ramp_locations"],
    "accessible": ["ramp_progress", "ramp_locations", "complaints_311"],
    "ada": ["ramp_progress", "ramp_locations"],
    "accessibility": ["ramp_progress", "ramp_locations", "complaints_311"],
    "inspection": [
        "inspection",
        "violations",
        "dismissals",
        "correspondences",
        "reinspection",
    ],
    "violation": ["violations", "dismissals", "inspection"],
    "complaint": ["complaints_311", "ramp_complaints", "correspondences"],
    "311": ["complaints_311"],
    "permit": [
        "street_permits",
        "permit_stipulations",
        "capital_intersections",
    ],
    "construction": [
        "street_construction_inspections",
        "street_permits",
        "street_closures_block",
        "capital_intersections",
    ],
    "conflict": ["street_permits", "inspection", "street_construction_inspections"],
    "street": [
        "street_permits",
        "street_construction_inspections",
        "street_resurfacing_schedule",
        "street_closures_block",
    ],
    "project management": [
        "street_permits",
        "street_construction_inspections",
        "capital_blocks",
        "capital_intersections",
    ],
    "schedule": ["street_resurfacing_schedule", "ramp_progress"],
    "budget": [
        "capital_blocks",
        "capital_intersections",
        "street_permits",
    ],
    "performance": ["inspection", "violations", "dismissals"],
    "quality": ["violations", "complaints_311"],
    "data": ["complaints_311", "violations", "inspection"],
}

def fetch_job_description(url):
    """Fetch and parse job description from cityjobs.nyc.gov"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract job title
        title_elem = soup.find('h1', class_='job-title') or soup.find('h1')
        title = title_elem.text.strip() if title_elem else "Unknown"

        # Extract job description content
        desc_elem = soup.find('div', class_='job-description') or soup.find(
            'div', {'class': re.compile('.*description.*')}
        )
        description = desc_elem.text if desc_elem else ""

        # Clean up text
        description = re.sub(r'\s+', ' ', description).strip()

        return {
            "title": title,
            "url": url,
            "description": description[:2000],  # First 2000 chars
            "raw_html": response.text,
        }
    except Exception as e:
        return {
            "title": "Error",
            "url": url,
            "error": str(e),
        }


def extract_keywords(text):
    """Extract relevant keywords from job description"""
    text_lower = text.lower()
    found_keywords = set()

    for keyword in KEYWORD_TO_DATASETS.keys():
        if keyword in text_lower:
            found_keywords.add(keyword)

    return list(found_keywords)


def map_to_datasets(keywords):
    """Map keywords to datasets"""
    datasets = set()
    for keyword in keywords:
        if keyword in KEYWORD_TO_DATASETS:
            datasets.update(KEYWORD_TO_DATASETS[keyword])
    return list(datasets)


def main():
    print("=" * 70)
    print("ANALYZING JOB DESCRIPTIONS")
    print("=" * 70)

    results = {
        "timestamp": datetime.now().isoformat(),
        "jobs": [],
    }

    for url in JOB_URLS:
        print(f"\n[FETCHING] {url}")

        job_data = fetch_job_description(url)

        if "error" in job_data:
            print(f"  Error: {job_data['error']}")
            continue

        print(f"  Title: {job_data['title']}")

        # Extract keywords
        keywords = extract_keywords(job_data["description"])
        print(f"  Keywords found: {', '.join(sorted(keywords)[:10])}")

        # Map to datasets
        datasets = list(set(map_to_datasets(keywords)))
        print(f"  Relevant datasets: {len(datasets)}")

        job_analysis = {
            "title": job_data["title"],
            "url": url,
            "keywords": keywords,
            "datasets": datasets,
            "description_excerpt": job_data["description"][:500],
        }

        results["jobs"].append(job_analysis)

    # Save results
    output_file = "job_description_analysis.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n[SUCCESS] Analysis saved to {output_file}")

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for job in results["jobs"]:
        print(f"\n{job['title']}")
        print("-" * 70)
        print(f"Datasets: {len(job['datasets'])}")
        for ds in sorted(job['datasets']):
            print(f"  - {ds}")

    return results


if __name__ == "__main__":
    main()
