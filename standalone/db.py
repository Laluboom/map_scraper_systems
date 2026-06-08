"""SQLite database — no server needed."""
import configparser
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

_cfg = configparser.ConfigParser()
_cfg.read(Path(__file__).parent / "config.ini")
_db_path = _cfg.get("database", "db_path", fallback="supplier_scraper.db")

engine = create_engine(f"sqlite:///{_db_path}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
