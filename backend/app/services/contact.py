"""Contact form: store every message first, then tell the owner; retry what failed."""

import logging
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.clock import Clock
from app.core.config import Settings
from app.integrations.notifier import Notifier
from app.models import ContactMessage

log = logging.getLogger(__name__)

RETRY_WINDOW = timedelta(days=7)
RETRY_BATCH = 10
NOTIFICATION_BODY_LIMIT = 3900  # leaves room for the header inside Telegram's 4096


class RateLimited(Exception):
    """Too many messages from this IP, or from everyone, in the last hour."""


def format_notification(row: ContactMessage) -> str:
    body = row.message[:NOTIFICATION_BODY_LIMIT]
    return f"New message on the portfolio\nFrom: {row.name} <{row.email}>\n\n{body}"


class ContactService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        notifier: Notifier,
        settings: Settings,
        clock: Clock,
    ) -> None:
        self._sessions = sessions
        self._notifier = notifier
        self._settings = settings
        self._clock = clock

    def submit(self, name: str, email: str, message: str, ip: str) -> int:
        """Save a message and return its id. Raises RateLimited when over the limits."""
        now = self._clock.now()
        since = now - timedelta(hours=1)
        with self._sessions() as db:
            if self._recent_count(db, since, ip) >= self._settings.contact_max_per_hour:
                raise RateLimited
            if self._recent_count(db, since) >= self._settings.contact_max_per_hour_global:
                raise RateLimited
            row = ContactMessage(at=now, name=name, email=email, message=message, ip=ip)
            db.add(row)
            db.commit()
            return row.id

    @staticmethod
    def _recent_count(db: Session, since: datetime, ip: str | None = None) -> int:
        stmt = select(func.count()).select_from(ContactMessage).where(ContactMessage.at > since)
        if ip is not None:
            stmt = stmt.where(ContactMessage.ip == ip)
        return db.scalar(stmt) or 0

    def deliver_pending(self) -> None:
        """Notify about every message not yet delivered (oldest first); stop at the first failure.

        Runs after each submission, so a Telegram outage is retried by the next visitor's message.
        """
        since = self._clock.now() - RETRY_WINDOW
        with self._sessions() as db:
            stmt = (
                select(ContactMessage)
                .where(ContactMessage.notified.is_(False), ContactMessage.at > since)
                .order_by(ContactMessage.id)
                .limit(RETRY_BATCH)
            )
            for row in db.scalars(stmt):
                try:
                    self._notifier.send(format_notification(row))
                except Exception:
                    log.exception("could not notify about contact message %s", row.id)
                    return
                row.notified = True
                db.commit()
