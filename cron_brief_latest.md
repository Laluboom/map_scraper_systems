# Daily brief — map_scraper_systems (2026-10-13)

## What I looked at

Full reads of `places_scraper.py` and `billing_guard.py`, the setup wizard and `/setup` page,
the daily-send-cap path in `web_server.py`, both send paths, the CSV export, the PyInstaller
spec, `build-exe.yml`, both test files, and the whole commit history. I traced every
frozen-vs-dev path resolution site (there are five copies of the same two-line idiom).

I did **not** open it in a browser. `standalone/` has no venv, no installed deps, no
`config.ini` and no DB, and `_setup_guard` (`web_server.py:66-70`) redirects every route to
`/setup` until `config.ini` exists — creating one would mean writing a project config file,
which this review isn't allowed to do. It also wouldn't have helped: the headline bug only
exists in the frozen build, and a source run takes the `__file__` fallback and looks healthy.

## The thing I want to flag first

**The scraper is built on the legacy Places API, and the setup flow tells clients to enable
something no new Google Cloud project can enable.** `places_scraper.py:26-27` call
`maps.googleapis.com/maps/api/place/textsearch/json` and `/place/details/json` — the legacy
endpoints. Google closed Places API (legacy) to new customers on 2025-03-01; projects that
hadn't enabled it before then can't, and only Places API (New) at `places.googleapis.com/v1/`
is offered. Existing projects are grandfathered, which is exactly why nobody has noticed.

Meanwhile `cli.py:79`, `cli.py:133` and `templates/setup.html:42` all instruct the user:
*"console.cloud.google.com → New Project → Enable 'Places API' → Credentials → Create API
Key."* So onboarding a second client fails at step one, and so does rotating to a fresh
project if the current key ever leaks. `make_guide_pdf.py:96,126` says the key is "Provided by
Schion" — the shipped product works today because it rides a single grandfathered project.

Please spend two minutes confirming this in the console before anyone writes code; it decides
whether this is rank 1 or rank 2. The migration itself is genuinely small — two functions, an
`X-Goog-FieldMask` header, and a dict adapter so `_save_trader` doesn't change. And it fixes a
bug that's now survived three reviews for free: legacy returns **HTTP 200** for
`REQUEST_DENIED`, so `raise_for_status()` at `:39`/`:64` sees nothing, `results` comes back
empty, `mark_done` at `:195` runs anyway, and `is_done` skips that area for 30 days. The new
API returns a real 4xx, so error handling starts working by itself.

## Two smaller new findings, both costing money

`DETAILS_FIELDS` at `places_scraper.py:28` requests `rating`, the only field there in Google's
top-priced billing tier — it drags *every* Place Details call into that tier. And nothing ever
reads it: `grep -rn rating standalone/` returns three lines, all writes (`:28`, `:97`,
`models.py:33`). Not in a template, not in `score_company`, not in the CSV export
(`web_server.py:728-740`). Deleting one word is an immediate per-call saving.

`billing_guard` is more uncomfortable. It hardcodes 10,000 free calls/month per endpoint
(`:24-25`), documents that as fact (`:4-9`), and tells the client it is "Stopping to avoid
charges" (`:61-62`). That number matches neither pricing model — legacy was one shared $200
monthly credit across all Maps SKUs, not two independent 10k allowances, and the post-2025
model is per-SKU tiered caps that are all lower than 10,000 for these SKUs. So the component
whose entire job is preventing a surprise bill will happily wave the client past the free
allowance onto their card, and `README.md:47` repeats the wrong figure to them. It also
increments the counter *before* the request (`:64`), so timeouts burn budget.

## What's carried over, and the uncomfortable part

Nothing from the 2026-09-20 or 2026-10-03 lists was touched. The last commit that changed
product code is `a08e1a3`, **2026-06-19** — almost four months ago. The only commits since are
the two review-notes commits, and the agent branch from September is still zero commits ahead
of `main`.

So the top item is the same as it was in September: **`cities_us.txt` has never been in the
release zip.** `build-exe.yml:38-42` packages four files; the spec bundles the city list into
`_MEIPASS` but nothing reads it from there (`web_server.py:32` is the only `_MEIPASS` use and
it's for templates). Every shipped build fails `--all-us` and `--resume`, and the Scrape page
renders "0 / 0 city×term combinations" — while `README.md:52-58` sells `--all-us` as the
headline feature. I kept it at rank 1 over the legacy-API finding because it is broken *today*
for the client who actually exists, whereas the API issue blocks future ones.

Rank 3 is the send cap: `_sent_today()` (`web_server.py:149-156`) compares local midnight
against naive-UTC `created_at` rows, so between 00:00 and 05:00 PKT it returns 0 no matter what
was just sent — both cap checks bypassed, and a run across midnight gets a fresh allowance on
top of the one it used. `cli.py send` has no cap at all, and `README.md:34` points the client at
that path. Gmail suspends accounts over this.

Rank 5 is the quick win: `README.md` names the Gist manifest `version.json` in three places
(74, 81, 83) when the live constant is `Supplier_Scraper.json`. Follow the README on the next
release and the update channel breaks silently for every client again, because
`check_for_update` swallows everything (`update_checker.py:47-48`).

I demoted the transient-SMTP-burns-a-contact bug to parked to make room — it's real, but it
only bites during a campaign, and there hasn't been one. Promote it the moment sending resumes.

## Test gap, specifically

Twelve tests, none touching `places_scraper.py` or `billing_guard.py` — the two modules that
spend money. The single test that would have caught the most recent bug-shaped commit
(`a08e1a3`, the compose preview) is a three-line addition at `test_core.py:107-119`: that class
exercises `build_email_body` with a company name and with an unknown placeholder, but never
with `company_name=None`, which is exactly the preview path at `web_server.py:427` that had to
be fixed by hand.

## Honest read

The code is better than its situation — small, readable, sensibly factored, and it works end to
end from source. But the artifact clients receive can't do its headline job, and the API it's
built on is closed to new customers. Four months idle across three untouched TODO lists says
the bottleneck isn't engineering, it's a decision: pick this up for a focused hour or two, or
move it out of `01_active_projects` and stop paying for reviews that nobody acts on.
