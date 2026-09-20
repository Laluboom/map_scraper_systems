# Supplier Scraper — Reference

**Client:** Schion International (Pakistan). **Purpose:** find non-ferrous scrap traders via
the Google Places API, score them, review locally, and email outreach over SMTP.
**Status (2026-09-20):** shipping, v1.0.2. Last code change 2026-06-19.

## What actually ships

Everything is in `standalone/`. It runs as a single PyInstaller `.exe` (or `python cli.py`)
with a local SQLite DB and a local FastAPI/Jinja dashboard on `127.0.0.1:8080`.

| Layer | Reality |
|---|---|
| CLI | Click — `setup`, `serve`, `scrape`, `validate`, `send`, `status` (`cli.py`) |
| Dashboard | FastAPI + Jinja2, server-rendered (`web_server.py`, `templates/`) |
| Scraping | Google Places Text Search + Place Details via `httpx` (`places_scraper.py`) |
| Email extraction | plain regex over page HTML, **no BeautifulSoup** (`website_email_extractor.py`) |
| Scoring | 3-layer keyword/place-type scoring, 0-100 (`keyword_classifier.py`) |
| Email delivery | **SMTP** (`email_sender.py`) — SendGrid was removed in `73762a0` |
| Validation | Hunter.io → ZeroBounce, both optional; returns `True` if neither key is set |
| Billing guard | monthly free-tier counters in `call_counts.json` (`billing_guard.py`) |
| Jobs | in-process threads with cancellation (`job_registry.py`) |
| Config | `config.ini` (configparser, `interpolation=None`) — gitignored |

`backend/` and `frontend/` are an **abandoned** Celery/Postgres/Scrapy/Selenium/React stack.
Nothing in `standalone/` imports them. Ignore them; they are candidates for deletion.

## Run it

```bash
cd standalone
python3 -m venv .venv && .venv/bin/pip install -r requirements_standalone.txt
.venv/bin/python cli.py serve            # → http://localhost:8080, redirects to /setup
.venv/bin/python cli.py scrape --city "Dallas, TX"
.venv/bin/python cli.py send --dry-run
.venv/bin/python -m unittest discover tests
```

Requires Python 3 (3.14 works; `sqlalchemy>=2.0.36` is pinned for it). Needs a Google Places
API key **with billing enabled** and SMTP credentials — both entered on `/setup`.

## Data files (next to the exe / in `standalone/`)

`supplier_scraper.db` · `config.ini` (secrets, never commit) · `call_counts.json` (monthly API
usage) · `email_template.txt` (body; subject lives in config.ini) · `cities_us.txt` (267 lines,
13 duplicates) · `supplier_scraper.log`

## Releasing

Bump `standalone/version.py` → commit → `git tag vX.Y.Z` → push tags → Actions builds the exe
→ upload it → edit the public Gist. Manifest filename is **`Supplier_Scraper.json`**
(`update_checker.py:15`); the root README still says `version.json` and is wrong. The client
sees the banner only on next app start — the check runs once at import (`web_server.py:125`).

## Current state of play

Working end to end: scrape → review → send, with job cancellation, CSV export, DB backup,
duplicate detection, daily send cap (web only), unsubscribe tracking, update banner.
Known weak points, in order: the scraper never inspects Google's JSON `status` field so a
denied key looks like an empty city and still marks the area done; `cli.py send` ignores the
daily cap the dashboard enforces; a transient SMTP error permanently marks a contact
`bounced` with no reset path; `/contacts/duplicates` is O(n²). See `TODO.md` for the detail.

Tests: `standalone/tests/` — 8 unit tests covering scoring, email extraction, the resume
window, and template substitution. No coverage of `places_scraper`, `email_sender.send_one`,
`billing_guard`, `update_checker`, or any HTTP route.
