"""File-based logging for the standalone app."""
import logging
import sys
from pathlib import Path

_BASE = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
_LOG_FILE = _BASE / "supplier_scraper.log"

def get_logger(name: str = "scraper") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    # File handler
    fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger

log = get_logger()
