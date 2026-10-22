"""Messages sent through the public contact form."""

from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ContactMessage


class AbstractContactRepository(ABC):
    @abstractmethod
    def add(self, message: ContactMessage) -> None: ...

    @abstractmethod
    def count_since(self, since: datetime, ip: str | None = None) -> int:
        """Messages stored after `since`, optionally only from one IP."""

    @abstractmethod
    def list_pending(self, since: datetime, limit: int) -> list[ContactMessage]:
        """Messages the owner has not been told about yet, oldest first."""


class SqlAlchemyContactRepository(AbstractContactRepository):
    def __init__(self, session: Session) -> None:
        self._s = session

    def add(self, message: ContactMessage) -> None:
        self._s.add(message)

    def count_since(self, since: datetime, ip: str | None = None) -> int:
        stmt = select(func.count()).select_from(ContactMessage).where(ContactMessage.at > since)
        if ip is not None:
            stmt = stmt.where(ContactMessage.ip == ip)
        return self._s.scalar(stmt) or 0

    def list_pending(self, since: datetime, limit: int) -> list[ContactMessage]:
        stmt = (
            select(ContactMessage)
            .where(ContactMessage.notified.is_(False), ContactMessage.at > since)
            .order_by(ContactMessage.id)
            .limit(limit)
        )
        return list(self._s.scalars(stmt))
