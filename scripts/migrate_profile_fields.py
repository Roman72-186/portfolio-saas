"""
Migration: add tg_username and enrollment_year columns to users table.

Run once on the VPS:
    docker compose exec app python scripts/migrate_profile_fields.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.database import engine


def migrate():
    with engine.connect() as conn:
        for col, definition in [
            ("tg_username",     "VARCHAR(100)"),
            ("enrollment_year", "INTEGER"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {definition}"))
                conn.commit()
                print(f"[OK] Added column: {col}")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    print(f"[SKIP] Column already exists: {col}")
                else:
                    print(f"[ERROR] {col}: {e}")
                    raise


if __name__ == "__main__":
    migrate()
    print("Done.")
