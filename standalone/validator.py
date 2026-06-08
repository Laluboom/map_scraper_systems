"""Email validation via Hunter.io (primary) and ZeroBounce (fallback)."""
import configparser
from pathlib import Path
import httpx

_cfg = configparser.ConfigParser()
_cfg.read(Path(__file__).parent / "config.ini")


def validate(email: str) -> bool:
    hunterio_key = _cfg.get("validation", "hunterio_api_key", fallback="")
    zerobounce_key = _cfg.get("validation", "zerobounce_api_key", fallback="")

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
