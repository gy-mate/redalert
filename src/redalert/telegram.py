"""Minimal Telegram Bot API client and Hungarian message formatting."""

import os

import requests

from redalert.scraper import StockLevel

_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramConfigError(RuntimeError):
    """Raised when the required Telegram environment variables are missing."""


def credentials() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    missing = [
        name
        for name, value in (
            ("TELEGRAM_BOT_TOKEN", token),
            ("TELEGRAM_CHAT_ID", chat_id),
        )
        if not value
    ]
    if missing:
        raise TelegramConfigError(
            "Missing required environment variable(s): " + ", ".join(missing)
        )
    assert token is not None and chat_id is not None  # narrowed by the check above
    return token, chat_id


def format_message(low: list[StockLevel], threshold: int) -> str:
    """Build the Hungarian alert message for the low blood types."""
    bullets = "\n".join(
        f"• <b>{level.blood_type}</b>: {level.text}"
        for level in sorted(low, key=lambda lvl: lvl.days)
    )
    return (
        f"🩸 <b>Alacsony vérkészlet</b>\n"
        f"\n"
        f"Az alábbi vércsoport(ok)ból kevesebb, mint"
        f" {threshold} napnyi készlete maradt az OVSZ-nek:\n"
        f"\n"
        f"{bullets}\n"
        f"\n"
        f"Ha teheted, fontold meg a véradást!\n"
        f"\n"
        f"Helyszínek: https://www.ovsz.hu/veradas"
    )


def send_message(text: str, timeout: float = 30.0) -> None:
    """Send a message to the configured chat using the bot token."""
    token, chat_id = credentials()
    response = requests.post(
        _API_URL.format(token=token),
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=timeout,
    )
    response.raise_for_status()
