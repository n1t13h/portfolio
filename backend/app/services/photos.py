"""Photo lifecycle: upload tickets, ingest, metadata, publishing, deletion, ordering."""

import logging
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from app.core.config import Settings
from app.core.errors import Conflict, InvalidRequest, NotFound
from app.integrations.storage import Bucket, Storage
from app.models import Photo, Status
from app.schemas.photos import PhotoOut, UploadTicketOut
from app.services import sync_state
from app.services.images import InvalidImage, process_jpeg
from app.services.mappers import admin_photo
from app.services.ordering import apply_order
from app.uow import AbstractUnitOfWork, UnitOfWorkFactory

log = logging.getLogger(__name__)

UPLOAD_URL_TTL_SECONDS = 600
EDITABLE_FIELDS = {"title", "place"}
IMMUTABLE = "public, max-age=31536000, immutable"  # variant files never change once written


def original_key(photo_id: str) -> str:
    return f"originals/{photo_id}.jpg"


class PhotoService:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, storage: Storage, settings: Settings
    ) -> None:
        self._uow = uow_factory
        self._storage = storage
        self._settings = settings

    # -- upload ---------------------------------------------------------------------------

    def request_upload(self) -> UploadTicketOut:
        photo_id = uuid.uuid4().hex
        key = original_key(photo_id)
        url = self._storage.presign_put(Bucket.PRIVATE, key, "image/jpeg", UPLOAD_URL_TTL_SECONDS)
        return UploadTicketOut(photo_id=photo_id, put_url=url, key=key)

    def confirm_upload(self, photo_id: str) -> PhotoOut:
        """Process a file the browser has PUT to the private bucket and create the photo."""
        with self._uow() as uow:
            if uow.photos.get(photo_id) is not None:
                raise Conflict("already confirmed")
        key = original_key(photo_id)
        if not self._storage.exists(Bucket.PRIVATE, key):
            raise NotFound("no uploaded file for this id")
        try:
            if self._storage.size(Bucket.PRIVATE, key) > self._settings.max_upload_bytes:
                raise InvalidImage("file too large")
            data = self._storage.get_bytes(Bucket.PRIVATE, key)
            return self.ingest_jpeg(data, photo_id=photo_id, store_original=False)
        except InvalidImage:
            self._storage.delete(Bucket.PRIVATE, key)
            raise

    def ingest_jpeg(
        self,
        data: bytes,
        *,
        photo_id: str | None = None,
        store_original: bool = True,
        title: str = "",
        place: str | None = None,
        status: Status = Status.DRAFT,
        exif_fallback: Mapping[str, Any] | None = None,
        unsplash_id: str | None = None,
        unsplash_url: str | None = None,
    ) -> PhotoOut:
        """Process JPEG bytes, store every file in R2 and save the photo in one transaction.

        `exif_fallback` fills metadata the file itself lacks; the file's own EXIF wins.
        """
        if len(data) > self._settings.max_upload_bytes:
            raise InvalidImage("file too large")
        processed = process_jpeg(data, max_pixels=self._settings.max_image_pixels)
        pid = photo_id or uuid.uuid4().hex
        written: list[tuple[Bucket, str]] = []
        try:
            if store_original:
                self._storage.put_bytes(Bucket.PRIVATE, original_key(pid), data, "image/jpeg")
                written.append((Bucket.PRIVATE, original_key(pid)))
            variant_keys: dict[str, str] = {}
            for edge, blob in processed.variants.items():
                key = f"photos/{pid}/{edge}.webp"
                self._storage.put_bytes(Bucket.PUBLIC, key, blob, "image/webp", IMMUTABLE)
                written.append((Bucket.PUBLIC, key))
                variant_keys[str(edge)] = key
            download_key = f"downloads/{pid}.jpg"
            self._storage.put_bytes(
                Bucket.PRIVATE, download_key, processed.download_jpeg, "image/jpeg"
            )
            written.append((Bucket.PRIVATE, download_key))

            with self._uow() as uow:
                photo = Photo(
                    id=pid,
                    title=title,
                    place=place,
                    aspect_ratio=processed.aspect_ratio,
                    exif={**(exif_fallback or {}), **processed.exif},
                    taken_at=processed.taken_at,
                    status=status,
                    sort_position=uow.photos.next_sort_position(),
                    original_key=original_key(pid),
                    variant_keys=variant_keys,
                    download_key=download_key,
                    unsplash_id=unsplash_id,
                    unsplash_url=unsplash_url,
                )
                uow.photos.add(photo)
                uow.commit()
                return admin_photo(photo, self._storage)
        except Exception:
            self._remove_quietly(written)  # leave no orphaned files behind
            raise

    # -- read / edit ----------------------------------------------------------------------

    def list_all(self) -> list[PhotoOut]:
        with self._uow() as uow:
            return [admin_photo(p, self._storage) for p in uow.photos.list_ordered()]

    def get(self, photo_id: str) -> PhotoOut:
        with self._uow() as uow:
            return admin_photo(self._get(uow, photo_id), self._storage)

    def update(self, photo_id: str, changes: Mapping[str, Any]) -> PhotoOut:
        if not set(changes) <= EDITABLE_FIELDS:
            raise InvalidRequest(f"only {sorted(EDITABLE_FIELDS)} can be edited")
        if "title" in changes and changes["title"] is None:
            raise InvalidRequest("title cannot be null")  # place may be cleared; title may not
        with self._uow() as uow:
            photo = self._get(uow, photo_id)
            for name, value in changes.items():
                setattr(photo, name, value)
            uow.commit()
            return admin_photo(photo, self._storage)

    def set_status(self, photo_id: str, status: Status) -> PhotoOut:
        with self._uow() as uow:
            photo = self._get(uow, photo_id)
            photo.status = status
            uow.commit()
            return admin_photo(photo, self._storage)

    def set_allow_download(self, photo_id: str, allow: bool) -> PhotoOut:
        with self._uow() as uow:
            photo = self._get(uow, photo_id)
            photo.allow_download = allow
            uow.commit()
            return admin_photo(photo, self._storage)

    def delete(self, photo_id: str) -> None:
        with self._uow() as uow:
            photo = self._get(uow, photo_id)
            doomed = [(Bucket.PUBLIC, key) for key in photo.variant_keys.values()]
            doomed += [
                (Bucket.PRIVATE, key) for key in (photo.original_key, photo.download_key) if key
            ]
            if photo.unsplash_id:  # so the next sync does not bring it back
                sync_state.skip(uow.sync_state.get_or_create(), photo.unsplash_id, "deleted")
            uow.photos.delete(photo)
            uow.commit()
        # Files go last and best-effort: a leftover file is harmless, a row pointing at
        # deleted files would show visitors broken images.
        self._remove_quietly(doomed)

    def reorder(self, ordered_ids: Sequence[str]) -> None:
        with self._uow() as uow:
            apply_order(uow.photos.list_ordered(), ordered_ids, "sort_position")
            uow.commit()

    # -- helpers --------------------------------------------------------------------------

    @staticmethod
    def _get(uow: AbstractUnitOfWork, photo_id: str) -> Photo:
        photo = uow.photos.get(photo_id)
        if photo is None:
            raise NotFound("photo not found")
        return photo

    def _remove_quietly(self, objects: Sequence[tuple[Bucket, str]]) -> None:
        for bucket, key in objects:
            try:
                self._storage.delete(bucket, key)
            except Exception:
                log.warning("could not remove %s/%s from storage", bucket.value, key, exc_info=True)
