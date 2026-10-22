"""Public photo routes: the global photo list and the opt-in download redirect."""

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse

from app.api.params import ResourceId
from app.api.public.caching import cached_json
from app.api.public.deps import get_catalog_service
from app.services.catalog import CatalogService

router = APIRouter(prefix="/photos", tags=["photos"])


@router.get("")
def list_photos(
    request: Request, catalog: CatalogService = Depends(get_catalog_service)
) -> Response:
    return cached_json(request, catalog.photos())


@router.get("/{photo_id}/download")
def download(
    photo_id: ResourceId, catalog: CatalogService = Depends(get_catalog_service)
) -> RedirectResponse:
    url = catalog.download_url(photo_id)
    return RedirectResponse(url, status_code=302, headers={"Cache-Control": "no-store"})
