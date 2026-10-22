"""Public response models. They carry no draft state, keys or internal ids."""

from pydantic import Field

from app.api.schemas import CamelModel
from app.integrations.storage import Storage
from app.models import Photo
from app.services.public_views import ChapterView, CollectionDetail, CollectionView


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


def photo_out(photo: Photo, storage: Storage) -> PublicPhoto:
    return PublicPhoto(
        id=photo.id,
        title=photo.title,
        place=photo.place,
        aspect_ratio=photo.aspect_ratio,
        exif=PublicExif(**photo.exif),
        variants={edge: storage.public_url(key) for edge, key in photo.variant_keys.items()},
        allow_download=photo.allow_download,
        download_url=f"/photos/{photo.id}/download" if photo.allow_download else None,
    )


def summary_out(view: CollectionView, storage: Storage) -> PublicCollectionSummary:
    c = view.collection
    return PublicCollectionSummary(
        slug=c.slug,
        title=c.title,
        place=c.place,
        year=c.year,
        intro=c.intro,
        covers=[photo_out(p, storage) for p in view.covers],
    )


def _chapter_out(view: ChapterView, storage: Storage) -> PublicChapter:
    return PublicChapter(
        title=view.chapter.title,
        note=view.chapter.note,
        photos=[photo_out(p, storage) for p in view.photos],
    )


def detail_out(detail: CollectionDetail, storage: Storage) -> PublicCollection:
    c = detail.collection
    return PublicCollection(
        slug=c.slug,
        title=c.title,
        place=c.place,
        year=c.year,
        intro=c.intro,
        covers=[photo_out(p, storage) for p in detail.covers],
        chapters=[_chapter_out(ch, storage) for ch in detail.chapters],
        photos=[photo_out(p, storage) for ch in detail.chapters for p in ch.photos],
    )
