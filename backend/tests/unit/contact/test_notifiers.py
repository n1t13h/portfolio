import json

import httpx
import pytest

from app.core.config import Settings
from app.integrations.notifier import (
    NotificationFailed,
    NullNotifier,
    TelegramNotifier,
    build_notifier,
)

# -- the Telegram adapter ----------------------------------------------------------------


def _telegram(settings: Settings, handler: httpx.MockTransport) -> TelegramNotifier:
    configured = settings.model_copy(
        update={"telegram_bot_token": "123:ABC", "telegram_chat_id": "42"}
    )
    return TelegramNotifier(configured, transport=handler)


def test_telegram_notifier_posts_plain_text_to_the_bot_api(settings: Settings) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    _telegram(settings, httpx.MockTransport(handler)).send("hello <b>there</b>")
    [request] = seen
    assert str(request.url) == "https://api.telegram.org/bot123:ABC/sendMessage"
    assert json.loads(request.content) == {"chat_id": "42", "text": "hello <b>there</b>"}


def test_telegram_notifier_raises_a_clean_error_on_http_failure(settings: Settings) -> None:
    notifier = _telegram(settings, httpx.MockTransport(lambda r: httpx.Response(500)))
    with pytest.raises(NotificationFailed, match="HTTP 500"):
        notifier.send("x")


def test_build_notifier_is_null_without_credentials(settings: Settings) -> None:
    assert isinstance(build_notifier(settings), NullNotifier)
    configured = settings.model_copy(update={"telegram_bot_token": "t", "telegram_chat_id": "1"})
    assert isinstance(build_notifier(configured), TelegramNotifier)
