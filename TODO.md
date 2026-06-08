# TODO — Supplier Scraper & Outreach System

Status legend: `[ ]` not started · `[~]` in progress · `[x]` done

---

## Phase 0 — Google Places API Scraper ✅ COMPLETE

- [x] Build `places_scraper.py` — Google Places Text Search + Place Details via httpx, paginate up to 3 pages (60 results/query), dedup by `google_place_id`
- [x] Build `website_email_extractor.py` — visits homepage + /contact + /about, regex email extraction, filters generic prefixes (noreply, admin, etc.)
- [x] Build `area_manager.py` — `is_done()` / `mark_done()` / `get_progress()` backed by `ScrapedArea` DB table
- [x] Build `keyword_classifier.py` — 3-layer scoring: company name (+30), Google place types (+40/+20), website text (+30), max score 100
- [x] Wire all into `cli.py` scrape command — `--city`, `--all-us`, `--resume`, `--terms` options
- [x] Add `cities_us.txt` — ~250 US cities, format "City, ST"
- [x] Add `search_terms.txt` — 8 default queries (reference; active terms live in config.ini)
- [x] Update `config.ini.example` — added `[googleplaces]` section with api_key, rescrape_days, search_terms, priority_threshold
- [x] Update `PLACEHOLDERS.md` — replaced PH-009 to PH-018 (spider CSS selectors) with single Google Places API key entry
- [x] Update web dashboard scrape page — city progress bar, Scrape City / Scrape All / Resume buttons, recently scraped areas table
- [x] Update `models.py` — added `priority_score`, `google_place_id`, `google_rating`, `google_url` to Trader; added `ScrapedArea` table
- [x] Update `cli.py` — fully rewritten with `setup` wizard, interactive API key prompting, `send` loop with per-trader status update + EmailLog

---

## Phase 1 — Test the standalone app end-to-end

- [ ] **Install dependencies** — `pip install -r requirements_standalone.txt`
- [ ] **Run setup wizard** — `python cli.py setup` — enter real Google Places API key, SendGrid key, sender email
- [ ] **Test single-city scrape** — `python cli.py scrape --city "Dallas, TX"` — confirm traders are saved with scores and emails
- [ ] **Check status** — `python cli.py status` — verify city count, trader count, priority count
- [ ] **Launch dashboard** — `python cli.py serve` — open http://localhost:8080 and verify all pages load
- [ ] **Test contacts page** — approve a few traders manually
- [ ] **Test dry-run send** — `python cli.py send --dry-run` — confirm approved traders appear
- [ ] **Test email send** — `python cli.py send` with real SendGrid key — confirm `email_status` flips to "sent"/"bounced"
- [ ] **Test resume** — run scrape again with `--resume` — confirm already-done city is skipped

---

## Phase 2 — Package as .exe (PyInstaller)

- [ ] Update `supplier_scraper.spec` — add new files to `datas`: `cities_us.txt`, `search_terms.txt`, new `.py` modules
- [ ] Run `pyinstaller supplier_scraper.spec` on Windows (or via Wine / cross-compile)
- [ ] Test the built `.exe` — run `supplier_scraper.exe setup` then `supplier_scraper.exe scrape --city "Dallas, TX"`
- [ ] Verify `config.ini` and `supplier_scraper.db` are created next to the `.exe` (not inside the bundle)
- [ ] Test `supplier_scraper.exe serve` — dashboard must load from bundled templates

---

## Phase 3 — Run full US scrape

- [ ] Confirm Google Places API billing is enabled (free $200/month credit covers first run)
- [ ] Run `supplier_scraper.exe scrape --all-us` — let it run overnight
- [ ] Monitor progress via dashboard `/scrape` page
- [ ] If interrupted, run `supplier_scraper.exe scrape --all-us --resume` to continue
- [ ] After full run: `status` command should show 10,000+ traders

---

## Phase 4 — Validate emails

- [ ] Get Hunter.io API key (free tier: 25 verifications/month; paid for bulk)
- [ ] Run `supplier_scraper.exe validate`
- [ ] Check dashboard — filter by validated emails before sending

---

## Phase 5 — Run outreach campaign

- [ ] Go to dashboard `/contacts` — review and approve priority traders
- [ ] Run `supplier_scraper.exe send --dry-run` — preview who gets emails
- [ ] Run `supplier_scraper.exe send --priority-only` — send to priority traders first
- [ ] Monitor `/logs` page for send/bounce status
- [ ] Run `supplier_scraper.exe send` for all approved traders

---

## Known Issues / Watch Points

- `web_server.py` scrape page runs the full scrape synchronously (blocking the browser for up to 5 minutes per call). For all-US runs, use the CLI instead of the dashboard. Dashboard is fine for single-city scrapes.
- `cities_us.txt` has some duplicate city entries (e.g. Glendale CA appears twice, Henderson NV appears twice). This causes a few redundant area records but no data loss — `google_place_id` UNIQUE index prevents duplicate traders.
- `search_terms.txt` is for reference only — the active terms are read from `config.ini [googleplaces] search_terms`. Edit config.ini to change them.
- `scraper_runner.py` and legacy Scrapy spiders are still present but unused in the Google Places flow. They can be removed before packaging to reduce `.exe` size.
- Email status "bounced" is set on any SendGrid API error (including config errors). Check `/logs` for the specific error message if bounces are unexpectedly high.

---

## Optional Enhancements (future)

- [ ] Add ZeroBounce as secondary email validator fallback (key placeholder already in config)
- [ ] Proxy support — `config.ini [proxy] proxy_url` is read but not yet passed to httpx in `places_scraper.py`
- [ ] Webhook receiver for SendGrid bounce/reply events
- [ ] CSV export of trader list from dashboard
- [ ] EU city list (`cities_eu.txt`) for European outreach
- [ ] Auto-open browser to dashboard on `serve` start (already implemented, uses `threading.Timer`)
