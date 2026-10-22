"""Messages sent through the public contact form."""

from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy import CursorResult, func, or_, select, update
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

    @abstractmethod
    def claim(self, message_id: int, now: datetime, stale_before: datetime) -> bool:
        """Take the right to deliver this message: True for exactly one caller at a time.

        Fails if it was delivered already or claimed after `stale_before` (a run that crashed
        mid-delivery loses its claim once it is that old). Must be atomic.
        """

    @abstractmethod
    def release(self, message_id: int) -> None:
        """Give the claim back after a failed delivery so the next run can retry at once."""

    @abstractmethod
    def mark_delivered(self, message_id: int) -> None: ...


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

    def claim(self, message_id: int, now: datetime, stale_before: datetime) -> bool:
        claimed: CursorResult[tuple[()]] = self._s.execute(  # type: ignore[assignment]
            update(ContactMessage)
            .where(
                ContactMessage.id == message_id,
                ContactMessage.notified.is_(False),
                or_(ContactMessage.claimed_at.is_(None), ContactMessage.claimed_at < stale_before),
            )
            .values(claimed_at=now)
        )
        return claimed.rowcount == 1

    def release(self, message_id: int) -> None:
        self._s.execute(
            update(ContactMessage).where(ContactMessage.id == message_id).values(claimed_at=None)
        )

    def mark_delivered(self, message_id: int) -> None:
        self._s.execute(
            update(ContactMessage)
            .where(ContactMessage.id == message_id)
            .values(notified=True, claimed_at=None)
        )

    def list_pending(self, since: datetime, limit: int) -> list[ContactMessage]:
        stmt = (
            select(ContactMessage)
            .where(ContactMessage.notified.is_(False), ContactMessage.at > since)
            .order_by(ContactMessage.id)
            .limit(limit)
        )
        return list(self._s.scalars(stmt))
