from app.services.audit import AuditService
from tests.fakes import FakeClock, FakeUnitOfWork


def test_an_audit_entry_records_what_happened_when_and_from_where(
    fake_uow: FakeUnitOfWork, clock: FakeClock
) -> None:
    AuditService(lambda: fake_uow, clock).record("photo.publish", "p1", "9.9.9.9")
    [entry] = fake_uow.store.audit
    assert (entry.action, entry.target, entry.ip, entry.at) == (
        "photo.publish",
        "p1",
        "9.9.9.9",
        clock.now(),
    )
    assert fake_uow.commits == 1


def test_target_and_ip_are_optional(fake_uow: FakeUnitOfWork, clock: FakeClock) -> None:
    AuditService(lambda: fake_uow, clock).record("photo.reorder")
    assert (fake_uow.store.audit[0].target, fake_uow.store.audit[0].ip) == ("", "")
