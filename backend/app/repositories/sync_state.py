"""The single-row state of the Unsplash sync, including its run lock."""

from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy import CursorResult, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import Conflict
from app.models import SyncState


class AbstractSyncStateRepository(ABC):
    @abstractmethod
    def get_or_create(self) -> SyncState:
        """The single state row, creating it if needed.

        Raises `Conflict` if another process created it at the same moment; the caller should
        roll back and ask again.
        """

    @abstractmethod
    def try_acquire(self, now: datetime, stale_before: datetime) -> bool:
        """Take the run lock if it is free, or was taken before `stale_before` (a crashed run).

        Must be atomic: with two callers racing, exactly one gets True.
        """


class SqlAlchemySyncStateRepository(AbstractSyncStateRepository):
    def __init__(self, session: Session) -> None:
        self._s = session

    def get_or_create(self) -> SyncState:
        row = self._s.get(SyncState, 1)
        if row is None:
            row = SyncState(id=1, pending={}, skipped={})
            self._s.add(row)
            try:
                self._s.flush()
            except IntegrityError as exc:  # a concurrent process inserted id=1 first
                raise Conflict("the sync state was created concurrently") from exc
        return row

    def try_acquire(self, now: datetime, stale_before: datetime) -> bool:
        claimed: CursorResult[tuple[()]] = self._s.execute(  # type: ignore[assignment]
            update(SyncState)
            .where(
                SyncState.id == 1,
                or_(SyncState.running.is_(False), SyncState.last_started_at < stale_before),
            )
            .values(running=True, last_started_at=now)
        )
        return claimed.rowcount == 1
