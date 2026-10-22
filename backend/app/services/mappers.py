"""Entity -> response-schema conversions."""

from collections.abc import Mapping, Sequence

from app.integrations.storage import Storage
from app.models import Chapter, Collection, Photo
from app.schemas.collections import ChapterOut, CollectionOut
from app.schemas.photos import PhotoOut
from app.schemas.public import (
    PublicChapter,
    PublicCollection,
    PublicCollectionSummary,
    PublicExif,
    PublicPhoto,
)
from app.services.public_views import ChapterView, CollectionDetail, CollectionView


def admin_photo(photo: Photo, storage: Storage) -> PhotoOut:
    return PhotoOut(
        id=photo.id,
        title=photo.title,
        place=photo.place,
        aspect_ratio=photo.aspect_ratio,
        exif=photo.exif,
        taken_at=photo.taken_at,
        status=photo.status,
        allow_download=photo.allow_download,
        sort_position=photo.sort_position,
        chapter_id=photo.chapter_id,
        unsplash_id=photo.unsplash_id,
        variants={edge: storage.public_url(key) for edge, key in photo.variant_keys.items()},
        created_at=photo.created_at,
    )


def admin_chapter(chapter: Chapter, photo_ids: Sequence[str]) -> ChapterOut:
    return ChapterOut(
        id=chapter.id,
        collection_id=chapter.collection_id,
        title=chapter.title,
        note=chapter.note,
        position=chapter.position,
        photo_ids=list(photo_ids),
    )


def admin_collection(
    collection: Collection,
    chapters: Sequence[Chapter],
    photo_ids_by_chapter: Mapping[str, Sequence[str]],
) -> CollectionOut:
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
        chapters=[admin_chapter(ch, photo_ids_by_chapter[ch.id]) for ch in chapters],
    )


def public_photo(photo: Photo, storage: Storage) -> PublicPhoto:
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


def public_summary(view: CollectionView, storage: Storage) -> PublicCollectionSummary:
    c = view.collection
    return PublicCollectionSummary(
        slug=c.slug,
        title=c.title,
        place=c.place,
        year=c.year,
        intro=c.intro,
        covers=[public_photo(p, storage) for p in view.covers],
    )


def _public_chapter(view: ChapterView, storage: Storage) -> PublicChapter:
    return PublicChapter(
        title=view.chapter.title,
        note=view.chapter.note,
        photos=[public_photo(p, storage) for p in view.photos],
    )


def public_detail(detail: CollectionDetail, storage: Storage) -> PublicCollection:
    c = detail.collection
    return PublicCollection(
        slug=c.slug,
        title=c.title,
        place=c.place,
        year=c.year,
        intro=c.intro,
        covers=[public_photo(p, storage) for p in detail.covers],
        chapters=[_public_chapter(ch, storage) for ch in detail.chapters],
        photos=[public_photo(p, storage) for ch in detail.chapters for p in ch.photos],
    )
