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


def public_summary(
    collection: Collection, covers: Sequence[Photo], storage: Storage
) -> PublicCollectionSummary:
    return PublicCollectionSummary(
        slug=collection.slug,
        title=collection.title,
        place=collection.place,
        year=collection.year,
        intro=collection.intro,
        covers=[public_photo(p, storage) for p in covers],
    )


def public_collection(
    collection: Collection,
    covers: Sequence[Photo],
    chapters: Sequence[tuple[Chapter, Sequence[Photo]]],
    storage: Storage,
) -> PublicCollection:
    return PublicCollection(
        slug=collection.slug,
        title=collection.title,
        place=collection.place,
        year=collection.year,
        intro=collection.intro,
        covers=[public_photo(p, storage) for p in covers],
        chapters=[
            PublicChapter(
                title=chapter.title,
                note=chapter.note,
                photos=[public_photo(p, storage) for p in photos],
            )
            for chapter, photos in chapters
        ],
        photos=[public_photo(p, storage) for _, photos in chapters for p in photos],
    )
