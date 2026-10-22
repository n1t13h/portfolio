"""The audit log: who did what, when and from where."""

from app.core.clock import Clock
from app.models import AuditLog
from app.uow import UnitOfWorkFactory


def entry(clock: Clock, action: str, target: str = "", ip: str = "") -> AuditLog:
    """An audit row, for services that record it inside their own transaction."""
    return AuditLog(at=clock.now(), action=action, target=target, ip=ip)


class AuditService:
    """Records one entry in its own transaction (for admin actions that already committed)."""

    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow = uow_factory
        self._clock = clock

    def record(self, action: str, target: str = "", ip: str = "") -> None:
        with self._uow() as uow:
            uow.audit.add(entry(self._clock, action, target, ip))
            uow.commit()
