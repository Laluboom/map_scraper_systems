"""
Google Places API scraper.
No Scrapy, no CSS selectors — pure HTTP calls via httpx.

Search flow per city × search_term:
  1. Text Search (up to 3 pages = 60 results)
  2. Place Details for each unique place_id
  3. Website email extraction
  4. Keyword scoring
  5. Save to DB
"""
import time
import configparser
from datetime import datetime
from pathlib import Path

import httpx

from db import SessionLocal
from models import Trader
from area_manager import is_done, mark_done
from website_email_extractor import extract_email, extract_email_and_text
from keyword_classifier import score_company, is_priority as score_is_priority
from billing_guard import check_text_search, check_place_details, BillingLimitError

TEXT_SEARCH_URL  = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_URL      = "https://maps.googleapis.com/maps/api/place/details/json"
DETAILS_FIELDS   = "name,formatted_phone_number,website,formatted_address,url,types,rating"


# ── API calls ──────────────────────────────────────────────────────────────

def _text_search_page(api_key: str, query: str, page_token: str = "") -> dict:
    check_text_search()
    params = {"query": query, "key": api_key}
    if page_token:
        params = {"pagetoken": page_token, "key": api_key}
    r = httpx.get(TEXT_SEARCH_URL, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def search_places(api_key: str, query: str) -> list[dict]:
    """Return up to 60 raw place dicts for the given query string."""
    results = []
    page_token = ""
    for _ in range(3):  # max 3 pages × 20 results = 60
        if page_token:
            time.sleep(2)  # Google requires a short delay before using next_page_token
        data = _text_search_page(api_key, query, page_token)
        results.extend(data.get("results", []))
        page_token = data.get("next_page_token", "")
        if not page_token:
            break
    return results


def get_place_details(api_key: str, place_id: str) -> dict:
    """Fetch phone, website, address for one place_id."""
    check_place_details()
    r = httpx.get(DETAILS_URL,
                  params={"place_id": place_id, "fields": DETAILS_FIELDS, "key": api_key},
                  timeout=10)
    r.raise_for_status()
    return r.json().get("result", {})


# ── DB save ────────────────────────────────────────────────────────────────

def _save_trader(db, details: dict, email: str | None, score: int,
                 tags: list, priority: bool, city: str, state: str = "",
                 country: str = "US"):
    place_id = details.get("place_id", "")

    # Skip if place_id already in DB
    if place_id and db.query(Trader).filter(Trader.google_place_id == place_id).first():
        return False

    # Skip if email already in DB
    if email and db.query(Trader).filter(Trader.email == email.lower()).first():
        return False

    trader = Trader(
        company_name   = details.get("name"),
        email          = email.lower() if email else None,
        phone          = details.get("formatted_phone_number"),
        website        = details.get("website"),
        address        = details.get("formatted_address"),
        city           = city,
        state          = state,
        country        = country,
        source         = "GooglePlaces",
        product_tags   = tags,
        priority_flag  = priority,
        priority_score = score,
        google_place_id= place_id,
        google_rating  = str(details.get("rating", "")),
        google_url     = details.get("url"),
        scraped_at     = datetime.utcnow(),
    )
    db.add(trader)
    db.commit()
    return True


# ── Main entry ─────────────────────────────────────────────────────────────

def run_places_scrape(
    api_key: str,
    cities: list[tuple[str, str]],   # [(city, state), ...]
    search_terms: list[str],
    rescrape_days: int = 30,
    priority_threshold: int = 40,
    print_fn=print,
    should_cancel=None,
):
    """
    Full scrape run.  cities = list of (city, state) tuples.
    print_fn receives progress strings so CLI and web can both use this.
    """
    db = SessionLocal()
    total_areas = len(cities) * len(search_terms)
    area_num = 0

    try:
        for city, state in cities:
            for term in search_terms:
                if should_cancel and should_cancel():
                    print_fn("  CANCEL requested — stopping scrape")
                    return

                area_num += 1
                label = f"[{area_num}/{total_areas}] {term!r} in {city}, {state}"

                if is_done(db, city, state, term, rescrape_days):
                    print_fn(f"  SKIP  {label}  (already done)")
                    continue

                print_fn(f"  SEARCH {label}…")
                try:
                    query = f"{term} {city} {state}"
                    raw_places = search_places(api_key, query)
                except BillingLimitError as exc:
                    print_fn(f"\n  BILLING LIMIT REACHED: {exc}")
                    return
                except Exception as exc:
                    print_fn(f"    API error: {exc}")
                    continue

                saved = 0
                for place in raw_places:
                    if should_cancel and should_cancel():
                        print_fn("  CANCEL requested — stopping after current area progress")
                        mark_done(db, city, state, term, saved)
                        return

                    place_id = place.get("place_id", "")
                    if not place_id:
                        continue
                    if db.query(Trader).filter(Trader.google_place_id == place_id).first():
                        continue  # already seen

                    # Get full details
                    try:
                        details = get_place_details(api_key, place_id)
                        time.sleep(0.1)  # gentle rate limit
                    except BillingLimitError as exc:
                        print_fn(f"\n  BILLING LIMIT REACHED: {exc}")
                        mark_done(db, city, state, term, saved)
                        return
                    except Exception as exc:
                        print_fn(f"    [skip] {place.get('name','?')} — Place Details failed: {exc}")
                        continue

                    details["place_id"] = place_id

                    # Extract email + website text in one fetch (avoids double request)
                    website = details.get("website") or place.get("website")
                    email, website_text = extract_email_and_text(website)

                    if not email:
                        print_fn(f"    [skip] {details.get('name','?')} — no email found")
                        continue

                    score, tags = score_company(
                        name         = details.get("name", ""),
                        google_types = details.get("types", []),
                        website_text = website_text,
                    )
                    priority = score_is_priority(score, priority_threshold)

                    if _save_trader(db, details, email, score, tags, priority, city, state):
                        saved += 1

                mark_done(db, city, state, term, saved)
                print_fn(f"    → saved {saved} new trader(s)")

    finally:
        db.close()
