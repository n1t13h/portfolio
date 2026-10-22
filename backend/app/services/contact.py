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
CLAIM_TTL = timedelta(minutes=5)  # a run that has held a message longer is assumed crashed
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
        now = self._clock.now()
        with self._uow() as uow:
            for row in uow.contacts.list_pending(now - RETRY_WINDOW, RETRY_BATCH):
                message_id, text = row.id, format_notification(row)
                if not uow.contacts.claim(message_id, now, now - CLAIM_TTL):
                    continue  # another run is delivering it
                uow.commit()  # make the claim visible to other runs before the slow part
                try:
                    self._notifier.send(text)
                except Exception:
                    log.exception("could not notify about contact message %s", message_id)
                    uow.contacts.release(message_id)
                    uow.commit()
                    return
                uow.contacts.mark_delivered(message_id)
                uow.commit()
