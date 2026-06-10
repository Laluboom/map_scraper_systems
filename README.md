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

---

## Releasing an update (for developer)

```
1. Edit standalone/version.py — bump __version__ = "1.0.1"
2. git commit -m "Release v1.0.1"
3. git tag v1.0.1
4. git push && git push --tags
   → GitHub Actions builds supplier_scraper.exe automatically (~5 min)
5. Download the .exe from the GitHub Release assets
6. Upload it wherever the client will download from (Google Drive, etc.)
7. Edit your public Gist (version.json):
     { "version": "1.0.1", "download_url": "https://...", "notes": "Bug fixes" }
   → Client's dashboard shows a yellow update banner on next startup
```

### First-time Gist setup

1. Go to gist.github.com, create a **public** Gist with filename `version.json`
2. Content: `{ "version": "1.0.0", "download_url": "", "notes": "Initial release" }`
3. Copy the **Raw** URL (looks like `https://gist.githubusercontent.com/YourUser/abc123/raw/version.json`)
4. Paste it into `standalone/update_checker.py` as `MANIFEST_URL`
5. Rebuild and ship — the checker is now live
