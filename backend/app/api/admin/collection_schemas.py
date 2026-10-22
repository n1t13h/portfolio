"""Request and response models for the collection and chapter routes."""

from pydantic import BaseModel, Field

from app.api.schemas import CamelModel
from app.models import Chapter, Collection, Status
from app.services.collections import SLUG_PATTERN


class ChapterOut(CamelModel):
    id: str
    collection_id: str
    title: str
    note: str
    position: int
    photo_ids: list[str]  # in display order


class CollectionOut(CamelModel):
    id: str
    slug: str
    title: str
    place: str
    year: str
    intro: str
    status: Status
    sort_position: int
    cover_photo_ids: list[str]
    chapters: list[ChapterOut]


def chapter_out(chapter: Chapter) -> ChapterOut:
    return ChapterOut(
        id=chapter.id,
        collection_id=chapter.collection_id,
        title=chapter.title,
        note=chapter.note,
        position=chapter.position,
        photo_ids=[p.id for p in chapter.photos],
    )


def collection_out(collection: Collection) -> CollectionOut:
    return CollectionOut(
        id=collection.id,
        slug=collection.slug,
        title=collection.title,
        place=collection.place,
        year=collection.year,
        intro=collection.intro,
        status=collection.status,
        sort_position=collection.sort_position,
        cover_photo_ids=list(collection.cover_photo_ids),
        chapters=[chapter_out(ch) for ch in collection.chapters],
    )


class CollectionCreate(BaseModel):
    slug: str = Field(pattern=SLUG_PATTERN)
    title: str
    place: str = ""
    year: str = ""
    intro: str = ""


class CollectionPatch(BaseModel):
    slug: str | None = Field(default=None, pattern=SLUG_PATTERN)
    title: str | None = None
    place: str | None = None
    year: str | None = None
    intro: str | None = None


class ChapterCreate(BaseModel):
    title: str = ""
    note: str = ""


class ChapterPatch(BaseModel):
    title: str | None = None
    note: str | None = None


class IdsBody(BaseModel):
    ids: list[str]


class PhotoIdsBody(CamelModel):
    photo_ids: list[str]
