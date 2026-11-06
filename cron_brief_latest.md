# Daily brief — map_scraper_systems — 2026-11-06

## What I looked at

`git log --oneline -30` and `git log -5 --stat` first, then the whole scrape path end to end:
`places_scraper.py`, `area_manager.py`, `billing_guard.py`, `models.py`, `db.py`, the `scrape`
and `send` commands in `cli.py`, the `/scrape/*` and `/send/*` routes in `web_server.py`, the
PyInstaller spec, `build-exe.yml`, all three test files, and `README.md`. I did **not** check it
in a browser — the dashboard is a local FastAPI app rather than a Node frontend, and its
dependencies aren't installed here (`import sqlalchemy` fails, no venv is checked in). Nothing
I found needed a running server.

## First, a correction to the last review

The 2026-10-13 notes said the agent branch from September was "still an empty branch (zero
commits ahead of `main`)." It wasn't. PR #1 merged as `fac30b0` on 2026-09-22 and the fix is
live in `places_scraper.py`. Two consecutive reviews told you to redo work that was already
done, and the TODO's task 2 still claimed the `REQUEST_DENIED` bug as unfixed. Dropped.

## The finding that matters

That merged fix closed **one of two** call sites, and the asymmetry is the whole bug.

`_text_search_page` and `get_place_details` both raise `PlacesApiError` on a non-`OK` status
now. But an exception out of `search_places()` lands on `places_scraper.py:160-162`, which does
`continue` *before* `mark_done` — area correctly left unmarked. An exception out of
`get_place_details` lands on `:185-187`, a **per-place** handler that prints `[skip]` and
continues the inner loop. The loop then runs out, `saved` is still 0, and `:209` calls
`mark_done(db, city, state, term, 0)` anyway.

So: Text Search succeeds (one call), the key gets denied or Google's QPS limiter returns
`OVER_QUERY_LIMIT`, all 20-60 Details calls fail individually, and the area goes into
`scraped_areas` as "done, 0 results." `ScrapedArea` (`models.py:48-53`) has no completeness
field, so `result_count=0` is indistinguishable from a city that genuinely had no
email-bearing businesses — you cannot detect this after the fact. `is_done`
(`area_manager.py:13-22`) then skips that city×term for 30 days, which bites precisely in the
mode the client uses for the 267-city run: Resume on the Scrape page.

Two more `mark_done` calls have the same defect and are deliberate: `:168` (cancel) and `:183`
(billing limit) both mark a partially-walked area as complete. Hit Cancel on place 3 of 60 and
the other 57 are written off for a month.

The fix is a local `area_failed` flag and deleting two `mark_done` calls — explicitly *not* a
new column, because `db.py:32-34` is `create_all`, which creates missing tables but never adds
columns, so a new `ScrapedArea` field would raise `no such column` on every client DB already
in the field. The single test that would have caught this: patch `httpx.get` with a side-effect
list — Text Search `OK`, Details 200 with `OVER_QUERY_LIMIT` — and assert `ScrapedArea` is
empty. It's a six-line variation on the test `test_places_scraper.py:22` already has.

## What else is proposed, and why

**`cities_us.txt` still isn't in the release zip.** Fourth review, verified again today.
`build-exe.yml` packages exactly four files and that one isn't among them; the spec bundles it
to `_MEIPASS`, but `web_server.py:32` is the only `_MEIPASS` read site and it's for
`templates/` only. So `--all-us` and Resume have never worked in any shipped build, and the
Scrape page renders "0 / 0 city×term combinations searched" on every client machine. It
survives because the dev path falls back to `Path(__file__).parent` — invisible unless you run
a real build. A `Copy-Item` plus a CI assertion on the zip contents ends it permanently.

**The daily send cap.** `_sent_today()` compares `EmailLog.created_at` against *local* midnight
while rows are written naive-UTC. At UTC+5 that means the cap counts zero between local 00:00
and 05:00, so a campaign started at 00:30 sends the entire pending list uncapped — and
`cli.py send`, which `README.md:34` is what tells the client to run, has no cap at all.
Gmail's ~500/day cutoff is an account suspension, not a soft failure.

**Quick win** is two one-liners of docs-vs-code drift: the README still names the update
manifest `version.json` in three places when the live constant is `Supplier_Scraper.json`
(follow the README on the next release and the update channel silently 404s again), and
`scrape --resume` on its own exits with "Specify --city or --all-us" despite `cli.py:9`
documenting it as a standalone command.

**Fifth** bundles the cost items: `rating` in `DETAILS_FIELDS` is the only top-tier-priced
field, it drags every Place Details call into that tier, and `google_rating` is read exactly
nowhere. `billing_guard`'s 10,000-calls/month free tier matches no Google pricing model that
has ever existed, so a guard that promises "Stopping to avoid charges" currently lets the
client onto their card.

## Health

Honestly? The code is good. It's readable, the module boundaries make sense, `job_registry`
and `billing_guard` are thoughtful, and the thing works end to end from source. Two problems:
six weeks idle with a severe correctness hole open, and **no CI runs the tests** —
`build-exe.yml` triggers only on version tags and only builds the exe. The test that shipped
with the last fix has never been executed anywhere, by its own PR description. If you only do
one thing beyond task 1, it's the ten-line `unittest discover` job on push; that's what stops
the next half-fix from looking like a whole one.

One decision outranks the whole list and I can't make it from here: the scraper is on Places
API **legacy** (`places_scraper.py:26-27`), closed to new Cloud projects since 2025-03-01,
while `cli.py:79,133` and `setup.html:42` all tell the client to create a new project and
enable it. Two minutes in the Cloud console on a fresh project answers whether a second client
can ever be onboarded. Worth doing before you touch anything else, and worth writing the answer
down so review five isn't guessing.
