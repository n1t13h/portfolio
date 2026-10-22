"""Collections, their chapters, and which photos sit in which chapter."""

import re
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from app.core.errors import Conflict, InvalidRequest, NotFound
from app.models import Chapter, Collection, Status
from app.schemas.collections import SLUG_PATTERN, ChapterOut, CollectionOut
from app.services.mappers import admin_chapter, admin_collection
from app.services.ordering import apply_order
from app.uow import AbstractUnitOfWork, UnitOfWorkFactory

COLLECTION_FIELDS = {"slug", "title", "place", "year", "intro"}
CHAPTER_FIELDS = {"title", "note"}


def _checked_changes(changes: Mapping[str, Any], allowed: set[str]) -> Mapping[str, Any]:
    if not set(changes) <= allowed:
        raise InvalidRequest(f"only {sorted(allowed)} can be edited")
    if any(value is None for value in changes.values()):
        raise InvalidRequest("fields cannot be null")
    return changes


class CollectionService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow = uow_factory

    # -- collections ----------------------------------------------------------------------

    def list_collections(self) -> list[CollectionOut]:
        with self._uow() as uow:
            return self._collections_out(uow, uow.collections.list_ordered())

    def get_collection(self, collection_id: str) -> CollectionOut:
        with self._uow() as uow:
            return self._collection_out(uow, self._collection(uow, collection_id))

    def create_collection(
        self, slug: str, title: str, place: str = "", year: str = "", intro: str = ""
    ) -> CollectionOut:
        with self._uow() as uow:
            self._check_slug(uow, slug)
            collection = Collection(
                id=_new_id(),
                slug=slug,
                title=title,
                place=place,
                year=year,
                intro=intro,
                sort_position=uow.collections.next_sort_position(),
            )
            uow.collections.add(collection)
            uow.commit()
            return self._collection_out(uow, collection)

    def update_collection(self, collection_id: str, changes: Mapping[str, Any]) -> CollectionOut:
        changes = _checked_changes(changes, COLLECTION_FIELDS)
        with self._uow() as uow:
            collection = self._collection(uow, collection_id)
            if "slug" in changes:
                self._check_slug(uow, changes["slug"], ignore_id=collection_id)
            for name, value in changes.items():
                setattr(collection, name, value)
            uow.commit()
            return self._collection_out(uow, collection)

    def set_status(self, collection_id: str, status: Status) -> CollectionOut:
        with self._uow() as uow:
            collection = self._collection(uow, collection_id)
            collection.status = status
            uow.commit()
            return self._collection_out(uow, collection)

    def delete_collection(self, collection_id: str) -> None:
        with self._uow() as uow:
            collection = self._collection(uow, collection_id)
            chapter_ids = [ch.id for ch in uow.collections.list_chapters(collection_id)]
            uow.photos.unassign_from_chapters(chapter_ids)
            uow.collections.delete(collection)
            uow.commit()

    def reorder_collections(self, ordered_ids: Sequence[str]) -> None:
        with self._uow() as uow:
            apply_order(uow.collections.list_ordered(), ordered_ids, "sort_position")
            uow.commit()

    def set_covers(self, collection_id: str, photo_ids: Sequence[str]) -> CollectionOut:
        with self._uow() as uow:
            collection = self._collection(uow, collection_id)
            if len(set(photo_ids)) != len(photo_ids):
                raise InvalidRequest("duplicate photo ids")
            if not set(photo_ids) <= uow.photos.ids_in_collection(collection_id):
                raise InvalidRequest("covers must be photos in this collection")
            collection.cover_photo_ids = list(photo_ids)
            uow.commit()
            return self._collection_out(uow, collection)

    # -- chapters -------------------------------------------------------------------------

    def create_chapter(self, collection_id: str, title: str = "", note: str = "") -> ChapterOut:
        with self._uow() as uow:
            self._collection(uow, collection_id)
            chapter = Chapter(
                id=_new_id(),
                collection_id=collection_id,
                title=title,
                note=note,
                position=uow.collections.next_chapter_position(collection_id),
            )
            uow.collections.add_chapter(chapter)
            uow.commit()
            return self._chapter_out(uow, chapter)

    def update_chapter(self, chapter_id: str, changes: Mapping[str, Any]) -> ChapterOut:
        changes = _checked_changes(changes, CHAPTER_FIELDS)
        with self._uow() as uow:
            chapter = self._chapter(uow, chapter_id)
            for name, value in changes.items():
                setattr(chapter, name, value)
            uow.commit()
            return self._chapter_out(uow, chapter)

    def delete_chapter(self, chapter_id: str) -> None:
        with self._uow() as uow:
            chapter = self._chapter(uow, chapter_id)
            collection_id = chapter.collection_id
            uow.photos.unassign_from_chapters([chapter_id])
            uow.collections.delete_chapter(chapter)
            uow.flush()
            self._prune_covers(uow, {collection_id})
            uow.commit()

    def reorder_chapters(self, collection_id: str, ordered_ids: Sequence[str]) -> None:
        with self._uow() as uow:
            self._collection(uow, collection_id)
            apply_order(uow.collections.list_chapters(collection_id), ordered_ids, "position")
            uow.commit()

    # -- photos in chapters ---------------------------------------------------------------

    def assign_photos(self, chapter_id: str, photo_ids: Sequence[str]) -> ChapterOut:
        """Append photos to the chapter in the given order, moving them out of any other one."""
        with self._uow() as uow:
            chapter = self._chapter(uow, chapter_id)
            if len(set(photo_ids)) != len(photo_ids):
                raise InvalidRequest("duplicate photo ids")
            photos = {p.id: p for p in uow.photos.get_many(photo_ids)}
            if len(photos) != len(photo_ids):
                raise InvalidRequest("unknown photo id")

            old_chapters = [p.chapter_id for p in photos.values() if p.chapter_id]
            left = uow.collections.collection_ids_of_chapters(old_chapters) - {
                chapter.collection_id
            }
            position = uow.photos.next_position_in_chapter(chapter_id)
            for photo_id in photo_ids:
                photos[photo_id].chapter_id = chapter_id
                photos[photo_id].position_in_chapter = position
                position += 1
            uow.flush()
            self._prune_covers(uow, left)
            uow.commit()
            return self._chapter_out(uow, chapter)

    def remove_photo(self, chapter_id: str, photo_id: str) -> None:
        with self._uow() as uow:
            chapter = self._chapter(uow, chapter_id)
            photo = uow.photos.get(photo_id)
            if photo is None or photo.chapter_id != chapter_id:
                raise NotFound("photo is not in this chapter")
            photo.chapter_id = None
            uow.flush()
            self._prune_covers(uow, {chapter.collection_id})
            uow.commit()

    def reorder_photos(self, chapter_id: str, ordered_ids: Sequence[str]) -> None:
        with self._uow() as uow:
            self._chapter(uow, chapter_id)
            apply_order(uow.photos.list_in_chapter(chapter_id), ordered_ids, "position_in_chapter")
            uow.commit()

    # -- helpers --------------------------------------------------------------------------

    @staticmethod
    def _collection(uow: AbstractUnitOfWork, collection_id: str) -> Collection:
        collection = uow.collections.get(collection_id)
        if collection is None:
            raise NotFound("collection not found")
        return collection

    @staticmethod
    def _chapter(uow: AbstractUnitOfWork, chapter_id: str) -> Chapter:
        chapter = uow.collections.get_chapter(chapter_id)
        if chapter is None:
            raise NotFound("chapter not found")
        return chapter

    @staticmethod
    def _check_slug(uow: AbstractUnitOfWork, slug: str, ignore_id: str | None = None) -> None:
        if not re.fullmatch(SLUG_PATTERN, slug):
            raise InvalidRequest("slug must be lowercase letters, digits and single hyphens")
        owner = uow.collections.slug_owner(slug)
        if owner is not None and owner != ignore_id:
            raise Conflict("slug already in use")

    @staticmethod
    def _prune_covers(uow: AbstractUnitOfWork, collection_ids: set[str]) -> None:
        """Drop cover photos that are no longer in their collection."""
        for collection_id in collection_ids:
            collection = uow.collections.get(collection_id)
            if collection is None or not collection.cover_photo_ids:
                continue
            inside = uow.photos.ids_in_collection(collection_id)
            collection.cover_photo_ids = [p for p in collection.cover_photo_ids if p in inside]

    @staticmethod
    def _chapter_out(uow: AbstractUnitOfWork, chapter: Chapter) -> ChapterOut:
        photo_ids = uow.photos.ids_by_chapter([chapter.id])[chapter.id]
        return admin_chapter(chapter, photo_ids)

    def _collection_out(self, uow: AbstractUnitOfWork, collection: Collection) -> CollectionOut:
        return self._collections_out(uow, [collection])[0]

    @staticmethod
    def _collections_out(
        uow: AbstractUnitOfWork, collections: Sequence[Collection]
    ) -> list[CollectionOut]:
        chapters = uow.collections.chapters_by_collection([c.id for c in collections])
        chapter_ids = [ch.id for chs in chapters.values() for ch in chs]
        photo_ids = uow.photos.ids_by_chapter(chapter_ids)
        return [admin_collection(c, chapters[c.id], photo_ids) for c in collections]


def _new_id() -> str:
    return uuid.uuid4().hex
