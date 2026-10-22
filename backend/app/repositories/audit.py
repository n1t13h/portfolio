"""Append-only audit log."""

from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog


class AbstractAuditRepository(ABC):
    @abstractmethod
    def add(self, entry: AuditLog) -> None: ...

    @abstractmethod
    def has_login_from(self, ip: str, since: datetime) -> bool:
        """Whether a successful login came from this IP at or after `since`."""


class SqlAlchemyAuditRepository(AbstractAuditRepository):
    def __init__(self, session: Session) -> None:
        self._s = session

    def add(self, entry: AuditLog) -> None:
        self._s.add(entry)

    def has_login_from(self, ip: str, since: datetime) -> bool:
        found = self._s.scalars(
            select(AuditLog.id).where(
                AuditLog.action == "login", AuditLog.ip == ip, AuditLog.at >= since
            )
        ).first()
        return found is not None
