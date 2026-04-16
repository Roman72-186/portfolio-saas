"""Add missing DB indexes: sessions.expires_at, notifications.created_at."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.db.database import engine


def run():
    with engine.connect() as conn:
        # sessions.expires_at — used in cleanup queries and session validation
        try:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_sessions_expires_at ON sessions (expires_at)"
            ))
            print("✓ ix_sessions_expires_at")
        except Exception as e:
            print(f"  sessions.expires_at: {e}")

        # notifications.created_at — used for sorting in student cabinet
        try:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications (created_at)"
            ))
            print("✓ ix_notifications_created_at")
        except Exception as e:
            print(f"  notifications.created_at: {e}")

        conn.commit()
    print("Done.")


if __name__ == "__main__":
    run()
