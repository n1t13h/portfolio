"""Dependencies for the public routes."""

from fastapi import Depends, Request

from app.core.deps import get_storage
from app.integrations.storage import Storage
from app.services.catalog import CatalogService


def get_catalog_service(
    request: Request, storage: Storage = Depends(get_storage)
) -> CatalogService:
    return CatalogService(request.app.state.uow_factory, storage)
