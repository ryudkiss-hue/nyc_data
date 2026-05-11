import json
import pytest

from socrata_toolkit.tools.dbeaver import (
    ConnectionInfo,
    generate_connection_guide,
    generate_dbeaver_profile,
    generate_jdbc_properties,
    generate_pgadmin_profile,
)


def test_connection_info_from_dsn():
    info = ConnectionInfo.from_dsn("postgresql://myuser:mypass@db.example.com:5433/mydb")
    assert info.host == "db.example.com"
    assert info.port == 5433
    assert info.database == "mydb"
    assert info.username == "myuser"
    assert info.password == "mypass"


def test_connection_info_defaults():
    info = ConnectionInfo.from_dsn("postgresql://localhost/testdb")
    assert info.host == "localhost"
    assert info.port == 5432
    assert info.database == "testdb"


def test_generate_dbeaver_profile(tmp_path):
    path = generate_dbeaver_profile(
        "postgresql://user:pass@localhost:5432/sidewalk_db",
        str(tmp_path / "dbeaver"),
    )
    data = json.loads(open(path).read())
    assert "connections" in data
    conn = list(data["connections"].values())[0]
    assert conn["name"] == "DOT Sidewalk DB"
    assert conn["configuration"]["host"] == "localhost"


def test_generate_pgadmin_profile(tmp_path):
    path = generate_pgadmin_profile(
        "localhost", 5432, "sidewalk_db", "dot_user",
        str(tmp_path / "pgadmin"),
    )
    data = json.loads(open(path).read())
    assert "Servers" in data
    server = data["Servers"]["1"]
    assert server["Host"] == "localhost"
    assert server["Username"] == "dot_user"


def test_generate_jdbc_properties(tmp_path):
    path = generate_jdbc_properties(
        "postgresql://user:pass@localhost/mydb",
        str(tmp_path / "jdbc"),
    )
    content = open(path).read()
    assert "jdbc.url=" in content
    assert "jdbc.username=user" in content


def test_generate_connection_guide(tmp_path):
    path = generate_connection_guide(
        "postgresql://user:pass@localhost:5432/mydb",
        str(tmp_path / "guide.md"),
    )
    content = open(path).read()
    assert "# Database Connection Guide" in content
    assert "DBeaver" in content
    assert "pgAdmin" in content
    assert "psql" in content
