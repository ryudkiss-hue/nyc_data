"""Demo / offline pack helpers when no analyst pack exists on disk."""



from __future__ import annotations



import json

import shutil

from pathlib import Path



import pandas as pd



from dash_app.data.analyst_pack import PACK_ROOT, latest_pack_dir



DEMO_PACK_DIR = PACK_ROOT / "demo_pack"

FIXTURES = Path("tests/fixtures/analyst")





def ensure_demo_pack() -> Path | None:

    """Return a pack directory usable for Explore/Construction preview."""

    existing = latest_pack_dir()

    if existing:

        return existing

    if DEMO_PACK_DIR.exists() and (DEMO_PACK_DIR / "manifest.json").exists():

        return DEMO_PACK_DIR

    return _materialize_demo_pack()





def _materialize_demo_pack() -> Path | None:

    """Build a minimal pack under outputs/analyst_pack/demo_pack from fixtures."""

    if not FIXTURES.exists():

        return None

    DEMO_PACK_DIR.mkdir(parents=True, exist_ok=True)

    insp = FIXTURES / "inspections.xlsx"

    if insp.exists():

        df = pd.read_excel(insp, engine="openpyxl")

        df = df.rename(

            columns={

                "severity": "severity_rating",

            },

            errors="ignore",

        )

        if "issued_date" not in df.columns:

            df["issued_date"] = "2024-06-01"

        if "smart_spine" not in df.columns:

            df["smart_spine"] = False

        df.to_excel(DEMO_PACK_DIR / "construction_list.xlsx", index=False)

    manifest = {

        "profile_name": "demo",

        "run_date": "demo",

        "dry_run": True,

        "artifacts": {"construction_list": str(DEMO_PACK_DIR / "construction_list.xlsx")},

        "warnings": ["Demo pack — fixture data only; not for production."],

        "sources": {},

    }

    (DEMO_PACK_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return DEMO_PACK_DIR





def demo_construction_records() -> list[dict]:

    pack = ensure_demo_pack()

    if not pack:

        return _in_memory_fixture_records()

    xlsx = pack / "construction_list.xlsx"

    if xlsx.exists():

        return pd.read_excel(xlsx, engine="openpyxl").to_dict("records")

    return _in_memory_fixture_records()





def _in_memory_fixture_records() -> list[dict]:

    return [

        {

            "location_id": "L001",

            "borough": "MANHATTAN",

            "severity_rating": 4,

            "pedestrian_volume": 100,

            "issued_date": "2020-01-01",

            "ada_flag": True,

            "smart_spine": True,

            "complaint_count": 2,

        },

        {

            "location_id": "L002",

            "borough": "BROOKLYN",

            "severity_rating": 2,

            "pedestrian_volume": 50,

            "issued_date": "2024-01-01",

            "ada_flag": False,

            "smart_spine": False,

            "complaint_count": 0,

        },

    ]





def copy_fixtures_to_demo() -> Path | None:

    """One-click: refresh demo pack from tests/fixtures/analyst."""

    if DEMO_PACK_DIR.exists():

        shutil.rmtree(DEMO_PACK_DIR)

    return _materialize_demo_pack()


