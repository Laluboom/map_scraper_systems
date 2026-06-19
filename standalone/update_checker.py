"""
Checks a public Gist for the latest version.
Silent-fails on any network error — never crashes the app.

To release an update:
  1. Bump __version__ in version.py
  2. Tag and push → GitHub Actions builds the .exe
  3. Upload the .exe somewhere (Google Drive, etc.)
  4. Edit the Gist below: bump version, paste the new download_url, update notes
"""
import json

# Public Gist raw URL — edit this file to publish updates to the client
# Format: { "version": "1.0.1", "download_url": "https://...", "notes": "..." }
MANIFEST_URL = "https://gist.githubusercontent.com/Laluboom/2d0d8017ff97f1ccc70d7141d0ab1ea2/raw/Supplier_Scraper.json"


def _parse_version(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.lstrip("v").split("."))
    except Exception:
        return (0, 0, 0)


def check_for_update(current_version: str) -> dict | None:
    """
    Returns {"version", "download_url", "notes"} if a newer version is available.
    Returns None if up-to-date, unreachable, or on any error.
    """
    if "PLACEHOLDER" in MANIFEST_URL:
        return None
    try:
        import httpx
        r = httpx.get(MANIFEST_URL, timeout=4, follow_redirects=True)
        if r.status_code != 200:
            return None
        data = r.json()
        latest = data.get("version", "")
        if not latest:
            return None
        if _parse_version(latest) > _parse_version(current_version):
            return {
                "version":      latest,
                "download_url": data.get("download_url", ""),
                "notes":        data.get("notes", ""),
            }
    except Exception:
        pass
    return None
