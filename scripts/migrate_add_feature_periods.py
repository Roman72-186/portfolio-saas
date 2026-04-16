"""Migration: create feature_periods table."""
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
        CREATE TABLE IF NOT EXISTS feature_periods (
            id SERIAL PRIMARY KEY,
            feature VARCHAR(30) NOT NULL,
            title VARCHAR(100),
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_by_id INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_feature_periods_feature_active
        ON feature_periods (feature, is_active)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_feature_periods_dates
        ON feature_periods (start_date, end_date)
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("[OK] Table feature_periods created.")

if __name__ == "__main__":
    main()
