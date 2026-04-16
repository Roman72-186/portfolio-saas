"""Migration: create mock_exam_attempts table."""
import os, sys

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
        CREATE TABLE IF NOT EXISTS mock_exam_attempts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            subject VARCHAR(50) NOT NULL,
            ticket_id INTEGER REFERENCES exam_tickets(id) ON DELETE SET NULL,
            ticket_title VARCHAR(200) NOT NULL,
            ticket_description TEXT,
            ticket_image_url VARCHAR(500),
            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            completed_at TIMESTAMPTZ,
            notif_2h_sent BOOLEAN NOT NULL DEFAULT FALSE,
            notif_3h_sent BOOLEAN NOT NULL DEFAULT FALSE,
            notif_10min_sent BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_mock_exam_attempts_user_active
        ON mock_exam_attempts (user_id, subject, completed_at)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_mock_exam_attempts_progress
        ON mock_exam_attempts (completed_at, started_at)
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("[OK] Table mock_exam_attempts created.")

if __name__ == "__main__":
    main()
