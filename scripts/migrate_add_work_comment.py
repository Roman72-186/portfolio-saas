"""One-time migration: add comment column to works table.

Run once on the production server:
    python scripts/migrate_add_work_comment.py
"""
import os
import sys


def main():
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    except ImportError:
        pass

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL env var is not set", file=sys.stderr)
        sys.exit(1)

    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 not installed", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS comment VARCHAR(1000)")
    conn.commit()
    cur.close()
    conn.close()
    print("Migration complete: comment column added to works.")


if __name__ == "__main__":
    main()
