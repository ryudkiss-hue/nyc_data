from __future__ import annotations

import json
from pathlib import Path


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def ask_bool(prompt: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    value = input(f"{prompt} ({d}): ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "1", "true"}


def main() -> None:
    print("\n=== Socrata Toolkit Installation Wizard ===\n")
    root = Path(ask("Project root directory", str(Path.cwd()))).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    cfg = {
        "socrata": {
            "app_token": ask("Socrata App Token (optional)", ""),
            "default_domain": ask("Default domain", "data.cityofnewyork.us"),
            "default_dataset_id": ask("Default dataset 4x4 ID", "h9gi-nx95"),
        },
        "postgres": {
            "enabled": ask_bool("Enable PostgreSQL integration", False),
            "dsn": "",
            "table": "socrata_data",
            "conflict_col": "id",
        },
        "mongodb": {
            "enabled": ask_bool("Enable MongoDB integration", False),
            "uri": "",
            "db": "socrata",
            "collection": "socrata_data",
            "conflict_field": "id",
        },
        "preferences": {
            "default_max_rows": int(ask("Default max rows", "10000")),
            "default_export_formats": ask("Default export formats (comma separated)", "json,xlsx").split(","),
            "launch_streamlit_after_setup": ask_bool("Launch Streamlit after setup", True),
        },
    }

    if cfg["postgres"]["enabled"]:
        cfg["postgres"]["dsn"] = ask("PostgreSQL DSN", "postgresql://user:pass@localhost:5432/mydb")
        cfg["postgres"]["table"] = ask("Default PostgreSQL table", "socrata_data")
        cfg["postgres"]["conflict_col"] = ask("Default PostgreSQL conflict column", "id")

    if cfg["mongodb"]["enabled"]:
        cfg["mongodb"]["uri"] = ask("MongoDB URI", "mongodb://localhost:27017")
        cfg["mongodb"]["db"] = ask("Default MongoDB DB", "socrata")
        cfg["mongodb"]["collection"] = ask("Default MongoDB collection", "socrata_data")
        cfg["mongodb"]["conflict_field"] = ask("Default MongoDB conflict field", "id")

    cfg_path = root / "socrata_toolkit.config.json"
    env_path = root / ".env.socrata"

    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    env_lines = []
    if cfg["socrata"]["app_token"]:
        env_lines.append(f'SOCRATA_APP_TOKEN={cfg["socrata"]["app_token"]}')
    if cfg["postgres"]["enabled"] and cfg["postgres"]["dsn"]:
        env_lines.append(f'PG_DSN={cfg["postgres"]["dsn"]}')
    if cfg["mongodb"]["enabled"] and cfg["mongodb"]["uri"]:
        env_lines.append(f'MONGO_URI={cfg["mongodb"]["uri"]}')
    env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    print(f"\nSaved config: {cfg_path}")
    print(f"Saved env file: {env_path}")
    print("\nNext steps:")
    print("1) pip install .")
    print("2) set env vars from .env.socrata")
    print("3) run: streamlit run socrata_toolkit/app.py")


if __name__ == "__main__":
    main()
