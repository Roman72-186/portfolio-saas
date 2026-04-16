#!/usr/bin/env python3
"""
Миграция: добавить составные индексы для ускорения запросов.

Добавляет:
- ix_notifications_user_read_created (Notification)
- ix_upload_log_user_status_uploaded (UploadLog)

Запуск:
    python scripts/migrate_add_perf_indexes_v2.py
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.db.database import engine


def main():
    print("🔨 Adding performance indexes (v2)...")

    # Use raw connection with autocommit for CONCURRENTLY indexes
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        # 1. Check and create ix_notifications_user_read_created
        check_notif_idx = text("""
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'ix_notifications_user_read_created'
        """)
        if not conn.execute(check_notif_idx).fetchone():
            print("  ➕ Creating index: ix_notifications_user_read_created")
            conn.execute(text("""
                CREATE INDEX CONCURRENTLY ix_notifications_user_read_created
                ON notifications (user_id, is_read, created_at)
            """))
            print("     ✅ Index created")
        else:
            print("  ⏭️  Index ix_notifications_user_read_created already exists")

        # 2. Check and create ix_upload_log_user_status_uploaded
        check_log_idx = text("""
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'ix_upload_log_user_status_uploaded'
        """)
        if not conn.execute(check_log_idx).fetchone():
            print("  ➕ Creating index: ix_upload_log_user_status_uploaded")
            conn.execute(text("""
                CREATE INDEX CONCURRENTLY ix_upload_log_user_status_uploaded
                ON upload_log (user_id, status, uploaded_at)
            """))
            print("     ✅ Index created")
        else:
            print("  ⏭️  Index ix_upload_log_user_status_uploaded already exists")

    print("\n✅ Migration complete!")


if __name__ == "__main__":
    main()
