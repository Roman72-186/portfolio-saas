"""
Migration: добавить поле deleted_at в users, создать таблицу audit_logs.

Запуск:
    PORTFOLIO_SSH_HOST=... PORTFOLIO_SSH_PASSWORD=... python scripts/migrate_user_deleted_audit_log.py
    # или локально:
    DATABASE_URL=postgresql://... python scripts/migrate_user_deleted_audit_log.py
"""
import os
import sys

# Позволяет запускать скрипт из корня portfolio-saas/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.database import engine


def run():
    with engine.begin() as conn:
        # 1. Поле deleted_at на users
        conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE NULL
        """))
        print("users.deleted_at — OK")

        # 2. Индекс на deleted_at + is_active
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_users_deleted_active
            ON users (deleted_at, is_active)
        """))
        print("ix_users_deleted_active — OK")

        # 3. Таблица audit_logs
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                action VARCHAR(50) NOT NULL,
                performed_by_id INTEGER NOT NULL REFERENCES users(id),
                target_user_id INTEGER REFERENCES users(id),
                details VARCHAR(1000),
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """))
        print("audit_logs — OK")

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_audit_logs_performed_by
            ON audit_logs (performed_by_id, created_at)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_audit_logs_target_user
            ON audit_logs (target_user_id, created_at)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_audit_logs_action_created
            ON audit_logs (action, created_at)
        """))
        print("audit_logs индексы — OK")

    print("\nМиграция выполнена успешно.")


if __name__ == "__main__":
    run()
