"""Initialize database tables."""
import sys
sys.path.insert(0, ".")

from app.db.database import engine, Base
from app.models import User, Session, UploadLog, LoginToken

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")
