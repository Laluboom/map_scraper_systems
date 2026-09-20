# Daily review — map_scraper_systems — 2026-09-20

## What I looked at

Full git history (24 commits), then the real source: `places_scraper.py`, `area_manager.py`,
`billing_guard.py`, `website_email_extractor.py`, all 801 lines of `web_server.py`,
`email_sender.py`, `job_registry.py`, `cli.py`, `update_checker.py`, `validator.py`, the test
suite, both READMEs, the CHANGELOG, and the dead `backend/` + `frontend/` trees.

I did **not** check it in a browser. Neither `venv` creation nor `pip install` would run in
this sandbox, and the dashboard is a local server-rendered Jinja app — five minutes of fighting
the environment wasn't going to tell me more than reading the routes did. All findings below
come from reading code, with file:line.

## The finding that matters

**The scraper never reads Google's JSON `status` field.** `places_scraper.py:38` and `:64` call
`r.raise_for_status()` and nothing else. The Places API returns **HTTP 200** for
`REQUEST_DENIED`, `OVER_QUERY_LIMIT` and `INVALID_REQUEST` — the failure is in the body, not the
status line. So a denied key produces `data.get("results", [])` → `[]`, the per-place loop at
`:151` never runs, and then `mark_done(db, city, state, term, 0)` fires at `:195` anyway.
`is_done` (`area_manager.py:13-22`) proceeds to skip that area for 30 days.

The consequence is specific and bad: run `--all-us` with billing not yet enabled — which the old
TODO recorded as still being the case — and the tool marches through all 267 cities printing
`→ saved 0 new trader(s)`, collects nothing, and writes a full `ScrapedArea` ledger saying it
did. `--resume` then skips the entire country for a month. Nothing anywhere surfaces
`error_message`. The same blind spot silently truncates pagination from 60 results to 20
whenever the `next_page_token` isn't warm after the fixed 2s sleep at `:49`.

This is the one workflow the product exists for, and it can fail completely without saying so.

## Also confirmed

`cli.py send` (`:311-377`) has no daily-cap check, while the dashboard path enforces one at
`web_server.py:484-488` and re-checks it in-loop at `:516`. Commit `00105ea` added the cap to
the web only; `9fdddf5` later aligned the CLI's eligibility filter but not the cap. The root
README tells the client to run the uncapped CLI path. Gmail suspends around 500/day.

Any SMTP exception — timeout, greylist, dropped wifi — becomes `email_status = "bounced"`
(`email_sender.py:114`, written at `web_server.py:523` / `cli.py:359`), and that is permanent:
the send query requires `pending`, and `/contacts/{id}/reset` (`:214-225`) clears `approved`
but not `email_status`. A five-minute network blip quietly retires every prospect in flight.

`/contacts/duplicates` loads every trader into memory (`:248`) and does a full pairwise
`SequenceMatcher` sweep (`:280-292`) — O(n²) against the project's own stated 10,000-trader
goal. And `cities_us.txt` has 13 duplicate lines out of 267, each burning a Text Search call
per term against the hard 10k/month counter in `billing_guard.py:24-25`.

## Test gap

The most recent bug-shaped commit is `a08e1a3`: the Gist manifest filename was wrong, so
`update_checker` 404'd and **no client ever saw an update banner** — invisible because
`update_checker.py:47-48` swallows everything. The single test that would have caught it is a
network smoke test asserting `httpx.get(MANIFEST_URL)` returns 200 and JSON containing a
`version` key. There is no test for `update_checker` at all, nor for `places_scraper`,
`send_one`, `billing_guard`, or any HTTP route. The existing 8 tests are decent but only cover
pure functions.

Relatedly, the root README's release runbook still says to name the Gist `version.json` — the
exact mistake `a08e1a3` fixed. Follow the README next release and it breaks again, silently.
That's the quick win.

## What I'm proposing

Ranked in `TODO.md`: (1) status-check the Places API and stop marking failed areas done, with a
regression test; (2) share the daily cap between CLI and web; (3) stop transient SMTP errors
from permanently burning contacts; (4) bucket before pairwise-matching on the duplicates page;
(5) the 15-minute README/Gist filename fix. I parked the `cities_us.txt` dedupe and deleting
the dead `backend/`+`frontend/` stack as known issues rather than spending a slot on them.

I also rewrote `REFERENCE.md`, which was 312 lines and materially wrong — it still described
SendGrid as the mail path (removed in `73762a0`) and BeautifulSoup as the extractor (it's plain
regex). The old `TODO.md` was equally stale: config.ini.example listed as required after
`d99c016` removed the dependency, CSV export listed as a future enhancement after `cae69f4`
shipped it, and a partial Google API key pasted into line 30.

## Verdict

Healthy. This is a real, finished, shipping product with small clean modules, a test suite,
release automation and a thought-through billing guard — noticeably better engineered than most
repos at this stage. It's been quiet for three months, which is fine for something that works.
The one thing to fix before the next scrape run is the silent-failure path, because it doesn't
just fail — it records success and locks itself out of retrying.
