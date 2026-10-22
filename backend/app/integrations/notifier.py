"""Notifications to the site owner (Telegram) behind a one-method interface."""

import logging
from typing import Protocol

import httpx

from app.core.config import Settings

log = logging.getLogger(__name__)

TELEGRAM_TEXT_LIMIT = 4096
TIMEOUT_SECONDS = 5.0


class NotificationFailed(Exception):
    """Delivery failed. The message omits the request URL, which contains the bot token."""


class Notifier(Protocol):
    def send(self, text: str) -> None:
        """Deliver `text`, raising on any failure so the caller can retry later."""
        ...


class TelegramNotifier:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        # httpx logs every request URL at INFO, and this URL contains the bot token.
        for noisy in ("httpx", "httpcore"):
            logging.getLogger(noisy).setLevel(logging.WARNING)
        self._url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        self._chat_id = settings.telegram_chat_id
        self._transport = transport

    def send(self, text: str) -> None:
        # Plain text on purpose: no parse_mode, so visitor-supplied text cannot inject markup.
        payload = {"chat_id": self._chat_id, "text": text[:TELEGRAM_TEXT_LIMIT]}
        try:
            with httpx.Client(timeout=TIMEOUT_SECONDS, transport=self._transport) as client:
                client.post(self._url, json=payload).raise_for_status()
        except httpx.HTTPStatusError as exc:
            # httpx puts the full URL, token included, in its messages; keep only the status.
            raise NotificationFailed(f"telegram answered HTTP {exc.response.status_code}") from None
        except httpx.HTTPError as exc:
            raise NotificationFailed(f"telegram unreachable ({type(exc).__name__})") from None


class NullNotifier:
    """Used when Telegram is not configured (local development)."""

    def send(self, text: str) -> None:
        log.warning("Telegram not configured; notification not sent")
        raise RuntimeError("telegram is not configured")


def build_notifier(settings: Settings) -> Notifier:
    if settings.telegram_bot_token and settings.telegram_chat_id:
        return TelegramNotifier(settings)
    return NullNotifier()
