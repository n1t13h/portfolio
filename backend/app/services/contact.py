"""Contact form: store every message first, then tell the owner; retry what failed."""

import logging
from datetime import timedelta

from app.core.clock import Clock
from app.core.config import Settings
from app.integrations.notifier import Notifier
from app.models import ContactMessage
from app.uow import UnitOfWorkFactory

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
        uow_factory: UnitOfWorkFactory,
        notifier: Notifier,
        settings: Settings,
        clock: Clock,
    ) -> None:
        self._uow = uow_factory
        self._notifier = notifier
        self._settings = settings
        self._clock = clock

    def submit(self, name: str, email: str, message: str, ip: str) -> int:
        """Save a message and return its id. Raises RateLimited when over the limits."""
        now = self._clock.now()
        since = now - timedelta(hours=1)
        with self._uow() as uow:
            if uow.contacts.count_since(since, ip) >= self._settings.contact_max_per_hour:
                raise RateLimited
            if uow.contacts.count_since(since) >= self._settings.contact_max_per_hour_global:
                raise RateLimited
            row = ContactMessage(at=now, name=name, email=email, message=message, ip=ip)
            uow.contacts.add(row)
            uow.commit()
            return row.id

    def deliver_pending(self) -> None:
        """Notify about every message not yet delivered (oldest first); stop at the first failure.

        Runs after each submission and from a timer, so a Telegram outage is retried.
        """
        since = self._clock.now() - RETRY_WINDOW
        with self._uow() as uow:
            for row in uow.contacts.list_pending(since, RETRY_BATCH):
                try:
                    self._notifier.send(format_notification(row))
                except Exception:
                    log.exception("could not notify about contact message %s", row.id)
                    return
                row.notified = True
                uow.commit()
