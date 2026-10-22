"""Append-only audit log."""

from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.models import AuditLog


class AbstractAuditRepository(ABC):
    @abstractmethod
    def add(self, entry: AuditLog) -> None: ...


class SqlAlchemyAuditRepository(AbstractAuditRepository):
    def __init__(self, session: Session) -> None:
        self._s = session

    def add(self, entry: AuditLog) -> None:
        self._s.add(entry)
