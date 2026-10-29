"""Send voucher codes / notifications to a Telegram chat via the bot token."""
from __future__ import annotations

import httpx

from ..config import get_settings

_TIMEOUT = httpx.Timeout(15.0)


async def send_message(chat_id: int | str, text: str, parse_mode: str | None = None) -> bool:
    s = get_settings()
    if not s.telegram_bot_token:
        return False
    url = f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage"
    payload: dict = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        return resp.status_code == 200


async def send_voucher(chat_id: int | str, code: str, plan_name: str, valid_until: str) -> bool:
    info = (
        f"✅ Payment confirmed!\n\n"
        f"Plan: {plan_name}\n"
        f"Valid until: {valid_until}\n\n"
        "Connect to the Wi-Fi and enter this code:"
    )
    await send_message(chat_id, info)
    # Send code alone so users can long-press to copy
    await send_message(chat_id, code)
    return True
