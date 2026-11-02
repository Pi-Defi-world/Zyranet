"""SMS fallback delivery via Termii."""
from __future__ import annotations

import httpx

from ..config import get_settings

_TIMEOUT = httpx.Timeout(15.0)


async def send_otp(phone: str, message: str) -> None:
    """Send an SMS via Termii. Best-effort; failures are non-fatal."""
    s = get_settings()
    if not s.termii_api_key or not s.termii_sender_id:
        return
    payload = {
        "api_key": s.termii_api_key,
        "to": phone,
        "from": s.termii_sender_id,
        "sms": message,
        "type": "plain",
        "channel": "generic",
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post("https://api.ng.termii.com/api/sms/send", json=payload)
        resp.raise_for_status()
