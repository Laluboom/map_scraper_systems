# Supplier Scraper

Finds non-ferrous scrap traders via Google Places, scores them, and sends outreach emails on behalf of Schion International.

---

## Setup

```bash
cd standalone
python3 -m venv .venv
.venv/bin/pip install -r requirements_standalone.txt
.venv/bin/python cli.py setup      # enter API keys
```

---

## Workflow

```bash
# 1. Scrape traders
.venv/bin/python cli.py scrape --city "Dallas, TX"

# 2. Check what was found
.venv/bin/python cli.py status

# 3. Open dashboard to review & approve contacts
.venv/bin/python cli.py serve      # → http://localhost:8080/contacts

# 4. Preview emails before sending
.venv/bin/python cli.py send --dry-run

# 5. Send to priority traders first
.venv/bin/python cli.py send --priority-only

# 6. Monitor results
# → http://localhost:8080/logs
```

---

## Data

| File | Contents |
|---|---|
| `standalone/supplier_scraper.db` | All traders, scores, email logs |
| `standalone/call_counts.json` | Monthly API usage (10k free calls/month per endpoint) |
| `standalone/config.ini` | API keys — never commit this |

---

## Full US scrape

```bash
.venv/bin/python cli.py scrape --all-us
# If interrupted:
.venv/bin/python cli.py scrape --all-us --resume
```

See `REFERENCE.md` for full technical details and `TODO.md` for remaining tasks.
