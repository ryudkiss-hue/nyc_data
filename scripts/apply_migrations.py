"""Applies database migrations."""
import os
import sys
import logging

log = logging.getLogger(__name__)

# Add project root so 'helpers' is discoverable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from helpers import load_env
except ImportError:
    # Fallback for CI environments
    def load_env():
        return {"PG_DSN": os.getenv("PG_DSN")}

def main():
    """Main migration logic."""
    env = load_env()
    dsn = str(env.get("PG_DSN") or "")
    if not dsn:
        log.warning("PG_DSN not set, skipping migrations")
        return

    try:
        import psycopg
        from psycopg import sql
    except ImportError:
        log.error("psycopg is required for migrations: pip install 'psycopg[binary]'")
        return

    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                path = "sql/migrations/001_create_alerts.sql"
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        cur.execute(sql.SQL(f.read()))
            log.info("Migration applied.")
    except Exception as e:  # pylint: disable=broad-exception-caught
        log.error("Migration failed: %s", e)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
