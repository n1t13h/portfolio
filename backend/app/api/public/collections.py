"""Public collection routes."""

from fastapi import APIRouter, Depends, Request, Response

from app.api.public.caching import cached_json
from app.api.public.deps import get_catalog_service
from app.services.catalog import CatalogService

router = APIRouter(prefix="/collections", tags=["collections"])


@router.get("")
def list_collections(
    request: Request, catalog: CatalogService = Depends(get_catalog_service)
) -> Response:
    return cached_json(request, catalog.collections())


@router.get("/{slug}")
def get_collection(
    slug: str, request: Request, catalog: CatalogService = Depends(get_catalog_service)
) -> Response:
    return cached_json(request, catalog.collection(slug))
