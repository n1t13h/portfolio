"""Builds the admin router, mounted under the secret path prefix."""

from fastapi import APIRouter, Depends

from app.api.admin import auth, chapters, collections, photos, sync
from app.api.admin.deps import csrf_guard, require_admin
from app.core.config import Settings


def build_admin_router(settings: Settings) -> APIRouter:
    router = APIRouter(
        prefix=f"/a/{settings.admin_path_prefix}", dependencies=[Depends(csrf_guard)]
    )
    router.include_router(auth.router)
    protected = [Depends(require_admin)]
    router.include_router(photos.router, dependencies=protected)
    router.include_router(collections.router, dependencies=protected)
    router.include_router(chapters.router, dependencies=protected)
    router.include_router(sync.router, dependencies=protected)
    return router
