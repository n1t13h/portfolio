"""Collections, their chapters, and which photos sit in which chapter."""

import re
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from app.core.errors import Conflict, InvalidRequest, NotFound
from app.models import Chapter, Collection, Status
from app.schemas.collections import SLUG_PATTERN, ChapterDraft, ChapterOut, CollectionOut
from app.services.audit import NO_AUDIT, AuditTrail
from app.services.covers import prune_covers
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
    def __init__(self, uow_factory: UnitOfWorkFactory, audit: AuditTrail = NO_AUDIT) -> None:
        self._uow = uow_factory
        self._audit = audit

    # -- collections ----------------------------------------------------------------------

    def list_collections(self) -> list[CollectionOut]:
        with self._uow() as uow:
            return [CollectionOut.model_validate(c) for c in uow.collections.list_ordered()]

    def get_collection(self, collection_id: str) -> CollectionOut:
        with self._uow() as uow:
            return CollectionOut.model_validate(self._collection(uow, collection_id))

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
            self._audit.record(uow, "collection.create", collection.id)
            uow.commit()
            return CollectionOut.model_validate(collection)

    def create_complete(
        self,
        slug: str,
        title: str,
        *,
        chapters: Sequence[ChapterDraft],
        cover_photo_ids: Sequence[str],
        status: Status,
        place: str = "",
        year: str = "",
        intro: str = "",
    ) -> CollectionOut:
        """Create a collection with its chapters, photos and covers in ONE transaction.

        Either everything is saved or nothing is, so a collection is never visible half-built.
        """
        with self._uow() as uow:
            self._check_slug(uow, slug)
            collection = Collection(
                id=_new_id(),
                slug=slug,
                title=title,
                place=place,
                year=year,
                intro=intro,
                status=status,
                sort_position=uow.collections.next_sort_position(),
                cover_photo_ids=[],
            )
            uow.collections.add(collection)
            placed: set[str] = set()
            left: set[str] = set()
            for position, draft in enumerate(chapters):
                if placed & set(draft.photo_ids):
                    raise InvalidRequest("a photo can only be in one chapter")
                chapter = Chapter(
                    id=_new_id(),
                    collection_id=collection.id,
                    title=draft.title,
                    note=draft.note,
                    position=position,
                )
                uow.collections.add_chapter(chapter)
                left |= self._place_photos(uow, chapter, draft.photo_ids)
                placed.update(draft.photo_ids)
            self._check_covers(cover_photo_ids, placed)
            collection.cover_photo_ids = list(cover_photo_ids)
            uow.flush()
            prune_covers(uow, left - {collection.id})
            self._audit.record(uow, "collection.create", collection.id)
            uow.commit()
            return CollectionOut.model_validate(self._collection(uow, collection.id))

    def update_collection(self, collection_id: str, changes: Mapping[str, Any]) -> CollectionOut:
        changes = _checked_changes(changes, COLLECTION_FIELDS)
        with self._uow() as uow:
            collection = self._collection(uow, collection_id)
            if "slug" in changes:
                self._check_slug(uow, changes["slug"], ignore_id=collection_id)
            for name, value in changes.items():
                setattr(collection, name, value)
            self._audit.record(uow, "collection.update", collection_id)
            uow.commit()
            return CollectionOut.model_validate(collection)

    def set_status(self, collection_id: str, status: Status) -> CollectionOut:
        with self._uow() as uow:
            collection = self._collection(uow, collection_id)
            collection.status = status
            published = status is Status.PUBLISHED
            self._audit.record(
                uow, "collection.publish" if published else "collection.unpublish", collection_id
            )
            uow.commit()
            return CollectionOut.model_validate(collection)

    def delete_collection(self, collection_id: str) -> None:
        with self._uow() as uow:
            collection = self._collection(uow, collection_id)
            chapter_ids = [ch.id for ch in uow.collections.list_chapters(collection_id)]
            uow.photos.unassign_from_chapters(chapter_ids)
            uow.collections.delete(collection)
            self._audit.record(uow, "collection.delete", collection_id)
            uow.commit()

    def reorder_collections(self, ordered_ids: Sequence[str]) -> None:
        with self._uow() as uow:
            apply_order(uow.collections.list_ordered(), ordered_ids, "sort_position")
            self._audit.record(uow, "collection.reorder")
            uow.commit()

    def set_covers(self, collection_id: str, photo_ids: Sequence[str]) -> CollectionOut:
        with self._uow() as uow:
            collection = self._collection(uow, collection_id)
            self._check_covers(photo_ids, uow.photos.ids_in_collection(collection_id))
            collection.cover_photo_ids = list(photo_ids)
            self._audit.record(uow, "collection.covers", collection_id)
            uow.commit()
            return CollectionOut.model_validate(collection)

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
            self._audit.record(uow, "chapter.create", chapter.id)
            uow.commit()
            return ChapterOut.model_validate(chapter)

    def update_chapter(self, chapter_id: str, changes: Mapping[str, Any]) -> ChapterOut:
        changes = _checked_changes(changes, CHAPTER_FIELDS)
        with self._uow() as uow:
            chapter = self._chapter(uow, chapter_id)
            for name, value in changes.items():
                setattr(chapter, name, value)
            self._audit.record(uow, "chapter.update", chapter_id)
            uow.commit()
            return ChapterOut.model_validate(chapter)

    def delete_chapter(self, chapter_id: str) -> None:
        with self._uow() as uow:
            chapter = self._chapter(uow, chapter_id)
            collection_id = chapter.collection_id
            uow.photos.unassign_from_chapters([chapter_id])
            uow.collections.delete_chapter(chapter)
            uow.flush()
            prune_covers(uow, {collection_id})
            self._audit.record(uow, "chapter.delete", chapter_id)
            uow.commit()

    def reorder_chapters(self, collection_id: str, ordered_ids: Sequence[str]) -> None:
        with self._uow() as uow:
            self._collection(uow, collection_id)
            apply_order(uow.collections.list_chapters(collection_id), ordered_ids, "position")
            self._audit.record(uow, "chapter.reorder", collection_id)
            uow.commit()

    # -- photos in chapters ---------------------------------------------------------------

    def assign_photos(self, chapter_id: str, photo_ids: Sequence[str]) -> ChapterOut:
        """Append photos to the chapter in the given order, moving them out of any other one."""
        with self._uow() as uow:
            chapter = self._chapter(uow, chapter_id)
            left = self._place_photos(uow, chapter, photo_ids)
            uow.flush()
            prune_covers(uow, left)
            self._audit.record(uow, "chapter.assign_photos", chapter_id)
            uow.commit()
            # Moving photos changed other rows, so read the chapter again for its new photo list.
            return ChapterOut.model_validate(self._chapter(uow, chapter_id))

    def remove_photo(self, chapter_id: str, photo_id: str) -> None:
        with self._uow() as uow:
            chapter = self._chapter(uow, chapter_id)
            photo = uow.photos.get(photo_id)
            if photo is None or photo.chapter_id != chapter_id:
                raise NotFound("photo is not in this chapter")
            photo.chapter_id = None
            uow.flush()
            prune_covers(uow, {chapter.collection_id})
            self._audit.record(uow, "chapter.remove_photo", f"{chapter_id}/{photo_id}")
            uow.commit()

    def reorder_photos(self, chapter_id: str, ordered_ids: Sequence[str]) -> None:
        with self._uow() as uow:
            self._chapter(uow, chapter_id)
            apply_order(uow.photos.list_in_chapter(chapter_id), ordered_ids, "position_in_chapter")
            self._audit.record(uow, "chapter.reorder_photos", chapter_id)
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
    def _check_covers(photo_ids: Sequence[str], inside: set[str]) -> None:
        if len(set(photo_ids)) != len(photo_ids):
            raise InvalidRequest("duplicate photo ids")
        if not set(photo_ids) <= inside:
            raise InvalidRequest("covers must be photos in this collection")

    @staticmethod
    def _place_photos(
        uow: AbstractUnitOfWork, chapter: Chapter, photo_ids: Sequence[str]
    ) -> set[str]:
        """Append the photos to the chapter in order. Returns the *other* collections they left."""
        if len(set(photo_ids)) != len(photo_ids):
            raise InvalidRequest("duplicate photo ids")
        photos = {p.id: p for p in uow.photos.get_many(photo_ids)}
        if len(photos) != len(photo_ids):
            raise InvalidRequest("unknown photo id")
        old_chapters = [p.chapter_id for p in photos.values() if p.chapter_id]
        left = uow.collections.collection_ids_of_chapters(old_chapters) - {chapter.collection_id}
        position = uow.photos.next_position_in_chapter(chapter.id)
        for photo_id in photo_ids:
            photos[photo_id].chapter_id = chapter.id
            photos[photo_id].position_in_chapter = position
            position += 1
        return left

    @staticmethod
    def _check_slug(uow: AbstractUnitOfWork, slug: str, ignore_id: str | None = None) -> None:
        if not re.fullmatch(SLUG_PATTERN, slug):
            raise InvalidRequest("slug must be lowercase letters, digits and single hyphens")
        owner = uow.collections.slug_owner(slug)
        if owner is not None and owner != ignore_id:
            raise Conflict("slug already in use")


def _new_id() -> str:
    return uuid.uuid4().hex
