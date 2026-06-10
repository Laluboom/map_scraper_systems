# Changelog

## 2026-06-10

### Added

- Added local `.gitignore` coverage for project notes, secrets, SQLite databases, runtime counters, Python caches, virtual environments, build outputs, logs, and editor files.
- Added `README.md` with setup, run, scraping, validation, sending, testing, packaging, and release instructions.
- Added `REFERENCE.md` and `TODO.md` as ignored local planning/reference files.
- Added unit tests for keyword scoring, website email extraction, scrape area resume logic, email template rendering, and background job tracking.
- Added `job_registry.py` for in-memory scrape/send job tracking in the standalone dashboard.
- Added scrape and email job status panels to the dashboard.
- Added auto-refresh while a scrape or send job is active.
- Added PyInstaller hidden import coverage for `job_registry`.
- Added cooperative cancellation support for long scrape and send jobs.
- Added Cancel buttons for active scrape and email jobs in the dashboard.
- Added cancel routes:
  - `POST /scrape/{job_id}/cancel`
  - `POST /send/{job_id}/cancel`
- Added cancellation test coverage for job registry behavior.

### Changed

- Updated web scrape and send handlers to use tracked background jobs instead of only raw thread timeout checks.
- Updated scrape progress reporting to feed dashboard job messages.
- Updated email campaign progress reporting to show current send position.
- Updated `places_scraper.run_places_scrape()` to accept an optional `should_cancel` callback.
- Updated dashboard docs to mention job status and cancellation support.
- Updated GitHub Actions release workflow permissions with `contents: write` so `softprops/action-gh-release` can create releases with `secrets.GITHUB_TOKEN`.

### Verified

- Confirmed local runtime/private files were not tracked and did not appear in Git history:
  - `config.ini`
  - `supplier_scraper.db`
  - `call_counts.json`
- Verified ignored local files remain ignored:
  - `REFERENCE.md`
  - `TODO.md`
  - `config.ini`
  - `supplier_scraper.db`
  - `call_counts.json`
- Verified background job implementation with:
  - `python3 -m unittest discover -s tests -v`
  - `python3 -m py_compile job_registry.py web_server.py tests/test_core.py tests/test_job_registry.py`
  - direct template render checks
  - live dashboard HTTP checks for `/send` and `/scrape`
- Verified cancellation implementation with:
  - `python3 -m unittest discover -s tests -v`
  - `python3 -m py_compile job_registry.py places_scraper.py web_server.py tests/test_job_registry.py`
  - direct template render checks for send/scrape Cancel buttons
- Verified GitHub Actions workflow YAML parses and exposes:

```yaml
permissions:
  contents: write
```

### Notes

- Release permission fix was committed as `2f52bba Allow workflow to create GitHub releases`.
- Dashboard job tracking baseline was committed as `14f22ec Add dashboard job status tracking`.
- Cooperative cancellation changes are not committed yet.
