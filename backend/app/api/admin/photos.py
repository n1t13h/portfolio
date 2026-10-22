"""Admin photo routes: upload tickets, confirm, edit, publish, download flag, delete, order."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from app.api.admin.deps import Auditor, get_auditor, get_photo_service
from app.api.schemas import CamelModel, ResourceId
from app.core.deps import get_storage
from app.integrations.storage import Storage
from app.models import Photo, Status
from app.services.photos import PhotoService

router = APIRouter(prefix="/photos", tags=["admin-photos"])

PhotoId = ResourceId


class UploadTicketOut(CamelModel):
    photo_id: str
    put_url: str
    key: str


class PhotoOut(CamelModel):
    id: str
    title: str
    place: str | None
    aspect_ratio: float
    exif: dict[str, Any]
    taken_at: datetime | None
    status: Status
    allow_download: bool
    sort_position: int
    chapter_id: str | None
    unsplash_id: str | None
    variants: dict[str, str]  # long edge -> public CDN URL
    created_at: datetime


class PhotoPatch(BaseModel):
    title: str | None = None
    place: str | None = None


class AllowDownloadBody(BaseModel):
    allow: bool


class OrderBody(BaseModel):
    ids: list[str]


def to_out(photo: Photo, storage: Storage) -> PhotoOut:
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


@router.post("/upload-url")
def upload_url(photos: PhotoService = Depends(get_photo_service)) -> UploadTicketOut:
    ticket = photos.request_upload()
    return UploadTicketOut(photo_id=ticket.photo_id, put_url=ticket.put_url, key=ticket.key)


@router.post("/{photo_id}/confirm")
def confirm(
    photo_id: PhotoId,
    photos: PhotoService = Depends(get_photo_service),
    storage: Storage = Depends(get_storage),
    audit: Auditor = Depends(get_auditor),
) -> PhotoOut:
    photo = photos.confirm_upload(photo_id)
    audit("photo.upload", photo_id)
    return to_out(photo, storage)


@router.get("")
def list_photos(
    photos: PhotoService = Depends(get_photo_service), storage: Storage = Depends(get_storage)
) -> list[PhotoOut]:
    return [to_out(p, storage) for p in photos.list_all()]


@router.put("/order", status_code=204)
def reorder(
    body: OrderBody,
    photos: PhotoService = Depends(get_photo_service),
    audit: Auditor = Depends(get_auditor),
) -> Response:
    photos.reorder(body.ids)
    audit("photo.reorder")
    return Response(status_code=204)


@router.patch("/{photo_id}")
def update(
    photo_id: PhotoId,
    body: PhotoPatch,
    photos: PhotoService = Depends(get_photo_service),
    storage: Storage = Depends(get_storage),
    audit: Auditor = Depends(get_auditor),
) -> PhotoOut:
    photo = photos.update(photo_id, body.model_dump(exclude_unset=True))
    audit("photo.update", photo_id)
    return to_out(photo, storage)


@router.post("/{photo_id}/publish")
def publish(
    photo_id: PhotoId,
    photos: PhotoService = Depends(get_photo_service),
    storage: Storage = Depends(get_storage),
    audit: Auditor = Depends(get_auditor),
) -> PhotoOut:
    photo = photos.set_status(photo_id, Status.PUBLISHED)
    audit("photo.publish", photo_id)
    return to_out(photo, storage)


@router.post("/{photo_id}/unpublish")
def unpublish(
    photo_id: PhotoId,
    photos: PhotoService = Depends(get_photo_service),
    storage: Storage = Depends(get_storage),
    audit: Auditor = Depends(get_auditor),
) -> PhotoOut:
    photo = photos.set_status(photo_id, Status.DRAFT)
    audit("photo.unpublish", photo_id)
    return to_out(photo, storage)


@router.put("/{photo_id}/allow-download")
def allow_download(
    photo_id: PhotoId,
    body: AllowDownloadBody,
    photos: PhotoService = Depends(get_photo_service),
    storage: Storage = Depends(get_storage),
    audit: Auditor = Depends(get_auditor),
) -> PhotoOut:
    photo = photos.set_allow_download(photo_id, body.allow)
    audit("photo.allow_download", f"{photo_id}={body.allow}")
    return to_out(photo, storage)


@router.delete("/{photo_id}", status_code=204)
def delete(
    photo_id: PhotoId,
    photos: PhotoService = Depends(get_photo_service),
    audit: Auditor = Depends(get_auditor),
) -> Response:
    photos.delete(photo_id)
    audit("photo.delete", photo_id)
    return Response(status_code=204)
