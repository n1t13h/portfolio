"""Incremental Unsplash -> R2 sync. New photos arrive as drafts for the admin to review.

How it stays cheap: the listing is newest-first, so a normal run stops at the first photo it
already has. Work that could not finish (rate limit, a bad file) is remembered in
`sync_state.pending`, so stopping at that boundary never loses a photo.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import CursorResult, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.clock import Clock
from app.core.config import Settings
from app.integrations.storage import Storage
from app.integrations.unsplash import RateLimited, UnsplashClient
from app.models import Photo, SyncState
from app.services.photos import PhotoService
from app.services.sync_state import state_row
from app.uow import SqlAlchemyUnitOfWork

log = logging.getLogger(__name__)

STALE_LOCK = timedelta(hours=1)  # a run older than this is assumed to have crashed
MAX_FAILURES = 3
REQUESTS_PER_PHOTO = 2  # details + download tracking (the file itself is not counted)


class SyncAlreadyRunning(Exception):
    pass


@dataclass(frozen=True)
class SyncResult:
    imported: int
    stopped_early: bool
    error: str | None


@dataclass(frozen=True)
class SyncStatus:
    running: bool
    last_started_at: datetime | None
    last_finished_at: datetime | None
    last_imported: int
    last_error: str | None
    rate_limit_remaining: int | None
    pending: int


@dataclass
class _Progress:
    pending: dict[str, int]
    skipped: dict[str, str]
    imported: int = 0
    stopped_early: bool = False

    def __post_init__(self) -> None:
        self.errors: list[str] = []


class SyncService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        client: UnsplashClient,
        storage: Storage,
        settings: Settings,
        clock: Clock,
    ) -> None:
        self._sessions = sessions
        self._client = client
        self._storage = storage
        self._settings = settings
        self._clock = clock

    # -- locking --------------------------------------------------------------------------

    def acquire(self) -> None:
        """Take the run lock, or raise SyncAlreadyRunning. Atomic across processes."""
        now = self._clock.now()
        with self._sessions() as db:
            try:
                state_row(db)
                db.commit()
            except IntegrityError:  # another process created the row first
                db.rollback()
            claimed: CursorResult[Any] = db.execute(  # type: ignore[assignment]
                update(SyncState)
                .where(
                    SyncState.id == 1,
                    or_(SyncState.running.is_(False), SyncState.last_started_at < now - STALE_LOCK),
                )
                .values(running=True, last_started_at=now)
            )
            db.commit()
            if claimed.rowcount != 1:
                raise SyncAlreadyRunning

    def status(self) -> SyncStatus:
        with self._sessions() as db:
            row = state_row(db)
            db.commit()
            started = row.last_started_at
            fresh = started is not None and _aware(started) > self._clock.now() - STALE_LOCK
            return SyncStatus(
                running=row.running and fresh,
                last_started_at=started,
                last_finished_at=row.last_finished_at,
                last_imported=row.last_imported,
                last_error=row.last_error,
                rate_limit_remaining=row.rate_limit_remaining,
                pending=len(row.pending),
            )

    # -- running --------------------------------------------------------------------------

    def run(self, full: bool = False) -> SyncResult:
        self.acquire()
        return self.execute(full)

    def execute(self, full: bool = False) -> SyncResult:
        """Do the sync. The caller must hold the lock (see `acquire`). Never raises."""
        with self._sessions() as db:
            row = state_row(db)
            skipped = dict(row.skipped)
            if full:  # a full resync retries failures, but never what the admin deleted
                skipped = {k: v for k, v in skipped.items() if v != "failed"}
            progress = _Progress(pending=dict(row.pending), skipped=skipped)
            db.commit()
        try:
            self._import_new(full, progress)
        except Exception as exc:
            log.exception("sync crashed")
            progress.errors.append(f"sync crashed: {exc}")
        finally:
            result = self._finish(progress)  # always release the lock, even on Ctrl-C
        return result

    def _import_new(self, full: bool, progress: _Progress) -> None:
        with self._sessions() as db:
            known = {u for u in db.scalars(select(Photo.unsplash_id)) if u}
            found: list[str] = []
            try:
                self._discover(known, progress, full, found)
            except RateLimited:
                progress.stopped_early = True
            # Oldest first: earlier-pending photos, then the newly found ones in reverse.
            queue = [*progress.pending, *reversed(found)]
            for unsplash_id in queue:
                progress.pending.setdefault(unsplash_id, 0)
            photos = PhotoService(
                lambda: SqlAlchemyUnitOfWork(self._sessions), self._storage, self._settings
            )
            for unsplash_id in dict.fromkeys(queue):
                remaining = self._client.rate_limit_remaining
                if remaining is not None and remaining < REQUESTS_PER_PHOTO:
                    progress.stopped_early = True
                    return
                if not self._import_one(photos, unsplash_id, progress):
                    return

    def _discover(self, known: set[str], progress: _Progress, full: bool, found: list[str]) -> None:
        page = 1
        while True:
            batch = self._client.list_latest(page)
            for summary in batch:
                if summary.id in known:
                    if not full:
                        return  # everything older is already imported
                    continue
                if summary.id not in progress.pending and summary.id not in progress.skipped:
                    found.append(summary.id)
            if len(batch) < self._client.per_page:
                return
            page += 1

    def _import_one(self, photos: PhotoService, unsplash_id: str, progress: _Progress) -> bool:
        """Import one photo. Returns False when the run must stop (rate limited)."""
        try:
            photo = self._client.get_photo(unsplash_id)
            data = self._client.download_original(photo)
            photos.ingest_jpeg(
                data,
                title=photo.title,
                place=photo.place,
                unsplash_id=photo.id,
                unsplash_url=photo.html_url,
            )
        except RateLimited:
            progress.stopped_early = True
            return False
        except Exception as exc:  # one bad photo must not block the rest
            log.exception("could not import unsplash photo %s", unsplash_id)
            failures = progress.pending.get(unsplash_id, 0) + 1
            if failures >= MAX_FAILURES:
                progress.pending.pop(unsplash_id, None)
                progress.skipped[unsplash_id] = "failed"
                progress.errors.append(
                    f"{unsplash_id}: giving up after {failures} failures ({exc})"
                )
            else:
                progress.pending[unsplash_id] = failures
                progress.errors.append(f"{unsplash_id}: {exc}")
            return True
        progress.pending.pop(unsplash_id, None)
        progress.imported += 1
        return True

    def _finish(self, progress: _Progress) -> SyncResult:
        error = "; ".join(progress.errors) or None
        with self._sessions() as db:
            row = state_row(db)
            row.running = False
            row.last_finished_at = self._clock.now()
            row.last_imported = progress.imported
            row.last_error = error
            row.rate_limit_remaining = self._client.rate_limit_remaining
            row.pending = progress.pending
            row.skipped = progress.skipped
            db.commit()
        return SyncResult(progress.imported, progress.stopped_early, error)


def _aware(moment: datetime) -> datetime:
    """SQLite hands datetimes back without a timezone; everything stored is UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)
