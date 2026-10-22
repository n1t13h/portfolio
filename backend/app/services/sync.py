"""Incremental Unsplash -> R2 sync. New photos arrive as drafts for the admin to review.

How it stays cheap: the listing is newest-first, so a normal run stops at the first photo it
already has. Work that could not finish (rate limit, a bad file) is remembered in
`sync_state.pending`, so stopping at that boundary never loses a photo.

Every step is its own short transaction; no database session is held open while waiting on
the network.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.core.clock import Clock
from app.core.config import Settings
from app.core.errors import Conflict
from app.integrations.storage import Storage
from app.integrations.unsplash import RateLimited, UnsplashClient
from app.schemas.sync import SyncStatusOut
from app.services.audit import NO_AUDIT, AuditTrail
from app.services.photos import PhotoService
from app.uow import UnitOfWorkFactory

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


@dataclass
class _Progress:
    """What this run has learned. Persisted only in `_finish`, merged with what others wrote."""

    pending: dict[str, int] = field(default_factory=dict)
    skipped: dict[str, str] = field(default_factory=dict)  # as of the start; used to skip ids
    failed_now: dict[str, str] = field(default_factory=dict)  # given up on during this run
    errors: list[str] = field(default_factory=list)
    imported: int = 0
    stopped_early: bool = False
    loaded: bool = False  # False if the run could not even read its saved state


class SyncService:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        client: UnsplashClient,
        storage: Storage,
        settings: Settings,
        clock: Clock,
    ) -> None:
        self._uow = uow_factory
        self._client = client
        self._storage = storage
        self._settings = settings
        self._clock = clock

    # -- locking --------------------------------------------------------------------------

    def acquire(self, audit: AuditTrail = NO_AUDIT, detail: str = "") -> None:
        """Take the run lock, or raise SyncAlreadyRunning. Atomic across processes.

        A manual start from the admin passes an `audit` trail, so "sync.start" is recorded in
        the same transaction as the lock; scheduled runs record nothing.
        """
        now = self._clock.now()
        with self._uow() as uow:
            try:
                uow.sync_state.get_or_create()
                uow.commit()
            except Conflict:  # another process created the row first
                uow.rollback()
            if not uow.sync_state.try_acquire(now, now - STALE_LOCK):
                raise SyncAlreadyRunning
            audit.record(uow, "sync.start", detail)
            uow.commit()

    def status(self) -> SyncStatusOut:
        with self._uow() as uow:
            row = uow.sync_state.get()
            if row is None:  # nothing has ever run
                return SyncStatusOut(
                    running=False,
                    last_started_at=None,
                    last_finished_at=None,
                    last_imported=0,
                    last_error=None,
                    rate_limit_remaining=None,
                    pending=0,
                )
            started = row.last_started_at
            fresh = started is not None and _aware(started) > self._clock.now() - STALE_LOCK
            return SyncStatusOut(
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
        progress = _Progress()
        try:
            self._load_state(full, progress)
            self._import_new(full, progress)
        except Exception as exc:
            log.exception("sync crashed")
            progress.errors.append(f"sync crashed: {exc}")
        finally:
            result = self._finish(progress, full)  # always release the lock, even on Ctrl-C
        return result

    def _load_state(self, full: bool, progress: _Progress) -> None:
        with self._uow() as uow:
            row = uow.sync_state.get_or_create()
            skipped = dict(row.skipped)
            if full:  # a full resync retries failures, but never what the admin deleted
                skipped = {k: v for k, v in skipped.items() if v != "failed"}
            progress.pending = dict(row.pending)
            progress.skipped = skipped
            uow.commit()
        progress.loaded = True

    def _import_new(self, full: bool, progress: _Progress) -> None:
        with self._uow() as uow:
            known = set(uow.photos.unsplash_id_map())
        found: list[str] = []
        try:
            self._discover(known, progress, full, found)
        except RateLimited:
            progress.stopped_early = True
        # Oldest first: earlier-pending photos, then the newly found ones in reverse.
        queue = [*progress.pending, *reversed(found)]
        for unsplash_id in queue:
            progress.pending.setdefault(unsplash_id, 0)
        photos = PhotoService(self._uow, self._storage, self._settings)
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
                progress.failed_now[unsplash_id] = "failed"
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

    def _finish(self, progress: _Progress, full: bool) -> SyncResult:
        error = "; ".join(progress.errors) or None
        with self._uow() as uow:
            row = uow.sync_state.get_or_create()
            row.running = False
            row.last_finished_at = self._clock.now()
            row.last_imported = progress.imported
            row.last_error = error
            row.rate_limit_remaining = self._client.rate_limit_remaining
            if progress.loaded:  # otherwise leave the saved state exactly as it was
                row.pending = progress.pending
                # Build on what is stored *now*, not on the snapshot from the start: the admin may
                # have deleted photos while this ran, and those must stay remembered.
                kept = {k: v for k, v in row.skipped.items() if not (full and v == "failed")}
                row.skipped = {**kept, **progress.failed_now}
            uow.commit()
        return SyncResult(progress.imported, progress.stopped_early, error)


def _aware(moment: datetime) -> datetime:
    """SQLite hands datetimes back without a timezone; everything stored is UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)
