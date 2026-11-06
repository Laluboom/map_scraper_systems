# Supplier Scraper — Reference

**Client:** Schion International (Pakistan). **Purpose:** find non-ferrous scrap traders via
the Google Places API, score them, review locally, and email outreach over SMTP.
**Status (2026-11-06):** shipping v1.0.2. Last product-code commit is `fac30b0` (2026-09-22,
PR #1 — Places error statuses); before that, nothing since `a08e1a3` (2026-06-19).

## What actually ships

Everything is in `standalone/`: a single PyInstaller `.exe` (or `python cli.py`) with a local
SQLite DB and a FastAPI/Jinja dashboard on `127.0.0.1:8080`.

| Layer | Reality |
|---|---|
| CLI | Click — `setup`, `serve`, `scrape`, `validate`, `send`, `status` (`cli.py`) |
| Dashboard | FastAPI + Jinja2, server-rendered (`web_server.py`, `templates/`) |
| Scraping | Google Places **(legacy)** Text Search + Place Details via `httpx` (`places_scraper.py:26-27`) |
| Email extraction | plain regex over page HTML, **no BeautifulSoup** (`website_email_extractor.py`) |
| Scoring | 3-layer keyword/place-type scoring, 0-100 (`keyword_classifier.py`) |
| Email delivery | **SMTP** (`email_sender.py`) — SendGrid was removed in `73762a0` |
| Validation | Hunter.io → ZeroBounce, both optional; `True` if neither key is set |
| Billing guard | monthly call counters in `call_counts.json` (`billing_guard.py`) |
| Jobs | in-process threads with cancellation (`job_registry.py`) |
| Config | `config.ini` (configparser, `interpolation=None`) — gitignored |

`backend/` and `frontend/` are an **abandoned** Celery/Postgres/Scrapy/Selenium/React stack.
Nothing in `standalone/` imports them — candidates for deletion.

## Run it

```bash
cd standalone
python3 -m venv .venv && .venv/bin/pip install -r requirements_standalone.txt
.venv/bin/python cli.py serve                        # → localhost:8080, redirects to /setup
.venv/bin/python cli.py scrape --city "Dallas, TX"
.venv/bin/python cli.py scrape --all-us --resume     # NOT `--resume` alone; that exits 1
.venv/bin/python -m unittest discover tests
```

Needs Python 3 (3.14 works; `sqlalchemy>=2.0.36` is pinned for it), a Google Places API key
**with billing enabled**, and SMTP credentials — both entered on `/setup`. No venv is checked
in and no CI job runs the tests, so assume the suite is unverified until you create one.
`requirements_standalone.txt` still lists `beautifulsoup4` and `lxml`; nothing imports either.

## Data files (beside the exe / in `standalone/`)

`supplier_scraper.db` · `config.ini` (secrets, never commit) · `call_counts.json` ·
`email_template.txt` (body; subject is in config.ini) · `cities_us.txt` (267 lines, 13
duplicates) · `supplier_scraper.log`. Frozen builds resolve all of these from
`Path(sys.executable).parent` and only `templates/` from `sys._MEIPASS` (`web_server.py:32`) —
so anything the app reads must be in the release **zip**, not just in the spec's `datas`.
`db.py:32-34` is `Base.metadata.create_all`: it creates missing tables but **never adds
columns**, so any new model field breaks existing client DBs.

## Releasing

Bump `standalone/version.py` → commit → `git tag vX.Y.Z` → push tags → Actions builds the exe
→ upload it → edit the public Gist. Manifest filename is **`Supplier_Scraper.json`**
(`update_checker.py:15`); root README still says `version.json` in three places and is wrong.
The banner appears only on next app start — the check runs once at import
(`web_server.py:124-130`).

## Current state of play

Works end to end *from source*: scrape → review → send, plus job cancellation, CSV export, DB
backup, duplicate detection, a daily send cap (web only), unsubscribe tracking, update banner.
Four things undercut that:

1. The release zip has never contained `cities_us.txt` (`build-exe.yml`, four files only), so
   `--all-us`/Resume fail on every client machine and the Scrape page reads "0 / 0
   combinations." Dev runs are unaffected, which is why it has survived four reviews.
2. The scraper targets the **legacy** Places API, closed to new Google Cloud projects since
   2025-03-01, while `cli.py:79,133` and `templates/setup.html:42` instruct clients to create a
   new project and enable it. Today's build depends on one grandfathered key.
3. The daily send cap is off between local 00:00 and 05:00 PKT (`_sent_today()` compares local
   midnight to naive-UTC rows, `web_server.py:150-157` vs `:538`), and `cli.py send` has no cap.
4. PR #1 fixed non-`OK` Places statuses on the Text Search path only. A Place Details failure is
   swallowed per-place at `places_scraper.py:185-187` and `:209` still calls `mark_done`, so a
   denied key or quota trip mid-area records it as "done, 0 results" and Resume skips it for 30
   days.

Detail and fix order in `TODO.md`.

Tests: 13 in `standalone/tests/` — 8 in `test_core.py` (scoring, email extraction, resume
window, template substitution), 4 in `test_job_registry.py` (job lifecycle), 1 in
`test_places_scraper.py` (`REQUEST_DENIED` on Text Search). Nothing covers `billing_guard`,
`email_sender.send_one`, `update_checker`, the daily cap, the Place Details failure path, or
any HTTP route.
