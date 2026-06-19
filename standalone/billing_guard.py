"""
Hard billing guard — enforces monthly free-tier call caps.

Free tier limits (Google Places API, as of 2026):
  Text Search:   10,000 calls/month
  Place Details: 10,000 calls/month

Counts are stored in call_counts.json next to this file, keyed by "YYYY-MM".
Raises BillingLimitError before any call that would exceed the cap.

Thread-safe: a module-level lock serialises all check+increment operations so
concurrent scrape threads (CLI + web server running at the same time) cannot
both read the same counter, both pass the limit check, and both proceed.
"""
import json
import sys
import threading
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
COUNTS_FILE = BASE_DIR / "call_counts.json"

FREE_TEXT_SEARCH   = 10_000
FREE_PLACE_DETAILS = 10_000

_lock = threading.Lock()


class BillingLimitError(Exception):
    pass


def _load() -> dict:
    if COUNTS_FILE.exists():
        try:
            return json.loads(COUNTS_FILE.read_text())
        except Exception:
            pass
    return {}


def _save(data: dict):
    COUNTS_FILE.write_text(json.dumps(data, indent=2))


def _month_key() -> str:
    return datetime.utcnow().strftime("%Y-%m")


def _check_and_increment(field: str, limit: int, label: str):
    """Atomically check the counter and increment it under the module lock."""
    with _lock:
        data = _load()
        key = _month_key()
        if key not in data:
            data[key] = {"text_search": 0, "place_details": 0}
        used = data[key].get(field, 0)
        if used >= limit:
            raise BillingLimitError(
                f"{label} free tier exhausted ({used}/{limit} this month). "
                "Stopping to avoid charges. Run `python cli.py status` to review what was collected."
            )
        data[key][field] = used + 1
        _save(data)


def check_text_search():
    """Call before every Text Search API request. Raises if free tier exhausted."""
    _check_and_increment("text_search", FREE_TEXT_SEARCH, "Text Search")


def check_place_details():
    """Call before every Place Details API request. Raises if free tier exhausted."""
    _check_and_increment("place_details", FREE_PLACE_DETAILS, "Place Details")


def get_usage_summary() -> str:
    with _lock:
        data = _load()
    key = _month_key()
    counts = data.get(key, {"text_search": 0, "place_details": 0})
    ts = counts.get("text_search", 0)
    pd = counts.get("place_details", 0)
    return (
        f"  [{key}] Text Search: {ts}/{FREE_TEXT_SEARCH} free calls used  |  "
        f"Place Details: {pd}/{FREE_PLACE_DETAILS} free calls used"
    )
