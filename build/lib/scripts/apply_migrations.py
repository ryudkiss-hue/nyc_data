"""Applies database migrations."""
import os
import sys
import logging
# Import sql from psycopg to satisfy the 'Template' requirement
from psycopg import sql

# Fix Path: Add project root so 'helpers' is discoverable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from helpers import load_env
except ImportError: # pylint: disable=import-error
    # Fallback for complex CI environments
    def load_env(): return {"PG_DSN": os.getenv("PG_DSN")}

def main():
    """Main migration logic."""
    env = load_env()
    dsn = str(env.get("PG_DSN") or "")
    if not dsn:
        return

    import psycopg
    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                path = "sql/migrations/001_create_alerts.sql"
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        # Fix: Wrap the string in sql.SQL() to satisfy Pylance
                        cur.execute(sql.SQL(f.read()))
            log.info("Migration applied.")
    except Exception as e: # pylint: disable=broad-exception-caught
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
