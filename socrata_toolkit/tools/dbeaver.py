"""DBeaver Connection Profile Generator for DOT Sidewalk Toolkit.

Generates DBeaver-compatible connection profile files (.dbp) and
data source JSON configurations that can be imported into DBeaver
for quick database access.

Also generates connection profiles for other database tools:
- pgAdmin 4 (servers.json)
- DataGrip / IntelliJ (datasources.xml)
- Generic JDBC properties files

Example::

    from socrata_toolkit.tools.dbeaver import (
        generate_dbeaver_profile,
        generate_pgadmin_profile,
        generate_connection_guide,
    )

    generate_dbeaver_profile("postgresql://user:pass@localhost/mydb", "output/dbeaver")
    generate_pgadmin_profile("localhost", 5432, "mydb", "user", "output/pgadmin")
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse


@dataclass
class ConnectionInfo:
    """Parsed database connection info."""
    host: str
    port: int
    database: str
    username: str
    password: str
    driver: str = "postgresql"

    @classmethod
    def from_dsn(cls, dsn: str) -> ConnectionInfo:
        """Parse a DSN string into ConnectionInfo."""
        parsed = urlparse(dsn)
        return cls(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            database=(parsed.path or "/").lstrip("/") or "postgres",
            username=parsed.username or "postgres",
            password=parsed.password or "",
            driver=parsed.scheme.replace("postgresql", "postgres").split("+")[0] if parsed.scheme else "postgres",
        )


def generate_dbeaver_profile(
    dsn: str,
    output_dir: str,
    connection_name: str = "DOT Sidewalk DB",
) -> str:
    """Generate a DBeaver data source configuration file.

    Creates a ``data-sources.json`` file that can be placed in DBeaver's
    workspace to auto-register the connection.

    Args:
        dsn: PostgreSQL connection string.
        output_dir: Directory to write the config file.
        connection_name: Display name in DBeaver.

    Returns:
        Path to the generated file.
    """
    info = ConnectionInfo.from_dsn(dsn)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    config = {
        "folders": {},
        "connections": {
            f"postgres-{info.database}": {
                "provider": "postgresql",
                "driver": "postgres-jdbc",
                "name": connection_name,
                "save-password": True,
                "configuration": {
                    "host": info.host,
                    "port": str(info.port),
                    "database": info.database,
                    "url": f"jdbc:postgresql://{info.host}:{info.port}/{info.database}",
                    "home": "postgresql",
                    "type": "dev",
                    "auth-model": "native",
                    "properties": {
                        "connectTimeout": "10",
                        "loginTimeout": "10",
                    },
                },
                "custom-properties": {},
                "auth-properties": {
                    "user": info.username,
                    "password": info.password,
                },
            },
        },
    }

    path = str(out / "data-sources.json")
    Path(path).write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path


def generate_pgadmin_profile(
    host: str,
    port: int,
    database: str,
    username: str,
    output_dir: str,
    server_name: str = "DOT Sidewalk DB",
) -> str:
    """Generate a pgAdmin 4 servers.json import file.

    Can be imported via pgAdmin's "Import/Export Servers" feature.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    config = {
        "Servers": {
            "1": {
                "Name": server_name,
                "Group": "NYC DOT",
                "Host": host,
                "Port": port,
                "MaintenanceDB": database,
                "Username": username,
                "SSLMode": "prefer",
                "Comment": "NYC DOT Sidewalk Inspection & Management Database",
            },
        },
    }

    path = str(out / "servers.json")
    Path(path).write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path


def generate_jdbc_properties(
    dsn: str,
    output_dir: str,
    filename: str = "connection.properties",
) -> str:
    """Generate a JDBC properties file for generic database tools."""
    info = ConnectionInfo.from_dsn(dsn)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    props = [
        f"jdbc.url=jdbc:postgresql://{info.host}:{info.port}/{info.database}",
        f"jdbc.username={info.username}",
        f"jdbc.password={info.password}",
        f"jdbc.driver=org.postgresql.Driver",
        f"# DOT Sidewalk Toolkit Connection",
    ]

    path = str(out / filename)
    Path(path).write_text("\n".join(props), encoding="utf-8")
    return path


def generate_connection_guide(
    dsn: str,
    output_path: str = "docs/connection_guide.md",
) -> str:
    """Generate a Markdown connection guide for all supported tools.

    Creates a document explaining how to connect DBeaver, pgAdmin,
    DataGrip, psql, and Python to the database.
    """
    info = ConnectionInfo.from_dsn(dsn)
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    guide = f"""# Database Connection Guide

## Connection Details

| Property | Value |
|----------|-------|
| Host | `{info.host}` |
| Port | `{info.port}` |
| Database | `{info.database}` |
| Username | `{info.username}` |
| Driver | PostgreSQL (JDBC) |

## DBeaver

1. Open DBeaver
2. File > Import > DBeaver > Data Sources
3. Select the `data-sources.json` file from `outputs/dbeaver/`
4. Or manually: New Connection > PostgreSQL > enter details above

## pgAdmin 4

1. Open pgAdmin
2. Tools > Import/Export Servers
3. Select `servers.json` from `outputs/pgadmin/`

## psql (Command Line)

```bash
psql "{dsn}"
```

## Python (psycopg)

```python
import psycopg
with psycopg.connect("{dsn}") as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM inspections LIMIT 10")
        rows = cur.fetchall()
```

## Python (SQLAlchemy)

```python
from sqlalchemy import create_engine
engine = create_engine("{dsn}")
df = pd.read_sql("SELECT * FROM inspections", engine)
```

## DataGrip / IntelliJ

1. Database > New > Data Source > PostgreSQL
2. Host: `{info.host}`, Port: `{info.port}`, Database: `{info.database}`
3. User: `{info.username}`

## Docker

The toolkit's `docker-compose.yml` includes a PostGIS database:

```bash
docker compose up -d postgres
# Connect at localhost:5432
```
"""

    p.write_text(guide, encoding="utf-8")
    return str(p)
