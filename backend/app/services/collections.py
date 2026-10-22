"""Collections, their chapters, and which photos sit in which chapter."""

import re
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.errors import Conflict, InvalidRequest, NotFound
from app.models import Chapter, Collection, Photo, Status
from app.schemas.collections import SLUG_PATTERN
from app.services.ordering import apply_order

COLLECTION_FIELDS = {"slug", "title", "place", "year", "intro"}
CHAPTER_FIELDS = {"title", "note"}


def _checked_changes(changes: Mapping[str, Any], allowed: set[str]) -> Mapping[str, Any]:
    if not set(changes) <= allowed:
        raise InvalidRequest(f"only {sorted(allowed)} can be edited")
    if any(value is None for value in changes.values()):
        raise InvalidRequest("fields cannot be null")
    return changes


class CollectionService:
    def __init__(self, session: Session) -> None:
        self._db = session

    # -- collections ----------------------------------------------------------------------

    def list_collections(self) -> Sequence[Collection]:
        return self._db.scalars(select(Collection).order_by(Collection.sort_position)).all()

    def get_collection(self, collection_id: str) -> Collection:
        collection = self._db.get(Collection, collection_id)
        if collection is None:
            raise NotFound("collection not found")
        return collection

    def create_collection(
        self, slug: str, title: str, place: str = "", year: str = "", intro: str = ""
    ) -> Collection:
        self._check_slug(slug)
        highest = self._db.scalar(select(func.max(Collection.sort_position)))
        collection = Collection(
            id=_new_id(),
            slug=slug,
            title=title,
            place=place,
            year=year,
            intro=intro,
            sort_position=0 if highest is None else highest + 1,
        )
        self._db.add(collection)
        self._db.commit()
        return collection

    def update_collection(self, collection_id: str, changes: Mapping[str, Any]) -> Collection:
        changes = _checked_changes(changes, COLLECTION_FIELDS)
        collection = self.get_collection(collection_id)
        if "slug" in changes:
            self._check_slug(changes["slug"], ignore_id=collection_id)
        for name, value in changes.items():
            setattr(collection, name, value)
        self._db.commit()
        return collection

    def set_status(self, collection_id: str, status: Status) -> Collection:
        collection = self.get_collection(collection_id)
        collection.status = status
        self._db.commit()
        return collection

    def delete_collection(self, collection_id: str) -> None:
        collection = self.get_collection(collection_id)
        chapter_ids = [ch.id for ch in collection.chapters]
        self._db.execute(
            update(Photo).where(Photo.chapter_id.in_(chapter_ids)).values(chapter_id=None)
        )
        self._db.delete(collection)
        self._db.commit()

    def reorder_collections(self, ordered_ids: Sequence[str]) -> None:
        apply_order(self.list_collections(), ordered_ids, "sort_position")
        self._db.commit()

    def set_covers(self, collection_id: str, photo_ids: Sequence[str]) -> Collection:
        collection = self.get_collection(collection_id)
        if len(set(photo_ids)) != len(photo_ids):
            raise InvalidRequest("duplicate photo ids")
        if not set(photo_ids) <= self._photo_ids_in(collection_id):
            raise InvalidRequest("covers must be photos in this collection")
        collection.cover_photo_ids = list(photo_ids)
        self._db.commit()
        return collection

    # -- chapters -------------------------------------------------------------------------

    def get_chapter(self, chapter_id: str) -> Chapter:
        chapter = self._db.get(Chapter, chapter_id)
        if chapter is None:
            raise NotFound("chapter not found")
        return chapter

    def create_chapter(self, collection_id: str, title: str = "", note: str = "") -> Chapter:
        collection = self.get_collection(collection_id)
        position = max((ch.position for ch in collection.chapters), default=-1) + 1
        chapter = Chapter(
            id=_new_id(), collection_id=collection_id, title=title, note=note, position=position
        )
        self._db.add(chapter)
        self._db.commit()
        return chapter

    def update_chapter(self, chapter_id: str, changes: Mapping[str, Any]) -> Chapter:
        changes = _checked_changes(changes, CHAPTER_FIELDS)
        chapter = self.get_chapter(chapter_id)
        for name, value in changes.items():
            setattr(chapter, name, value)
        self._db.commit()
        return chapter

    def delete_chapter(self, chapter_id: str) -> None:
        chapter = self.get_chapter(chapter_id)
        collection_id = chapter.collection_id
        self._db.execute(
            update(Photo).where(Photo.chapter_id == chapter_id).values(chapter_id=None)
        )
        self._db.delete(chapter)
        self._db.flush()
        self._prune_covers({collection_id})
        self._db.commit()

    def reorder_chapters(self, collection_id: str, ordered_ids: Sequence[str]) -> None:
        apply_order(self.get_collection(collection_id).chapters, ordered_ids, "position")
        self._db.commit()

    # -- photos in chapters ---------------------------------------------------------------

    def assign_photos(self, chapter_id: str, photo_ids: Sequence[str]) -> Chapter:
        """Append photos to the chapter in the given order, moving them out of any other one."""
        chapter = self.get_chapter(chapter_id)
        if len(set(photo_ids)) != len(photo_ids):
            raise InvalidRequest("duplicate photo ids")
        photos = {p.id: p for p in self._db.scalars(select(Photo).where(Photo.id.in_(photo_ids)))}
        if len(photos) != len(photo_ids):
            raise InvalidRequest("unknown photo id")

        left_collections = self._collections_of(photos.values()) - {chapter.collection_id}
        position = max((p.position_in_chapter for p in chapter.photos), default=-1) + 1
        for photo_id in photo_ids:
            photos[photo_id].chapter_id = chapter_id
            photos[photo_id].position_in_chapter = position
            position += 1
        self._db.flush()
        self._prune_covers(left_collections)
        self._db.commit()
        self._db.refresh(chapter)
        return chapter

    def remove_photo(self, chapter_id: str, photo_id: str) -> None:
        chapter = self.get_chapter(chapter_id)
        photo = self._db.get(Photo, photo_id)
        if photo is None or photo.chapter_id != chapter_id:
            raise NotFound("photo is not in this chapter")
        photo.chapter_id = None
        self._db.flush()
        self._prune_covers({chapter.collection_id})
        self._db.commit()

    def reorder_photos(self, chapter_id: str, ordered_ids: Sequence[str]) -> None:
        apply_order(self.get_chapter(chapter_id).photos, ordered_ids, "position_in_chapter")
        self._db.commit()

    # -- helpers --------------------------------------------------------------------------

    def _check_slug(self, slug: str, ignore_id: str | None = None) -> None:
        if not re.fullmatch(SLUG_PATTERN, slug):
            raise InvalidRequest("slug must be lowercase letters, digits and single hyphens")
        taken = self._db.scalar(select(Collection.id).where(Collection.slug == slug))
        if taken is not None and taken != ignore_id:
            raise Conflict("slug already in use")

    def _photo_ids_in(self, collection_id: str) -> set[str]:
        stmt = select(Photo.id).join(Chapter).where(Chapter.collection_id == collection_id)
        return set(self._db.scalars(stmt))

    def _collections_of(self, photos: Any) -> set[str]:
        chapter_ids = {p.chapter_id for p in photos if p.chapter_id}
        if not chapter_ids:
            return set()
        stmt = select(Chapter.collection_id).where(Chapter.id.in_(chapter_ids))
        return set(self._db.scalars(stmt))

    def _prune_covers(self, collection_ids: set[str]) -> None:
        """Drop cover photos that are no longer in their collection."""
        for collection_id in collection_ids:
            collection = self._db.get(Collection, collection_id)
            if collection is None or not collection.cover_photo_ids:
                continue
            inside = self._photo_ids_in(collection_id)
            collection.cover_photo_ids = [p for p in collection.cover_photo_ids if p in inside]


def _new_id() -> str:
    return uuid.uuid4().hex
