"""Read-side queries for the public site. Drafts are filtered out here, once.

A photo is public only if it is published AND not inside a draft collection, so an
unreleased collection can never leak through the global photo list or the download link.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.models import Chapter, Collection, Photo, Status


@dataclass(frozen=True)
class CollectionView:
    collection: Collection
    covers: list[Photo]


@dataclass(frozen=True)
class ChapterView:
    chapter: Chapter
    photos: list[Photo]


@dataclass(frozen=True)
class CollectionDetail:
    collection: Collection
    covers: list[Photo]
    chapters: list[ChapterView]


def _public_photos() -> Select[Photo]:
    return (
        select(Photo)
        .outerjoin(Chapter, Photo.chapter_id == Chapter.id)
        .outerjoin(Collection, Chapter.collection_id == Collection.id)
        .where(
            Photo.status == Status.PUBLISHED,
            or_(Photo.chapter_id.is_(None), Collection.status == Status.PUBLISHED),
        )
    )


def _covers(collection: Collection, visible: dict[str, Photo]) -> list[Photo]:
    return [visible[pid] for pid in collection.cover_photo_ids if pid in visible]


class PublicViews:
    def __init__(self, session: Session) -> None:
        self._db = session

    def photos(self) -> Sequence[Photo]:
        stmt = _public_photos().order_by(Photo.sort_position, Photo.created_at, Photo.id)
        return self._db.scalars(stmt).all()

    def downloadable_photo(self, photo_id: str) -> Photo:
        stmt = _public_photos().where(Photo.id == photo_id, Photo.allow_download.is_(True))
        photo = self._db.scalars(stmt).first()
        if photo is None or not photo.download_key:
            raise NotFound("not found")
        return photo

    def collections(self) -> list[CollectionView]:
        stmt = (
            select(Collection)
            .where(Collection.status == Status.PUBLISHED)
            .order_by(Collection.sort_position)
        )
        collections = self._db.scalars(stmt).all()
        by_collection = self._photos_by_collection([c.id for c in collections])
        return [
            CollectionView(c, _covers(c, {p.id: p for p in by_collection.get(c.id, [])}))
            for c in collections
        ]

    def collection(self, slug: str) -> CollectionDetail:
        stmt = select(Collection).where(
            Collection.slug == slug, Collection.status == Status.PUBLISHED
        )
        collection = self._db.scalars(stmt).first()
        if collection is None:
            raise NotFound("collection not found")

        chapters = list(collection.chapters)  # ordered by position
        photos_stmt = (
            select(Photo)
            .where(
                Photo.chapter_id.in_([ch.id for ch in chapters]),
                Photo.status == Status.PUBLISHED,
            )
            .order_by(Photo.position_in_chapter, Photo.id)
        )
        by_chapter: dict[str, list[Photo]] = defaultdict(list)
        for photo in self._db.scalars(photos_stmt):
            assert photo.chapter_id is not None
            by_chapter[photo.chapter_id].append(photo)

        visible = {p.id: p for photos in by_chapter.values() for p in photos}
        views = [ChapterView(ch, by_chapter[ch.id]) for ch in chapters if by_chapter[ch.id]]
        return CollectionDetail(collection, _covers(collection, visible), views)

    def _photos_by_collection(self, collection_ids: list[str]) -> dict[str, list[Photo]]:
        stmt = (
            select(Photo, Chapter.collection_id)
            .join(Chapter, Photo.chapter_id == Chapter.id)
            .where(Chapter.collection_id.in_(collection_ids), Photo.status == Status.PUBLISHED)
        )
        grouped: dict[str, list[Photo]] = defaultdict(list)
        for photo, collection_id in self._db.execute(stmt):
            grouped[collection_id].append(photo)
        return grouped
