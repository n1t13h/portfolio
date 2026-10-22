"""ContactService against the in-memory unit of work, a fake notifier and a hand-moved clock."""

import logging
from datetime import timedelta

import pytest

from app.core.config import Settings
from app.models import ContactMessage
from app.services.contact import (
    NOTIFICATION_BODY_LIMIT,
    RETRY_BATCH,
    ContactService,
    RateLimited,
)
from tests.fakes import FakeClock, FakeNotifier, FakeUnitOfWork


@pytest.fixture
def service(
    fake_uow: FakeUnitOfWork, notifier: FakeNotifier, settings: Settings, clock: FakeClock
) -> ContactService:
    return ContactService(lambda: fake_uow, notifier, settings, clock)


def send(service: ContactService, message: str = "hello", ip: str = "1.1.1.1") -> int:
    return service.submit("Asha", "asha@example.com", message, ip)


def messages(uow: FakeUnitOfWork) -> list[ContactMessage]:
    return list(uow.store.contacts)


# -- submitting ---------------------------------------------------------------------------


def test_a_message_is_stored_before_anyone_is_told(
    service: ContactService, fake_uow: FakeUnitOfWork, notifier: FakeNotifier, clock: FakeClock
) -> None:
    message_id = send(service, "Love the Ujjain set.", ip="2.2.2.2")

    [stored] = messages(fake_uow)
    assert stored.id == message_id
    assert (stored.name, stored.email, stored.message, stored.ip) == (
        "Asha",
        "asha@example.com",
        "Love the Ujjain set.",
        "2.2.2.2",
    )
    assert stored.at == clock.now() and stored.notified is False
    assert notifier.sent == []  # submitting never talks to Telegram
    assert fake_uow.commits == 1


def test_one_ip_is_limited_per_hour_and_released_when_the_hour_passes(
    service: ContactService, clock: FakeClock, settings: Settings
) -> None:
    for _ in range(settings.contact_max_per_hour):
        send(service)
    with pytest.raises(RateLimited):
        send(service)
    assert send(service, ip="9.9.9.9")  # someone else is fine

    clock.advance(3601)
    assert send(service)


def test_everyone_together_is_limited_per_hour_so_rotating_ips_cannot_flood_the_owner(
    service: ContactService, settings: Settings, fake_uow: FakeUnitOfWork
) -> None:
    for i in range(settings.contact_max_per_hour_global):
        send(service, ip=f"10.0.0.{i}")
    with pytest.raises(RateLimited):
        send(service, ip="10.9.9.9")
    assert len(messages(fake_uow)) == settings.contact_max_per_hour_global


def test_a_refused_message_is_not_stored(
    service: ContactService, settings: Settings, fake_uow: FakeUnitOfWork
) -> None:
    for _ in range(settings.contact_max_per_hour):
        send(service)
    with pytest.raises(RateLimited):
        send(service, "one too many")
    assert "one too many" not in [m.message for m in messages(fake_uow)]


# -- telling the owner --------------------------------------------------------------------


def test_pending_messages_are_sent_with_sender_and_text_then_marked_delivered(
    service: ContactService, notifier: FakeNotifier, fake_uow: FakeUnitOfWork
) -> None:
    send(service, "Love the Ujjain set.")
    service.deliver_pending()

    [text] = notifier.sent
    assert "Asha" in text and "asha@example.com" in text and "Love the Ujjain set." in text
    assert messages(fake_uow)[0].notified is True


def test_nothing_is_sent_twice(service: ContactService, notifier: FakeNotifier) -> None:
    send(service)
    service.deliver_pending()
    service.deliver_pending()
    assert len(notifier.sent) == 1


def test_a_failure_leaves_the_message_pending_and_does_not_raise(
    service: ContactService,
    notifier: FakeNotifier,
    fake_uow: FakeUnitOfWork,
    caplog: pytest.LogCaptureFixture,
) -> None:
    send(service)
    notifier.fail = True
    with caplog.at_level(logging.ERROR):
        service.deliver_pending()
    assert messages(fake_uow)[0].notified is False
    assert "could not notify" in caplog.text


def test_a_later_run_delivers_what_failed_oldest_first(
    service: ContactService, notifier: FakeNotifier, fake_uow: FakeUnitOfWork
) -> None:
    send(service, "first")
    send(service, "second")
    notifier.fail = True
    service.deliver_pending()
    notifier.fail = False

    service.deliver_pending()

    assert ["first" in t for t in notifier.sent] == [True, False]
    assert "second" in notifier.sent[1]
    assert all(m.notified for m in messages(fake_uow))


def test_delivery_stops_at_the_first_failure_so_order_is_kept(
    service: ContactService, notifier: FakeNotifier, fake_uow: FakeUnitOfWork
) -> None:
    send(service, "one")
    send(service, "two")
    send(service, "three")
    calls = {"n": 0}
    original = notifier.send

    def fail_on_second(text: str) -> None:
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("telegram down")
        original(text)

    notifier.send = fail_on_second  # type: ignore[method-assign]
    service.deliver_pending()
    assert [m.notified for m in messages(fake_uow)] == [True, False, False]


def test_only_a_batch_is_delivered_per_run(
    service: ContactService,
    notifier: FakeNotifier,
    fake_uow: FakeUnitOfWork,
    settings: Settings,
) -> None:
    settings.contact_max_per_hour = 100
    settings.contact_max_per_hour_global = 100
    for i in range(RETRY_BATCH + 3):
        send(service, f"m{i}")
    service.deliver_pending()
    assert len(notifier.sent) == RETRY_BATCH
    service.deliver_pending()
    assert len(notifier.sent) == RETRY_BATCH + 3


def test_messages_older_than_a_week_are_not_retried(
    service: ContactService, notifier: FakeNotifier, clock: FakeClock
) -> None:
    send(service, "ancient")
    clock.advance(timedelta(days=8).total_seconds())
    service.deliver_pending()
    assert notifier.sent == []


def test_a_very_long_message_is_trimmed_in_the_notification_but_kept_whole_in_storage(
    service: ContactService, notifier: FakeNotifier, fake_uow: FakeUnitOfWork
) -> None:
    send(service, "y" * 5000)
    service.deliver_pending()
    assert len(notifier.sent[0]) <= 4096
    assert notifier.sent[0].count("y") == NOTIFICATION_BODY_LIMIT
    assert len(messages(fake_uow)[0].message) == 5000


# -- overlapping delivery runs ------------------------------------------------------------


def claim_like_another_run(uow: FakeUnitOfWork, message_id: int, clock: FakeClock) -> None:
    with uow:
        assert uow.contacts.claim(message_id, clock.now(), clock.now() - timedelta(minutes=5))
        uow.commit()


def test_a_message_another_run_is_already_delivering_is_not_sent_again(
    service: ContactService,
    notifier: FakeNotifier,
    fake_uow: FakeUnitOfWork,
    clock: FakeClock,
) -> None:
    message_id = send(service)
    claim_like_another_run(fake_uow, message_id, clock)

    service.deliver_pending()

    assert notifier.sent == []
    assert messages(fake_uow)[0].notified is False


def test_if_the_other_run_crashed_the_message_is_delivered_once_its_claim_goes_stale(
    service: ContactService,
    notifier: FakeNotifier,
    fake_uow: FakeUnitOfWork,
    clock: FakeClock,
) -> None:
    message_id = send(service)
    claim_like_another_run(fake_uow, message_id, clock)

    clock.advance(6 * 60)
    service.deliver_pending()

    assert len(notifier.sent) == 1 and messages(fake_uow)[0].notified is True


def test_a_failed_delivery_releases_the_message_so_the_next_run_can_retry_immediately(
    service: ContactService, notifier: FakeNotifier, fake_uow: FakeUnitOfWork
) -> None:
    send(service)
    notifier.fail = True
    service.deliver_pending()
    notifier.fail = False

    service.deliver_pending()  # no 5-minute wait for a claim to expire

    assert len(notifier.sent) == 1 and messages(fake_uow)[0].notified is True


def test_two_runs_back_to_back_still_send_each_message_exactly_once(
    service: ContactService, notifier: FakeNotifier
) -> None:
    send(service, "one")
    send(service, "two")
    service.deliver_pending()
    service.deliver_pending()
    assert len(notifier.sent) == 2
