"""Zyranet Telegram bot: /buy voucher, plan buttons, payment/delivery."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app import models, schemas
from app.config import get_settings
from app.db import async_session
from app.services import vouchers as vsvc
from app.services.payments import get_provider
from app.services.telegram import send_voucher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("zyranet.bot")

settings = get_settings()


def get_bot() -> Bot:
    """Build the Bot lazily so the module imports without a valid token."""
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    return Bot(token=settings.telegram_bot_token)


dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message) -> None:
    log.info("start from %s", message.from_user.username or message.from_user.id)
    await message.reply(
        "Welcome to Zyranet Wi-Fi vouchers.\n\n"
        "Buy with /buy. Each voucher is one-time, single-user, and expires.\n"
        "Get help with /help."
    )


@dp.message(Command("help"))
async def help_cmd(message: Message) -> None:
    await message.reply(
        "Commands:\n"
        "/buy — list plans and pick one\n"
        "/status — check your active vouchers"
    )


@dp.message(Command("status"))
async def status(message: Message) -> None:
    async with async_session() as session:
        u = await session.scalar(
            select(models.User).where(models.User.telegram_id == message.from_user.id)
        )
        if u is None:
            await message.reply("No vouchers yet. Use /buy.")
            return
        rows = (
            await session.scalars(
                select(models.Voucher)
                .where(models.Voucher.user_id == u.id)
                .order_by(models.Voucher.created_at.desc())
            )
        ).all()
    if not rows:
        await message.reply("No vouchers yet. Use /buy.")
        return
    lines = [
        f"`{v.code}` — {v.plan.name} — {v.status.value}" for v in rows if v.status.value != "unused"
    ]
    await message.reply(
        "\n".join(lines[:10]) or "No active vouchers yet. Use /buy.",
        parse_mode="Markdown",
    )


@dp.message(Command("buy"))
async def buy(message: Message) -> None:
    async with async_session() as session:
        plans = list(
            (await session.scalars(select(models.Plan).where(models.Plan.active.is_(True)))).all()
        )
    if not plans:
        await message.reply("No plans available right now.")
        return
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    kb = InlineKeyboardBuilder()
    for p in plans:
        price = f"{p.price_kobo / 100:,.0f}"
        kb.button(text=f"{p.name} — ₦{price}", callback_data=f"plan:{p.name}")
    kb.adjust(1)
    await message.reply("Choose a plan:", reply_markup=kb.as_markup())


@dp.callback_query(F.data.startswith("plan:"))
async def on_plan(callback: CallbackQuery) -> None:
    plan_name = callback.data.split(":", 1)[1]
    user = callback.from_user
    log.info("plan chosen %s by %s", plan_name, user.username or user.id)
    try:
        async with async_session() as session:
            u = await session.scalar(select(models.User).where(models.User.telegram_id == user.id))
            if u is None:
                u = models.User(
                    telegram_id=user.id,
                    telegram_username=user.username,
                    telegram_name=user.full_name,
                )
                session.add(u)
                await session.flush()
            txn = await vsvc.create_purchase(
                session,
                schemas.PurchaseRequest(
                    plan_name=plan_name, telegram_chat_id=user.id, provider="flutterwave"
                ),
                user_id=u.id,
            )

        if settings.has_payment_keys:
            provider = get_provider(txn.provider.value)
            init = await provider.initialize(
                reference=txn.provider_ref,
                amount_kobo=txn.amount_kobo,
                currency=txn.currency,
                customer_email=provider.normalize_email(u.phone, user.username),
                phone=u.phone,
                metadata={"telegram_id": user.id, "voucher_id": txn.voucher_id},
            )
            await callback.message.answer(  # type: ignore[union-attr]
                f"Plan: {plan_name}\n"
                f"Ref: {txn.provider_ref}\n\n"
                f"Pay here to activate your voucher:\n{init.checkout_url}"
            )
        else:
            # Dev mode (no payment keys): activate immediately + deliver the code.
            async with async_session() as session:
                voucher = await vsvc.activate_on_success(session, txn.voucher_id)
            await send_voucher(user.id, voucher.code, plan_name, str(voucher.valid_until))
            await callback.message.answer("Voucher issued. Check the code in the message above.")
    except Exception as exc:  # pragma: no cover - surfaced to user
        log.exception("plan handler failed")
        await callback.message.answer(f"Something went wrong: {exc}")  # type: ignore[union-attr]


async def main() -> None:
    bot = get_bot()
    me = await bot.get_me()
    log.info("bot running as @%s", me.username)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
