"""
Hard billing guard — enforces monthly free-tier call caps.

Free tier limits (Google Places API, as of 2026):
  Text Search:   10,000 calls/month
  Place Details: 10,000 calls/month

Counts are stored in call_counts.json next to this file, keyed by "YYYY-MM".
Raises BillingLimitError before any call that would exceed the cap.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
COUNTS_FILE = BASE_DIR / "call_counts.json"

FREE_TEXT_SEARCH   = 10_000
FREE_PLACE_DETAILS = 10_000


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


def _get_counts() -> dict:
    """Return {text_search: N, place_details: N} for the current month."""
    data = _load()
    key = _month_key()
    return data.get(key, {"text_search": 0, "place_details": 0})


def _increment(field: str):
    data = _load()
    key = _month_key()
    if key not in data:
        data[key] = {"text_search": 0, "place_details": 0}
    data[key][field] += 1
    _save(data)


def check_text_search():
    """Call before every Text Search API request. Raises if free tier exhausted."""
    counts = _get_counts()
    used = counts.get("text_search", 0)
    if used >= FREE_TEXT_SEARCH:
        raise BillingLimitError(
            f"Text Search free tier exhausted ({used}/{FREE_TEXT_SEARCH} this month). "
            "Stopping to avoid charges. Run `python cli.py status` to review what was collected."
        )
    _increment("text_search")


def check_place_details():
    """Call before every Place Details API request. Raises if free tier exhausted."""
    counts = _get_counts()
    used = counts.get("place_details", 0)
    if used >= FREE_PLACE_DETAILS:
        raise BillingLimitError(
            f"Place Details free tier exhausted ({used}/{FREE_PLACE_DETAILS} this month). "
            "Stopping to avoid charges. Run `python cli.py status` to review what was collected."
        )
    _increment("place_details")


def get_usage_summary() -> str:
    counts = _get_counts()
    ts = counts.get("text_search", 0)
    pd = counts.get("place_details", 0)
    month = _month_key()
    return (
        f"  [{month}] Text Search: {ts}/{FREE_TEXT_SEARCH} free calls used  |  "
        f"Place Details: {pd}/{FREE_PLACE_DETAILS} free calls used"
    )
