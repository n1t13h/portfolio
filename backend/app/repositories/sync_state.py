"""The single-row state of the Unsplash sync, including its run lock."""

from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy import CursorResult, or_, update
from sqlalchemy.orm import Session

from app.models import SyncState


class AbstractSyncStateRepository(ABC):
    @abstractmethod
    def get_or_create(self) -> SyncState: ...

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
            self._s.flush()
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
