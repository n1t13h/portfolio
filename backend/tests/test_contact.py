import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db import Base, make_engine, make_session_factory
from app.integrations.notifier import (
    NotificationFailed,
    NullNotifier,
    TelegramNotifier,
    build_notifier,
)
from app.models import ContactMessage
from app.services.contact import ContactService, RateLimited
from tests.fakes import FakeClock, FakeNotifier

VALID = {"name": "Asha", "email": "asha@example.com", "message": "Love the Ujjain set."}


def rows(db: Session) -> list[ContactMessage]:
    db.expire_all()
    return list(db.scalars(select(ContactMessage).order_by(ContactMessage.id)))


def test_message_saved_and_notified(
    client: TestClient, notifier: FakeNotifier, db: Session
) -> None:
    resp = client.post("/contact", json=VALID)
    assert resp.status_code == 202
    [row] = rows(db)
    assert (row.name, row.email, row.message, row.notified) == (*VALID.values(), True)
    [text] = notifier.sent
    assert "Asha" in text and "asha@example.com" in text and "Love the Ujjain set." in text


def test_notifier_failure_still_saves_and_returns_2xx(
    client: TestClient, notifier: FakeNotifier, db: Session
) -> None:
    notifier.fail = True
    resp = client.post("/contact", json=VALID)
    assert resp.status_code == 202
    [row] = rows(db)
    assert row.notified is False


def test_failed_notification_is_retried_on_next_submission(
    client: TestClient, notifier: FakeNotifier, db: Session
) -> None:
    notifier.fail = True
    client.post("/contact", json=VALID)
    notifier.fail = False
    client.post("/contact", json={**VALID, "message": "Second one"})
    assert [r.notified for r in rows(db)] == [True, True]
    assert len(notifier.sent) == 2
    assert "Love the Ujjain set." in notifier.sent[0]  # oldest delivered first


def test_honeypot_filled_returns_2xx_but_saves_nothing(
    client: TestClient, notifier: FakeNotifier, db: Session
) -> None:
    resp = client.post("/contact", json={**VALID, "website": "http://spam.example"})
    assert resp.status_code == 202
    assert rows(db) == []
    assert notifier.sent == []


def test_rate_limit_per_ip(client: TestClient, clock: FakeClock) -> None:
    for _ in range(5):
        assert client.post("/contact", json=VALID).status_code == 202
    assert client.post("/contact", json=VALID).status_code == 429
    clock.advance(3601)
    assert client.post("/contact", json=VALID).status_code == 202


def test_global_cap_across_ips(
    client: TestClient, settings: Settings, clock: FakeClock, notifier: FakeNotifier
) -> None:
    service = ContactService(client.app.state.session_factory, notifier, settings, clock)  # type: ignore[attr-defined]
    for i in range(settings.contact_max_per_hour_global):
        service.submit("A", "a@b.co", "hi", ip=f"10.0.0.{i}")
    with pytest.raises(RateLimited):
        service.submit("A", "a@b.co", "hi", ip="10.9.9.9")


@pytest.mark.parametrize(
    "patch",
    [
        {"message": "x" * 5001},
        {"message": "   "},
        {"name": ""},
        {"name": "n" * 101},
        {"email": "not-an-email"},
        {"email": "a@b"},
        {"email": "a b@c.com"},
    ],
)
def test_invalid_input_rejected(client: TestClient, db: Session, patch: dict[str, str]) -> None:
    assert client.post("/contact", json={**VALID, **patch}).status_code == 422
    assert rows(db) == []


def test_long_message_is_truncated_in_the_notification_not_in_the_database(
    client: TestClient, notifier: FakeNotifier, db: Session
) -> None:
    client.post("/contact", json={**VALID, "message": "y" * 5000})
    assert len(notifier.sent[0]) <= 4096
    assert len(rows(db)[0].message) == 5000


def test_contact_needs_no_login_or_csrf_header(client: TestClient) -> None:
    assert "X-CSRF" not in client.headers
    assert client.post("/contact", json=VALID).status_code == 202


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


def test_bot_token_never_reaches_the_logs(
    client: TestClient,
    settings: Settings,
    caplog: pytest.LogCaptureFixture,
    clock: FakeClock,
    db: Session,
) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach {request.url}")

    for transport in (
        httpx.MockTransport(lambda r: httpx.Response(500)),
        httpx.MockTransport(refuse),
    ):
        caplog.clear()
        service = ContactService(
            client.app.state.session_factory,  # type: ignore[attr-defined]
            _telegram(settings, transport),
            settings,
            clock,
        )
        service.submit("A", "a@b.co", "hello", ip="1.2.3.4")
        with caplog.at_level("DEBUG"):
            service.deliver_pending()
        assert "123:ABC" not in caplog.text
        assert "could not notify" in caplog.text  # it was logged, just without the secret
        db.query(ContactMessage).delete()
        db.commit()


def test_build_notifier_is_null_without_credentials(settings: Settings) -> None:
    assert isinstance(build_notifier(settings), NullNotifier)
    configured = settings.model_copy(update={"telegram_bot_token": "t", "telegram_chat_id": "1"})
    assert isinstance(build_notifier(configured), TelegramNotifier)


def test_notify_pending_command_delivers_messages_a_visitor_never_retriggered(
    tmp_path: Path, settings: Settings
) -> None:
    from app.cli import notify_pending

    file_settings = settings.model_copy(update={"database_url": f"sqlite:///{tmp_path / 'c.db'}"})
    engine = make_engine(file_settings.database_url)
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as db:
        db.add(ContactMessage(at=FakeClock().now(), name="A", email="a@b.co", message="hi"))
        db.commit()

    fake = FakeNotifier()
    assert notify_pending(file_settings, notifier=fake, clock=FakeClock()) == 0

    assert len(fake.sent) == 1
    with make_session_factory(engine)() as db:
        assert db.query(ContactMessage).one().notified is True
