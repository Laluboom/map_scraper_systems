# TODO — Supplier Scraper & Outreach System

Ranked, best first. Reviewed 2026-10-13. Everything below is anchored to code I read.

**Note on the last two reviews:** nothing has been touched. The last commit that changed a
line of product code is `a08e1a3`, dated **2026-06-19** — nearly four months ago. The only
commits since are the two review-notes commits, and
`agent/2026-09-20-google-places-error-statuses-are-never-c` is still an empty branch (zero
commits ahead of `main`). Items 1, 3 and 4 below are carried over for the third time.

This repo sits in `01_active_projects` but has not been active since June. Either pick one
item off this list or move it to a maintenance tier — a third stale review is not useful.

---

## 1. [BUG] The release zip has never shipped `cities_us.txt` — `--all-us` and resume scraping are dead on every client machine

Third review running. This is the whole product; everything else is secondary.

When frozen, the app reads the city list from the directory **next to the exe**:

- `standalone/cli.py:22-28` — `BASE_DIR = Path(sys.executable).parent`, `CITIES_FILE = BASE_DIR / "cities_us.txt"`
- `standalone/web_server.py:627` (`/scrape/start`) and `:566` (`_scrape_page_ctx`) — both `Path(sys.executable).parent / "cities_us.txt"`

`standalone/supplier_scraper.spec:16-17` bundles `cities_us.txt` and `search_terms.txt` into
`datas`, which PyInstaller unpacks to `sys._MEIPASS`. **Nothing reads `cities_us.txt` from
`_MEIPASS`** — `web_server.py:32` is the only `_MEIPASS` use in the repo and it is for
`templates/` only. So the bundled copy is unreachable, and the copy beside the exe does not
exist, because `.github/workflows/build-exe.yml:38-42` still packages exactly four files:

```
dist\supplier_scraper.exe, dist\config.ini, dist\README.md, dist\SETUP_GUIDE.pdf
```

`cities_us.txt` has never been in the zip in any revision since the distribution system landed
in `f38f5bd`. v1.0.0 → v1.0.2 all ship without it, and nothing in `README.md` or
`SETUP_GUIDE.pdf` tells the client to create it. Note the dev path works fine
(`cli.py:25`/`web_server.py:630` fall back to `Path(__file__).parent`), which is exactly why
this has survived three reviews — it is invisible unless you run a real build.

What the client actually sees:

- `cli.py scrape --all-us` → `_load_cities()` returns `[]` → `cli.py:261` prints
  "cities_us.txt not found at …" and `sys.exit(1)`
- Dashboard → Scrape → "Scrape All US" or "Resume" → `web_server.py:668` →
  redirect with "No cities loaded. Check cities_us.txt"
- Dashboard → Scrape page, always: `num_cities = 0` (`web_server.py:565-569`) →
  `total_areas_possible = 0` → `templates/scrape.html:46` renders **"0 / 0 city×term
  combinations searched"**, `:47` hides the progress bar entirely, and `:71` offers
  *"iterate all 0 city × term combinations"*.

Only single-city scraping has ever worked in a shipped build, while root `README.md:52-58`
documents `--all-us` as a headline feature.

Do:
- Add `Copy-Item "cities_us.txt" "dist\cities_us.txt"` to `build-exe.yml` and add it to the
  `Compress-Archive -Path` list. Drop `search_terms.txt` from `spec:17` instead of shipping it
  — nothing reads it; search terms come from `config.ini`'s `search_terms` key.
- Belt and braces: give the three read sites a `_MEIPASS` fallback so the bundled copy is used
  when none sits beside the exe. One shared helper — the frozen/dev two-liner is currently
  copy-pasted in **five** places (`cli.py:22-25`, `web_server.py:17-19`, `:30-34`,
  `billing_guard.py:21`, `db.py:8`, `app_logger.py:6`).
- Add a CI step after `Compress-Archive` asserting the zip contains `cities_us.txt`, so this
  cannot regress silently a fourth time.

~45 min.

---

## 2. [BUG] The scraper is built on the *legacy* Places API, which no new Google Cloud project can enable — the product is unshippable to any new client

New this review, and the one finding here that is a business problem rather than a code
problem.

Both call sites use the legacy endpoints:

- `standalone/places_scraper.py:26` — `https://maps.googleapis.com/maps/api/place/textsearch/json`
- `standalone/places_scraper.py:27` — `https://maps.googleapis.com/maps/api/place/details/json`

Google closed **Places API (legacy)** to new customers on **2025-03-01**. A project that had
never enabled it before that date cannot enable it at all; the replacement is Places API (New)
at `places.googleapis.com/v1/…`. Existing projects are grandfathered, which is why the current
client's key still works and why this has gone unnoticed.

But the setup flow tells every client to create a brand-new project and enable the thing they
cannot enable:

- `standalone/cli.py:79` — *"console.cloud.google.com → New Project → Enable 'Places API' → Credentials → Create API Key"*
- `standalone/cli.py:133` — same copy in the `setup` wizard
- `standalone/templates/setup.html:42` — same copy on the first-run setup page

So: onboarding a second client fails, and so does rotating to a fresh project if the current
key is ever compromised or the project is deleted. `make_guide_pdf.py:96,126` says the key is
"Provided by Schion", which is the only reason the shipped product works today — it depends
entirely on one grandfathered project.

**Verify before doing the work** (2 minutes, and it decides the priority): open the Cloud
console on a fresh project and try to enable "Places API". If it is absent and only
"Places API (New)" is offered, this is confirmed.

Do — scope to the two functions, keep `_save_trader` untouched behind an adapter:
- `_text_search_page` → `POST https://places.googleapis.com/v1/places:searchText`, API key in
  the `X-Goog-Api-Key` header, body `{"textQuery": query, "pageToken": …}`, and a
  `X-Goog-FieldMask` header listing the fields you want (the field mask is mandatory and it is
  what you get billed for — see task 4).
- `get_place_details` → `GET https://places.googleapis.com/v1/places/{place_id}` with a field
  mask header.
- Map the new camelCase response back to the keys `_save_trader` already expects:
  `places[]`→results, `id`→`place_id`, `displayName.text`→`name`,
  `nationalPhoneNumber`→`formatted_phone_number`, `websiteUri`→`website`,
  `formattedAddress`→`formatted_address`, `googleMapsUri`→`url`, `types`, `rating`.
- Delete the `time.sleep(2)` at `places_scraper.py:49` — the next-page delay was a legacy
  requirement and `nextPageToken` in the new API does not need it.
- **This migration also fixes the carried-over `REQUEST_DENIED` bug for free.** The legacy API
  returns **HTTP 200** with the error in a JSON `status` field, and `places_scraper.py:38-40`
  and `:61-65` only call `r.raise_for_status()` — so a bad key or disabled billing produced
  `data.get("results", [])` → `[]` (`:51`), `saved` stayed 0, `mark_done` at `:195` still ran,
  and `is_done` (`area_manager.py:13-22`) then skipped that area for `rescrape_days` (30). A
  bad key walked every area, printed `→ saved 0 new trader(s)` hundreds of times, and poisoned
  `--resume` for a month. The new API returns a real 4xx, so `raise_for_status()` starts
  working — but still make sure the `except Exception: continue` at `:146-148` does **not**
  swallow auth/quota errors into the "just move on" path; those should abort the run the way
  `BillingLimitError` does.
- One unit test: a mocked `403` from `searchText` must abort the run and leave `ScrapedArea`
  empty.

~1 hour. If the response mapping balloons, stop at a working Text Search and leave Details for
the next session — a half-migrated scraper that errors loudly still beats one that lies.

---

## 3. [BUG] The daily send cap is completely disabled between local midnight and 05:00, and `cli.py send` ignores it entirely

Two defects in one guard; fix them together, because the fix is to give both send paths one
shared implementation.

**(a) UTC/local mismatch.** `web_server.py:149-156`:

```python
today_start = _dt.combine(date.today(), _dt.min.time())   # LOCAL midnight, naive
... EmailLog.created_at >= today_start
```

but rows are written with `created_at=datetime.utcnow()` (`web_server.py:537`, `cli.py:373`) —
naive **UTC**. The client is in Pakistan (UTC+5, no DST), so the comparison is off by five
hours:

```
sent local 00:00 -> stored 19:00 previous UTC day -> counted toward cap: False
sent local 04:00 -> stored 23:00 previous UTC day -> counted toward cap: False
sent local 05:00 -> stored 00:00 same UTC day     -> counted toward cap: True
```

Between local 00:00 and 05:00 `_sent_today()` returns **0** no matter how much was just sent,
so the pre-flight check at `:486` passes and the in-loop re-check at `:516` never trips. A
campaign started at 00:30 sends the entire pending list uncapped; a campaign running across
midnight gets its counter reset and is granted a fresh `daily_send_cap` on top of the one it
already used. Gmail cuts off around 500/day and suspends the account — this is the failure that
ends the campaign outright, and it is in the path that supposedly *has* a cap.

**(b) The CLI has no cap at all.** `cli.py:311-384` queries every eligible trader and sends
with only `throttle_per_minute` pacing (`cli.py:325`) — no `_daily_cap()`, no `_sent_today()`.
Commit `00105ea` added the cap to the web path; `9fdddf5` later aligned `cli.py`'s *eligibility
filter* with the web one but left the cap behind. Root `README.md:34` tells the client to run
`cli.py send --priority-only`, i.e. the uncapped path. The two paths don't even agree on
throttle defaults: `cli.py:325` falls back to 30/min, `web_server.py:491` to 20/min.

Do:
- Move `_daily_cap()` and `_sent_today()` into `email_sender.py` and call them from both
  `web_server.py:/send/start` and `cli.py send`. One throttle default.
- Fix the window while you are there: compare against a UTC day start, or switch
  `EmailLog.created_at` to timezone-aware `datetime.now(UTC)` and compare aware-to-aware. Pick
  one and apply it consistently — `models.py:29,45,52` use naive `utcnow()` while
  `job_registry.py:12-13` already uses aware `datetime.now(UTC)`. (`utcnow()` also emits a
  `DeprecationWarning` on the 3.14 this repo targets; `python3 -V` here is 3.14.4.)
- Regression test: insert an `EmailLog` with `created_at` four hours before UTC midnight,
  freeze local time to 02:00 Asia/Karachi, assert it **is** counted.

~45 min.

---

## 4. [IMPROVEMENT] `billing_guard` promises protection it cannot deliver, and `DETAILS_FIELDS` buys the most expensive SKU for a column nothing reads

`billing_guard.py:4-9` and `:24-25` assert a flat free tier of **10,000 calls/month per
endpoint**, and `:61-62` tells the client it is "Stopping to avoid charges." That number does
not correspond to either Google pricing model: the legacy model was a single shared **$200
monthly credit** across all Maps SKUs (not two independent 10k allowances), and the post-2025
model is per-SKU monthly caps tiered Essentials / Pro / Enterprise, all of which are **below**
10,000 for the SKUs this code calls. Either way the guard lets the client run well past the
free allowance and onto their card, which is the exact opposite of its stated job. `README.md:47`
repeats the wrong number to the client.

Compounding it, `places_scraper.py:28`:

```python
DETAILS_FIELDS = "name,formatted_phone_number,website,formatted_address,url,types,rating"
```

`rating` is the only field here in the top-priced tier, and it drags **every single Place
Details call** into that tier. And it is dead weight — `grep -rn rating standalone/` returns
exactly three hits: this line, the write at `places_scraper.py:97`, and the column at
`models.py:33`. `google_rating` is never read: not in any template, not in
`keyword_classifier.score_company`, not in the CSV export (`web_server.py:728-740`). The
client pays the premium rate on every lookup for a value nobody ever looks at.

Do:
- Delete `rating` from `DETAILS_FIELDS`. Leave the `models.py:33` column alone (dropping it
  needs a migration and it costs nothing to keep). One-line change, immediate per-call saving.
- Replace the `FREE_TEXT_SEARCH`/`FREE_PLACE_DETAILS` constants with the real current
  allowances read off the client's own Cloud console billing page, and correct the docstring
  and `README.md:47`. If the allowance is a shared credit rather than per-endpoint call counts,
  say so in the docstring rather than implying a guarantee the design cannot make.
- `billing_guard.py:64` increments the counter *before* the HTTP request, so a timeout still
  consumes budget. Move the increment to after a successful response while you are in here.

~30 min. If you are doing task 2 first, fold the `DETAILS_FIELDS` change into the new field
mask instead of doing it twice.

---

## 5. [QUICK WIN ~15min] The release runbook names the wrong Gist file — it will re-break the update banner

Commit `a08e1a3` fixed `update_checker.py:15` from `version.json` to `Supplier_Scraper.json`
because the wrong filename 404'd silently and no client ever saw an update banner. The live
constant is correct today. Root `README.md` still says `version.json` in three places: line 74
(release step 7), line 81 (first-time Gist setup step 1) and line 83 (the example raw URL).
Follow the README on the next release and the update channel breaks again, silently, for every
client — `check_for_update` swallows every exception (`update_checker.py:47-48`).

Do: correct the filename in all three `README.md` spots and in the `update_checker.py:13-14`
comment, and note in the README that the manifest is fetched once at process start
(`web_server.py:123-130`), so clients only see the banner after a restart.

~15 min.

---

## Parked / known issues (still true, not yet worth a slot)

- **[BUG, demoted from slot 4 twice]** One transient SMTP failure permanently burns a contact.
  `email_sender.py:114-115` returns `{"success": False}` for *any* exception — timeout,
  temporary 4xx greylist, dropped wifi. Both callers (`web_server.py:523`, `cli.py:359`) then
  write `email_status = "bounced"`, which is permanent: the send query requires
  `email_status == "pending"` (`web_server.py:458`, `cli.py:332`), and the only un-do in the
  UI, `/contacts/{id}/reset` (`web_server.py:214-225`), clears `approved` and *not*
  `email_status`. A five-minute network blip mid-campaign silently retires every prospect in
  flight. `bounced` is also overloaded as the unsubscribe sentinel (`web_server.py:235`), so
  the dashboard's "bounced" tile (`web_server.py:172`) conflates three unrelated states.
  Cheapest fix: have `/contacts/{id}/reset` also set `email_status = "pending"` and
  `sent_at = None`. ~45 min. Promote this if a campaign is about to run.
- `/contacts/duplicates` is O(n²): `web_server.py:248` loads every non-unsubscribed trader into
  memory and `:280-292` runs a full pairwise `SequenceMatcher().ratio()`. At the stated
  10,000-trader goal that is ~50M comparisons and the page never returns. Bucket by a 4-char
  name prefix before comparing. ~45 min.
- `requirements_standalone.txt:6-7` pins `beautifulsoup4==4.12.3` and `lxml>=5.2.1`, but
  `grep -rn "bs4\|BeautifulSoup\|lxml" standalone/` returns **nothing** — email extraction is
  pure regex (`website_email_extractor.py:8`). Dead deps that CI installs on every tagged
  build, and `lxml>=5.2.1` is unpinned in the pipeline that produces the client's artifact.
  Delete both lines.
- `cities_us.txt` has **13 duplicate entries** out of 267 (Akron OH, Arvada CO, Billings MT,
  Costa Mesa CA, Eugene OR, Glendale CA, Henderson NV, Inglewood CA, Lansing MI, Palmdale CA,
  Peoria IL, Rancho Cucamonga CA, Tallahassee FL). Each costs a redundant Text Search call per
  term. Fold into task 1.
- `places_scraper.py:192` calls `_save_trader` with no `try`, and `_save_trader:102` commits
  inline. An `IntegrityError` on the `google_place_id` unique constraint (`models.py:32`) —
  exactly the CLI+web concurrency `billing_guard`'s docstring anticipates — propagates out of
  `run_places_scrape` and kills the whole run, with only `finally: db.close()` to catch it.
- `backend/` and `frontend/` are the abandoned Celery + Postgres + Scrapy + Selenium + SendGrid
  + React stack. Nothing in `standalone/` imports them. `backend/requirements.txt` still pins
  `python-jose==3.3.0`, `pillow==10.3.0`, `scrapy==2.11.1`; `frontend/` has no lockfile. Dead
  weight and dependency-scanner noise — delete when convenient.
- `validator.py:40` returns `True` when no Hunter.io/ZeroBounce key is set, so `email_valid`
  means "not checked" rather than "verified". Don't read the dashboard's "valid" count
  (`web_server.py:173`) as validation.
- `website_email_extractor.extract_email_and_text` does up to 6 sequential fetches at 8s
  timeout each (`:29`, `:44`) — ~48s worst case per place, and the worst case is the *no email*
  path whose result is discarded (`places_scraper.py:181-183`). It also returns raw HTML as
  `website_text`, which `keyword_classifier.score_company:59-63` substring-matches — so a
  product keyword in a CSS class or nav menu earns the full +30.
- `_setup_guard` middleware (`web_server.py:66-70`) re-reads and re-parses `config.ini` from
  disk on every single HTTP request.
- **Test coverage of the API layer is zero.** `tests/test_core.py` (123 lines) and
  `tests/test_job_registry.py` (75 lines) cover the classifier, email extractor, area manager,
  template builder and job registry. Nothing touches `places_scraper.py` or `billing_guard.py`
  — the two modules that spend the client's money. Both tasks 2 and 4 should land with a test.
- Small gap worth closing opportunistically: `test_core.py:107-119` exercises
  `build_email_body` with a company name and with an unknown placeholder, but **not** with
  `company_name=None` — which is exactly the compose-preview path (`web_server.py:427`) that
  commit `a08e1a3` had to fix by hand. One three-line assertion.
- Stray `standalone/tests/__pycache__/test_places_scraper.cpython-314.pyc` with no matching
  `.py` — review debris from 2026-09-20, gitignored, harmless. Delete if it bothers you.
- `config.ini` is gitignored; never commit it. Do not paste API keys into this file either.
