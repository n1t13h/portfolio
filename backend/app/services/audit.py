"""The audit log: who did what, when and from where.

Entries are written into the *caller's* transaction, so a change and its record are saved
together or not at all.
"""

from app.core.clock import Clock, SystemClock
from app.models import AuditLog
from app.uow import AbstractUnitOfWork


class AuditTrail:
    """Records admin actions for one request (its client IP is fixed when it is built)."""

    def __init__(self, clock: Clock, ip: str = "") -> None:
        self._clock = clock
        self._ip = ip

    def record(self, uow: AbstractUnitOfWork, action: str, target: str = "") -> None:
        """Add an entry to `uow`. The caller commits; nothing is saved if it does not."""
        uow.audit.add(AuditLog(at=self._clock.now(), action=action, target=target, ip=self._ip))


class _NullAuditTrail(AuditTrail):
    """For work that is not an admin action (CLI, scheduled sync, seed): records nothing."""

    def __init__(self) -> None:
        super().__init__(SystemClock())

    def record(self, uow: AbstractUnitOfWork, action: str, target: str = "") -> None:
        return None


NO_AUDIT = _NullAuditTrail()
