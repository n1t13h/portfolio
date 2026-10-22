"""Admin collection and chapter models."""

from pydantic import BaseModel, ConfigDict, Field

from app.models import Status
from app.schemas.base import CamelModel

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


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


class CollectionCreate(BaseModel):
    slug: str = Field(pattern=SLUG_PATTERN)
    title: str
    place: str = ""
    year: str = ""
    intro: str = ""


class CollectionPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str | None = Field(default=None, pattern=SLUG_PATTERN)
    title: str | None = None
    place: str | None = None
    year: str | None = None
    intro: str | None = None


class ChapterDraft(BaseModel):
    """A chapter to build together with its collection (see `CollectionService.create_complete`)."""

    title: str = ""
    note: str = ""
    photo_ids: list[str] = []


class ChapterCreate(BaseModel):
    title: str = ""
    note: str = ""


class ChapterPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    note: str | None = None
