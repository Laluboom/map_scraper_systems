# Supplier Scraper

Standalone Python tool for finding scrap/recycling supplier prospects, reviewing them locally, and sending outreach emails through SMTP.

## What It Does

- Scrapes Google Places for scrap, recycling, and industrial supplier searches.
- Fetches place details such as phone, website, address, rating, and Google URL.
- Visits company websites and extracts contact emails.
- Scores companies with keyword and Google place-type signals.
- Stores contacts, scrape progress, and email logs in SQLite.
- Provides a local FastAPI/Jinja dashboard for review and outreach.
- Packages as a Windows executable with PyInstaller.

## Requirements

- Python 3
- Google Places API key for scraping
- SMTP account for sending emails
- Optional Hunter.io or ZeroBounce API key for email validation

Install dependencies:

```bash
python3 -m pip install -r requirements_standalone.txt
```

## Setup

Run the setup wizard:

```bash
python3 cli.py setup
```

This creates or updates `config.ini` with Google Places, SMTP, and optional validation settings.

`config.ini` is local-only and should not be committed.

## Run The Dashboard

```bash
python3 cli.py serve
```

Open:

```text
http://localhost:8080
```

Dashboard pages:

- `Dashboard`: Summary counts.
- `Contacts`: Review, approve, reject, and reset traders.
- `Scrape`: Start city or all-US scraping, view recent scrape job status, and request cancellation.
- `Send Emails`: Send to approved pending contacts, view recent send job status, and request cancellation.
- `Compose`: Send a one-off email.
- `Email Template`: Edit sender and outreach template.
- `Logs`: Review email send logs.

## Scraping

Scrape one city:

```bash
python3 cli.py scrape --city "Dallas, TX"
```

Scrape all cities from `cities_us.txt`:

```bash
python3 cli.py scrape --all-us
```

Resume recent progress:

```bash
python3 cli.py scrape --all-us --resume
```

Override search terms:

```bash
python3 cli.py scrape --city "Dallas, TX" --terms "scrap yard,copper recycling"
```

## Email Validation

Validate unvalidated emails:

```bash
python3 cli.py validate
```

If no validation API keys are configured, validation currently assumes emails are valid.

## Sending Emails

Review and approve contacts in the dashboard first, then send:

```bash
python3 cli.py send
```

Preview without sending:

```bash
python3 cli.py send --dry-run
```

Only send to priority contacts:

```bash
python3 cli.py send --priority-only
```

The email subject is stored in `config.ini`; the body is stored in `email_template.txt`.

## Status

```bash
python3 cli.py status
```

This prints database counts and Google Places billing-guard usage.

## Tests

Run the local unit tests:

```bash
python3 -m unittest discover -s tests -v
```

## Data Files

Local runtime files:

- `config.ini`: Local credentials/config.
- `supplier_scraper.db`: SQLite database.
- `call_counts.json`: Google Places API usage counter.
- `email_template.txt`: Outreach body template.

The first three are ignored by Git.

## Packaging

Build the Windows executable with PyInstaller:

```bash
pyinstaller supplier_scraper.spec
```

Output is written to `dist/`.

## Release Notes

Current version is defined in `version.py`.

For GitHub release automation, the workflow token needs permission to create releases:

```yaml
permissions:
  contents: write
```

If using a personal access token, it needs repository contents read/write permission.
