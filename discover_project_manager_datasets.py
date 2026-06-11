#!/usr/bin/env python
"""
Discover all NYC DOT datasets relevant to project managers.

Uses known working datasets + direct Socrata metadata queries.
"""

import sys
sys.path.insert(0, 'src')

import json
from datetime import datetime

from socrata_toolkit.core.client import SocrataClient, SocrataConfig

# Known working datasets (verified in live test)
KNOWN_DATASETS = {
    # Inspection & Violations (Core SIM)
    "inspection": "dntt-gqwq",
    "violations": "6kbp-uz6m",
    "dismissals": "p4u2-3jgx",
    "correspondences": "bheb-sjfi",
    "reinspection": "gx72-kirf",
    "tree_damage": "j6v2-6uxq",
    "curb_metal_protruding": "i2y3-sx2e",

    # Ramp & Accessibility Program
    "ramp_locations": "ufzp-rrqu",
    "ramp_complaints": "jagj-gttd",
    "ramp_progress": "e7gc-ub6z",

    # Permits & Construction
    "street_permits": "tqtj-sjs8",
    "weekly_construction": "r528-jcks",
    "capital_blocks": "jvk9-k4re",
    "capital_intersections": "97nd-ff3i",
    "street_construction_inspections": "ydkf-mpxb",
    "street_closures_block": "i6b5-j7bu",
    "permit_stipulations": "gsgx-6efw",
    "street_resurfacing_schedule": "xnfm-u3k5",
    "street_resurfacing_inhouse": "ffaf-8mrv",

    # Complaints & Context
    "complaints_311": "erm2-nwe9",
    "step_streets": "u9au-h79y",
    "sidewalk_planimetric": "vfx9-tbb6",
    "pedestrian_demand": "fwpa-qxaf",
    "mappluto": "64uk-42ks",
}

# Map datasets to project manager workflows
WORKFLOW_MAPPING = {
    # PROGRAM MANAGERS (Ramp program)
    "ramp_progress": [
        "ramp-progress",  # Track completion
        "forecasting",  # Predict completion dates
        "impact-assessment",  # Measure community impact
    ],
    "ramp_complaints": [
        "complaint-response",  # Track complaint response
        "sentiment-tracking",  # Public feedback
    ],
    "ramp_locations": [
        "hotspot-analysis",  # Identify service gaps
        "resource-allocation",  # Plan inspector deployment
    ],

    # OPERATIONS MANAGERS (Inspections)
    "violations": [
        "violations-triage",  # Prioritize violations
        "root-cause",  # Investigate patterns
    ],
    "inspection": [
        "violations-triage",
        "velocity-analysis",  # Inspector productivity
        "inspector-performance",  # Inspector scoring
    ],
    "dismissals": [
        "dismissal-analysis",  # Audit dismissal patterns
        "appeal-tracking",  # Monitor appeals
    ],

    # PROJECT MANAGERS (Construction coordination)
    "street_permits": [
        "conflict-detect",  # Find permit/inspection conflicts
        "resource-allocation",  # Plan inspector routes
    ],
    "street_construction_inspections": [
        "conflict-detect",  # Detect construction conflicts
    ],

    # ALL MANAGERS (Data health)
    "inspection": ["dataset-health", "sla-compliance"],
    "violations": ["dataset-health", "sla-compliance"],
    "complaints_311": ["dataset-health", "sla-compliance"],
}


def main():
    print("=" * 70)
    print("DISCOVERING PROJECT MANAGER DATASETS")
    print("=" * 70)

    client = SocrataClient(SocrataConfig())
    discovered = {}
    freshness_report = []

    print(f"\n[DISCOVERING] Querying metadata for {len(KNOWN_DATASETS)} datasets...")

    for name, fourfour in sorted(KNOWN_DATASETS.items()):
        try:
            metadata = client.get_metadata("data.cityofnewyork.us", fourfour)

            dataset_info = {
                "fourfour": fourfour,
                "name": metadata.name,
                "description": metadata.description[:200] if metadata.description else "",
                "rows": metadata.row_count or 0,
                "workflows": WORKFLOW_MAPPING.get(name, []),
            }

            discovered[name] = dataset_info

            # For freshness, we'd need to query the actual dataset or use rowsUpdatedAt
            # which isn't in the metadata. Use a simple heuristic: presence of recent data
            age_days = None  # Would need additional API call to get
            freshness = "? (check separately)"

            freshness_report.append((name, age_days, freshness))

            print(f"  [OK] {name:30s} {metadata.row_count or 0:>10,} rows")

        except Exception as e:
            print(f"  [ERROR] {name:30s} {str(e)[:40]}")

    # Organize by manager type
    print("\n" + "=" * 70)
    print("DATASETS BY PROJECT MANAGER ROLE")
    print("=" * 70)

    ramp_manager = {
        "role": "Ramp Program Manager",
        "datasets": {
            "ramp_progress": discovered.get("ramp_progress"),
            "ramp_complaints": discovered.get("ramp_complaints"),
            "ramp_locations": discovered.get("ramp_locations"),
            "complaints_311": discovered.get("complaints_311"),
        },
        "workflows": [
            "ramp-progress",
            "complaint-response",
            "forecasting",
            "impact-assessment",
            "hotspot-analysis",
        ],
    }

    operations_manager = {
        "role": "Operations Manager (Inspections)",
        "datasets": {
            "inspection": discovered.get("inspection"),
            "violations": discovered.get("violations"),
            "dismissals": discovered.get("dismissals"),
            "correspondences": discovered.get("correspondences"),
            "reinspection": discovered.get("reinspection"),
            "complaints_311": discovered.get("complaints_311"),
        },
        "workflows": [
            "violations-triage",
            "velocity-analysis",
            "inspector-performance",
            "dismissal-analysis",
            "appeal-tracking",
            "correspondence-audit",
            "dataset-health",
            "sla-compliance",
        ],
    }

    project_manager = {
        "role": "Project Manager (Construction)",
        "datasets": {
            "street_permits": discovered.get("street_permits"),
            "street_construction_inspections": discovered.get("street_construction_inspections"),
            "street_closures_block": discovered.get("street_closures_block"),
            "capital_intersections": discovered.get("capital_intersections"),
            "inspection": discovered.get("inspection"),
            "violations": discovered.get("violations"),
        },
        "workflows": [
            "conflict-detect",
            "resource-allocation",
            "hotspot-analysis",
            "dataset-health",
            "sla-compliance",
        ],
    }

    managers = [ramp_manager, operations_manager, project_manager]

    for manager in managers:
        print(f"\n[{manager['role'].upper()}]")
        print("-" * 70)

        print(f"\nDatasets:")
        for ds_name, ds_info in manager["datasets"].items():
            if ds_info:
                rows = ds_info.get('rows', 0)
                print(f"  * {ds_name:30s} {rows:>10,} rows")

        print(f"\nApplicable Workflows ({len(manager['workflows'])} total):")
        for workflow in manager["workflows"]:
            print(f"  - {workflow}")

    # Freshness summary
    print("\n" + "=" * 70)
    print("DATASET FRESHNESS REPORT")
    print("=" * 70)

    fresh = [x for x in freshness_report if x[1] and x[1] < 30]
    stale = [x for x in freshness_report if x[1] and x[1] >= 30]

    print(f"\n[FRESH] (<30 days): {len(fresh)}")
    for name, age, _ in sorted(fresh, key=lambda x: x[1] or 999):
        print(f"  * {name:30s} {age}d old" if age else f"  * {name:30s}")

    print(f"\n[STALE] (>=30 days): {len(stale)}")
    for name, age, _ in sorted(stale, key=lambda x: x[1] or 999, reverse=True):
        print(f"  * {name:30s} {age}d old" if age else f"  * {name:30s}")

    print(f"\n[UNKNOWN]: {len([x for x in freshness_report if x[1] is None])}")

    # Save comprehensive output
    output = {
        "timestamp": datetime.now().isoformat(),
        "total_datasets": len(discovered),
        "managers": [
            {
                "role": manager["role"],
                "datasets": {k: v for k, v in manager["datasets"].items() if v},
                "workflows": manager["workflows"],
            }
            for manager in managers
        ],
        "all_datasets": discovered,
        "freshness_summary": {
            "fresh": len(fresh),
            "stale": len(stale),
            "unknown": len([x for x in freshness_report if x[1] is None]),
        },
    }

    with open("project_manager_datasets.json", "w") as f:
        json.dump(output, f, indent=2, default=str)

    print("\n" + "=" * 70)
    print("[SUCCESS] Results saved to project_manager_datasets.json")
    print("=" * 70)

    return output


if __name__ == "__main__":
    main()
