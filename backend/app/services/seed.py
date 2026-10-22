"""One-time import of the existing site (snapshot + curation) into the backend.

Safe to run again: photos already present (matched by Unsplash id) are left alone, collections
already present (matched by slug) are skipped, and a rate-limit stop simply resumes next time.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings
from app.integrations.storage import Storage
from app.integrations.unsplash import API_BASE, RateLimited, UnsplashClient, UnsplashPhoto
from app.models import Status
from app.schemas.collections import ChapterDraft
from app.schemas.photos import PhotoOut
from app.schemas.seed import SeedData, SeedPhoto
from app.services.collections import CollectionService
from app.services.photos import PhotoService
from app.uow import UnitOfWorkFactory

log = logging.getLogger(__name__)


@dataclass
class SeedReport:
    imported: int = 0
    already_present: int = 0
    collections_created: int = 0
    remaining: list[str] = field(default_factory=list)  # not imported yet; run again
    missing_from_unsplash: list[str] = field(default_factory=list)  # 404: gone for good


def seed_from_json(
    path: Path,
    uow_factory: UnitOfWorkFactory,
    storage: Storage,
    settings: Settings,
    unsplash: UnsplashClient,
) -> SeedReport:
    data = SeedData.model_validate_json(Path(path).read_text())
    snapshot = {p.id: p for p in data.photos}
    in_order = dict.fromkeys([*data.order, *snapshot])  # curated order, then anything left over
    ordered = [i for i in in_order if i in snapshot]
    report = SeedReport()

    photos = PhotoService(uow_factory, storage, settings)
    with uow_factory() as uow:
        by_unsplash_id = uow.photos.unsplash_id_map()

    for index, unsplash_id in enumerate(ordered):
        if unsplash_id in by_unsplash_id:
            report.already_present += 1
            continue
        try:
            photo = _import_one(
                photos, unsplash, snapshot[unsplash_id], unsplash_id in data.excluded
            )
        except RateLimited:
            report.remaining += [i for i in ordered[index:] if i not in by_unsplash_id]
            return report
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404:
                log.exception("could not import %s", unsplash_id)
                report.remaining.append(unsplash_id)
            else:
                report.missing_from_unsplash.append(unsplash_id)
            continue
        except Exception:  # a network blip should not abandon the other photos
            log.exception("could not import %s", unsplash_id)
            report.remaining.append(unsplash_id)
            continue
        by_unsplash_id[unsplash_id] = photo.id
        report.imported += 1

    if report.remaining:
        return report  # collections and order are applied once every photo is in
    _apply_order(photos, [by_unsplash_id[i] for i in ordered if i in by_unsplash_id])
    report.collections_created = _create_collections(uow_factory, data, by_unsplash_id)
    return report


def _import_one(
    photos: PhotoService, unsplash: UnsplashClient, source: SeedPhoto, excluded: bool
) -> PhotoOut:
    # /photos/{id}/download both reports the download and returns the file URL, so the
    # per-photo details request is unnecessary: about one API request per photo.
    ref = UnsplashPhoto(
        id=source.id,
        title=source.title,
        place=source.place,
        html_url=source.unsplash_url,
        download_location=f"{API_BASE}/photos/{source.id}/download",
    )
    # One transaction creates the photo in its final state. The file's own EXIF wins; the
    # snapshot fills whatever the file lacks.
    return photos.ingest_jpeg(
        unsplash.download_original(ref),
        title=source.title,
        place=source.place,
        status=Status.DRAFT if excluded else Status.PUBLISHED,
        exif_fallback=_snake_case_exif(source.exif or {}),
        unsplash_id=source.id,
        unsplash_url=source.unsplash_url,
    )


def _snake_case_exif(exif: dict[str, Any]) -> dict[str, Any]:
    return {("focal_length" if k == "focalLength" else k): v for k, v in exif.items()}


def _apply_order(photos: PhotoService, seeded_ids: list[str]) -> None:
    others = [p.id for p in photos.list_all() if p.id not in set(seeded_ids)]
    photos.reorder([*seeded_ids, *others])


def _create_collections(
    uow_factory: UnitOfWorkFactory, data: SeedData, by_unsplash_id: dict[str, str]
) -> int:
    collections = CollectionService(uow_factory)
    created = 0
    for source in data.collections:
        with uow_factory() as uow:
            exists = uow.collections.slug_owner(source.slug) is not None
        if exists:
            continue
        chapters = [
            ChapterDraft(
                title=chapter.title,
                note=chapter.note,
                photo_ids=[by_unsplash_id[i] for i in chapter.photo_ids if i in by_unsplash_id],
            )
            for chapter in source.chapters
        ]
        placed = {photo_id for chapter in chapters for photo_id in chapter.photo_ids}
        covers = [by_unsplash_id[i] for i in source.cover_ids if by_unsplash_id.get(i) in placed]
        # One transaction: a collection is never published before its chapters and covers exist.
        collections.create_complete(
            source.slug,
            source.title,
            chapters=chapters,
            cover_photo_ids=covers,
            status=Status.PUBLISHED,
            place=source.place,
            year=source.year,
            intro=source.intro,
        )
        created += 1
    return created
