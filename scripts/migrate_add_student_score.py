"""One-time migration: add student_score column to works table.

Run once on the production server:
    python scripts/migrate_add_student_score.py

Reads DATABASE_URL from environment (or .env file if python-dotenv is available).
Safe to run multiple times — uses IF NOT EXISTS.
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
        print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute(
        "ALTER TABLE works ADD COLUMN IF NOT EXISTS student_score NUMERIC(5,2)"
    )
    conn.commit()
    cur.close()
    conn.close()
    print("Migration complete: student_score column added to works table.")


if __name__ == "__main__":
    main()
