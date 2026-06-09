"""SQLite database — no server needed."""
import configparser
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

_BASE = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent

_cfg = configparser.ConfigParser()
_cfg.read(_BASE / "config.ini")
_db_path_raw = _cfg.get("database", "db_path", fallback="supplier_scraper.db")
# Resolve relative paths against the app's base directory, not CWD
_db_path = str(_BASE / _db_path_raw) if not Path(_db_path_raw).is_absolute() else _db_path_raw

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
