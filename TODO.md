# TODO — Supplier Scraper & Outreach System

Ranked, best first. Reviewed 2026-11-06. Everything below is anchored to code I read.

**Correction to the last review:** the 2026-10-13 notes claimed
`agent/2026-09-20-google-places-error-statuses-are-never-c` was "an empty branch, zero commits
ahead of main." It was not — PR #1 merged as `fac30b0` on 2026-09-22 and the fix is live
(`places_scraper.py:30-34,47-49,77-78`). Don't re-do it. But it fixed **one of two** call
sites, and the hole it left is now task 1.

Still true: no product code has changed since `fac30b0` (six weeks), and nothing before that
since `a08e1a3` (2026-06-19). Tasks 2, 3, 4 and 5 are carried over — 2 for the fourth time.

**The decision that outranks this whole list** (not a 1-hour task, so it isn't one below):
the scraper targets Google **Places API (legacy)** (`places_scraper.py:26-27`), closed to new
Cloud projects since 2025-03-01, while `cli.py:79`, `cli.py:133` and
`templates/setup.html:42` all instruct the client to create a *new* project and enable it.
Today's build works only because Schion's project is grandfathered. Spend two minutes on this
before anything else: open the Cloud console on a fresh project and try to enable "Places
API". If only "Places API (New)" is offered, the product cannot be onboarded to a second
client or re-keyed after a compromise, and the `places.googleapis.com/v1` migration becomes
the next multi-session project. Record the answer here either way so review five isn't guessing.

---

## 1. [BUG] The ghost-area bug is only half fixed — a Place Details failure still marks the area done and poisons `--resume` for 30 days

PR #1 taught `_text_search_page` and `get_place_details` to raise `PlacesApiError` on a
non-`OK` status. That closed the Text Search path, because an exception out of
`search_places()` lands on `run_places_scrape:160-162`, which does `continue` **before**
`mark_done`. The Place Details path has the opposite shape:

- `places_scraper.py:179` — `get_place_details` raises `PlacesApiError`
- `:185-187` — `except Exception: print_fn("[skip] … Place Details failed"); continue`
  (per-place, swallowed)
- loop ends with `saved == 0`
- `:209` — **`mark_done(db, city, state, term, saved)` runs anyway**
- `area_manager.py:13-22` — `is_done` sees the row and returns `True` for `rescrape_days` (30)

So: Text Search succeeds (1 call), then the key gets denied / quota trips / Google returns
`OVER_QUERY_LIMIT` on the QPS limiter, all 20-60 Details calls fail individually, and the area
is recorded as "done, 0 results." `result_count=0` is indistinguishable from a legitimately
empty city, so nothing can detect it after the fact. On the 267-city × 3-term run the client
actually uses — "Resume" on the Scrape page (`web_server.py:683` passes `rescrape_days` only
when `use_resume`) — those areas are skipped for a month and never retried.

Two more `mark_done` calls have the same defect, and they are deliberate:

- `:168-169` — cancel mid-area marks the whole area done. Hit Cancel on place 3 of 60 and the
  other 57 are written off for 30 days.
- `:183-184` — `BillingLimitError` mid-area, same thing.

Do — **no schema change**; `db.py:32-34` is `create_all`, which does not add columns to an
existing client DB, so a new `ScrapedArea.complete` flag would raise `no such column` on every
machine already in the field:

- Set a local `area_failed = False` in the per-area block; set it `True` in the `:185-187`
  handler. Guard `:209` with `if not area_failed:` and print why it was left unmarked.
- Delete the `mark_done` at `:168` and `:183`. A partially-walked area must stay unmarked —
  re-searching it later costs one Text Search call, which is the cheap half of the bill.
- Keep per-place skips that are *not* API failures (`:171-176` no `place_id`/already seen,
  `:195-197` no email) out of `area_failed` — those are real, complete outcomes.
- **The test that would have caught this** (and the one `test_places_scraper.py:22` missed):
  patch `httpx.get` with a side-effect list — Text Search returns `status="OK"` with one
  result, Details returns 200 with `status="OVER_QUERY_LIMIT"` — then assert
  `ScrapedArea.count() == 0`. Mirror the existing test's in-memory-SQLite setup.

~45 min.

---

## 2. [BUG] The release zip has never shipped `cities_us.txt` — `--all-us` and Resume are dead on every client machine

**Fourth review.** This is the whole product; everything else is secondary. Verified again
today, unchanged.

Frozen builds read the city list from the directory beside the exe:

- `cli.py:22-28` — `BASE_DIR = Path(sys.executable).parent`, `CITIES_FILE = BASE_DIR / "cities_us.txt"`
- `web_server.py:567` (`_scrape_page_ctx`) and `:631` (`/scrape/start`) — same construction

`supplier_scraper.spec:15-16` bundles `cities_us.txt` and `search_terms.txt` into `datas`,
which PyInstaller unpacks to `sys._MEIPASS`. **Nothing reads `cities_us.txt` from `_MEIPASS`** —
`web_server.py:32` is the only `_MEIPASS` use in the repo and it covers `templates/` only. The
bundled copy is unreachable; the copy beside the exe does not exist, because
`build-exe.yml` still packages exactly four files:

```
dist\supplier_scraper.exe, dist\config.ini, dist\README.md, dist\SETUP_GUIDE.pdf
```

`cities_us.txt` has not been in the zip in any revision since the distribution system landed in
`f38f5bd`. v1.0.0 → v1.0.2 all ship without it, and neither `README.md` nor `SETUP_GUIDE.pdf`
tells the client to create it. The dev path works (`cli.py:25`, `web_server.py:571` fall back
to `Path(__file__).parent`), which is exactly why this has survived four reviews — it is
invisible unless you run a real build.

What the client sees:

- `scrape --all-us` → `_load_cities()` (`cli.py:84-97`) returns `[]` → `cli.py:261` prints
  "cities_us.txt not found at …" and `sys.exit(1)`
- Scrape page → "Scrape All US" or "Resume" → `web_server.py:672` → "No cities loaded. Check cities_us.txt"
- Scrape page, always: `num_cities = 0` (`web_server.py:578-581`) → `total_areas_possible = 0` →
  `templates/scrape.html:46` renders **"0 / 0 city×term combinations searched"**, `:47` hides
  the progress bar, `:71` offers *"iterate all 0 city × term combinations"*

Only single-city scraping has ever worked in a shipped build, while `README.md:52-58`
documents `--all-us` as a headline feature.

Do:
- Add `Copy-Item "cities_us.txt" "dist\cities_us.txt"` to `build-exe.yml`'s package step and add
  it to the `Compress-Archive -Path` list. Drop `search_terms.txt` from `spec:16` rather than
  shipping it — nothing reads it; terms come from `config.ini`'s `search_terms` key.
- Add a CI step after `Compress-Archive` asserting the zip contains `cities_us.txt`, so this
  cannot regress silently a fifth time.
- Belt and braces: give the three read sites a `_MEIPASS` fallback so the bundled copy is used
  when none sits beside the exe. One shared helper — the frozen/dev two-liner is copy-pasted in
  **six** places (`cli.py:22-25`, `web_server.py:17-19`, `:30-34`, `billing_guard.py:21`,
  `db.py:8`, `app_logger.py:6`).
- While in the file: `cities_us.txt` has 13 duplicates out of 267 (Akron OH, Arvada CO,
  Billings MT, Costa Mesa CA, Eugene OR, Glendale CA, Henderson NV, Inglewood CA, Lansing MI,
  Palmdale CA, Peoria IL, Rancho Cucamonga CA, Tallahassee FL). Each costs a redundant Text
  Search per term.

~45 min.

---

## 3. [BUG] The daily send cap is disabled between local 00:00 and 05:00, and `cli.py send` ignores it entirely

Two defects in one guard. Fix together, because the fix is to give both send paths one
implementation.

**(a) UTC/local mismatch.** `web_server.py:150-157`:

```python
today_start = _dt.combine(date.today(), _dt.min.time())   # LOCAL midnight, naive
... EmailLog.created_at >= today_start
```

Rows are written with `created_at=datetime.utcnow()` (`web_server.py:538`, `cli.py:371`) —
naive **UTC**. The client is in Pakistan (UTC+5, no DST), so the window is off by five hours:

```
sent local 00:00 -> stored 19:00 previous UTC day -> counted: False
sent local 04:00 -> stored 23:00 previous UTC day -> counted: False
sent local 05:00 -> stored 00:00 same UTC day     -> counted: True
```

Between local 00:00 and 05:00 `_sent_today()` returns **0** regardless of what was just sent,
so the pre-flight check at `:486` passes and the in-loop re-check at `:513` never trips. A
campaign started at 00:30 sends the entire pending list uncapped; one running across midnight
gets its counter reset and a fresh `daily_send_cap` on top of the one it already spent. Gmail
cuts off near 500/day and suspends the account — this is the failure that ends the campaign,
and it is in the path that supposedly *has* a cap.

**(b) The CLI has no cap at all.** `cli.py:311-383` queries every eligible trader and sends with
only `throttle_per_minute` pacing (`cli.py:325`) — no `_daily_cap()`, no `_sent_today()`.
Commit `00105ea` added the cap to the web path; `9fdddf5` later aligned `cli.py`'s *eligibility
filter* with the web one (`cli.py:329-335` vs `web_server.py:498-504` — now identical) but left
the cap behind. `README.md:34` tells the client to run `cli.py send --priority-only`, i.e. the
uncapped path. The two paths don't even agree on the throttle default: `cli.py:325` falls back
to 30/min, `web_server.py:491` to 20/min.

Do:
- Move `_daily_cap()` and `_sent_today()` into `email_sender.py`; call from both
  `web_server.py:/send/start` and `cli.py send`. One throttle default.
- Fix the window: compare against a UTC day start, or switch `EmailLog.created_at` to aware
  `datetime.now(UTC)` and compare aware-to-aware. Pick one and apply it consistently —
  `models.py:29,45,52` use naive `utcnow()` while `job_registry.py` already uses aware
  `datetime.now(UTC)`. (`utcnow()` also emits a `DeprecationWarning` on the 3.14 this repo
  targets; `python3 -V` here is 3.14.4.)
- Regression test: insert an `EmailLog` four hours before UTC midnight, freeze local time to
  02:00 Asia/Karachi, assert it **is** counted.

~45 min.

---

## 4. [QUICK WIN ~15min] Two places where the docs promise something the code doesn't do — both one-liners

(a) **The release runbook names the wrong Gist file.** `a08e1a3` fixed `update_checker.py:15`
from `version.json` to `Supplier_Scraper.json` because the wrong name 404'd silently and no
client ever saw an update banner. The live constant is right. `README.md` still says
`version.json` at line 74 (release step 7), line 81 (Gist setup step 1) and line 83 (the
example raw URL). Follow the README on the next release and the update channel breaks again,
silently, for every client — `check_for_update` swallows every exception
(`update_checker.py:47-48`).

(b) **`scrape --resume` on its own exits with an error.** `cli.py:9` and the `--resume` help at
`cli.py:231` document it as "Continue from where you left off," but `--resume` only sets
`rescrape_days` (`cli.py:273`) — it never loads a city list. With neither `--city` nor
`--all-us`, control reaches `cli.py:265-267` and prints `Specify --city "City, ST" or --all-us`
then `sys.exit(1)`. The working incantation is `scrape --all-us --resume`, which is documented
nowhere.

Do: correct the filename in the three `README.md` spots and in the `update_checker.py:13-14`
comment; note in the README that the manifest is fetched once at process start
(`web_server.py:124-130`), so clients only see the banner after a restart. Change
`cli.py:258` to `elif all_us or resume:` and fix the docstring at `cli.py:9`.

~15 min.

---

## 5. [IMPROVEMENT] `billing_guard` promises protection it can't deliver, and `DETAILS_FIELDS` buys the priciest SKU for a column nothing reads

`billing_guard.py:4-9` and `:24-25` assert a flat free tier of **10,000 calls/month per
endpoint**, and `:60-63` tells the client it is "Stopping to avoid charges." That number
matches neither Google pricing model: the legacy model was a single shared **$200 monthly
credit** across all Maps SKUs (not two independent 10k allowances), and the post-2025 model is
per-SKU monthly caps tiered Essentials / Pro / Enterprise, all **below** 10,000 for the SKUs
this code calls. Either way the guard lets the client run past the free allowance and onto
their card — the exact opposite of its stated job. `README.md:47` repeats the wrong number.

Compounding it, `places_scraper.py:28`:

```python
DETAILS_FIELDS = "name,formatted_phone_number,website,formatted_address,url,types,rating"
```

`rating` is the only field here in the top-priced tier, and it drags **every** Place Details
call into that tier. It is dead weight: `grep -rn rating standalone/` returns exactly three
hits — this line, the write at `places_scraper.py:111`, and the column at `models.py:33`.
`google_rating` is never read: not in any template, not in `keyword_classifier.score_company`,
not in the CSV export. The client pays the premium rate on every lookup for a value nobody
looks at.

Do:
- Delete `rating` from `DETAILS_FIELDS`. Leave the `models.py:33` column alone — dropping it
  needs a migration `create_all` won't do, and it costs nothing to keep.
- Replace `FREE_TEXT_SEARCH`/`FREE_PLACE_DETAILS` with the real allowances read off Schion's
  own Cloud console billing page, and correct the docstring and `README.md:47`. If the
  allowance is a shared credit rather than per-endpoint call counts, say so in the docstring
  rather than implying a guarantee the design cannot make.
- `billing_guard.py:64` increments the counter *before* the HTTP request (`check_text_search`
  at `places_scraper.py:40`, `check_place_details` at `:70`), so a timeout still consumes
  budget. Move the increment to after a successful response.

~30 min.

---

## Parked / known issues (still true, not yet worth a slot)

- **The test suite has never been run in CI, and can't be run here.** 13 tests across
  `tests/test_core.py` (8), `test_job_registry.py` (4), `test_places_scraper.py` (1), and no
  workflow invokes them — `build-exe.yml` only builds on `v*.*.*` tags. The
  `test_places_scraper.py` that shipped with PR #1 was never executed (the PR body says so
  outright: no `sqlalchemy`/`httpx` in that sandbox); same here today, no venv and
  `ModuleNotFoundError: No module named 'sqlalchemy'`. A `python -m unittest discover tests`
  job on push is ~10 lines and would have caught task 1's gap the moment it was written.
- **[BUG, demoted from a slot three times]** One transient SMTP failure permanently burns a
  contact. `email_sender.py:114-115` returns `{"success": False}` for *any* exception — timeout,
  temporary 4xx greylist, dropped wifi. Both callers (`web_server.py:520`, `cli.py:357`) then
  write `email_status = "bounced"`, which is permanent: the send query requires
  `email_status == "pending"` (`web_server.py:500`, `cli.py:331`), and the only UI un-do,
  `/contacts/{id}/reset`, clears `approved` and *not* `email_status`. A five-minute blip
  mid-campaign silently retires every prospect in flight. `bounced` is also the unsubscribe
  sentinel, so the dashboard's "bounced" tile conflates three unrelated states. Cheapest fix:
  have `/contacts/{id}/reset` also set `email_status = "pending"` and `sent_at = None`. ~45 min.
  **Promote this the moment a campaign is scheduled.**
- `/contacts/duplicates` is O(n²): `web_server.py:248` loads every non-unsubscribed trader into
  memory and runs a full pairwise `SequenceMatcher().ratio()`. At the stated 10,000-trader goal
  that is ~50M comparisons and the page never returns. Bucket by a 4-char name prefix first.
- `requirements_standalone.txt:6-7` pins `beautifulsoup4==4.12.3` and `lxml>=5.2.1`, but
  `grep -rn "bs4\|BeautifulSoup\|lxml" standalone/` returns **nothing** — extraction is pure
  regex (`website_email_extractor.py:8`). Dead deps CI installs on every tagged build, and
  `lxml>=5.2.1` is unpinned in the pipeline that produces the client's artifact. Delete both.
- `places_scraper.py:206` calls `_save_trader` with no `try`, and `_save_trader:116` commits
  inline. An `IntegrityError` on the `google_place_id` unique constraint (`models.py:32`) —
  exactly the CLI+web concurrency `billing_guard`'s docstring anticipates — propagates out of
  `run_places_scrape` and kills the run, with only `finally: db.close()` behind it.
- `backend/` and `frontend/` are the abandoned Celery + Postgres + Scrapy + Selenium + SendGrid
  + React stack. Nothing in `standalone/` imports them. `backend/requirements.txt` still pins
  `python-jose==3.3.0`, `pillow==10.3.0`, `scrapy==2.11.1`; `frontend/` has no lockfile. Dead
  weight and dependency-scanner noise — delete when convenient.
- `validator.py:40` returns `True` when no Hunter.io/ZeroBounce key is set, so `email_valid`
  means "not checked," not "verified." Don't read the dashboard's "valid" count as validation.
- `website_email_extractor.extract_email_and_text` does up to 6 sequential fetches at 8s
  timeout each — ~48s worst case per place, and the worst case is the *no email* path whose
  result is discarded (`places_scraper.py:195-197`). It also returns raw HTML as
  `website_text`, which `keyword_classifier.score_company` substring-matches — so a product
  keyword in a CSS class or nav menu earns the full +30.
- `_setup_guard` middleware (`web_server.py:66-70`) re-reads and re-parses `config.ini` from
  disk on every single HTTP request.
- `_scrape_page_ctx:578-581` counts cities as "every non-comment line," while `scrape_start:641`
  and `cli.py:94-96` require a comma. All 267 current lines have one, so the progress
  denominator happens to agree with reality — add a line without a state and it silently
  won't. Fold into task 2.
- Small gap worth closing opportunistically: `test_core.py:107-119` exercises
  `build_email_body` with a company name and with an unknown placeholder, but **not** with
  `company_name=None` — exactly the compose-preview path `a08e1a3` had to fix by hand. One
  three-line assertion.
- Stray `standalone/tests/__pycache__` entries with no matching `.py` — gitignored, harmless.
- `config.ini` is gitignored; never commit it, and don't paste API keys into this file either.
