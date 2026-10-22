"""Photo storage queries."""

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import Chapter, Photo


class AbstractPhotoRepository(ABC):
    @abstractmethod
    def add(self, photo: Photo) -> None: ...

    @abstractmethod
    def get(self, photo_id: str) -> Photo | None: ...

    @abstractmethod
    def get_many(self, photo_ids: Sequence[str]) -> list[Photo]:
        """The photos that exist among `photo_ids`, in no particular order."""

    @abstractmethod
    def list_ordered(self) -> list[Photo]:
        """Every photo in the admin's global order."""

    @abstractmethod
    def delete(self, photo: Photo) -> None: ...

    @abstractmethod
    def next_sort_position(self) -> int:
        """One past the highest global position (0 when there are no photos)."""

    @abstractmethod
    def unsplash_id_map(self) -> dict[str, str]:
        """Unsplash id -> photo id, for photos that came from Unsplash."""

    @abstractmethod
    def list_in_chapter(self, chapter_id: str) -> list[Photo]:
        """The chapter's photos in display order."""

    @abstractmethod
    def ids_by_chapter(self, chapter_ids: Sequence[str]) -> dict[str, list[str]]:
        """chapter id -> its photo ids in display order (chapters without photos map to [])."""

    @abstractmethod
    def ids_in_collection(self, collection_id: str) -> set[str]: ...

    @abstractmethod
    def next_position_in_chapter(self, chapter_id: str) -> int: ...

    @abstractmethod
    def unassign_from_chapters(self, chapter_ids: Sequence[str]) -> None:
        """Take every photo out of these chapters (the photos themselves stay)."""


class SqlAlchemyPhotoRepository(AbstractPhotoRepository):
    def __init__(self, session: Session) -> None:
        self._s = session

    def add(self, photo: Photo) -> None:
        self._s.add(photo)

    def get(self, photo_id: str) -> Photo | None:
        return self._s.get(Photo, photo_id)

    def get_many(self, photo_ids: Sequence[str]) -> list[Photo]:
        if not photo_ids:
            return []
        return list(self._s.scalars(select(Photo).where(Photo.id.in_(photo_ids))))

    def list_ordered(self) -> list[Photo]:
        stmt = select(Photo).order_by(Photo.sort_position, Photo.created_at, Photo.id)
        return list(self._s.scalars(stmt))

    def delete(self, photo: Photo) -> None:
        self._s.delete(photo)

    def next_sort_position(self) -> int:
        highest = self._s.scalar(select(func.max(Photo.sort_position)))
        return 0 if highest is None else highest + 1

    def unsplash_id_map(self) -> dict[str, str]:
        rows = self._s.execute(
            select(Photo.unsplash_id, Photo.id).where(Photo.unsplash_id.is_not(None))
        )
        return {unsplash_id: photo_id for unsplash_id, photo_id in rows if unsplash_id is not None}

    def list_in_chapter(self, chapter_id: str) -> list[Photo]:
        stmt = (
            select(Photo)
            .where(Photo.chapter_id == chapter_id)
            .order_by(Photo.position_in_chapter, Photo.id)
        )
        return list(self._s.scalars(stmt))

    def ids_by_chapter(self, chapter_ids: Sequence[str]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = defaultdict(list, {cid: [] for cid in chapter_ids})
        if chapter_ids:
            stmt = (
                select(Photo.chapter_id, Photo.id)
                .where(Photo.chapter_id.in_(chapter_ids))
                .order_by(Photo.position_in_chapter, Photo.id)
            )
            for chapter_id, photo_id in self._s.execute(stmt):
                grouped[str(chapter_id)].append(photo_id)
        return dict(grouped)

    def ids_in_collection(self, collection_id: str) -> set[str]:
        stmt = (
            select(Photo.id)
            .join(Chapter, Photo.chapter_id == Chapter.id)
            .where(Chapter.collection_id == collection_id)
        )
        return set(self._s.scalars(stmt))

    def next_position_in_chapter(self, chapter_id: str) -> int:
        stmt = select(func.max(Photo.position_in_chapter)).where(Photo.chapter_id == chapter_id)
        highest = self._s.scalar(stmt)
        return 0 if highest is None else highest + 1

    def unassign_from_chapters(self, chapter_ids: Sequence[str]) -> None:
        if chapter_ids:
            self._s.execute(
                update(Photo).where(Photo.chapter_id.in_(chapter_ids)).values(chapter_id=None)
            )
            self._s.expire_all()  # the bulk UPDATE bypassed any photos already loaded
