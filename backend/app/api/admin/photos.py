"""Admin photo routes: upload tickets, confirm, edit, publish, download flag, delete, order."""

from fastapi import APIRouter, Depends, Response

from app.api.admin.deps import get_photo_service
from app.api.params import ResourceId
from app.models import Status
from app.schemas.common import IdsBody
from app.schemas.photos import AllowDownloadBody, PhotoOut, PhotoPatch, UploadTicketOut
from app.services.photos import PhotoService

router = APIRouter(prefix="/photos", tags=["admin-photos"])


@router.post("/upload-url")
def upload_url(photos: PhotoService = Depends(get_photo_service)) -> UploadTicketOut:
    return photos.request_upload()


@router.post("/{photo_id}/confirm")
def confirm(
    photo_id: ResourceId,
    photos: PhotoService = Depends(get_photo_service),
) -> PhotoOut:
    photo = photos.confirm_upload(photo_id)
    return photo


@router.get("")
def list_photos(photos: PhotoService = Depends(get_photo_service)) -> list[PhotoOut]:
    return photos.list_all()


@router.put("/order", status_code=204)
def reorder(
    body: IdsBody,
    photos: PhotoService = Depends(get_photo_service),
) -> Response:
    photos.reorder(body.ids)
    return Response(status_code=204)


@router.patch("/{photo_id}")
def update(
    photo_id: ResourceId,
    body: PhotoPatch,
    photos: PhotoService = Depends(get_photo_service),
) -> PhotoOut:
    photo = photos.update(photo_id, body.model_dump(exclude_unset=True))
    return photo


@router.post("/{photo_id}/publish")
def publish(
    photo_id: ResourceId,
    photos: PhotoService = Depends(get_photo_service),
) -> PhotoOut:
    photo = photos.set_status(photo_id, Status.PUBLISHED)
    return photo


@router.post("/{photo_id}/unpublish")
def unpublish(
    photo_id: ResourceId,
    photos: PhotoService = Depends(get_photo_service),
) -> PhotoOut:
    photo = photos.set_status(photo_id, Status.DRAFT)
    return photo


@router.put("/{photo_id}/allow-download")
def allow_download(
    photo_id: ResourceId,
    body: AllowDownloadBody,
    photos: PhotoService = Depends(get_photo_service),
) -> PhotoOut:
    photo = photos.set_allow_download(photo_id, body.allow)
    return photo


@router.delete("/{photo_id}", status_code=204)
def delete(
    photo_id: ResourceId,
    photos: PhotoService = Depends(get_photo_service),
) -> Response:
    photos.delete(photo_id)
    return Response(status_code=204)
