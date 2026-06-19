"""
Visit a company website and extract the best contact email.
Tries homepage → /contact → /about if needed.
"""
import re
from urllib.parse import urljoin, urlparse

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}")

# File/asset extensions that are never valid TLDs — filters srcset/JS false positives
_ASSET_TLDS = {
    "png", "jpg", "jpeg", "gif", "svg", "webp", "ico", "bmp", "tiff",
    "js", "jsx", "ts", "tsx", "css", "scss", "sass", "less", "vue",
    "woff", "woff2", "ttf", "eot", "otf", "mp4", "mp3", "pdf",
    "zip", "gz", "tar", "map", "json", "xml",
}


def _valid_email(email: str) -> bool:
    tld = email.rsplit(".", 1)[-1].lower()
    return tld.isalpha() and tld not in _ASSET_TLDS


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
    email, _ = extract_email_and_text(website_url)
    return email


def extract_email_and_text(website_url: str | None) -> tuple[str | None, str]:
    """Return (best_email, full_page_text) in a single fetch pass."""
    if not website_url:
        return None, ""

    if not website_url.startswith("http"):
        website_url = "https://" + website_url

    parsed = urlparse(website_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    all_text = ""

    # Try homepage first
    html = _fetch(website_url)
    all_text = html
    emails = [e for e in EMAIL_RE.findall(html) if _valid_email(e)]
    found = _best_email(emails)
    if found:
        return found.lower(), all_text

    # Try common contact/about subpages
    for path in SUBPAGES:
        html = _fetch(urljoin(base, path))
        all_text += html
        emails = [e for e in EMAIL_RE.findall(html) if _valid_email(e)]
        found = _best_email(emails)
        if found:
            return found.lower(), all_text

    return None, all_text
