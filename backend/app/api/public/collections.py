"""Public collection routes."""

from fastapi import APIRouter, Depends, Request, Response

from app.api.public.caching import cached_json
from app.api.public.deps import get_public_views
from app.core.deps import get_storage
from app.integrations.storage import Storage
from app.services.mappers import public_detail, public_summary
from app.services.public_views import PublicViews

router = APIRouter(prefix="/collections", tags=["collections"])


@router.get("")
def list_collections(
    request: Request,
    views: PublicViews = Depends(get_public_views),
    storage: Storage = Depends(get_storage),
) -> Response:
    return cached_json(request, [public_summary(v, storage) for v in views.collections()])


@router.get("/{slug}")
def get_collection(
    slug: str,
    request: Request,
    views: PublicViews = Depends(get_public_views),
    storage: Storage = Depends(get_storage),
) -> Response:
    return cached_json(request, public_detail(views.collection(slug), storage))
