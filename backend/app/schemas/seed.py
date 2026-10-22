"""Models for the seed file produced by scripts/export-curation.mjs."""

from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _Seed(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SeedPhoto(_Seed):
    id: str
    title: str
    place: str | None = None
    exif: dict[str, Any] | None = None
    unsplash_url: str


class SeedChapter(_Seed):
    title: str
    note: str
    photo_ids: list[str]


class SeedCollection(_Seed):
    slug: str
    title: str
    place: str
    year: str
    intro: str
    cover_ids: list[str]
    chapters: list[SeedChapter]


class SeedData(_Seed):
    photos: list[SeedPhoto]
    order: list[str]
    excluded: list[str] = []
    collections: list[SeedCollection]
