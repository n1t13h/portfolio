"""Read side for the public site. The visibility rules live here, once.

A photo is public only if it is published AND not inside a draft collection, so an unreleased
collection can never leak through the global photo list or the download link.
"""

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.models import Chapter, Collection, Photo, Status


class AbstractCatalogRepository(ABC):
    @abstractmethod
    def list_public_photos(self) -> list[Photo]:
        """Public photos in the admin's global order."""

    @abstractmethod
    def get_downloadable_photo(self, photo_id: str) -> Photo | None:
        """A public photo whose owner allowed downloads, else None."""

    @abstractmethod
    def list_published_collections(self) -> list[Collection]: ...

    @abstractmethod
    def get_published_collection(self, slug: str) -> Collection | None: ...

    @abstractmethod
    def list_chapters(self, collection_id: str) -> list[Chapter]: ...

    @abstractmethod
    def published_photos_by_collection(
        self, collection_ids: Sequence[str]
    ) -> dict[str, list[Photo]]:
        """collection id -> its published photos (in no particular order)."""

    @abstractmethod
    def published_photos_by_chapter(self, chapter_ids: Sequence[str]) -> dict[str, list[Photo]]:
        """chapter id -> its published photos in display order (chapters without any map to [])."""


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


class SqlAlchemyCatalogRepository(AbstractCatalogRepository):
    def __init__(self, session: Session) -> None:
        self._s = session

    def list_public_photos(self) -> list[Photo]:
        stmt = _public_photos().order_by(Photo.sort_position, Photo.created_at, Photo.id)
        return list(self._s.scalars(stmt))

    def get_downloadable_photo(self, photo_id: str) -> Photo | None:
        stmt = _public_photos().where(Photo.id == photo_id, Photo.allow_download.is_(True))
        return self._s.scalars(stmt).first()

    def list_published_collections(self) -> list[Collection]:
        stmt = (
            select(Collection)
            .where(Collection.status == Status.PUBLISHED)
            .order_by(Collection.sort_position, Collection.id)
        )
        return list(self._s.scalars(stmt))

    def get_published_collection(self, slug: str) -> Collection | None:
        stmt = select(Collection).where(
            Collection.slug == slug, Collection.status == Status.PUBLISHED
        )
        return self._s.scalars(stmt).first()

    def list_chapters(self, collection_id: str) -> list[Chapter]:
        stmt = (
            select(Chapter)
            .where(Chapter.collection_id == collection_id)
            .order_by(Chapter.position, Chapter.id)
        )
        return list(self._s.scalars(stmt))

    def published_photos_by_collection(
        self, collection_ids: Sequence[str]
    ) -> dict[str, list[Photo]]:
        grouped: dict[str, list[Photo]] = defaultdict(list)
        if collection_ids:
            stmt = (
                select(Photo, Chapter.collection_id)
                .join(Chapter, Photo.chapter_id == Chapter.id)
                .where(Chapter.collection_id.in_(collection_ids), Photo.status == Status.PUBLISHED)
            )
            for photo, collection_id in self._s.execute(stmt):
                grouped[collection_id].append(photo)
        return dict(grouped)

    def published_photos_by_chapter(self, chapter_ids: Sequence[str]) -> dict[str, list[Photo]]:
        grouped: dict[str, list[Photo]] = defaultdict(list, {cid: [] for cid in chapter_ids})
        if chapter_ids:
            stmt = (
                select(Photo)
                .where(Photo.chapter_id.in_(chapter_ids), Photo.status == Status.PUBLISHED)
                .order_by(Photo.position_in_chapter, Photo.id)
            )
            for photo in self._s.scalars(stmt):
                grouped[str(photo.chapter_id)].append(photo)
        return dict(grouped)
