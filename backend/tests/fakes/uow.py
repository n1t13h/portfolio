"""An in-memory unit of work for unit-testing services without a database.

It behaves like the SQL one where services depend on it: column defaults are applied and
integer ids assigned on `add`, deleting a collection or chapter frees its photos, unique
constraints are checked at `commit`, and leaving a `with` block without committing undoes every
change (including edits to objects that were already loaded). The repository contract tests run
the same behaviour checks against this fake and the real SQL repositories, so it cannot drift.
"""

import copy
import itertools
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Integer
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import IntegrityError

from app.models import (
    Admin,
    AuditLog,
    Chapter,
    Collection,
    ContactMessage,
    LoginFailure,
    Photo,
    Status,
    SyncState,
)
from app.repositories.audit import AbstractAuditRepository
from app.repositories.auth import AbstractAdminRepository, AbstractLoginFailureRepository
from app.repositories.catalog import AbstractCatalogRepository
from app.repositories.collections import AbstractCollectionRepository
from app.repositories.contacts import AbstractContactRepository
from app.repositories.photos import AbstractPhotoRepository
from app.repositories.sync_state import AbstractSyncStateRepository
from app.uow import AbstractUnitOfWork


class InMemoryStore:
    """Everything the repositories share, with snapshot/restore for rollback."""

    def __init__(self) -> None:
        self.photos: dict[str, Photo] = {}
        self.collections: dict[str, Collection] = {}
        self.chapters: dict[str, Chapter] = {}
        self.admins: list[Admin] = []
        self.login_failures: list[LoginFailure] = []
        self.audit: list[AuditLog] = []
        self.sync_state: SyncState | None = None
        self.contacts: list[ContactMessage] = []
        self._ids = itertools.count(1)

    def apply_defaults(self, entity: Any) -> None:
        """Do what the database does on INSERT: fill generated ids and column defaults."""
        for column in entity.__table__.columns:
            if getattr(entity, column.key, None) is not None:
                continue
            if column.primary_key and isinstance(column.type, Integer):
                setattr(entity, column.key, next(self._ids))
            elif column.default is not None:
                arg = column.default.arg
                setattr(entity, column.key, arg(None) if callable(arg) else arg)

    def _entities(self) -> list[Any]:
        singles = [self.sync_state] if self.sync_state else []
        return [
            *self.photos.values(),
            *self.collections.values(),
            *self.chapters.values(),
            *self.admins,
            *self.login_failures,
            *self.audit,
            *singles,
            *self.contacts,
        ]

    def snapshot(self) -> dict[str, Any]:
        return {
            "photos": dict(self.photos),
            "collections": dict(self.collections),
            "chapters": dict(self.chapters),
            "admins": list(self.admins),
            "login_failures": list(self.login_failures),
            "audit": list(self.audit),
            "sync_state": self.sync_state,
            "contacts": list(self.contacts),
            "values": [(e, self._values(e)) for e in self._entities()],
        }

    @staticmethod
    def _values(entity: Any) -> dict[str, Any]:
        return {
            attr.key: copy.deepcopy(getattr(entity, attr.key, None))
            for attr in sa_inspect(entity).mapper.column_attrs
        }

    def restore(self, snap: dict[str, Any]) -> None:
        self.photos = dict(snap["photos"])
        self.collections = dict(snap["collections"])
        self.chapters = dict(snap["chapters"])
        self.admins = list(snap["admins"])
        self.login_failures = list(snap["login_failures"])
        self.audit = list(snap["audit"])
        self.sync_state = snap["sync_state"]
        self.contacts = list(snap["contacts"])
        for entity, values in snap["values"]:
            for key, value in values.items():
                setattr(entity, key, copy.deepcopy(value))

    def check_constraints(self) -> None:
        for label, values in (
            ("photo.unsplash_id", [p.unsplash_id for p in self.photos.values() if p.unsplash_id]),
            ("collection.slug", [c.slug for c in self.collections.values()]),
        ):
            if len(values) != len(set(values)):
                raise IntegrityError("commit", {}, Exception(f"UNIQUE constraint failed: {label}"))


def _photo_sort_key(photo: Photo) -> tuple[int, datetime, str]:
    return (photo.sort_position, photo.created_at, photo.id)


class FakePhotoRepository(AbstractPhotoRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def add(self, photo: Photo) -> None:
        self._store.apply_defaults(photo)
        self._store.photos[photo.id] = photo

    def get(self, photo_id: str) -> Photo | None:
        return self._store.photos.get(photo_id)

    def get_many(self, photo_ids: Sequence[str]) -> list[Photo]:
        return [self._store.photos[i] for i in photo_ids if i in self._store.photos]

    def list_ordered(self) -> list[Photo]:
        return sorted(self._store.photos.values(), key=_photo_sort_key)

    def delete(self, photo: Photo) -> None:
        self._store.photos.pop(photo.id, None)

    def next_sort_position(self) -> int:
        return max((p.sort_position for p in self._store.photos.values()), default=-1) + 1

    def unsplash_id_map(self) -> dict[str, str]:
        return {p.unsplash_id: p.id for p in self._store.photos.values() if p.unsplash_id}

    def list_in_chapter(self, chapter_id: str) -> list[Photo]:
        photos = [p for p in self._store.photos.values() if p.chapter_id == chapter_id]
        return sorted(photos, key=lambda p: (p.position_in_chapter, p.id))

    def ids_by_chapter(self, chapter_ids: Sequence[str]) -> dict[str, list[str]]:
        return {cid: [p.id for p in self.list_in_chapter(cid)] for cid in chapter_ids}

    def ids_in_collection(self, collection_id: str) -> set[str]:
        chapters = {c.id for c in self._store.chapters.values() if c.collection_id == collection_id}
        return {p.id for p in self._store.photos.values() if p.chapter_id in chapters}

    def next_position_in_chapter(self, chapter_id: str) -> int:
        positions = [p.position_in_chapter for p in self.list_in_chapter(chapter_id)]
        return max(positions, default=-1) + 1

    def unassign_from_chapters(self, chapter_ids: Sequence[str]) -> None:
        for photo in self._store.photos.values():
            if photo.chapter_id in chapter_ids:
                photo.chapter_id = None


class FakeCollectionRepository(AbstractCollectionRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def add(self, collection: Collection) -> None:
        self._store.apply_defaults(collection)
        self._store.collections[collection.id] = collection

    def get(self, collection_id: str) -> Collection | None:
        return self._store.collections.get(collection_id)

    def delete(self, collection: Collection) -> None:
        for chapter in self.list_chapters(collection.id):
            self.delete_chapter(chapter)
        self._store.collections.pop(collection.id, None)

    def list_ordered(self) -> list[Collection]:
        return sorted(self._store.collections.values(), key=lambda c: (c.sort_position, c.id))

    def slug_owner(self, slug: str) -> str | None:
        return next((c.id for c in self._store.collections.values() if c.slug == slug), None)

    def next_sort_position(self) -> int:
        return max((c.sort_position for c in self._store.collections.values()), default=-1) + 1

    def add_chapter(self, chapter: Chapter) -> None:
        self._store.apply_defaults(chapter)
        self._store.chapters[chapter.id] = chapter

    def get_chapter(self, chapter_id: str) -> Chapter | None:
        return self._store.chapters.get(chapter_id)

    def delete_chapter(self, chapter: Chapter) -> None:
        for photo in self._store.photos.values():  # like ON DELETE SET NULL
            if photo.chapter_id == chapter.id:
                photo.chapter_id = None
        self._store.chapters.pop(chapter.id, None)

    def list_chapters(self, collection_id: str) -> list[Chapter]:
        chapters = [c for c in self._store.chapters.values() if c.collection_id == collection_id]
        return sorted(chapters, key=lambda c: (c.position, c.id))

    def chapters_by_collection(self, collection_ids: Sequence[str]) -> dict[str, list[Chapter]]:
        return {cid: self.list_chapters(cid) for cid in collection_ids}

    def next_chapter_position(self, collection_id: str) -> int:
        positions = [c.position for c in self.list_chapters(collection_id)]
        return max(positions, default=-1) + 1

    def collection_ids_of_chapters(self, chapter_ids: Sequence[str]) -> set[str]:
        chapters = (self._store.chapters.get(cid) for cid in chapter_ids)
        return {c.collection_id for c in chapters if c is not None}


class FakeCatalogRepository(AbstractCatalogRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def _is_public(self, photo: Photo) -> bool:
        if photo.status != Status.PUBLISHED:
            return False
        if photo.chapter_id is None:
            return True
        chapter = self._store.chapters.get(photo.chapter_id)
        collection = self._store.collections.get(chapter.collection_id) if chapter else None
        return collection is not None and collection.status == Status.PUBLISHED

    def list_public_photos(self) -> list[Photo]:
        public = [p for p in self._store.photos.values() if self._is_public(p)]
        return sorted(public, key=_photo_sort_key)

    def get_downloadable_photo(self, photo_id: str) -> Photo | None:
        photo = self._store.photos.get(photo_id)
        if photo is not None and photo.allow_download and self._is_public(photo):
            return photo
        return None

    def list_published_collections(self) -> list[Collection]:
        published = [c for c in self._store.collections.values() if c.status == Status.PUBLISHED]
        return sorted(published, key=lambda c: (c.sort_position, c.id))

    def get_published_collection(self, slug: str) -> Collection | None:
        return next(
            (
                c
                for c in self._store.collections.values()
                if c.slug == slug and c.status == Status.PUBLISHED
            ),
            None,
        )

    def list_chapters(self, collection_id: str) -> list[Chapter]:
        chapters = [c for c in self._store.chapters.values() if c.collection_id == collection_id]
        return sorted(chapters, key=lambda c: (c.position, c.id))

    def published_photos_by_collection(
        self, collection_ids: Sequence[str]
    ) -> dict[str, list[Photo]]:
        grouped: dict[str, list[Photo]] = {}
        for photo in self._store.photos.values():
            chapter = self._store.chapters.get(photo.chapter_id or "")
            if (
                chapter
                and chapter.collection_id in collection_ids
                and photo.status == Status.PUBLISHED
            ):
                grouped.setdefault(chapter.collection_id, []).append(photo)
        return grouped

    def published_photos_by_chapter(self, chapter_ids: Sequence[str]) -> dict[str, list[Photo]]:
        result: dict[str, list[Photo]] = {cid: [] for cid in chapter_ids}
        for photo in sorted(
            self._store.photos.values(), key=lambda p: (p.position_in_chapter, p.id)
        ):
            if photo.chapter_id in result and photo.status == Status.PUBLISHED:
                result[photo.chapter_id].append(photo)
        return result


class FakeAdminRepository(AbstractAdminRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def add(self, admin: Admin) -> None:
        self._store.apply_defaults(admin)
        self._store.admins.append(admin)

    def get(self, admin_id: int) -> Admin | None:
        return next((a for a in self._store.admins if a.id == admin_id), None)

    def get_first(self) -> Admin | None:
        return self._store.admins[0] if self._store.admins else None

    def get_by_username(self, username: str) -> Admin | None:
        return next((a for a in self._store.admins if a.username == username), None)


class FakeLoginFailureRepository(AbstractLoginFailureRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def add(self, failure: LoginFailure) -> None:
        self._store.apply_defaults(failure)
        self._store.login_failures.append(failure)

    def count_for_key(self, key: str) -> int:
        return sum(1 for f in self._store.login_failures if f.key == key)

    def count_for_username(self, username: str) -> int:
        suffix = f"|{username.lower()}"
        return sum(1 for f in self._store.login_failures if f.key.lower().endswith(suffix))

    def delete_up_to(self, cutoff: datetime) -> None:
        self._store.login_failures = [f for f in self._store.login_failures if f.at > cutoff]

    def delete_for_key(self, key: str) -> None:
        self._store.login_failures = [f for f in self._store.login_failures if f.key != key]

    def delete_all(self) -> None:
        self._store.login_failures = []


class FakeAuditRepository(AbstractAuditRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def add(self, entry: AuditLog) -> None:
        self._store.apply_defaults(entry)
        self._store.audit.append(entry)


class FakeSyncStateRepository(AbstractSyncStateRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def get_or_create(self) -> SyncState:
        if self._store.sync_state is None:
            state = SyncState(id=1, pending={}, skipped={})
            self._store.apply_defaults(state)
            self._store.sync_state = state
        return self._store.sync_state

    def try_acquire(self, now: datetime, stale_before: datetime) -> bool:
        state = self._store.sync_state
        if state is None:
            return False
        free = not state.running or (
            state.last_started_at is not None and state.last_started_at < stale_before
        )
        if free:
            state.running = True
            state.last_started_at = now
        return free


class FakeContactRepository(AbstractContactRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def add(self, message: ContactMessage) -> None:
        self._store.apply_defaults(message)
        self._store.contacts.append(message)

    def count_since(self, since: datetime, ip: str | None = None) -> int:
        return sum(1 for m in self._store.contacts if m.at > since and (ip is None or m.ip == ip))

    def list_pending(self, since: datetime, limit: int) -> list[ContactMessage]:
        pending = [m for m in self._store.contacts if not m.notified and m.at > since]
        return sorted(pending, key=lambda m: m.id)[:limit]


class FakeUnitOfWork(AbstractUnitOfWork):
    """Shares one in-memory store across `with` blocks, like a database would persist."""

    def __init__(self) -> None:
        self.store = InMemoryStore()
        self.photos = FakePhotoRepository(self.store)
        self.collections = FakeCollectionRepository(self.store)
        self.catalog = FakeCatalogRepository(self.store)
        self.admins = FakeAdminRepository(self.store)
        self.login_failures = FakeLoginFailureRepository(self.store)
        self.audit = FakeAuditRepository(self.store)
        self.sync_state = FakeSyncStateRepository(self.store)
        self.contacts = FakeContactRepository(self.store)
        self.commits = 0
        self._snapshot: dict[str, Any] | None = None
        self._commit_error: Exception | None = None

    def __enter__(self) -> "FakeUnitOfWork":
        self._snapshot = self.store.snapshot()
        return self

    def commit(self) -> None:
        if self._commit_error is not None:
            error, self._commit_error = self._commit_error, None
            raise error
        self.store.check_constraints()
        self.commits += 1
        self._snapshot = self.store.snapshot()

    def rollback(self) -> None:
        if self._snapshot is not None:
            self.store.restore(self._snapshot)

    def flush(self) -> None:
        pass

    def fail_next_commit(self, error: Exception) -> None:
        """Make the next commit raise `error` (e.g. to test cleanup after a failed save)."""
        self._commit_error = error

    @property
    def audit_actions(self) -> list[str]:
        return [entry.action for entry in self.store.audit]
