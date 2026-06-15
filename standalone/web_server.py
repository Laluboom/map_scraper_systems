"""FastAPI web UI — replaces React, no Node.js needed."""
import csv
import io
import sys
import configparser
from datetime import datetime, date
from pathlib import Path
from urllib.parse import quote_plus
import jinja2
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from job_registry import jobs
from app_logger import log


def _cfg_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "config.ini"
    return Path(__file__).parent / "config.ini"


def _read_cfg() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read(_cfg_path())
    return cfg

from db import SessionLocal, init_db
from models import Trader, EmailLog, ScrapedArea

# Resolve templates dir both when run as script and when bundled by PyInstaller
if getattr(sys, "frozen", False):
    _base = Path(sys._MEIPASS)
else:
    _base = Path(__file__).parent

_env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(_base / "templates")), autoescape=True, auto_reload=True)


def _render(name: str, **ctx) -> HTMLResponse:
    ctx.setdefault("update_info", _update_info)
    return HTMLResponse(_env.get_template(name).render(**ctx))

app = FastAPI()
try:
    init_db()
except Exception as _db_err:
    import traceback
    print(f"[STARTUP ERROR] Database initialisation failed: {_db_err}")
    traceback.print_exc()

# Check for updates once at startup; cached for the lifetime of the process
_update_info: dict | None = None
try:
    from version import __version__ as _current_version
    from update_checker import check_for_update as _check_for_update
    _update_info = _check_for_update(_current_version)
except Exception:
    pass


def _config_warnings() -> list[str]:
    """Return human-readable warnings for missing/placeholder config values."""
    cfg = _read_cfg()
    warnings = []
    gkey = cfg.get("googleplaces", "api_key", fallback="")
    if not gkey or "PLACEHOLDER" in gkey:
        warnings.append("Google Places API key not set — scraping will not work. Run setup.")
    smtp_pw = cfg.get("email", "smtp_password", fallback="")
    smtp_user = cfg.get("email", "smtp_user", fallback="")
    if not smtp_user or not smtp_pw or "PLACEHOLDER" in smtp_pw:
        warnings.append("SMTP credentials not set — email sending will not work. Run setup.")
    return warnings


# Daily send counter — resets automatically when the date changes
_send_counter: dict = {"date": None, "count": 0}

def _daily_cap() -> int:
    cfg = _read_cfg()
    return cfg.getint("email", "daily_send_cap", fallback=200)

def _sent_today() -> int:
    if _send_counter["date"] != date.today():
        _send_counter["date"] = date.today()
        _send_counter["count"] = 0
    return _send_counter["count"]

def _increment_sent(n: int = 1):
    _sent_today()  # ensure date is current
    _send_counter["count"] += n


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
               "sent": sent, "bounced": bounced, "valid": valid},
        config_warnings=_config_warnings())


@app.get("/contacts", response_class=HTMLResponse)
def contacts(request: Request, filter: str = "all"):
    db = SessionLocal()
    try:
        q = db.query(Trader)
        if filter == "priority":
            q = q.filter(Trader.priority_flag == True)
        elif filter == "approved":
            q = q.filter(Trader.approved == True)
        elif filter == "rejected":
            q = q.filter(Trader.approved == False)
        elif filter == "pending":
            q = q.filter(Trader.approved == True, Trader.email_status == "pending")
        elif filter == "unsubscribed":
            q = q.filter(Trader.unsubscribed == True)
        traders = q.order_by(Trader.priority_flag.desc()).limit(500).all()
    finally:
        db.close()
    return _render("contacts.html", traders=traders, filter=filter)


@app.post("/contacts/{trader_id}/approve")
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


@app.post("/contacts/{trader_id}/reject")
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


@app.post("/contacts/{trader_id}/reset")
def reset(trader_id: str):
    db = SessionLocal()
    try:
        t = db.query(Trader).filter(Trader.id == trader_id).first()
        if t:
            t.approved = None
            t.email_status = "pending"
            t.sent_at = None
            db.commit()
            db.refresh(t)
    finally:
        db.close()
    return RedirectResponse("/contacts", status_code=302)


@app.post("/contacts/{trader_id}/unsubscribe")
def unsubscribe(trader_id: str):
    db = SessionLocal()
    try:
        t = db.query(Trader).filter(Trader.id == trader_id).first()
        if t:
            t.unsubscribed = True
            t.email_status = "bounced"  # stop future sends
            db.commit()
            log.info(f"Marked unsubscribed: {t.email} ({t.company_name})")
    finally:
        db.close()
    return RedirectResponse("/contacts", status_code=302)


@app.get("/contacts/duplicates", response_class=HTMLResponse)
def contacts_duplicates(request: Request):
    from difflib import SequenceMatcher
    db = SessionLocal()
    try:
        traders = db.query(Trader).filter(Trader.unsubscribed.isnot(True)).all()
    finally:
        db.close()

    groups = []

    # 1. Exact email duplicates
    from collections import defaultdict
    by_email = defaultdict(list)
    for t in traders:
        if t.email:
            by_email[t.email.lower().strip()].append(t)
    for email, group in by_email.items():
        if len(group) > 1:
            groups.append({"reason": f"Same email: {email}", "traders": group})

    # 2. Same phone number
    by_phone = defaultdict(list)
    for t in traders:
        phone = (t.phone or "").strip().replace(" ", "").replace("-", "")
        if len(phone) >= 7:
            by_phone[phone].append(t)
    for phone, group in by_phone.items():
        if len(group) > 1:
            ids_already = {t.id for g in groups for t in g["traders"]}
            if not all(t.id in ids_already for t in group):
                groups.append({"reason": f"Same phone: {phone}", "traders": group})

    # 3. Similar company names (>= 85% match)
    checked = set()
    name_groups = []
    trader_list = [t for t in traders if t.company_name]
    for i, a in enumerate(trader_list):
        if a.id in checked:
            continue
        cluster = [a]
        for b in trader_list[i+1:]:
            if b.id in checked:
                continue
            ratio = SequenceMatcher(None,
                a.company_name.lower().strip(),
                b.company_name.lower().strip()).ratio()
            if ratio >= 0.85:
                cluster.append(b)
                checked.add(b.id)
        if len(cluster) > 1:
            checked.add(a.id)
            name_groups.append({"reason": f"Similar name: \"{a.company_name}\"", "traders": cluster})
    groups.extend(name_groups)

    return _render("duplicates.html", groups=groups)


@app.post("/contacts/{trader_id}/delete")
def delete_trader(trader_id: str):
    db = SessionLocal()
    try:
        t = db.query(Trader).filter(Trader.id == trader_id).first()
        if t:
            db.delete(t)
            db.commit()
            log.info(f"Deleted trader: {trader_id}")
    finally:
        db.close()
    return RedirectResponse("/contacts/duplicates", status_code=302)


@app.get("/backup/download")
def backup_download():
    import sqlite3, tempfile, os
    from db import _db_path
    # Use SQLite's online backup API — safe even while the DB is in use
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    src = sqlite3.connect(_db_path)
    dst = sqlite3.connect(tmp.name)
    src.backup(dst)
    dst.close()
    src.close()
    data = Path(tmp.name).read_bytes()
    os.unlink(tmp.name)
    filename = f"supplier_scraper_backup_{date.today()}.db"
    return StreamingResponse(iter([data]),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.get("/email-template", response_class=HTMLResponse)
def email_template_page(request: Request, msg: str = "", error: str = ""):
    from email_sender import load_template, DEFAULT_BODY, DEFAULT_SUBJECT, build_email_body
    cfg = _read_cfg()
    from_email = cfg.get("email", "from_email", fallback="sender@example.com")
    from_name  = cfg.get("email", "from_name",  fallback="John Doe")

    subject, body = load_template()
    preview_body = build_email_body("Gulf Metals LLC", body)
    return _render("email_template.html",
        subject=subject, body=body, preview_body=preview_body,
        from_email=from_email, from_name=from_name,
        msg=msg, error=error)


@app.post("/email-template/save")
async def email_template_save(request: Request):
    from email_sender import save_template
    form = await request.form()
    subject = (form.get("subject") or "").strip()
    body    = form.get("body") or ""
    if not subject:
        return RedirectResponse("/email-template?msg=Subject+cannot+be+empty&error=1", status_code=302)
    save_template(subject, body)
    return RedirectResponse("/email-template?msg=Template+saved+successfully", status_code=302)


@app.post("/email-template/save-sender")
async def email_template_save_sender(request: Request):
    form = await request.form()
    from_name  = (form.get("from_name")  or "").strip()
    from_email_val = (form.get("from_email") or "").strip()
    if not from_name or not from_email_val:
        return RedirectResponse("/email-template?msg=Name+and+email+are+required&error=1", status_code=302)
    cfg = _read_cfg()
    if not cfg.has_section("email"):
        cfg.add_section("email")
    cfg.set("email", "from_name",  from_name)
    cfg.set("email", "from_email", from_email_val)
    with open(_cfg_path(), "w") as f:
        cfg.write(f)
    return RedirectResponse("/email-template?msg=Sender+saved+successfully", status_code=302)


@app.post("/email-template/reset")
def email_template_reset():
    from email_sender import save_template, DEFAULT_SUBJECT, DEFAULT_BODY
    save_template(DEFAULT_SUBJECT, DEFAULT_BODY)
    return RedirectResponse("/email-template?msg=Template+reset+to+default", status_code=302)


@app.get("/compose", response_class=HTMLResponse)
def compose_page(request: Request, msg: str = "", error: str = ""):
    from email_sender import load_template, DEFAULT_BODY
    cfg = _read_cfg()
    from_email_val = cfg.get("email", "from_email", fallback="")
    from_name  = cfg.get("email", "from_name",  fallback="John Doe")
    subject, body = load_template()
    return _render("compose.html",
        from_email=from_email_val, from_name=from_name,
        subject=subject, body=body, default_body=DEFAULT_BODY,
        msg=msg, error=error)


@app.post("/compose/send")
async def compose_send(request: Request):
    form = await request.form()
    to_email       = (form.get("to_email")    or "").strip()
    subject        = (form.get("subject")     or "").strip()
    body           = (form.get("body")        or "").strip()
    from_name      = (form.get("from_name")   or "").strip()
    from_email_val = (form.get("from_email")  or "").strip()

    if not to_email or not subject or not body:
        return RedirectResponse("/compose?msg=To,+subject+and+body+are+all+required&error=1", status_code=302)

    cfg = _read_cfg()
    smtp_password = cfg.get("email", "smtp_password", fallback="")
    if not smtp_password or "PLACEHOLDER" in smtp_password:
        return RedirectResponse("/compose?msg=SMTP+credentials+not+configured.+Run+setup+first.&error=1", status_code=302)

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        smtp_host = cfg.get("email", "smtp_host", fallback="smtp.gmail.com")
        smtp_port = cfg.getint("email", "smtp_port", fallback=587)
        smtp_user = cfg.get("email", "smtp_user", fallback="")

        mime = MIMEMultipart("alternative")
        mime["Subject"] = subject
        mime["From"]    = f"{from_name} <{from_email_val}>"
        mime["To"]      = to_email
        mime.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email_val, to_email, mime.as_string())

        return RedirectResponse(f"/compose?msg=Email+sent+to+{quote_plus(to_email)}", status_code=302)
    except Exception as exc:
        print(f"[compose/send] error: {exc}")
        return RedirectResponse("/compose?msg=Send+failed.+Check+terminal+for+details.&error=1", status_code=302)


@app.get("/send", response_class=HTMLResponse)
def send_page(request: Request, msg: str = "", error: str = ""):
    db = SessionLocal()
    try:
        ready = db.query(Trader).filter(
            Trader.approved == True,
            Trader.email_status == "pending",
            Trader.email != None,
            Trader.email_valid.isnot(False),
            Trader.unsubscribed.isnot(True),
        ).count()
    finally:
        db.close()
    return _render("send.html",
        ready=ready,
        msg=msg,
        error=error,
        active_job=jobs.active("send"),
        recent_jobs=jobs.recent("send", limit=5))


@app.post("/send/start")
def send_start():
    import time
    from email_sender import send_one

    active = jobs.active("send")
    if active:
        msg = f"Send job already running: {active.label}"
        return RedirectResponse(f"/send?msg={quote_plus(msg)}", status_code=302)

    cap = _daily_cap()
    sent_so_far = _sent_today()
    if sent_so_far >= cap:
        msg = f"Daily send cap reached ({cap} emails/day). Resets at midnight."
        return RedirectResponse(f"/send?msg={quote_plus(msg)}&error=1", status_code=302)

    cfg = _read_cfg()
    throttle = cfg.getint("email", "throttle_per_minute", fallback=20)
    delay = 60 / max(throttle, 1)

    def _run(job):
        db = SessionLocal()
        try:
            traders = db.query(Trader).filter(
                Trader.approved == True,
                Trader.email_status == "pending",
                Trader.email != None,
                Trader.email_valid.isnot(False),
                Trader.unsubscribed.isnot(True),
            ).all()
            total = len(traders)
            if not total:
                jobs.mark_complete(job.id, "No approved traders ready to send")
                return

            sent_count = failed_count = 0
            for index, trader in enumerate(traders, 1):
                if job.cancel_requested:
                    jobs.mark_canceled(job.id, f"Campaign canceled. Sent: {sent_count}, failed: {failed_count}")
                    return

                # Re-check daily cap inside loop
                if _sent_today() >= _daily_cap():
                    jobs.mark_canceled(job.id, f"Daily cap reached. Sent: {sent_count} today.")
                    log.warning(f"Daily send cap hit after {sent_count} emails.")
                    return

                jobs.update(job.id, f"Sending {index}/{total}: {trader.email}")
                result = send_one(trader.email, trader.company_name)
                new_status = "sent" if result["success"] else "bounced"
                trader.email_status = new_status
                if result["success"]:
                    trader.sent_at = datetime.utcnow()
                    sent_count += 1
                    _increment_sent()
                    log.info(f"Sent to {trader.email} ({trader.company_name})")
                else:
                    failed_count += 1
                    log.warning(f"Failed to send to {trader.email}: {result.get('error')}")
                db.add(EmailLog(
                    trader_id=trader.id,
                    status=new_status,
                    message_id=result.get("message_id"),
                    error_message=result.get("error"),
                    created_at=datetime.utcnow(),
                ))
                db.commit()
                time.sleep(delay)
            jobs.mark_complete(job.id, f"Campaign complete. Sent: {sent_count}, failed: {failed_count}")
            log.info(f"Campaign complete — sent: {sent_count}, failed: {failed_count}")
        except Exception as exc:
            log.error(f"Campaign error: {exc}")
            jobs.mark_complete(job.id, f"Campaign error — check supplier_scraper.log")
        finally:
            db.close()

    job = jobs.start("send", "Email campaign", _run)
    msg = f"Campaign started — sending up to {cap - sent_so_far} emails today (cap: {cap}/day)."
    return RedirectResponse(f"/send?msg={quote_plus(msg)}", status_code=302)


@app.post("/send/{job_id}/cancel")
def send_cancel(job_id: str):
    if jobs.request_cancel(job_id, "Cancel requested — stopping after the current email"):
        msg = "Cancel requested for email campaign."
    else:
        msg = "No running email campaign found for that job."
    return RedirectResponse(f"/send?msg={quote_plus(msg)}", status_code=302)


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
        active_job=jobs.active("scrape"),
        recent_jobs=jobs.recent("scrape", limit=5),
    )


@app.get("/scrape", response_class=HTMLResponse)
def scrape_page(request: Request, msg: str = "", error: str = ""):
    return _render("scrape.html", **_scrape_page_ctx(msg=msg, error=error))


@app.post("/scrape/start")
async def scrape_start(request: Request):
    form = await request.form()
    mode = form.get("mode", "city")
    city = (form.get("city") or "").strip()

    active = jobs.active("scrape")
    if active:
        msg = f"Scrape job already running: {active.label}"
        return RedirectResponse(f"/scrape?msg={quote_plus(msg)}", status_code=302)

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

    label = city if mode == "city" else ("all US cities (resume)" if use_resume else "all US cities")

    def _run(job):
        init_db()
        def _progress(message: str):
            print(message)
            jobs.update(job.id, message.strip())

        run_places_scrape(
            api_key=api_key,
            cities=cities,
            search_terms=search_terms,
            rescrape_days=rescrape_days if use_resume else 0,
            priority_threshold=priority_thresh,
            print_fn=_progress,
            should_cancel=lambda: jobs.is_cancel_requested(job.id),
        )
        if job.cancel_requested:
            jobs.mark_canceled(job.id, f"Scrape canceled for {label}")
            return
        jobs.mark_complete(job.id, f"Scrape complete for {label}")

    job = jobs.start("scrape", label, _run)
    msg = quote_plus(f"Scrape started for {label}. Job ID: {job.id[:8]}")
    return RedirectResponse(f"/scrape?msg={msg}", status_code=302)


@app.post("/scrape/{job_id}/cancel")
def scrape_cancel(job_id: str):
    if jobs.request_cancel(job_id, "Cancel requested — stopping after the current scrape step"):
        msg = "Cancel requested for scrape job."
    else:
        msg = "No running scrape job found for that job."
    return RedirectResponse(f"/scrape?msg={quote_plus(msg)}", status_code=302)


@app.get("/logs", response_class=HTMLResponse)
def logs_page(request: Request):
    db = SessionLocal()
    try:
        logs_data = db.query(EmailLog).order_by(EmailLog.created_at.desc()).limit(300).all()
    finally:
        db.close()
    return _render("logs.html", logs=logs_data)


@app.get("/contacts/export.csv")
def contacts_export():
    db = SessionLocal()
    try:
        traders = db.query(Trader).order_by(Trader.priority_flag.desc()).all()
    finally:
        db.close()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Company", "Email", "Phone", "Website", "City", "State",
                "Priority", "Email Valid", "Approved", "Email Status", "Sent At", "Tags"])
    for t in traders:
        w.writerow([
            t.company_name or "", t.email or "", t.phone or "",
            t.website or "", t.city or "", t.state or "",
            "Yes" if t.priority_flag else "No",
            "Yes" if t.email_valid else ("No" if t.email_valid is False else ""),
            "Approved" if t.approved else ("Rejected" if t.approved is False else ""),
            t.email_status or "",
            t.sent_at.strftime("%Y-%m-%d %H:%M") if t.sent_at else "",
            ", ".join(t.product_tags) if t.product_tags else (t.tags or ""),
        ])
    buf.seek(0)
    filename = f"contacts_{date.today()}.csv"
    return StreamingResponse(iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, msg: str = "", error: str = ""):
    cfg = _read_cfg()
    return _render("settings.html",
        from_name=cfg.get("email", "from_name", fallback=""),
        from_email=cfg.get("email", "from_email", fallback=""),
        smtp_host=cfg.get("email", "smtp_host", fallback="smtp.gmail.com"),
        smtp_port=cfg.get("email", "smtp_port", fallback="587"),
        smtp_user=cfg.get("email", "smtp_user", fallback=""),
        smtp_password=cfg.get("email", "smtp_password", fallback=""),
        msg=msg, error=error)


@app.post("/settings/save")
async def settings_save(request: Request):
    form = await request.form()
    cfg = _read_cfg()
    if not cfg.has_section("email"):
        cfg.add_section("email")
    cfg.set("email", "from_name",  (form.get("from_name")  or "").strip())
    cfg.set("email", "from_email", (form.get("from_email") or "").strip())
    cfg.set("email", "smtp_host",  (form.get("smtp_host")  or "smtp.gmail.com").strip())
    cfg.set("email", "smtp_port",  (form.get("smtp_port")  or "587").strip())
    cfg.set("email", "smtp_user",  (form.get("smtp_user")  or "").strip())
    password = (form.get("smtp_password") or "").strip()
    if password:
        cfg.set("email", "smtp_password", password)
    with open(_cfg_path(), "w") as f:
        cfg.write(f)
    return RedirectResponse("/settings?msg=Settings+saved+successfully", status_code=302)


@app.get("/logs/export.csv")
def logs_export():
    db = SessionLocal()
    try:
        logs_data = db.query(EmailLog).order_by(EmailLog.created_at.desc()).all()
        traders = {t.id: t.company_name for t in db.query(Trader).all()}
    finally:
        db.close()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Trader ID", "Company", "Status", "Message ID", "Error", "Sent At"])
    for l in logs_data:
        w.writerow([
            l.trader_id or "", traders.get(l.trader_id, ""),
            l.status or "", l.message_id or "", l.error_message or "",
            l.created_at.strftime("%Y-%m-%d %H:%M") if l.created_at else "",
        ])
    buf.seek(0)
    filename = f"email_logs_{date.today()}.csv"
    return StreamingResponse(iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"})
