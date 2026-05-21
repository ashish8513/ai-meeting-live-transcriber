from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from api.config import get_settings

settings = get_settings()
_db_url = settings.database_url
_connect_args = {}
if _db_url.startswith("sqlite"):
    Path("data").mkdir(parents=True, exist_ok=True)
    _connect_args = {"check_same_thread": False}

engine = create_engine(_db_url, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from api import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
