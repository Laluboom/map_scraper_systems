# Supplier Scraper & Outreach System — Reference

**Client:** Schion International (Pakistan)
**Purpose:** Automate identification, contact collection, and email outreach to non-ferrous scrap traders across US, Canada, EU, and globally.

---

## Overview

A standalone Windows/Linux executable (no Python required at runtime) that:
- Finds scrap/recycling companies in any US city via the **Google Places API** (no CSS selectors needed)
- Scores and prioritizes companies by keyword matching (name, Google category, website text)
- Extracts emails by visiting each company's website
- Validates emails via Hunter.io / ZeroBounce
- Sends personalized outreach emails via SendGrid
- Provides a local web dashboard (FastAPI + Jinja2) for reviewing and approving contacts

All data is stored in a local **SQLite** database. No cloud database or Docker required.

---

## Target Products (Priority Order)

| Priority | Product |
|----------|---------|
| 1 | Sealed Units / AC or Fridge Compressor Scrap |
| 2 | Electric Motor Scrap |
| 3 | Battery Scrap |
| 4 | Aluminum Cables |
| 5 | Copper Cables |

Traders not listing these are still collected and tagged as **General Traders** (fallback logic).

---

## Tech Stack (Standalone / .exe version)

| Layer | Technology |
|-------|-----------|
| CLI | Python + Click |
| Web dashboard | FastAPI + Uvicorn + Jinja2 HTML |
| Scraping | Google Places API (httpx) + BeautifulSoup for email extraction |
| Database | SQLite via SQLAlchemy ORM |
| Email Delivery | SendGrid API |
| Email Validation | Hunter.io API + ZeroBounce API |
| Packaging | PyInstaller → single .exe |
| Config | `config.ini` (configparser) — no .env |

All user-required API keys are entered interactively via `supplier_scraper.exe setup` and saved to `config.ini` automatically.

---

## Project Layout

```
standalone/
  cli.py                  — Click CLI entry point (setup/serve/scrape/validate/send/status)
  web_server.py           — FastAPI web dashboard
  db.py                   — SQLAlchemy SQLite setup, init_db()
  models.py               — ORM models: Trader, EmailLog, ScrapedArea
  places_scraper.py       — Google Places API engine (search + details + save)
  keyword_classifier.py   — 3-layer scoring: name (+30), place types (+40), website text (+30)
  website_email_extractor.py — visits company website, extracts best email via regex
  area_manager.py         — ScrapedArea tracking; is_done() / mark_done() / get_progress()
  email_sender.py         — SendGrid send_one() + build_email_body()
  validator.py            — Hunter.io + ZeroBounce email validation
  prioritizer.py          — legacy keyword lists (still used by keyword_classifier.py)
  scraper_runner.py       — legacy Scrapy runner (unused for Places flow)
  config.ini              — all API keys and settings (gitignored)
  config.ini.example      — template checked into repo
  cities_us.txt           — ~250 US cities, format "City, ST" one per line
  search_terms.txt        — 8 default search queries (reference; actual terms in config.ini)
  requirements_standalone.txt — pip dependencies
  supplier_scraper.spec   — PyInstaller build spec
  templates/              — Jinja2 HTML templates (base, dashboard, contacts, send, scrape, logs)

REFERENCE.md              — this file
TODO.md                   — task tracker
PLACEHOLDERS.md           — all user-fillable values
```

---

## Database Schema (SQLite)

### Trader table
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `company_name` | TEXT | |
| `email` | TEXT | Indexed |
| `phone` | TEXT | |
| `address` | TEXT | |
| `city` | TEXT | |
| `country` | TEXT | |
| `source` | TEXT | Which search term / city |
| `product_tags` | JSON | Matched keyword tags |
| `priority_flag` | BOOLEAN | True if score ≥ threshold (default 40) |
| `priority_score` | INTEGER | 0–100 composite score |
| `email_valid` | BOOLEAN | Hunter.io / ZeroBounce result |
| `email_status` | TEXT | `pending` / `sent` / `bounced` |
| `approved` | BOOLEAN | Admin approval before send |
| `scraped_at` | DATETIME | |
| `sent_at` | DATETIME | |
| `google_place_id` | TEXT UNIQUE | Prevents re-scraping same business |
| `google_rating` | TEXT | |
| `google_url` | TEXT | Google Maps link |

### ScrapedArea table
| Field | Type | Notes |
|-------|------|-------|
| `id` | TEXT PK | `"{city}|{state}|{term}"` |
| `scraped_at` | DATETIME | |
| `result_count` | INTEGER | Traders found in that area |

### EmailLog table
| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `trader_id` | UUID | Foreign key to Trader |
| `status` | TEXT | `sent` / `bounced` |
| `message_id` | TEXT | SendGrid message ID |
| `error_message` | TEXT | |
| `created_at` | DATETIME | |

---

## Google Places Scraping Flow

```
cli.py scrape --all-us --resume
  │
  ├─ load cities from cities_us.txt (~250 cities)
  ├─ load search_terms from config.ini [googleplaces]
  │
  └─ for each (city × term):
        area_manager.is_done() → skip if scraped within rescrape_days
        │
        places_scraper.search_places(query, city) → up to 60 raw results (3 pages)
        │
        for each result:
          if Trader.google_place_id already exists → skip
          │
          places_scraper.get_place_details(place_id) → phone, website, url, rating
          │
          website_email_extractor.extract_email(website) → best email or None
          │
          keyword_classifier.score_company(name, types, website_text)
            Layer 1 — name keywords:       +30
            Layer 2 — Google place types:  +40 (high) or +20 (secondary)
            Layer 3 — website keywords:    +30
            priority_flag = score >= priority_threshold (default 40)
          │
          save Trader to DB
        │
        area_manager.mark_done(city, term, count)
        print "[N/total] found X, saved Y new"
```

---

## CLI Commands

```
supplier_scraper.exe setup                        # interactive wizard — sets all API keys
supplier_scraper.exe serve [--port 8080]          # launch web dashboard
supplier_scraper.exe scrape --city "Dallas, TX"   # scrape one city
supplier_scraper.exe scrape --all-us              # scrape all US cities
supplier_scraper.exe scrape --all-us --resume     # skip cities done within rescrape_days
supplier_scraper.exe scrape --terms "copper,scrap metal"  # override search terms
supplier_scraper.exe validate                     # validate emails via Hunter.io
supplier_scraper.exe send [--dry-run] [--priority-only]   # send outreach emails
supplier_scraper.exe status                       # print DB summary
```

---

## config.ini Sections

```ini
[googleplaces]
api_key = ...              # Google Cloud → Enable Places API → Create credential
rescrape_days = 30         # re-search a city+term after this many days
search_terms = scrap metal recycling,copper recycling,...
priority_threshold = 40    # score ≥ this → priority_flag=True

[email]
sendgrid_api_key = ...
from_email = ...           # must be verified sender in SendGrid
from_name = John Doe
throttle_per_minute = 30

[validation]
hunterio_api_key = ...
zerobounce_api_key = ...   # optional fallback

[proxy]
proxy_url =                # optional: http://user:pass@host:port

[database]
db_path = supplier_scraper.db
```

---

## Keyword Scoring (keyword_classifier.py)

**Layer 1 — Company name** (+30 if any match):
`scrap, recycl, metal, copper, aluminum, aluminium, cable, wire, motor, battery, compressor, salvage, nonferrous, non-ferrous, junk`

**Layer 2 — Google place types** (+40 high / +20 secondary):
- High: `recycling_center`, `scrap_yard`
- Secondary: `metal_supplier`, `waste_management_service`, `electrical_supply_store`, `wholesale_store`

**Layer 3 — Website text** (+30 if any match):
`sealed unit, compressor scrap, electric motor, battery scrap, aluminum cable, copper cable, non-ferrous, scrap yard, recycling center`

---

## Email Template

> **Subject:** Inquiry for Non-Ferrous Scrap Supply

```
Dear [Company Name],

We are an ISO & EPA certified recycle company based in Pakistan.
We are currently buying Non-ferrous scrap from companies in the US, EU & UK
region and would like to know if you can offer us the below mentioned items
on a regular basis:

* Sealed Units scrap
* Electric motors scrap
* Battery Scrap
* Aluminum cables
* Copper cables

We take approx. 1,200 M.tons/month of each item and would like to know if
you can offer any of the material regularly.
We are one of the few companies certified by the EPA to import battery scrap.

We await your reply.

Best regards,
John Doe
Manager (Purchasing)
SCHION INTERNATIONAL
Tel: +92 21 32570013
Cell: +92 33 33 44 99 59
Mail: Noaman@schion.com.pk
Web: www.schion.com.pk
```

---

## Web Dashboard Pages

| URL | Page |
|-----|------|
| `/` | Dashboard — stats overview (total, priority, approved, sent, bounced) |
| `/contacts` | Trader table — filter by all/priority/approved/pending; approve/reject |
| `/scrape` | Scrape controls — city input, Scrape All / Resume buttons, progress bar, recent areas table |
| `/send` | Send controls — shows count ready to send; Start Send button |
| `/logs` | Email log — last 300 send attempts with status |

---

## API Cost Estimate (Google Places)

- Text Search: ~$17 per 1,000 calls
- Place Details: ~$17 per 1,000 calls
- 250 cities × 8 terms × ~3 pages = ~6,000 search calls ≈ **$102**
- ~120,000 detail calls ≈ **$2,040** (only for places with a website)
- Google gives **$200/month free credit** → first month nearly free
- Cost saver: skip Place Details if the place has no website (no email possible)

---

## Quality Requirements

| Metric | Target |
|--------|--------|
| Valid email accuracy | ≥ 90% |
| Email delivery success | ≥ 95% |
| Response rate (priority traders) | ≥ 80% |
| Max campaign size | 50,000+ traders |

---

## Compliance & Legal

- **CAN-SPAM Act** — US email regulations (unsubscribe note in template, individual sends)
- **GDPR** — EU data privacy compliance
- No bulk CC/BCC — individual sends only, throttled by `throttle_per_minute`
