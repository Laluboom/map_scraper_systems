"""FastAPI web UI — replaces React, no Node.js needed."""
import sys
import configparser
from datetime import datetime
from pathlib import Path
import jinja2
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from db import SessionLocal, init_db
from models import Trader, EmailLog, ScrapedArea

# Resolve templates dir both when run as script and when bundled by PyInstaller
if getattr(sys, "frozen", False):
    _base = Path(sys._MEIPASS)
else:
    _base = Path(__file__).parent

_env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(_base / "templates")), autoescape=True)


def _render(name: str, **ctx) -> HTMLResponse:
    return HTMLResponse(_env.get_template(name).render(**ctx))

app = FastAPI()
init_db()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    db = SessionLocal()
    try:
        total = db.query(Trader).count()
        priority = db.query(Trader).filter(Trader.priority_flag == True).count()
        approved = db.query(Trader).filter(Trader.approved == True).count()
        sent = db.query(Trader).filter(Trader.email_status == "sent").count()
        bounced = db.query(Trader).filter(Trader.email_status == "bounced").count()
        valid = db.query(Trader).filter(Trader.email_valid == True).count()
    finally:
        db.close()
    return _render("dashboard.html",
        stats={"total": total, "priority": priority, "approved": approved,
               "sent": sent, "bounced": bounced, "valid": valid})


@app.get("/contacts", response_class=HTMLResponse)
def contacts(request: Request, filter: str = "all"):
    db = SessionLocal()
    try:
        q = db.query(Trader)
        if filter == "priority":
            q = q.filter(Trader.priority_flag == True)
        elif filter == "approved":
            q = q.filter(Trader.approved == True)
        elif filter == "pending":
            q = q.filter(Trader.email_status == "pending")
        traders = q.order_by(Trader.priority_flag.desc()).limit(500).all()
    finally:
        db.close()
    return _render("contacts.html", traders=traders, filter=filter)


@app.get("/contacts/{trader_id}/approve")
def approve(trader_id: str):
    db = SessionLocal()
    try:
        t = db.query(Trader).filter(Trader.id == trader_id).first()
        if t:
            t.approved = True
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/contacts", status_code=302)


@app.get("/contacts/{trader_id}/reject")
def reject(trader_id: str):
    db = SessionLocal()
    try:
        t = db.query(Trader).filter(Trader.id == trader_id).first()
        if t:
            t.approved = False
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/contacts", status_code=302)


@app.get("/send", response_class=HTMLResponse)
def send_page(request: Request, msg: str = "", error: str = ""):
    db = SessionLocal()
    try:
        ready = db.query(Trader).filter(
            Trader.approved == True,
            Trader.email_status == "pending",
            Trader.email != None,
        ).count()
    finally:
        db.close()
    return _render("send.html", ready=ready, msg=msg, error=error)


@app.post("/send/start")
def send_start():
    import time, configparser
    from pathlib import Path
    from email_sender import send_one

    cfg = configparser.ConfigParser()
    cfg.read(Path(__file__).parent / "config.ini")
    throttle = cfg.getint("email", "throttle_per_minute", fallback=30)
    delay = 60 / max(throttle, 1)

    db = SessionLocal()
    try:
        traders = db.query(Trader).filter(
            Trader.approved == True,
            Trader.email_status == "pending",
            Trader.email != None,
        ).all()

        sent_count = failed_count = 0
        for trader in traders:
            result = send_one(trader.email, trader.company_name)
            new_status = "sent" if result["success"] else "bounced"
            trader.email_status = new_status
            if result["success"]:
                trader.sent_at = datetime.utcnow()
                sent_count += 1
            else:
                failed_count += 1
            log = EmailLog(
                trader_id=trader.id,
                status=new_status,
                message_id=result.get("message_id"),
                error_message=result.get("error"),
                created_at=datetime.utcnow(),
            )
            db.add(log)
            db.commit()
            time.sleep(delay)

        msg = f"Done. Sent: {sent_count}, Failed: {failed_count}"
        return RedirectResponse(f"/send?msg={msg}", status_code=302)
    finally:
        db.close()


def _scrape_page_ctx(msg="", error=""):
    if getattr(sys, "frozen", False):
        _cfg_path = Path(sys.executable).parent / "config.ini"
        _cities_path = Path(sys.executable).parent / "cities_us.txt"
    else:
        _cfg_path = Path(__file__).parent / "config.ini"
        _cities_path = Path(__file__).parent / "cities_us.txt"

    cfg = configparser.ConfigParser()
    cfg.read(_cfg_path)
    rescrape_days = cfg.getint("googleplaces", "rescrape_days", fallback=30)
    raw_terms = cfg.get("googleplaces", "search_terms",
                        fallback="scrap metal recycling,copper recycling,electric motor scrap")
    num_terms = len([t for t in raw_terms.split(",") if t.strip()])
    num_cities = sum(
        1 for line in _cities_path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ) if _cities_path.exists() else 0
    total_areas_possible = num_cities * num_terms

    db = SessionLocal()
    try:
        done_areas = db.query(ScrapedArea).count()
        recent_areas = (
            db.query(ScrapedArea)
            .order_by(ScrapedArea.scraped_at.desc())
            .limit(50)
            .all()
        )
    finally:
        db.close()

    pct = round(done_areas / total_areas_possible * 100) if total_areas_possible else 0
    return dict(
        msg=msg, error=error,
        done_areas=done_areas,
        total_areas=total_areas_possible,
        total_areas_possible=total_areas_possible,
        pct=pct,
        rescrape_days=rescrape_days,
        recent_areas=recent_areas,
    )


@app.get("/scrape", response_class=HTMLResponse)
def scrape_page(request: Request, msg: str = "", error: str = ""):
    return _render("scrape.html", **_scrape_page_ctx(msg=msg, error=error))


@app.post("/scrape/start")
async def scrape_start(request: Request):
    import threading
    form = await request.form()
    mode = form.get("mode", "city")
    city = (form.get("city") or "").strip()

    if getattr(sys, "frozen", False):
        _cfg_path = Path(sys.executable).parent / "config.ini"
        _cities_path = Path(sys.executable).parent / "cities_us.txt"
    else:
        _cfg_path = Path(__file__).parent / "config.ini"
        _cities_path = Path(__file__).parent / "cities_us.txt"

    cfg = configparser.ConfigParser()
    cfg.read(_cfg_path)
    api_key = cfg.get("googleplaces", "api_key", fallback="")
    if not api_key or "PLACEHOLDER" in api_key:
        return RedirectResponse("/scrape?msg=Google+Places+API+key+not+set.+Run+setup+first.&error=1", status_code=302)

    rescrape_days = cfg.getint("googleplaces", "rescrape_days", fallback=30)
    priority_thresh = cfg.getint("googleplaces", "priority_threshold", fallback=40)
    raw_terms = cfg.get("googleplaces", "search_terms",
                        fallback="scrap metal recycling,copper recycling,electric motor scrap")
    search_terms = [t.strip() for t in raw_terms.split(",") if t.strip()]

    if mode == "city":
        if not city:
            return RedirectResponse('/scrape?msg=Enter+a+city+e.g.+"Dallas,+TX"&error=1', status_code=302)
        parts = city.rsplit(",", 1)
        if len(parts) != 2:
            return RedirectResponse('/scrape?msg=Use+format+"City,+ST"&error=1', status_code=302)
        cities = [(parts[0].strip(), parts[1].strip())]
        use_resume = False
    elif mode == "resume":
        cities = [
            (ln.rsplit(",", 1)[0].strip(), ln.rsplit(",", 1)[1].strip())
            for ln in _cities_path.read_text().splitlines()
            if ln.strip() and not ln.startswith("#") and "," in ln
        ] if _cities_path.exists() else []
        use_resume = True
    else:  # all
        cities = [
            (ln.rsplit(",", 1)[0].strip(), ln.rsplit(",", 1)[1].strip())
            for ln in _cities_path.read_text().splitlines()
            if ln.strip() and not ln.startswith("#") and "," in ln
        ] if _cities_path.exists() else []
        use_resume = False

    if not cities:
        return RedirectResponse("/scrape?msg=No+cities+loaded.+Check+cities_us.txt&error=1", status_code=302)

    from places_scraper import run_places_scrape
    from db import init_db

    def _run():
        init_db()
        run_places_scrape(
            api_key=api_key,
            cities=cities,
            search_terms=search_terms,
            rescrape_days=rescrape_days if use_resume else 0,
            priority_threshold=priority_thresh,
            print_fn=print,
        )

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=300)

    label = city if mode == "city" else ("all US cities (resume)" if use_resume else "all US cities")
    return RedirectResponse(f"/scrape?msg=Scrape+complete+for+{label.replace(' ', '+')}", status_code=302)


@app.get("/logs", response_class=HTMLResponse)
def logs_page(request: Request):
    db = SessionLocal()
    try:
        logs = db.query(EmailLog).order_by(EmailLog.created_at.desc()).limit(300).all()
    finally:
        db.close()
    return _render("logs.html", logs=logs)
