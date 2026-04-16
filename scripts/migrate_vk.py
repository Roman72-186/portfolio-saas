"""Migration: drop old tables, recreate with new schema (users + updated sessions/upload_log)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine, Base

# Import all models so Base.metadata knows about them
from app.models.user import User
from app.models.session import Session
from app.models.upload_log import UploadLog
from app.models.login_token import LoginToken


def migrate():
    print("Dropping old tables: sessions, upload_log...")
    with engine.begin() as conn:
        conn.execute(Session.__table__.drop(engine, checkfirst=True))
        conn.execute(UploadLog.__table__.drop(engine, checkfirst=True))
        # users table may not exist yet
        conn.execute(User.__table__.drop(engine, checkfirst=True))

    print("Creating all tables with new schema...")
    Base.metadata.create_all(bind=engine)
    print("Done! Tables: users, sessions, upload_log, login_tokens")


if __name__ == "__main__":
    migrate()
