"""Add one-time login support to an existing database."""
import os
import sys

from sqlalchemy import inspect, text

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.db.database import engine, Base
from app.models.user import User
from app.models.session import Session
from app.models.upload_log import UploadLog
from app.models.login_token import LoginToken


def migrate() -> None:
    with engine.begin() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        if "users" in tables:
            user_columns = {column["name"] for column in inspector.get_columns("users")}
            if "is_group_member" not in user_columns:
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN is_group_member BOOLEAN NOT NULL DEFAULT FALSE"
                ))
            if "last_vk_check_at" not in user_columns:
                conn.execute(text(
                    "ALTER TABLE users ADD COLUMN last_vk_check_at TIMESTAMP WITH TIME ZONE NULL"
                ))

    Base.metadata.create_all(bind=engine)
    print("Migration complete: users updated, login_tokens table ensured.")


if __name__ == "__main__":
    migrate()
