# Daily brief — map_scraper_systems — 2026-10-03

## What I looked at

No source file has changed since `a08e1a3` (2026-09-20); the only commit since is last
review's own notes commit. The branch
`agent/2026-09-20-google-places-error-statuses-are-never-c` is **zero commits ahead of main** —
an empty branch. So none of the five items from the 2026-09-20 list was implemented, and all
five are still real.

Rather than re-report them, I spent this pass on the part the last review didn't read: the
packaging and release path — `.github/workflows/build-exe.yml`, `supplier_scraper.spec`, and
every place the frozen app resolves a file path. Plus a fresh look at `web_server.py`'s send
path.

I did **not** check it in a browser. This box has no `ensurepip`/`python3-venv`, so
`python3 -m venv` fails and the app's deps can't be installed; only 4 of the 12 unit tests run
(`test_job_registry.py` passes, `test_core.py` errors on `import sqlalchemy`). I confirmed the
UI symptom by reading `templates/scrape.html` against the context `web_server.py` feeds it
instead.

## The finding that matters

**The release zip has never contained `cities_us.txt`, so the full-US scrape has never worked
on the client's machine.**

When frozen, all three read sites resolve the city list from the directory *beside the exe* —
`cli.py:22-28`, `web_server.py:566`, `web_server.py:627`. The spec file *does* bundle it
(`supplier_scraper.spec:16`), but PyInstaller puts `datas` into `sys._MEIPASS`, and
`web_server.py:32` is the repo's only `_MEIPASS` use — it covers `templates/` and nothing else.
So the bundled copy is unreachable, and the beside-the-exe copy doesn't exist, because
`build-exe.yml:41` zips exactly four files: the exe, `config.ini`, `README.md` and
`SETUP_GUIDE.pdf`. `git log -p --follow` on the workflow shows `cities_us.txt` was never in the
zip in any revision since the distribution system landed in `f38f5bd` — v1.0.0 through v1.0.2
all ship without it, and nothing in the README or setup guide tells the client to create it.

What the client sees: `scrape --all-us` prints "cities_us.txt not found" and exits
(`cli.py:261`); the dashboard's All-US and Resume buttons bounce with "No cities loaded"
(`web_server.py:667`); and the Scrape page permanently reads **"0 / 0 city×term combinations
searched"** with the progress bar suppressed, because `num_cities` is 0
(`web_server.py:577-580` → `scrape.html:46-47`), while the help text at `scrape.html:71`
offers to "iterate all 0 city × term combinations". Only single-city scraping has ever worked
in a shipped build — against a README that documents `--all-us` as a headline feature.

This is a packaging bug, which is why reading `standalone/*.py` alone doesn't surface it. It
also reframes last review's #1 (the Places `status` blindness): that bug poisons `--resume`
for 30 days, but `--resume` has never run on the client's machine at all.

## Second finding: the daily send cap is off for five hours every night

`_sent_today()` (`web_server.py:151-161`) builds `today_start` from `date.today()` — **local**
midnight, naive — but `EmailLog.created_at` is written with `datetime.utcnow()`
(`web_server.py:537`). The client is in Pakistan, UTC+5. I simulated it under
`TZ=Asia/Karachi`:

```
sent local 00:00 -> stored 2026-10-03 19:00 -> counted: False
sent local 04:00 -> stored 2026-10-03 23:00 -> counted: False
sent local 05:00 -> stored 2026-10-04 00:00 -> counted: True
```

Between local midnight and 05:00 the count is **0** regardless of what was just sent, so the
pre-flight check at `:486` passes and the in-loop re-check at `:516` never trips. A campaign
started at 00:30 sends the entire pending list uncapped; a campaign running across midnight
gets a fresh full `daily_send_cap` on top of the one it already spent. Gmail cuts off near
500/day and then suspends the account — and this is the path that supposedly *has* the cap.
`cli.py send` (`:311-384`) still has no cap at all, which is the path the README tells the
client to use. Both get fixed by lifting `_daily_cap()`/`_sent_today()` into
`email_sender.py` once.

## Test gap

The single assertion closest to the most recent bug-shaped commit: `a08e1a3` fixed the compose
preview rendering literal `{greeting}` placeholders, i.e. the `build_email_body(None, body)`
call at `web_server.py:427`. `test_core.py:107-119` tests `build_email_body` with a company
name and with an unknown placeholder — never with `company_name=None`. Three lines.

## What I'm proposing

Ranked in `TODO.md`: (1) ship `cities_us.txt` in the zip plus a `_MEIPASS` fallback and a CI
assertion so it can't regress silently; (2) one shared, timezone-correct daily cap used by both
send paths; (3) read Google's JSON `status` and stop marking failed areas done — carried over;
(4) stop a transient SMTP error permanently burning a contact — carried over; (5) quick win,
fix the three places root `README.md` still names the Gist manifest `version.json` when
`update_checker.py:15` uses `Supplier_Scraper.json`.

The `/contacts/duplicates` O(n²) item from last review is demoted to parked — it only bites at
10k traders, and the DB can't reach 10k while task 1 is unfixed.

## Health

The code itself is in good shape: small single-purpose modules, 12 real unit tests, sensible
cancellation and billing guards. The problem has moved downstream — the shipping pipeline is
now the weakest part of this project, and it's shipping a product whose main workflow doesn't
start. Tasks 1 and 2 are both under an hour and both affect the client directly; do them
before anything else on the list.
