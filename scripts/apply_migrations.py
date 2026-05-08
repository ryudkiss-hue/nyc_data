"""Simple migration runner for local development.

Usage: set `PG_DSN` env var or pass `--dsn` and run:

    python scripts/apply_migrations.py --dsn postgresql://user:pass@host/db

The script will execute SQL files in `sql/migrations` in alphabetical order.
"""
from __future__ import annotations

import os
import glob
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", help="Postgres DSN", default=os.getenv("PG_DSN"))
    parser.add_argument("--migrations-dir", default="sql/migrations")
    args = parser.parse_args()
    if not args.dsn:
        raise SystemExit("Provide a Postgres DSN via --dsn or PG_DSN env var")
    try:
        import psycopg
    except Exception as exc:
        raise SystemExit("Install psycopg to run migrations: pip install '.[postgres]'") from exc

    files = sorted(glob.glob(os.path.join(args.migrations_dir, "*.sql")))
    if not files:
        print("No migration files found")
        return
    conn = psycopg.connect(args.dsn)
    cur = conn.cursor()
    for f in files:
        print("Applying", f)
        with open(f, "r", encoding="utf-8") as fh:
            sql = fh.read()
            cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()
    print("Migrations applied")

if __name__ == "__main__":
    main()
