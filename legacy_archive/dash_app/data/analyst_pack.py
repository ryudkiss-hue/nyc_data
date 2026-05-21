"""Load latest Analyst Pack artifacts for Dash pages."""



from __future__ import annotations



import json

from pathlib import Path



import pandas as pd

import yaml



PACK_ROOT = Path("outputs/analyst_pack")





def latest_pack_dir() -> Path | None:

    if not PACK_ROOT.exists():

        return None

    dirs = sorted([d for d in PACK_ROOT.iterdir() if d.is_dir()], reverse=True)

    return dirs[0] if dirs else None





def load_manifest(pack_dir: Path | None = None) -> dict:

    pack = pack_dir or latest_pack_dir()

    if not pack:

        return {}

    manifest = pack / "manifest.json"

    if not manifest.exists():

        return {"pack_dir": str(pack), "artifacts": {}}

    data = json.loads(manifest.read_text(encoding="utf-8"))

    data.setdefault("pack_dir", str(pack))

    return data





def load_construction_list(pack_dir: Path | None = None) -> pd.DataFrame:

    pack = pack_dir or latest_pack_dir()

    if not pack:

        return pd.DataFrame()

    xlsx = pack / "construction_list.xlsx"

    if xlsx.exists():

        return pd.read_excel(xlsx, engine="openpyxl")

    return pd.DataFrame()





def load_construction_diff(pack_dir: Path | None = None) -> str:

    pack = pack_dir or latest_pack_dir()

    if not pack:

        return ""

    path = pack / "construction_list_diff.md"

    return path.read_text(encoding="utf-8") if path.exists() else ""





def load_pack_file(name: str, pack_dir: Path | None = None) -> str:

    pack = pack_dir or latest_pack_dir()

    if not pack:

        return ""

    path = pack / name

    return path.read_text(encoding="utf-8") if path.exists() else ""





def artifact_links(manifest: dict) -> list[dict[str, str]]:

    artifacts = manifest.get("artifacts", {})

    return [{"label": k.replace("_", " ").title(), "path": v} for k, v in artifacts.items()]





def load_role_kpi_dashboard(pack_dir: Path | None = None) -> dict:

    pack = pack_dir or latest_pack_dir()

    if not pack:

        return {}

    path = pack / "role_kpi_dashboard.json"

    if path.exists():

        return json.loads(path.read_text(encoding="utf-8"))

    kpi_path = pack / "program_kpi.json"

    if kpi_path.exists():

        data = json.loads(kpi_path.read_text(encoding="utf-8"))

        return data.get("role", {})

    return {}





def load_program_kpi(pack_dir: Path | None = None) -> dict:

    pack = pack_dir or latest_pack_dir()

    if not pack:

        return {}

    path = pack / "program_kpi.json"

    if not path.exists():

        return {}

    return json.loads(path.read_text(encoding="utf-8"))





def list_configured_roles() -> list[dict[str, str]]:

    """Role profiles shipped under config/role_profiles/."""

    root = Path("config/role_profiles")

    roles: list[dict[str, str]] = []

    if not root.exists():

        return roles

    for yaml_path in sorted(root.glob("*.yaml")):

        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}

        roles.append(

            {

                "role_id": str(data.get("role_id", yaml_path.stem)),

                "display_name": str(data.get("display_name", yaml_path.stem)),

                "jid": str(data.get("job_reference", {}).get("jid", "")),

            }

        )

    return roles


