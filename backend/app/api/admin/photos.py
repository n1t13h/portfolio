"""Admin photo routes: upload tickets, confirm, edit, publish, download flag, delete, order."""

from fastapi import APIRouter, Depends, Response

from app.api.admin.deps import Auditor, get_auditor, get_photo_service
from app.api.params import ResourceId
from app.core.deps import get_storage
from app.integrations.storage import Storage
from app.models import Status
from app.schemas.common import IdsBody
from app.schemas.photos import AllowDownloadBody, PhotoOut, PhotoPatch, UploadTicketOut
from app.services.mappers import admin_photo
from app.services.photos import PhotoService

router = APIRouter(prefix="/photos", tags=["admin-photos"])

PhotoId = ResourceId


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
    return admin_photo(photo, storage)


@router.get("")
def list_photos(
    photos: PhotoService = Depends(get_photo_service), storage: Storage = Depends(get_storage)
) -> list[PhotoOut]:
    return [admin_photo(p, storage) for p in photos.list_all()]


@router.put("/order", status_code=204)
def reorder(
    body: IdsBody,
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
    return admin_photo(photo, storage)


@router.post("/{photo_id}/publish")
def publish(
    photo_id: PhotoId,
    photos: PhotoService = Depends(get_photo_service),
    storage: Storage = Depends(get_storage),
    audit: Auditor = Depends(get_auditor),
) -> PhotoOut:
    photo = photos.set_status(photo_id, Status.PUBLISHED)
    audit("photo.publish", photo_id)
    return admin_photo(photo, storage)


@router.post("/{photo_id}/unpublish")
def unpublish(
    photo_id: PhotoId,
    photos: PhotoService = Depends(get_photo_service),
    storage: Storage = Depends(get_storage),
    audit: Auditor = Depends(get_auditor),
) -> PhotoOut:
    photo = photos.set_status(photo_id, Status.DRAFT)
    audit("photo.unpublish", photo_id)
    return admin_photo(photo, storage)


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
    return admin_photo(photo, storage)


@router.delete("/{photo_id}", status_code=204)
def delete(
    photo_id: PhotoId,
    photos: PhotoService = Depends(get_photo_service),
    audit: Auditor = Depends(get_auditor),
) -> Response:
    photos.delete(photo_id)
    audit("photo.delete", photo_id)
    return Response(status_code=204)
