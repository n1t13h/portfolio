"""Public response models. They carry no draft state, keys or internal ids."""

from pydantic import Field

from app.schemas.base import CamelModel


class PublicExif(CamelModel):
    camera: str | None = None
    focal_length: float | None = None
    aperture: float | None = None
    shutter: str | None = None
    iso: int | None = None


class PublicPhoto(CamelModel):
    id: str
    title: str
    place: str | None
    aspect_ratio: float
    exif: PublicExif
    variants: dict[str, str]  # long edge in px -> CDN URL
    allow_download: bool
    download_url: str | None  # a path on this API; only present when downloads are allowed


class PublicChapter(CamelModel):
    title: str
    note: str
    photos: list[PublicPhoto]


class PublicCollectionSummary(CamelModel):
    slug: str
    title: str
    place: str
    year: str
    intro: str
    covers: list[PublicPhoto]


class PublicCollection(PublicCollectionSummary):
    chapters: list[PublicChapter]
    photos: list[PublicPhoto] = Field(description="every photo, in chapter order")
