"""Email sending via SendGrid. Subject from config.ini, body from email_template.txt."""
import configparser
import time
from pathlib import Path

import sys as _sys
_BASE = Path(_sys.executable).parent if getattr(_sys, "frozen", False) else Path(__file__).parent

DEFAULT_SUBJECT = "Inquiry for Non-Ferrous Scrap Supply"
DEFAULT_BODY = """\
Dear {greeting},

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
Noaman Alam
Manager (Purchasing)
SCHION INTERNATIONAL
Tel: +92 21 32570013
Cell: +92 33 33 44 99 59
Mail: Noaman@schion.com.pk
Web: www.schion.com.pk

--
To unsubscribe, reply with UNSUBSCRIBE in the subject line.
"""

_TEMPLATE_FILE = _BASE / "email_template.txt"


def load_template() -> tuple[str, str]:
    """Return (subject, body_template) from disk, falling back to defaults."""
    cfg = configparser.ConfigParser()
    cfg.read(_BASE / "config.ini")
    subject = cfg.get("email", "subject", fallback=DEFAULT_SUBJECT)
    body = _TEMPLATE_FILE.read_text(encoding="utf-8") if _TEMPLATE_FILE.exists() else DEFAULT_BODY
    return subject, body


def save_template(subject: str, body: str):
    """Persist subject to config.ini and body to email_template.txt."""
    cfg = configparser.ConfigParser()
    cfg.read(_BASE / "config.ini")
    if not cfg.has_section("email"):
        cfg.add_section("email")
    cfg.set("email", "subject", subject)
    with open(_BASE / "config.ini", "w") as f:
        cfg.write(f)
    _TEMPLATE_FILE.write_text(body, encoding="utf-8")


def build_email_body(company_name: str | None, body_template: str) -> str:
    greeting = company_name if company_name else "Sir"
    try:
        return body_template.format(company_name=company_name or "", greeting=greeting)
    except KeyError:
        return body_template  # unknown placeholder — send as-is


def send_one(to_email: str, company_name: str | None) -> dict:
    cfg = configparser.ConfigParser()
    cfg.read(_BASE / "config.ini")
    api_key   = cfg.get("email", "sendgrid_api_key", fallback="")
    from_email = cfg.get("email", "from_email", fallback="")
    from_name  = cfg.get("email", "from_name", fallback="Noaman Alam")

    if not api_key or "PLACEHOLDER" in api_key:
        return {"success": False, "error": "SendGrid API key not configured in config.ini"}

    subject, body_template = load_template()
    body = build_email_body(company_name, body_template)

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
    except ImportError:
        return {"success": False, "error": "sendgrid package not installed (pip install sendgrid)"}

    msg = Mail(
        from_email=(from_email, from_name),
        to_emails=to_email,
        subject=subject,
        plain_text_content=body,
    )
    try:
        sg = SendGridAPIClient(api_key)
        resp = sg.send(msg)
        return {"success": True, "message_id": resp.headers.get("X-Message-Id", "")}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def send_campaign(traders, throttle_per_minute: int = 30) -> dict:
    delay = 60 / max(throttle_per_minute, 1)
    results = {"sent": 0, "failed": 0, "errors": []}
    for trader in traders:
        result = send_one(trader.email, trader.company_name)
        if result["success"]:
            results["sent"] += 1
        else:
            results["failed"] += 1
            results["errors"].append(f"{trader.email}: {result['error']}")
        time.sleep(delay)
    return results
