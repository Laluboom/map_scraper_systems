"""Email validation via Hunter.io (primary) and ZeroBounce (fallback)."""
import configparser
import sys
from pathlib import Path
import httpx

_BASE = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent


def validate(email: str) -> bool:
    cfg = configparser.ConfigParser()
    cfg.read(_BASE / "config.ini")
    hunterio_key = cfg.get("validation", "hunterio_api_key", fallback="")
    zerobounce_key = cfg.get("validation", "zerobounce_api_key", fallback="")

    if hunterio_key and "PLACEHOLDER" not in hunterio_key:
        try:
            r = httpx.get(
                "https://api.hunter.io/v2/email-verifier",
                params={"email": email, "api_key": hunterio_key},
                timeout=10,
            )
            result = r.json().get("data", {}).get("result", "")
            return result in ("deliverable", "risky")
        except Exception:
            pass

    if zerobounce_key and "PLACEHOLDER" not in zerobounce_key:
        try:
            r = httpx.get(
                "https://api.zerobounce.net/v2/validate",
                params={"api_key": zerobounce_key, "email": email, "ip_address": ""},
                timeout=10,
            )
            return r.json().get("status", "") in ("valid", "catch-all")
        except Exception:
            pass

    # No validator configured — skip validation, assume valid
    return True
