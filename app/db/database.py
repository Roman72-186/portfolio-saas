from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

_pool_kwargs = (
    dict(pool_size=10, max_overflow=5, pool_recycle=1800, pool_pre_ping=True)
    if settings.database_url.startswith("postgresql")
    else {}
)
engine = create_engine(settings.database_url, **_pool_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
