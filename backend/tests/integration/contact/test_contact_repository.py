"""Repository contract for contact messages."""

from app.models import ContactMessage
from app.uow import AbstractUnitOfWork
from tests.support.builders import at


def message(minutes: int, ip: str = "1.1.1.1", notified: bool = False) -> ContactMessage:
    return ContactMessage(
        at=at(minutes), name="A", email="a@b.co", message=f"m{minutes}", ip=ip, notified=notified
    )


def test_messages_are_counted_after_a_moment_and_optionally_per_ip(uow: AbstractUnitOfWork) -> None:
    with uow:
        for m in (message(0), message(10), message(20, ip="2.2.2.2"), message(30)):
            uow.contacts.add(m)
        uow.commit()
    with uow:
        assert uow.contacts.count_since(at(5)) == 3  # strictly after
        assert uow.contacts.count_since(at(5), ip="1.1.1.1") == 2
        assert uow.contacts.count_since(at(5), ip="9.9.9.9") == 0
        assert uow.contacts.count_since(at(99)) == 0


def test_pending_messages_are_unnotified_recent_oldest_first_and_limited(
    uow: AbstractUnitOfWork,
) -> None:
    with uow:
        uow.contacts.add(message(0))  # too old
        uow.contacts.add(message(10))
        uow.contacts.add(message(20, notified=True))  # already delivered
        uow.contacts.add(message(30))
        uow.contacts.add(message(40))
        uow.commit()
    with uow:
        pending = uow.contacts.list_pending(since=at(5), limit=10)
        assert [m.message for m in pending] == ["m10", "m30", "m40"]
        assert [m.message for m in uow.contacts.list_pending(since=at(5), limit=2)] == [
            "m10",
            "m30",
        ]


def test_a_stored_message_gets_an_id_and_starts_unnotified(uow: AbstractUnitOfWork) -> None:
    with uow:
        stored = ContactMessage(at=at(0), name="A", email="a@b.co", message="hi")
        uow.contacts.add(stored)
        uow.flush()
        assert stored.id is not None
        assert stored.notified is False
