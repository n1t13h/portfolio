"""Public photo routes: the global photo list and the opt-in download redirect."""

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse

from app.api.public.caching import cached_json
from app.api.public.deps import get_public_views
from app.api.public.schemas import photo_out
from app.api.schemas import ResourceId
from app.core.deps import get_storage
from app.integrations.storage import Bucket, Storage
from app.services.public_views import PublicViews

router = APIRouter(prefix="/photos", tags=["photos"])

DOWNLOAD_URL_TTL_SECONDS = 300


@router.get("")
def list_photos(
    request: Request,
    views: PublicViews = Depends(get_public_views),
    storage: Storage = Depends(get_storage),
) -> Response:
    return cached_json(request, [photo_out(p, storage) for p in views.photos()])


@router.get("/{photo_id}/download")
def download(
    photo_id: ResourceId,
    views: PublicViews = Depends(get_public_views),
    storage: Storage = Depends(get_storage),
) -> RedirectResponse:
    photo = views.downloadable_photo(photo_id)
    assert photo.download_key is not None
    url = storage.presign_get(Bucket.PRIVATE, photo.download_key, DOWNLOAD_URL_TTL_SECONDS)
    return RedirectResponse(url, status_code=302, headers={"Cache-Control": "no-store"})
