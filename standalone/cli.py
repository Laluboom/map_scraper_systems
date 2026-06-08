"""
supplier_scraper.exe — main entry point.

Usage:
  supplier_scraper.exe setup                           First-time setup wizard
  supplier_scraper.exe serve                           Start dashboard at http://localhost:8080
  supplier_scraper.exe scrape --city "Dallas, TX"      Scrape one city via Google Places
  supplier_scraper.exe scrape --all-us                 Scrape all US cities
  supplier_scraper.exe scrape --resume                 Continue from where you left off
  supplier_scraper.exe validate                        Validate emails in DB
  supplier_scraper.exe send [--dry-run] [--priority]   Send outreach emails
  supplier_scraper.exe status                          Print DB summary
"""
import sys
import webbrowser
import threading
import shutil
import configparser
from pathlib import Path

import click

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

CONFIG_PATH = BASE_DIR / "config.ini"
CITIES_FILE = BASE_DIR / "cities_us.txt"


# ── Config helpers ─────────────────────────────────────────────────────────

def _load_cfg() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH)
    return cfg


def _save_cfg(cfg: configparser.ConfigParser):
    with open(CONFIG_PATH, "w") as f:
        cfg.write(f)


def _ensure_config():
    """Create config.ini from example if missing, then exit so user can fill it in."""
    if not CONFIG_PATH.exists():
        example = BASE_DIR / "config.ini.example"
        if example.exists():
            shutil.copy(example, CONFIG_PATH)
            click.echo(f"Created config.ini at {CONFIG_PATH}")
            click.echo("Run 'supplier_scraper.exe setup' to enter your API keys interactively.")
        else:
            click.echo("config.ini not found. Run 'supplier_scraper.exe setup' first.")
        sys.exit(1)


def _prompt_and_save_key(cfg: configparser.ConfigParser, section: str, key: str,
                          label: str, url: str) -> str:
    """Ask the user to type in an API key, save it to config.ini, return the value."""
    click.echo(f"\n  {label}")
    click.echo(f"  Get it at: {url}")
    value = click.prompt("  Paste your key here", hide_input=False).strip()
    if not cfg.has_section(section):
        cfg.add_section(section)
    cfg.set(section, key, value)
    _save_cfg(cfg)
    click.echo(f"  Saved to config.ini ✓")
    return value


def _get_places_api_key() -> str:
    """
    Return the Google Places API key.
    If it's still a placeholder, prompt the user to enter it now and save it.
    """
    _ensure_config()
    cfg = _load_cfg()
    key = cfg.get("googleplaces", "api_key", fallback="")
    if not key or "PLACEHOLDER" in key:
        click.echo("\n  Google Places API key is not set.")
        key = _prompt_and_save_key(
            cfg, "googleplaces", "api_key",
            label="Google Places API Key",
            url="console.cloud.google.com → New Project → Enable 'Places API' → Credentials → Create API Key",
        )
    return key


def _load_cities() -> list[tuple[str, str]]:
    """Load (city, state) pairs from cities_us.txt."""
    cities = []
    path = CITIES_FILE
    if not path.exists():
        return []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.rsplit(",", 1)
        if len(parts) == 2:
            cities.append((parts[0].strip(), parts[1].strip()))
    return cities


def _load_search_terms(cfg: configparser.ConfigParser) -> list[str]:
    raw = cfg.get("googleplaces", "search_terms",
                  fallback="scrap metal recycling,copper recycling,electric motor scrap")
    return [t.strip() for t in raw.split(",") if t.strip()]


# ── Commands ───────────────────────────────────────────────────────────────

@click.group()
def cli():
    """Supplier Scraper — Google Places scrap trader finder & email outreach."""
    pass


@cli.command()
def setup():
    """Interactive first-time setup wizard. Sets all API keys in config.ini."""
    example = BASE_DIR / "config.ini.example"
    if not CONFIG_PATH.exists():
        if example.exists():
            shutil.copy(example, CONFIG_PATH)
            click.echo(f"Created config.ini at {CONFIG_PATH}")
        else:
            click.echo("config.ini.example not found.")
            sys.exit(1)

    cfg = _load_cfg()

    click.echo("\n" + "=" * 52)
    click.echo("  Supplier Scraper — Setup Wizard")
    click.echo("=" * 52)
    click.echo("  Press Enter to skip any key you don't have yet.")
    click.echo("  You can re-run setup at any time to update keys.")

    # Google Places API key (most important — needed for scraping)
    click.echo("\n── Step 1: Google Places API (required for scraping) ──")
    cur = cfg.get("googleplaces", "api_key", fallback="")
    if cur and "PLACEHOLDER" not in cur:
        click.echo(f"  Already set: {cur[:8]}…")
    else:
        v = click.prompt(
            "  Google Places API Key\n"
            "  (console.cloud.google.com → Enable Places API → Credentials)\n"
            "  Key", default="", show_default=False
        ).strip()
        if v:
            if not cfg.has_section("googleplaces"):
                cfg.add_section("googleplaces")
            cfg.set("googleplaces", "api_key", v)
            click.echo("  Saved ✓")

    # SendGrid
    click.echo("\n── Step 2: SendGrid (required for sending emails) ──")
    cur = cfg.get("email", "sendgrid_api_key", fallback="")
    if cur and "PLACEHOLDER" not in cur:
        click.echo(f"  Already set: {cur[:8]}…")
    else:
        v = click.prompt(
            "  SendGrid API Key\n"
            "  (sendgrid.com → Settings → API Keys → Create Key)\n"
            "  Key", default="", show_default=False
        ).strip()
        if v:
            if not cfg.has_section("email"):
                cfg.add_section("email")
            cfg.set("email", "sendgrid_api_key", v)
            click.echo("  Saved ✓")

    # Sender email
    cur = cfg.get("email", "from_email", fallback="")
    if cur and "PLACEHOLDER" not in cur:
        click.echo(f"  Sender email already set: {cur}")
    else:
        v = click.prompt(
            "  Verified sender email address\n"
            "  (must be verified in SendGrid → Sender Authentication)\n"
            "  Email", default="", show_default=False
        ).strip()
        if v:
            cfg.set("email", "from_email", v)
            click.echo("  Saved ✓")

    # Hunter.io (optional)
    click.echo("\n── Step 3: Hunter.io — email validation (optional) ──")
    cur = cfg.get("validation", "hunterio_api_key", fallback="")
    if cur and "PLACEHOLDER" not in cur:
        click.echo(f"  Already set: {cur[:8]}…")
    else:
        v = click.prompt(
            "  Hunter.io API Key (hunter.io → Dashboard → API)\n"
            "  Key [skip]", default="", show_default=False
        ).strip()
        if v:
            if not cfg.has_section("validation"):
                cfg.add_section("validation")
            cfg.set("validation", "hunterio_api_key", v)
            click.echo("  Saved ✓")
        else:
            click.echo("  Skipped — emails will be assumed valid without verification")

    _save_cfg(cfg)
    click.echo("\n" + "=" * 52)
    click.echo("  Setup complete. Run: supplier_scraper.exe serve")
    click.echo("=" * 52)


@cli.command()
@click.option("--port", default=8080, help="Port (default 8080)")
@click.option("--no-browser", is_flag=True, help="Don't open browser automatically")
def serve(port, no_browser):
    """Start the web dashboard at http://localhost:<port>"""
    _ensure_config()
    import uvicorn
    from web_server import app

    url = f"http://localhost:{port}"
    click.echo(f"Starting dashboard at {url}")
    click.echo("Press Ctrl+C to stop.")
    if not no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


@cli.command()
@click.option("--city",   default="", help='Single city e.g. "Dallas, TX"')
@click.option("--all-us", is_flag=True, help="Scrape all cities in cities_us.txt")
@click.option("--resume", is_flag=True, help="Skip cities already scraped recently")
@click.option("--terms",  default="", help="Override search terms (comma-separated)")
def scrape(city, all_us, resume, terms):
    """Find scrap traders via Google Places API and save to database."""
    api_key = _get_places_api_key()

    from db import init_db
    from places_scraper import run_places_scrape
    init_db()

    cfg = _load_cfg()
    rescrape_days   = cfg.getint("googleplaces", "rescrape_days",     fallback=30)
    priority_thresh = cfg.getint("googleplaces", "priority_threshold", fallback=40)

    # Resolve search terms
    if terms:
        search_terms = [t.strip() for t in terms.split(",") if t.strip()]
    else:
        search_terms = _load_search_terms(cfg)

    # Resolve cities
    if city:
        parts = city.rsplit(",", 1)
        if len(parts) != 2:
            click.echo("Use format: --city \"Dallas, TX\"")
            sys.exit(1)
        cities = [(parts[0].strip(), parts[1].strip())]
    elif all_us:
        cities = _load_cities()
        if not cities:
            click.echo(f"cities_us.txt not found at {CITIES_FILE}")
            sys.exit(1)
        click.echo(f"Loaded {len(cities)} cities × {len(search_terms)} search terms"
                   f" = {len(cities)*len(search_terms)} areas to search")
    else:
        click.echo("Specify --city \"City, ST\" or --all-us")
        sys.exit(1)

    if resume:
        click.echo("Resume mode: already-done areas will be skipped.")

    run_places_scrape(
        api_key           = api_key,
        cities            = cities,
        search_terms      = search_terms,
        rescrape_days     = rescrape_days if resume else 0,
        priority_threshold= priority_thresh,
        print_fn          = click.echo,
    )
    click.echo("\nScrape complete. Open the dashboard to review results.")


@cli.command()
def validate():
    """Validate all unvalidated emails via Hunter.io / ZeroBounce."""
    _ensure_config()
    from db import SessionLocal, init_db
    from models import Trader
    from validator import validate as val
    init_db()
    db = SessionLocal()
    try:
        traders = db.query(Trader).filter(
            Trader.email_valid == None, Trader.email != None
        ).all()
        if not traders:
            click.echo("No unvalidated emails found.")
            return
        click.echo(f"Validating {len(traders)} emails…")
        for i, t in enumerate(traders, 1):
            t.email_valid = val(t.email)
            if i % 10 == 0:
                db.commit()
                click.echo(f"  {i}/{len(traders)}")
        db.commit()
        click.echo("Validation complete.")
    finally:
        db.close()


@cli.command()
@click.option("--priority-only", is_flag=True, help="Only send to priority traders")
@click.option("--dry-run", is_flag=True, help="Preview without sending")
def send(priority_only, dry_run):
    """Send outreach emails to all approved traders."""
    _ensure_config()
    from db import SessionLocal, init_db
    from models import Trader, EmailLog
    from email_sender import send_one
    from datetime import datetime
    import time
    init_db()

    cfg = _load_cfg()
    throttle = cfg.getint("email", "throttle_per_minute", fallback=30)
    delay = 60 / max(throttle, 1)

    db = SessionLocal()
    try:
        q = db.query(Trader).filter(
            Trader.approved == True,
            Trader.email_status == "pending",
            Trader.email != None,
        )
        if priority_only:
            q = q.filter(Trader.priority_flag == True)
        traders = q.all()

        if not traders:
            click.echo("No approved traders ready to send.")
            click.echo("Go to the dashboard → Contacts and approve traders first.")
            return

        if dry_run:
            click.echo(f"DRY RUN — would send to {len(traders)} traders:")
            for t in traders:
                score = f"  score={t.priority_score}" if t.priority_score else ""
                click.echo(f"  {t.company_name or 'Unknown'} <{t.email}>{score}")
            return

        click.echo(f"Sending to {len(traders)} traders…")
        sent_count = failed_count = 0
        errors = []

        for trader in traders:
            result = send_one(trader.email, trader.company_name)
            new_status = "sent" if result["success"] else "bounced"
            trader.email_status = new_status
            if result["success"]:
                trader.sent_at = datetime.utcnow()
                sent_count += 1
            else:
                failed_count += 1
                errors.append(f"  {trader.email}: {result['error']}")

            db.add(EmailLog(
                trader_id     = trader.id,
                status        = new_status,
                message_id    = result.get("message_id"),
                error_message = result.get("error"),
                created_at    = datetime.utcnow(),
            ))
            db.commit()
            time.sleep(delay)

        click.echo(f"Done. Sent: {sent_count}, Failed: {failed_count}")
        if errors:
            click.echo("Errors:")
            for e in errors:
                click.echo(e)
    finally:
        db.close()


@cli.command()
def status():
    """Show database summary."""
    from db import SessionLocal, init_db
    from models import Trader, EmailLog, ScrapedArea
    init_db()
    db = SessionLocal()
    try:
        total    = db.query(Trader).count()
        priority = db.query(Trader).filter(Trader.priority_flag == True).count()
        approved = db.query(Trader).filter(Trader.approved == True).count()
        valid    = db.query(Trader).filter(Trader.email_valid == True).count()
        sent     = db.query(Trader).filter(Trader.email_status == "sent").count()
        bounced  = db.query(Trader).filter(Trader.email_status == "bounced").count()
        logs     = db.query(EmailLog).count()
        areas    = db.query(ScrapedArea).count()
    finally:
        db.close()

    click.echo("=" * 44)
    click.echo("  Supplier Scraper — Status")
    click.echo("=" * 44)
    click.echo(f"  Cities searched:  {areas}")
    click.echo(f"  Total traders:    {total}")
    click.echo(f"  Priority traders: {priority}")
    click.echo(f"  Approved:         {approved}")
    click.echo(f"  Email-validated:  {valid}")
    click.echo(f"  Emails sent:      {sent}")
    click.echo(f"  Bounced:          {bounced}")
    click.echo(f"  Log entries:      {logs}")
    click.echo("=" * 44)


if __name__ == "__main__":
    cli()
