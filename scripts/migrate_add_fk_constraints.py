"""Migration: add missing FK constraints and indexes on works table."""
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

    # FK: works.scored_by_id → users.id
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_works_scored_by'
                  AND table_name = 'works'
            ) THEN
                ALTER TABLE works
                    ADD CONSTRAINT fk_works_scored_by
                    FOREIGN KEY (scored_by_id) REFERENCES users(id)
                    ON DELETE SET NULL;
                RAISE NOTICE 'Added FK fk_works_scored_by';
            ELSE
                RAISE NOTICE 'FK fk_works_scored_by already exists';
            END IF;
        END
        $$;
    """)

    # Index: works.status (used in cabinet queries)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_works_status
        ON works (status);
    """)

    # Index: sessions.expires_at (used in cleanup job)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_sessions_expires_at
        ON sessions (expires_at);
    """)

    # Index: login_tokens.expires_at (used in cleanup job)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_login_tokens_expires_at
        ON login_tokens (expires_at);
    """)

    # Index: notifications.is_read (used in cabinet student queries)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_notifications_is_read
        ON notifications (user_id, is_read);
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("[OK] FK constraints and indexes applied.")


if __name__ == "__main__":
    main()
