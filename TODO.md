# TODO — Supplier Scraper & Outreach System

Ranked, best first. Reviewed 2026-09-20. Everything below is anchored to code I read.

---

## 1. [BUG] Google Places error statuses are never checked — a failed scrape silently marks every area "done"

`standalone/places_scraper.py:38` and `:64` only call `r.raise_for_status()`. The Places API
returns **HTTP 200** for `REQUEST_DENIED`, `OVER_QUERY_LIMIT` and `INVALID_REQUEST` — the error
lives in the JSON `status` / `error_message` fields, which nothing in this repo reads
(`grep -n "status" places_scraper.py` → only `raise_for_status`).

Failure chain:
- `_text_search_page` returns `{"status": "REQUEST_DENIED", ...}` with no `results` key
- `search_places` (`:51`) does `data.get("results", [])` → `[]`
- the per-place loop at `:151` never executes, `saved` stays 0
- `mark_done(db, city, state, term, 0)` at `:195` still runs
- `is_done` (`standalone/area_manager.py:13-22`) now skips that area for `rescrape_days` (30)

So a full `--all-us` run with a bad key or billing disabled walks all 267 cities × N terms,
prints `→ saved 0 new trader(s)` 800+ times, and then `--resume` skips everything for a month.
This is not hypothetical — the old TODO recorded Google billing as never enabled, which is
exactly the state that produces `REQUEST_DENIED`.

Same bug truncates pagination: `search_places` sleeps 2s before reusing `next_page_token`
(`:49`), and Google intermittently answers `INVALID_REQUEST` if the token isn't warm yet —
silently capping results at 20 instead of 60.

Do:
- In `_text_search_page` / `get_place_details`, read `data.get("status")`. Accept `OK` and
  `ZERO_RESULTS`; raise a `PlacesApiError` carrying `error_message` for everything else.
- In `run_places_scrape`, only call `mark_done` when the search genuinely succeeded.
- Add one unit test: a mocked 200 response with `status="REQUEST_DENIED"` must leave
  `ScrapedArea` empty. That single test also covers the ghost-record class of bug that
  commit `9fdddf5` fixed by hand.

~1 hour.

---

## 2. [BUG] `cli.py send` bypasses the daily send cap that the dashboard enforces

`web_server.py:484-488` checks `_sent_today() >= _daily_cap()` before starting, and re-checks
inside the loop at `:516`. `cli.py:311-377` has no cap logic at all — it queries every eligible
trader and sends with only `throttle_per_minute` pacing.

Commit `00105ea` added the cap to the web path; commit `9fdddf5` later aligned cli.py's
*eligibility filter* with the web one but left the cap behind. The client's own README (root,
"Workflow" step 5) tells them to run `cli.py send --priority-only`, i.e. the uncapped path.
Gmail cuts off around 500/day and suspends the account — this is the single failure that ends
the campaign outright.

Do: lift `_daily_cap()` / `_sent_today()` out of `web_server.py` into `email_sender.py` and
call them from both paths. That also removes one of two copies.

~30 min.

---

## 3. [BUG] One transient SMTP failure permanently burns a contact

`email_sender.py:114-115` returns `success: False` for *any* exception — timeout, temporary
4xx greylist, dropped wifi. Both callers (`web_server.py:523`, `cli.py:359`) then write
`email_status = "bounced"`, which is permanent: the send query requires
`email_status == "pending"` (`web_server.py:458`, `cli.py:332`), and the only un-do in the UI,
`/contacts/{id}/reset` (`web_server.py:214-225`), clears `approved` and *not* `email_status`.

A 5-minute network blip mid-campaign silently retires however many prospects were in flight,
and nothing in the dashboard can bring them back.

Do either (cheapest first):
- Have `/contacts/{id}/reset` also set `email_status = "pending"` and `sent_at = None`, plus a
  "Retry failed sends" button on `/send` that resets rows whose last `EmailLog.error_message`
  looks transient; **or**
- Distinguish hard bounces (SMTP 5xx / `SMTPRecipientsRefused`) from soft failures in
  `send_one` and only mark the hard ones.

~45 min.

---

## 4. [IMPROVEMENT] `/contacts/duplicates` is O(n²) and will hang at the target trader count

`web_server.py:248` loads every non-unsubscribed trader into memory, then `:280-292` does a
full pairwise `SequenceMatcher(...).ratio()` over all of them. The project's own stated goal is
10,000+ traders after a full US scrape — that is ~50 million ratio() calls, each itself
quadratic in name length. The page will effectively never return, and it holds a worker thread
while it tries.

Do: bucket candidates before comparing — group by `company_name.lower()` first token, or by a
4-char prefix, and only run `SequenceMatcher` within a bucket. Cap group size. Exact-email and
phone grouping above it (`:254-274`) are already O(n) and fine; leave them.

~45 min.

---

## 5. [QUICK WIN ~15min] The release runbook names the wrong Gist file — it will re-break the update banner

Commit `a08e1a3` fixed `update_checker.py:15` from `version.json` to `Supplier_Scraper.json`
because the wrong filename 404'd silently and no client ever saw an update banner. But the
root `README.md` release section still says to create the Gist with filename `version.json`
(steps 1-2 of "First-time Gist setup") and step 7 still calls it `version.json`. Follow the
README on the next release and the update channel breaks again, silently, for every client —
`check_for_update` swallows everything (`update_checker.py:47-48`).

Do: correct the filename in root `README.md` (both places) and in the `update_checker.py`
docstring, and note in the README that the manifest is fetched once at process start
(`web_server.py:125-130`) so clients only see it on restart.

~15 min.

---

## Parked / known issues (still true, not yet worth a slot)

- `standalone/cities_us.txt` has **13 duplicate entries** out of 267 (Akron OH, Arvada CO,
  Billings MT, Costa Mesa CA, Eugene OR, Glendale CA, Henderson NV, Inglewood CA, Lansing MI,
  Palmdale CA, Peoria IL, Rancho Cucamonga CA, Tallahassee FL). Each costs a redundant Text
  Search call per term against a hard 10k/month free cap (`billing_guard.py:24-25`). ~5 min to
  dedupe, worth folding into the next scraper change.
- `backend/` and `frontend/` are the abandoned Celery + Postgres + Scrapy + Selenium + SendGrid
  + React stack. Nothing in `standalone/` imports them. `backend/requirements.txt` still pins
  `python-jose==3.3.0`, `pillow==10.3.0`, `scrapy==2.11.1`; `frontend/` has no lockfile. Dead
  weight and dependency-scanner noise — delete when convenient.
- `validator.py:40` returns `True` when no Hunter.io/ZeroBounce key is set, so `email_valid`
  means "not checked" rather than "verified". Fine, but don't read the dashboard's "valid"
  count as validation.
- `website_email_extractor.extract_email_and_text` does up to 6 fetches at 8s timeout each
  (`:29`, `:44`) — worst case ~48s per place, and the worst case is the *no email* path that
  gets discarded. Watch this if all-US runs turn out to be slow.
- `_setup_guard` middleware (`web_server.py:66-70`) re-reads and re-parses `config.ini` from
  disk on every single HTTP request.
- `config.ini` is gitignored; never commit it. Do not paste API keys into this file either.
