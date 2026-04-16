"""Add tariff column to works table and populate from users.

Run once on the server after deploying the new code:
    python scripts/migrate_add_work_tariff.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.db.database import engine

with engine.connect() as conn:
    # 1. Add column
    try:
        conn.execute(text("ALTER TABLE works ADD COLUMN tariff VARCHAR(50)"))
        conn.commit()
        print("+ works.tariff column added")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print("= works.tariff already exists")
        else:
            raise

    # 2. Populate from users table
    result = conn.execute(text(
        "UPDATE works SET tariff = (SELECT tariff FROM users WHERE users.id = works.user_id) "
        "WHERE tariff IS NULL"
    ))
    conn.commit()
    print(f"+ populated tariff for {result.rowcount} work records")

print("Migration complete.")
