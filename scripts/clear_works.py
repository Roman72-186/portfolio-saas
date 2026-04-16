"""
One-time utility: delete ALL works and mock exam locks from the database.
User accounts are NOT affected.

Run inside Docker:
    docker exec portfolio-saas-app-1 python scripts/clear_works.py
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
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)

    import psycopg2
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM works")
    works_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM mock_exam_locks")
    locks_count = cur.fetchone()[0]

    cur.execute("DELETE FROM works")
    cur.execute("DELETE FROM mock_exam_locks")
    conn.commit()

    cur.close()
    conn.close()
    print(f"Deleted {works_count} works and {locks_count} mock exam locks.")
    print("User accounts untouched.")


if __name__ == "__main__":
    main()
