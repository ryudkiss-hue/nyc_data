"""Interactive installation wizard for the NYC DOT Sidewalk Toolkit.

Guides the user through configuring:
- Socrata API connection (app token, default domain/dataset)
- PostgreSQL integration
- MongoDB integration
- Export preferences (formats, max rows)
- Work management integration (Monday.com, M365, Google Workspace)

Generates a ``socrata_toolkit.config.json`` file and an ``.env.socrata``
environment file that the CLI and Python API auto-detect.

Run with::

    python -m socrata_toolkit.install_wizard
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"{prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return value or default


def ask_bool(prompt: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    try:
        value = input(f"{prompt} ({d}): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    if not value:
        return default
    return value in {"y", "yes", "1", "true"}


def main() -> None:
    print()
    print("=" * 60)
    print("  NYC DOT Sidewalk Toolkit -- Installation Wizard")
    print("=" * 60)
    print()
    print("This wizard will help you configure the toolkit for your")
    print("environment. All settings are saved to a local config file")
    print("and can be changed later.")
    print()

    root = Path(ask("Project root directory", str(Path.cwd()))).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------
    # Socrata API
    # -------------------------------------------------------------------
    print("\n--- Socrata API ---")
    cfg: dict = {
        "socrata": {
            "app_token": ask("Socrata App Token (optional, increases rate limits)", ""),
            "default_domain": ask("Default domain", "data.cityofnewyork.us"),
            "default_dataset_id": ask("Default dataset 4x4 ID", "h9gi-nx95"),
        },
    }

    # -------------------------------------------------------------------
    # PostgreSQL
    # -------------------------------------------------------------------
    print("\n--- PostgreSQL ---")
    pg_enabled = ask_bool("Enable PostgreSQL integration", False)
    cfg["postgres"] = {
        "enabled": pg_enabled,
        "dsn": "",
        "table": "socrata_data",
        "conflict_col": "id",
    }
    if pg_enabled:
        cfg["postgres"]["dsn"] = ask("PostgreSQL DSN", "postgresql://user:pass@localhost:5432/mydb")
        cfg["postgres"]["table"] = ask("Default table", "socrata_data")
        cfg["postgres"]["conflict_col"] = ask("Default conflict column", "id")

    # -------------------------------------------------------------------
    # MongoDB
    # -------------------------------------------------------------------
    print("\n--- MongoDB ---")
    mongo_enabled = ask_bool("Enable MongoDB integration", False)
    cfg["mongodb"] = {
        "enabled": mongo_enabled,
        "uri": "",
        "db": "socrata",
        "collection": "socrata_data",
        "conflict_field": "id",
    }
    if mongo_enabled:
        cfg["mongodb"]["uri"] = ask("MongoDB URI", "mongodb://localhost:27017")
        cfg["mongodb"]["db"] = ask("Default DB", "socrata")
        cfg["mongodb"]["collection"] = ask("Default collection", "socrata_data")
        cfg["mongodb"]["conflict_field"] = ask("Default conflict field", "id")

    # -------------------------------------------------------------------
    # Export Preferences
    # -------------------------------------------------------------------
    print("\n--- Export Preferences ---")
    cfg["preferences"] = {
        "default_max_rows": int(ask("Default max rows", "10000")),
        "default_export_formats": ask("Default export formats (comma separated)", "json,xlsx").split(","),
        "reports_dir": ask("Reports output directory", "outputs/reports"),
        "charts_dir": ask("Charts output directory", "outputs/charts"),
    }

    # -------------------------------------------------------------------
    # Work Management
    # -------------------------------------------------------------------
    print("\n--- Work Management Integrations ---")
    cfg["integrations"] = {}

    if ask_bool("Configure Monday.com integration", False):
        cfg["integrations"]["monday"] = {
            "enabled": True,
            "api_key_env": "MONDAY_API_KEY",
            "board_id": ask("Default board ID", ""),
        }

    if ask_bool("Configure Microsoft 365 integration", False):
        cfg["integrations"]["m365"] = {
            "enabled": True,
            "tenant_id_env": "M365_TENANT_ID",
            "client_id_env": "M365_CLIENT_ID",
            "sharepoint_site": ask("SharePoint site URL", ""),
            "teams_webhook": ask("Teams webhook URL (optional)", ""),
        }

    if ask_bool("Configure Google Workspace integration", False):
        cfg["integrations"]["google"] = {
            "enabled": True,
            "credentials_path": ask("Service account JSON path", "credentials.json"),
            "spreadsheet_id": ask("Default spreadsheet ID", ""),
        }

    # -------------------------------------------------------------------
    # Save Configuration
    # -------------------------------------------------------------------
    cfg_path = root / "socrata_toolkit.config.json"
    env_path = root / ".env.socrata"

    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    env_lines = []
    if cfg["socrata"]["app_token"]:
        env_lines.append(f'SOCRATA_APP_TOKEN={cfg["socrata"]["app_token"]}')
    if pg_enabled and cfg["postgres"]["dsn"]:
        env_lines.append(f'PG_DSN={cfg["postgres"]["dsn"]}')
    if mongo_enabled and cfg["mongodb"]["uri"]:
        env_lines.append(f'MONGO_URI={cfg["mongodb"]["uri"]}')
    env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    # Create output directories
    (root / cfg["preferences"]["reports_dir"]).mkdir(parents=True, exist_ok=True)
    (root / cfg["preferences"]["charts_dir"]).mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 60)
    print("  Setup Complete")
    print("=" * 60)
    print()
    print(f"  Config saved to:  {cfg_path}")
    print(f"  Env file saved to: {env_path}")
    print()
    print("  Next steps:")
    print("  1. pip install -e .")
    print("  2. source .env.socrata  (or set env vars manually)")
    print("  3. socrata doctor  (verify installation)")
    print("  4. socrata search 'sidewalk'  (try a search)")
    print()
    print("  For more help: socrata --help")
    print()


if __name__ == "__main__":
    main()
