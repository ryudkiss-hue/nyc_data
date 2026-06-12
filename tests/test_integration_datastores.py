import os

import pytest


@pytest.mark.skipif(not os.getenv("RUN_INTEGRATION"), reason="Set RUN_INTEGRATION=1")
def test_postgres_connection():
    pytest.importorskip("psycopg")
    import psycopg

    dsn = os.getenv("PG_DSN")
    assert dsn
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            assert cur.fetchone()[0] == 1


@pytest.mark.skipif(not os.getenv("RUN_INTEGRATION"), reason="Set RUN_INTEGRATION=1")
def test_mongo_connection():
    pytest.importorskip("pymongo")
    from pymongo import MongoClient

    uri = os.getenv("MONGO_URI")
    assert uri
    c = MongoClient(uri)
    assert c.admin.command("ping")["ok"] == 1.0


# ---------------------------------------------------------------------------
# Round-trip integration: exercise the real exporters against live datastores.
# These catch SQL-generation, driver-compat, and upsert-conflict bugs that the
# mocked unit tests cannot. Gated on RUN_INTEGRATION (CI service containers).
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not os.getenv("RUN_INTEGRATION"), reason="Set RUN_INTEGRATION=1")
def test_postgres_exporter_roundtrip():
    pytest.importorskip("psycopg")
    import psycopg

    from socrata_toolkit.core.exporters import PostgresExporter

    dsn = os.getenv("PG_DSN")
    table = "it_roundtrip"
    batch1 = [{"id": 1, "name": "Alice", "score": 10}, {"id": 2, "name": "Bob", "score": 20}]
    # upsert that updates id=2 and inserts id=3
    batch2 = [{"id": 2, "name": "Bobby", "score": 25}, {"id": 3, "name": "Cara", "score": 30}]

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(f'DROP TABLE IF EXISTS "{table}"')
        conn.commit()

    with PostgresExporter(dsn) as pg:
        n1 = pg.upsert_batches([batch1], table=table, conflict_column="id")
        n2 = pg.upsert_batches([batch2], table=table, conflict_column="id")
    assert n1 == 2
    assert n2 == 2

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(f'SELECT id, name, score FROM "{table}" ORDER BY id')
            rows = cur.fetchall()
    # 3 distinct ids; id=2 updated to Bobby/25 (conflict upsert worked)
    assert len(rows) == 3
    by_id = {r[0]: (r[1], r[2]) for r in rows}
    assert by_id[2] == ("Bobby", 25)
    assert by_id[3] == ("Cara", 30)


@pytest.mark.skipif(not os.getenv("RUN_INTEGRATION"), reason="Set RUN_INTEGRATION=1")
def test_mongo_exporter_roundtrip():
    pytest.importorskip("pymongo")
    from pymongo import MongoClient

    from socrata_toolkit.core.exporters import MongoExporter

    uri = os.getenv("MONGO_URI")
    db_name = "it_test_db"
    collection = "it_roundtrip"

    client = MongoClient(uri)
    client[db_name][collection].drop()

    batch1 = [{"_id": 1, "name": "Alice"}, {"_id": 2, "name": "Bob"}]
    batch2 = [{"_id": 2, "name": "Bobby"}, {"_id": 3, "name": "Cara"}]
    with MongoExporter(uri, db_name) as mongo:
        mongo.upsert_batches([batch1], collection, "_id")
        mongo.upsert_batches([batch2], collection, "_id")

    docs = {d["_id"]: d["name"] for d in client[db_name][collection].find()}
    assert docs == {1: "Alice", 2: "Bobby", 3: "Cara"}  # upsert updated _id=2
    client[db_name][collection].drop()
