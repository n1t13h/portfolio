"""Repository contract for contact messages."""

from datetime import timedelta

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


# -- claiming a message before telling the owner (so two runs never both send it) ----------

CLAIM_TTL = timedelta(minutes=5)


def stored_id(uow: AbstractUnitOfWork, minutes: int = 10) -> int:
    with uow:
        row = message(minutes)
        uow.contacts.add(row)
        uow.commit()
        return row.id


def test_a_free_message_can_be_claimed_once(uow: AbstractUnitOfWork) -> None:
    message_id = stored_id(uow)
    with uow:
        assert uow.contacts.claim(message_id, at(20), at(20) - CLAIM_TTL) is True
        uow.commit()
    with uow:
        assert uow.contacts.claim(message_id, at(21), at(21) - CLAIM_TTL) is False


def test_a_claim_from_a_crashed_run_can_be_taken_over_once_stale(uow: AbstractUnitOfWork) -> None:
    message_id = stored_id(uow)
    with uow:
        assert uow.contacts.claim(message_id, at(20), at(20) - CLAIM_TTL)
        uow.commit()
    with uow:
        later = at(20) + timedelta(minutes=6)
        assert uow.contacts.claim(message_id, later, later - CLAIM_TTL) is True


def test_a_released_message_can_be_claimed_again_at_once(uow: AbstractUnitOfWork) -> None:
    message_id = stored_id(uow)
    with uow:
        assert uow.contacts.claim(message_id, at(20), at(20) - CLAIM_TTL)
        uow.contacts.release(message_id)
        uow.commit()
    with uow:
        assert uow.contacts.claim(message_id, at(20), at(20) - CLAIM_TTL) is True


def test_a_delivered_message_cannot_be_claimed_and_is_no_longer_pending(
    uow: AbstractUnitOfWork,
) -> None:
    message_id = stored_id(uow)
    with uow:
        assert uow.contacts.claim(message_id, at(20), at(20) - CLAIM_TTL)
        uow.contacts.mark_delivered(message_id)
        uow.commit()
    with uow:
        assert uow.contacts.claim(message_id, at(99), at(99) - CLAIM_TTL) is False
        assert uow.contacts.list_pending(since=at(0), limit=10) == []


def test_claiming_an_unknown_message_is_refused(uow: AbstractUnitOfWork) -> None:
    with uow:
        assert uow.contacts.claim(12345, at(0), at(0) - CLAIM_TTL) is False
