"""One-time migration: create notifications table.

Run inside Docker:
    docker exec portfolio-saas-app-1 python scripts/migrate_add_notifications.py
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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            title       VARCHAR(200) NOT NULL,
            text        TEXT,
            work_id     INTEGER REFERENCES works(id),
            is_read     BOOLEAN NOT NULL DEFAULT FALSE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id)")
    conn.commit()
    cur.close()
    conn.close()
    print("Migration complete: notifications table created.")


if __name__ == "__main__":
    main()
