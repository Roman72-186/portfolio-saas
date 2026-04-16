"""Add subject column to works table."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.db.database import engine

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE works ADD COLUMN subject VARCHAR(50)"))
        conn.commit()
        print("+ works.subject")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print("= works.subject already exists")
        else:
            raise
print("Migration complete.")
