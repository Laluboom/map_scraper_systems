"""
Visit a company website and extract the best contact email.
Tries homepage → /contact → /about if needed.
"""
import re
from urllib.parse import urljoin, urlparse

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

GENERIC_PREFIXES = {
    "noreply", "no-reply", "donotreply", "support", "webmaster",
    "admin", "postmaster", "hostmaster", "mailer-daemon",
}

SUBPAGES = ["/contact", "/contact-us", "/about", "/about-us", "/reach-us"]


def _best_email(emails: list[str]) -> str | None:
    """Prefer non-generic emails; return None if list is empty."""
    non_generic = [
        e for e in emails
        if e.split("@")[0].lower() not in GENERIC_PREFIXES
    ]
    return (non_generic or emails or [None])[0]


def _fetch(url: str) -> str:
    try:
        import httpx
        r = httpx.get(url, timeout=8, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code < 400:
            return r.text
    except Exception:
        pass
    return ""


def extract_email(website_url: str | None) -> str | None:
    """Return the best email found on the company's website, or None."""
    if not website_url:
        return None

    # Normalise URL
    if not website_url.startswith("http"):
        website_url = "https://" + website_url

    base = f"{urlparse(website_url).scheme}://{urlparse(website_url).netloc}"

    # Try homepage first
    html = _fetch(website_url)
    emails = EMAIL_RE.findall(html)
    found = _best_email(emails)
    if found:
        return found.lower()

    # Try common contact/about subpages
    for path in SUBPAGES:
        html = _fetch(urljoin(base, path))
        emails = EMAIL_RE.findall(html)
        found = _best_email(emails)
        if found:
            return found.lower()

    return None
