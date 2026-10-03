# Supplier Scraper — Reference

**Client:** Schion International (Pakistan). **Purpose:** find non-ferrous scrap traders via
the Google Places API, score them, review locally, and email outreach over SMTP.
**Status (2026-10-03):** shipping v1.0.2. **No code change since `a08e1a3` (2026-09-20).**

## What actually ships

Everything is in `standalone/`: a single PyInstaller `.exe` (or `python cli.py`) with a local
SQLite DB and a FastAPI/Jinja dashboard on `127.0.0.1:8080`.

| Layer | Reality |
|---|---|
| CLI | Click — `setup`, `serve`, `scrape`, `validate`, `send`, `status` (`cli.py`) |
| Dashboard | FastAPI + Jinja2, server-rendered (`web_server.py`, `templates/`) |
| Scraping | Google Places Text Search + Place Details via `httpx` (`places_scraper.py`) |
| Email extraction | plain regex over page HTML, **no BeautifulSoup** (`website_email_extractor.py`) |
| Scoring | 3-layer keyword/place-type scoring, 0-100 (`keyword_classifier.py`) |
| Email delivery | **SMTP** (`email_sender.py`) — SendGrid was removed in `73762a0` |
| Validation | Hunter.io → ZeroBounce, both optional; `True` if neither key is set |
| Billing guard | monthly free-tier counters in `call_counts.json` (`billing_guard.py`) |
| Jobs | in-process threads with cancellation (`job_registry.py`) |
| Config | `config.ini` (configparser, `interpolation=None`) — gitignored |

`backend/` and `frontend/` are an **abandoned** Celery/Postgres/Scrapy/Selenium/React stack.
Nothing in `standalone/` imports them — candidates for deletion.

## Run it

```bash
cd standalone
python3 -m venv .venv && .venv/bin/pip install -r requirements_standalone.txt
.venv/bin/python cli.py serve            # → localhost:8080, redirects to /setup
.venv/bin/python cli.py scrape --city "Dallas, TX"
.venv/bin/python -m unittest discover tests
```

Needs Python 3 (3.14 works; `sqlalchemy>=2.0.36` is pinned for it), a Google Places API key
**with billing enabled**, and SMTP credentials — both entered on `/setup`.
`requirements_standalone.txt` still lists `beautifulsoup4` and `lxml`; nothing imports either.

## Data files (beside the exe / in `standalone/`)

`supplier_scraper.db` · `config.ini` (secrets, never commit) · `call_counts.json` (monthly API
usage) · `email_template.txt` (body; subject is in config.ini) · `cities_us.txt` (267 lines,
13 duplicates) · `supplier_scraper.log`. Frozen builds resolve all of these from
`Path(sys.executable).parent` and only `templates/` from `sys._MEIPASS` (`web_server.py:32`) —
so anything the app reads must be in the release **zip**, not just in the spec's `datas`.

## Releasing

Bump `standalone/version.py` → commit → `git tag vX.Y.Z` → push tags → Actions builds the exe
→ upload it → edit the public Gist. Manifest filename is **`Supplier_Scraper.json`**
(`update_checker.py:15`); root README still says `version.json` in three places and is wrong.
The banner appears only on next app start — the check runs once at import
(`web_server.py:123-130`).

## Current state of play

Works end to end *from source*: scrape → review → send, plus job cancellation, CSV export, DB
backup, duplicate detection, a daily send cap (web only), unsubscribe tracking, update banner.
The **shipped artifact is broken for the headline workflow** though — the release zip has never
contained `cities_us.txt` (`build-exe.yml:41`), so `--all-us`/`--resume` fail on every client
machine and the Scrape page reads "0 / 0 combinations". Then: the daily send cap is off between
local 00:00 and 05:00 PKT (`_sent_today()` compares local midnight to UTC rows,
`web_server.py:151-161` vs `:537`) and `cli.py send` has no cap at all; and the scraper never
inspects Google's JSON `status`, so a denied key looks like an empty city and still marks the
area done for 30 days. Detail in `TODO.md`.

Tests: 12 in `standalone/tests/` — 8 in `test_core.py` (scoring, email extraction, resume
window, template substitution), 4 in `test_job_registry.py` (job lifecycle). Nothing covers
`places_scraper`, `email_sender.send_one`, `billing_guard`, `update_checker`, the daily cap, or
any HTTP route.
