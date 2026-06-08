# PLACEHOLDERS — What to Fill In Before Running

Every item below is a `PLACEHOLDER_*` value or commented-out block in the codebase.
Fill these in and the system becomes fully operational.

---

## Credentials & API Keys

All keys live in `standalone/config.ini`. Run `supplier_scraper.exe setup` to enter them interactively — they are saved automatically. You do not need to edit config.ini by hand.

| ID | Config section / key | What to do |
|----|----------------------|------------|
| PH-002 | `[email] sendgrid_api_key` | Sign up at sendgrid.com → Settings → API Keys → Create Key |
| PH-003 | `[email] from_email` | Must be a verified sender in your SendGrid account |
| PH-005 | `[validation] hunterio_api_key` | Sign up at hunter.io → Dashboard → API (optional) |
| PH-006 | `[validation] zerobounce_api_key` | Sign up at zerobounce.net → Dashboard → API (optional fallback) |
| PH-007 | `[proxy] proxy_url` | Your proxy provider's endpoint, e.g. `http://user:pass@host:port` (optional) |

---

## Google Places API (replaces all spider selectors)

The old CSS-selector spiders (PH-009 through PH-018) have been replaced by the Google Places API
integration. No CSS selectors or per-website inspection is needed.

| ID | File | Variable / Location | What to do |
|----|------|---------------------|------------|
| PH-009 | `standalone/config.ini` | `[googleplaces] api_key` | Go to console.cloud.google.com → Create/select a project → Enable **Places API (New)** → Credentials → Create API Key. Paste the key when prompted by `supplier_scraper.exe setup` — it is saved automatically. |

### Optional tuning (already set to good defaults in `config.ini`)

| Setting | Default | Description |
|---------|---------|-------------|
| `rescrape_days` | `30` | Re-search a city+term combination after this many days |
| `search_terms` | 8 terms | Comma-separated queries run in every city. Edit in `config.ini [googleplaces]` |
| `priority_threshold` | `40` | Score 0-100: companies at or above this get `priority_flag=True` |

---

---

## Minimum Required to Run (standalone .exe)

1. Run `supplier_scraper.exe setup` — it walks you through all keys interactively.
2. At minimum, fill in:
   - **PH-009** Google Places API key (required for scraping)
   - **PH-002** SendGrid API key + **PH-003** verified sender email (required for sending)
3. Optional but recommended:
   - **PH-005** Hunter.io key (email validation before sending)
4. Then run: `supplier_scraper.exe scrape --city "Dallas, TX"` to test, then `supplier_scraper.exe serve` for the dashboard.

Everything else (proxies, CI/CD, ZeroBounce) is optional.
