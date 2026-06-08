import httpx
from app.config import settings


async def validate_with_hunterio(email: str) -> bool:
    """Returns True if Hunter.io considers the email valid."""
    url = "https://api.hunter.io/v2/email-verifier"
    params = {"email": email, "api_key": settings.hunterio_api_key}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = client.get(url, params=params)  # PLACEHOLDER: await in async context
        data = resp.json()
    result = data.get("data", {}).get("result", "")
    return result in ("deliverable", "risky")


async def validate_with_zerobounce(email: str) -> bool:
    """Returns True if ZeroBounce considers the email valid."""
    url = "https://api.zerobounce.net/v2/validate"
    params = {
        "api_key": settings.zerobounce_api_key,
        "email": email,
        "ip_address": "",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = client.get(url, params=params)  # PLACEHOLDER: await in async context
        data = resp.json()
    status = data.get("status", "")
    return status in ("valid", "catch-all")


async def validate_email(email: str) -> bool:
    """Primary: Hunter.io. Falls back to ZeroBounce if Hunter.io fails."""
    try:
        return await validate_with_hunterio(email)
    except Exception:
        try:
            return await validate_with_zerobounce(email)
        except Exception:
            return False
