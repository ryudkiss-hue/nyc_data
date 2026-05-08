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
