# TODO — Supplier Scraper & Outreach System

Ranked, best first. Reviewed 2026-10-03. Everything below is anchored to code I read.

**Note on the last review:** nothing from the 2026-09-20 list was touched. No code has
changed since `a08e1a3`; the only commit since is the review-notes commit itself, and
`agent/2026-09-20-google-places-error-statuses-are-never-c` is an empty branch (zero commits
ahead of `main`). Items 3 and 4 below are carried over unchanged and still real.

---

## 1. [BUG] The release zip has never shipped `cities_us.txt` — `--all-us` and resume scraping are dead on every client machine

This is the whole product. Everything else on this list is secondary.

When frozen, the app reads the city list from the directory **next to the exe**:

- `standalone/cli.py:22-28` — `BASE_DIR = Path(sys.executable).parent`, `CITIES_FILE = BASE_DIR / "cities_us.txt"`
- `standalone/web_server.py:627` (`/scrape/start`) and `:566` (`_scrape_page_ctx`) — both `Path(sys.executable).parent / "cities_us.txt"`

`standalone/supplier_scraper.spec:16-17` bundles `cities_us.txt` and `search_terms.txt` into
`datas`, which PyInstaller unpacks to `sys._MEIPASS`. **Nothing reads `cities_us.txt` from
`_MEIPASS`** — `web_server.py:32` is the only `_MEIPASS` use in the repo and it is for
`templates/` only. So the bundled copy is unreachable, and the copy beside the exe does not
exist, because `.github/workflows/build-exe.yml:41` packages exactly four files:

```
dist\supplier_scraper.exe, dist\config.ini, dist\README.md, dist\SETUP_GUIDE.pdf
```

`git log -p --follow .github/workflows/build-exe.yml` shows `cities_us.txt` was never in the
zip in any revision since the distribution system landed in `f38f5bd`. v1.0.0 → v1.0.2 all
ship without it, and nothing in `README.md` or `SETUP_GUIDE.pdf` tells the client to create it.

What the client actually sees:

- `cli.py scrape --all-us` → `_load_cities()` returns `[]` → `cli.py:261` prints
  "cities_us.txt not found at …" and `sys.exit(1)`
- Dashboard → Scrape → "Scrape All US" or "Resume" → `web_server.py:667` →
  redirect with "No cities loaded. Check cities_us.txt"
- Dashboard → Scrape page, always: `num_cities = 0` (`web_server.py:577-580`) →
  `total_areas_possible = 0` → `templates/scrape.html:46` renders **"0 / 0 city×term
  combinations searched"**, `:47` hides the progress bar entirely, and `:71` offers
  *"iterate all 0 city × term combinations"*.

Only single-city scraping has ever worked in a shipped build. Meanwhile root `README.md:52-58`
documents `--all-us` as a headline feature.

Do:
- Add `Copy-Item "cities_us.txt" "dist\cities_us.txt"` to `build-exe.yml` and add it to the
  `Compress-Archive -Path` list. Same for `search_terms.txt` if anything is meant to read it
  (right now nothing does — search terms come from `config.ini`'s `search_terms` key, so
  consider dropping it from `spec:17` instead).
- Belt and braces: give the three read sites a `_MEIPASS` fallback so a bundled copy is used
  when none sits beside the exe. One shared `_cities_path()` helper — `cli.py` and
  `web_server.py` currently duplicate this path logic three times.
- Add a CI step after `Compress-Archive` that asserts the zip contains `cities_us.txt`, so
  this cannot regress silently again.

~45 min.

---

## 2. [BUG] The daily send cap is completely disabled between local midnight and 05:00, and `cli.py send` ignores it entirely

Two defects in one guard; fix them together because the fix is to give both send paths one
shared implementation.

**(a) UTC/local mismatch.** `web_server.py:151-161`:

```python
today_start = _dt.combine(date.today(), _dt.min.time())   # LOCAL midnight, naive
... EmailLog.created_at >= today_start
```

but rows are written with `created_at=datetime.utcnow()` (`web_server.py:537`, `cli.py:373`) —
naive **UTC**. The client is in Pakistan (UTC+5, no DST), so the comparison is off by five
hours. Verified by simulation:

```
sent local 00:00 -> stored 2026-10-03 19:00 -> counted toward cap: False
sent local 04:00 -> stored 2026-10-03 23:00 -> counted toward cap: False
sent local 05:00 -> stored 2026-10-04 00:00 -> counted toward cap: True
```

Between local 00:00 and 05:00 `_sent_today()` returns **0** no matter how much was just sent,
so the pre-flight check at `:486` passes and the in-loop re-check at `:516` never trips. A
campaign started at 00:30 sends the entire pending list uncapped; a campaign running across
midnight gets its counter reset and is granted a fresh `daily_send_cap` on top of the one it
already used. Gmail cuts off around 500/day and suspends the account — this is the failure
that ends the campaign outright, and it is in the path that supposedly *has* the cap.

**(b) The CLI has no cap at all.** `cli.py:311-384` queries every eligible trader and sends
with only `throttle_per_minute` pacing — no `_daily_cap()`, no `_sent_today()`. Commit
`00105ea` added the cap to the web path; `9fdddf5` later aligned `cli.py`'s *eligibility
filter* with the web one but left the cap behind. Root `README.md:34` tells the client to run
`cli.py send --priority-only`, i.e. the uncapped path. The two paths don't even agree on
throttle defaults: `cli.py:325` falls back to 30/min, `web_server.py:491` to 20/min.

Do:
- Move `_daily_cap()` and `_sent_today()` into `email_sender.py` and call them from both
  `web_server.py:/send/start` and `cli.py send`. One throttle default.
- Fix the window while you're there: compare against a UTC day start
  (`datetime.utcnow().date()`), or switch `EmailLog.created_at` to timezone-aware
  `datetime.now(UTC)` and compare aware-to-aware. Pick one and apply it consistently —
  `models.py:29,45,52` use naive `utcnow()` while `job_registry.py:12-13` already uses aware
  `datetime.now(UTC)`. (`utcnow()` also emits a `DeprecationWarning` on the 3.14 the repo
  targets.)
- Regression test: insert an `EmailLog` with `created_at` four hours before UTC midnight,
  freeze local time to 02:00 Asia/Karachi, assert it **is** counted.

~45 min.

---

## 3. [BUG] Google Places error statuses are never checked — a failed scrape silently marks every area "done" for 30 days

Carried over from 2026-09-20, untouched. `standalone/places_scraper.py:38-40` and `:61-65`
only call `r.raise_for_status()`. The Places API returns **HTTP 200** for `REQUEST_DENIED`,
`OVER_QUERY_LIMIT` and `INVALID_REQUEST` — the error lives in the JSON `status` /
`error_message` fields, and `grep -n status standalone/places_scraper.py` still matches only
`raise_for_status`.

Failure chain:
- `_text_search_page` returns `{"status": "REQUEST_DENIED", ...}` with no `results` key
- `search_places:51` does `data.get("results", [])` → `[]`
- the per-place loop at `:151` never runs, `saved` stays 0
- `mark_done(db, city, state, term, 0)` at `:195` still executes
- `is_done` (`area_manager.py:13-22`) now skips that area for `rescrape_days` (30)

A bad key or disabled billing therefore walks every area, prints `→ saved 0 new trader(s)`
hundreds of times, and then `--resume` skips all of it for a month. Same blindness truncates
pagination: `search_places:48-49` sleeps a fixed 2s before reusing `next_page_token` and never
detects `INVALID_REQUEST`, silently capping results at 20 instead of 60.

Do:
- In `_text_search_page` and `get_place_details`, read `data.get("status")`. Accept `OK` and
  `ZERO_RESULTS`; raise a `PlacesApiError` carrying `error_message` otherwise.
- In `run_places_scrape`, only call `mark_done` when the search genuinely succeeded. Note the
  `except Exception: continue` at `:146-148` must not swallow the new error class into the
  "just move on" path for key/quota failures — those should abort the run like
  `BillingLimitError` does.
- Add one unit test: a mocked 200 response with `status="REQUEST_DENIED"` must leave
  `ScrapedArea` empty. That single test also covers the ghost-record class of bug that
  `9fdddf5` fixed by hand.

~1 hour.

---

## 4. [BUG] One transient SMTP failure permanently burns a contact

Carried over from 2026-09-20, untouched. `email_sender.py:114-115` returns
`{"success": False}` for *any* exception — timeout, temporary 4xx greylist, dropped wifi. Both
callers (`web_server.py:523`, `cli.py:359`) then write `email_status = "bounced"`, which is
permanent: the send query requires `email_status == "pending"` (`web_server.py:458`,
`cli.py:332`), and the only un-do in the UI, `/contacts/{id}/reset`
(`web_server.py:214-225`), clears `approved` and *not* `email_status`.

A five-minute network blip mid-campaign silently retires every prospect that was in flight,
and nothing in the dashboard can bring them back. Note `bounced` is also overloaded as the
unsubscribe sentinel (`web_server.py:235`), so the dashboard's "bounced" tile
(`web_server.py:172`) already conflates three unrelated states.

Do either (cheapest first):
- Have `/contacts/{id}/reset` also set `email_status = "pending"` and `sent_at = None`, plus a
  "Retry failed sends" button on `/send` that resets rows whose last `EmailLog.error_message`
  looks transient; **or**
- Distinguish hard bounces (`SMTPRecipientsRefused`, SMTP 5xx) from soft failures in
  `send_one` and only mark the hard ones, writing soft failures as a distinct
  `email_status = "deferred"`.

~45 min.

---

## 5. [QUICK WIN ~15min] The release runbook names the wrong Gist file — it will re-break the update banner

Commit `a08e1a3` fixed `update_checker.py:15` from `version.json` to `Supplier_Scraper.json`
because the wrong filename 404'd silently and no client ever saw an update banner. Root
`README.md` still says `version.json` in three places: line 74 (release step 7), line 81
(first-time Gist setup step 1) and line 83 (the example raw URL). Follow the README on the
next release and the update channel breaks again, silently, for every client —
`check_for_update` swallows everything (`update_checker.py:47-48`).

Do: correct the filename in all three `README.md` spots and in the `update_checker.py`
docstring, and note in the README that the manifest is fetched once at process start
(`web_server.py:123-130`) so clients only see the banner on restart.

~15 min.

---

## Parked / known issues (still true, not yet worth a slot)

- `/contacts/duplicates` is O(n²): `web_server.py:248` loads every non-unsubscribed trader
  into memory and `:280-292` runs a full pairwise `SequenceMatcher().ratio()`. At the stated
  10,000-trader goal that is ~50M comparisons and the page never returns. Bucket by a 4-char
  name prefix before comparing. ~45 min. (Was item 4 last review; demoted only because the DB
  is nowhere near 10k while task 1 is unfixed.)
- `requirements_standalone.txt:6-7` pins `beautifulsoup4==4.12.3` and `lxml>=5.2.1`, but
  `grep -rn "bs4\|BeautifulSoup\|lxml" standalone/` returns **nothing** — email extraction is
  pure regex (`website_email_extractor.py:8`). Dead deps that CI installs on every tagged
  build, and `lxml>=5.2.1` is unpinned in the pipeline that produces the client's signed-ish
  artifact. Delete both lines.
- `cities_us.txt` has **13 duplicate entries** out of 267 (Akron OH, Arvada CO, Billings MT,
  Costa Mesa CA, Eugene OR, Glendale CA, Henderson NV, Inglewood CA, Lansing MI, Palmdale CA,
  Peoria IL, Rancho Cucamonga CA, Tallahassee FL). Each costs a redundant Text Search call per
  term against the 10k/month cap in `billing_guard.py:24-25`. Fold into task 1.
- `billing_guard.py:64` increments the counter *before* the HTTP request, so a timeout still
  consumes free-tier budget.
- `places_scraper.py:192` calls `_save_trader` with no `try`, and `_save_trader:102` commits
  inline. An `IntegrityError` on the `google_place_id` unique constraint (`models.py:32`) —
  exactly the CLI+web concurrency `billing_guard`'s docstring anticipates — propagates out of
  `run_places_scrape` and kills the whole run with only `finally: db.close()` to catch it.
- `backend/` and `frontend/` are the abandoned Celery + Postgres + Scrapy + Selenium +
  SendGrid + React stack. Nothing in `standalone/` imports them. `backend/requirements.txt`
  still pins `python-jose==3.3.0`, `pillow==10.3.0`, `scrapy==2.11.1`; `frontend/` has no
  lockfile. Dead weight and dependency-scanner noise — delete when convenient.
- `validator.py:40` returns `True` when no Hunter.io/ZeroBounce key is set, so `email_valid`
  means "not checked" rather than "verified". Don't read the dashboard's "valid" count
  (`web_server.py:173`) as validation.
- `website_email_extractor.extract_email_and_text` does up to 6 sequential fetches at 8s
  timeout each (`:29`, `:44`) — ~48s worst case per place, and the worst case is the *no email*
  path whose result is discarded. It also returns raw HTML as `website_text`, which
  `keyword_classifier.score_company:59-63` substring-matches — so a product keyword in a CSS
  class or nav menu earns the full +30.
- `_setup_guard` middleware (`web_server.py:66-70`) re-reads and re-parses `config.ini` from
  disk on every single HTTP request.
- Test gap worth closing opportunistically: `test_core.py:107-119` exercises
  `build_email_body` with a company name and with an unknown placeholder, but **not** with
  `company_name=None` — which is exactly the compose-preview path (`web_server.py:427`) that
  commit `a08e1a3` had to fix by hand. One three-line assertion.
- `config.ini` is gitignored; never commit it. Do not paste API keys into this file either.
