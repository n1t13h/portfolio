"""Collection and chapter storage queries."""

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Chapter, Collection


class AbstractCollectionRepository(ABC):
    # -- collections
    @abstractmethod
    def add(self, collection: Collection) -> None: ...

    @abstractmethod
    def get(self, collection_id: str) -> Collection | None: ...

    @abstractmethod
    def delete(self, collection: Collection) -> None: ...

    @abstractmethod
    def list_ordered(self) -> list[Collection]:
        """Every collection in the admin's order."""

    @abstractmethod
    def slug_owner(self, slug: str) -> str | None:
        """The id of the collection using `slug`, if any."""

    @abstractmethod
    def next_sort_position(self) -> int: ...

    # -- chapters
    @abstractmethod
    def add_chapter(self, chapter: Chapter) -> None: ...

    @abstractmethod
    def get_chapter(self, chapter_id: str) -> Chapter | None: ...

    @abstractmethod
    def delete_chapter(self, chapter: Chapter) -> None: ...

    @abstractmethod
    def list_chapters(self, collection_id: str) -> list[Chapter]:
        """The collection's chapters in display order."""

    @abstractmethod
    def chapters_by_collection(self, collection_ids: Sequence[str]) -> dict[str, list[Chapter]]:
        """collection id -> its chapters in order (collections without chapters map to [])."""

    @abstractmethod
    def next_chapter_position(self, collection_id: str) -> int: ...

    @abstractmethod
    def collection_ids_of_chapters(self, chapter_ids: Sequence[str]) -> set[str]: ...


class SqlAlchemyCollectionRepository(AbstractCollectionRepository):
    def __init__(self, session: Session) -> None:
        self._s = session

    def add(self, collection: Collection) -> None:
        self._s.add(collection)

    def get(self, collection_id: str) -> Collection | None:
        return self._s.get(Collection, collection_id)

    def delete(self, collection: Collection) -> None:
        self._s.delete(collection)

    def list_ordered(self) -> list[Collection]:
        stmt = select(Collection).order_by(Collection.sort_position, Collection.id)
        return list(self._s.scalars(stmt))

    def slug_owner(self, slug: str) -> str | None:
        return self._s.scalar(select(Collection.id).where(Collection.slug == slug))

    def next_sort_position(self) -> int:
        highest = self._s.scalar(select(func.max(Collection.sort_position)))
        return 0 if highest is None else highest + 1

    def add_chapter(self, chapter: Chapter) -> None:
        self._s.add(chapter)

    def get_chapter(self, chapter_id: str) -> Chapter | None:
        return self._s.get(Chapter, chapter_id)

    def delete_chapter(self, chapter: Chapter) -> None:
        self._s.delete(chapter)

    def list_chapters(self, collection_id: str) -> list[Chapter]:
        return self.chapters_by_collection([collection_id])[collection_id]

    def chapters_by_collection(self, collection_ids: Sequence[str]) -> dict[str, list[Chapter]]:
        grouped: dict[str, list[Chapter]] = defaultdict(list, {cid: [] for cid in collection_ids})
        if collection_ids:
            stmt = (
                select(Chapter)
                .where(Chapter.collection_id.in_(collection_ids))
                .order_by(Chapter.position, Chapter.id)
            )
            for chapter in self._s.scalars(stmt):
                grouped[chapter.collection_id].append(chapter)
        return dict(grouped)

    def next_chapter_position(self, collection_id: str) -> int:
        stmt = select(func.max(Chapter.position)).where(Chapter.collection_id == collection_id)
        highest = self._s.scalar(stmt)
        return 0 if highest is None else highest + 1

    def collection_ids_of_chapters(self, chapter_ids: Sequence[str]) -> set[str]:
        if not chapter_ids:
            return set()
        stmt = select(Chapter.collection_id).where(Chapter.id.in_(chapter_ids))
        return set(self._s.scalars(stmt))
