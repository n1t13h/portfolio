"""The audit trail writes into the caller's transaction, so a change and its record stand or fall
together."""

from app.services.audit import NO_AUDIT, AuditTrail
from tests.fakes import FakeClock, FakeUnitOfWork


def test_an_entry_records_what_happened_when_and_from_where(
    fake_uow: FakeUnitOfWork, clock: FakeClock
) -> None:
    with fake_uow as uow:
        AuditTrail(clock, "9.9.9.9").record(uow, "photo.publish", "p1")
        uow.commit()

    [entry] = fake_uow.store.audit
    assert (entry.action, entry.target, entry.ip, entry.at) == (
        "photo.publish",
        "p1",
        "9.9.9.9",
        clock.now(),
    )


def test_target_and_ip_are_optional(fake_uow: FakeUnitOfWork, clock: FakeClock) -> None:
    with fake_uow as uow:
        AuditTrail(clock).record(uow, "photo.reorder")
        uow.commit()
    assert (fake_uow.store.audit[0].target, fake_uow.store.audit[0].ip) == ("", "")


def test_it_never_commits_on_its_own_and_is_lost_if_the_caller_does_not_commit(
    fake_uow: FakeUnitOfWork, clock: FakeClock
) -> None:
    with fake_uow as uow:
        AuditTrail(clock).record(uow, "photo.delete", "p1")
        assert fake_uow.commits == 0
    assert fake_uow.store.audit == []


def test_a_null_trail_records_nothing(fake_uow: FakeUnitOfWork) -> None:
    with fake_uow as uow:
        NO_AUDIT.record(uow, "photo.delete", "p1")
        uow.commit()
    assert fake_uow.store.audit == []
