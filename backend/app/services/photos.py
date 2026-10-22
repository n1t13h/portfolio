"""Photo lifecycle: upload tickets, ingest, metadata, publishing, deletion, ordering."""

import logging
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import Conflict, InvalidRequest, NotFound
from app.integrations.storage import Bucket, Storage
from app.models import Photo, Status
from app.services import sync_state
from app.services.images import InvalidImage, process_jpeg
from app.services.ordering import apply_order

log = logging.getLogger(__name__)

UPLOAD_URL_TTL_SECONDS = 600
EDITABLE_FIELDS = {"title", "place"}
IMMUTABLE = "public, max-age=31536000, immutable"  # variant files never change once written


def original_key(photo_id: str) -> str:
    return f"originals/{photo_id}.jpg"


@dataclass(frozen=True)
class UploadTicket:
    photo_id: str
    put_url: str
    key: str


class PhotoService:
    def __init__(self, session: Session, storage: Storage, settings: Settings) -> None:
        self._db = session
        self._storage = storage
        self._settings = settings

    # -- upload ---------------------------------------------------------------------------

    def request_upload(self) -> UploadTicket:
        photo_id = uuid.uuid4().hex
        key = original_key(photo_id)
        url = self._storage.presign_put(Bucket.PRIVATE, key, "image/jpeg", UPLOAD_URL_TTL_SECONDS)
        return UploadTicket(photo_id, url, key)

    def confirm_upload(self, photo_id: str) -> Photo:
        """Process a file the browser has PUT to the private bucket and create the photo."""
        if self._db.get(Photo, photo_id) is not None:
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
        unsplash_id: str | None = None,
        unsplash_url: str | None = None,
    ) -> Photo:
        """Process JPEG bytes, store every file in R2 and insert a draft photo."""
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

            photo = Photo(
                id=pid,
                title=title,
                place=place,
                aspect_ratio=processed.aspect_ratio,
                exif=processed.exif,
                taken_at=processed.taken_at,
                sort_position=self._next_position(),
                original_key=original_key(pid),
                variant_keys=variant_keys,
                download_key=download_key,
                unsplash_id=unsplash_id,
                unsplash_url=unsplash_url,
            )
            self._db.add(photo)
            self._db.commit()
        except Exception:
            self._db.rollback()  # keep the caller's session usable
            self._remove_quietly(written)  # and leave no orphaned files behind
            raise
        return photo

    # -- read / edit ----------------------------------------------------------------------

    def list_all(self) -> Sequence[Photo]:
        stmt = select(Photo).order_by(Photo.sort_position, Photo.created_at, Photo.id)
        return self._db.scalars(stmt).all()

    def get(self, photo_id: str) -> Photo:
        photo = self._db.get(Photo, photo_id)
        if photo is None:
            raise NotFound("photo not found")
        return photo

    def update(self, photo_id: str, changes: Mapping[str, Any]) -> Photo:
        if not set(changes) <= EDITABLE_FIELDS:
            raise InvalidRequest(f"only {sorted(EDITABLE_FIELDS)} can be edited")
        if "title" in changes and changes["title"] is None:
            raise InvalidRequest("title cannot be null")  # place may be cleared; title may not
        photo = self.get(photo_id)
        for name, value in changes.items():
            setattr(photo, name, value)
        self._db.commit()
        return photo

    def set_status(self, photo_id: str, status: Status) -> Photo:
        photo = self.get(photo_id)
        photo.status = status
        self._db.commit()
        return photo

    def set_allow_download(self, photo_id: str, allow: bool) -> Photo:
        photo = self.get(photo_id)
        photo.allow_download = allow
        self._db.commit()
        return photo

    def delete(self, photo_id: str) -> None:
        photo = self.get(photo_id)
        doomed = [(Bucket.PUBLIC, key) for key in photo.variant_keys.values()]
        doomed += [(Bucket.PRIVATE, key) for key in (photo.original_key, photo.download_key) if key]
        if photo.unsplash_id:  # so the next sync does not bring it back
            sync_state.skip(self._db, photo.unsplash_id, "deleted")
        self._db.delete(photo)
        self._db.commit()
        # Files go last and best-effort: a leftover file is harmless, a row pointing at
        # deleted files would show visitors broken images.
        self._remove_quietly(doomed)

    def _remove_quietly(self, objects: Sequence[tuple[Bucket, str]]) -> None:
        for bucket, key in objects:
            try:
                self._storage.delete(bucket, key)
            except Exception:
                log.warning("could not remove %s/%s from storage", bucket.value, key, exc_info=True)

    def reorder(self, ordered_ids: Sequence[str]) -> None:
        apply_order(self.list_all(), ordered_ids, "sort_position")
        self._db.commit()

    def _next_position(self) -> int:
        highest = self._db.scalar(select(func.max(Photo.sort_position)))
        return 0 if highest is None else highest + 1
