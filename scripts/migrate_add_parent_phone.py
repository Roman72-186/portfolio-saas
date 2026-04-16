"""
Migration: add parent_phone column to users table.

Run once on the VPS:
    docker compose exec app python scripts/migrate_add_parent_phone.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.database import engine


def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN parent_phone VARCHAR(30)"))
            conn.commit()
            print("[OK] Added column: parent_phone")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("[SKIP] Column already exists: parent_phone")
            else:
                print(f"[ERROR] parent_phone: {e}")
                raise


if __name__ == "__main__":
    migrate()
    print("Done.")
