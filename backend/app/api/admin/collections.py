"""Admin collection routes: CRUD, publishing, ordering, covers, and creating chapters."""

from fastapi import APIRouter, Depends, Response

from app.api.admin.deps import get_collection_service
from app.api.params import ResourceId
from app.models import Status
from app.schemas.collections import (
    ChapterCreate,
    ChapterOut,
    CollectionCreate,
    CollectionOut,
    CollectionPatch,
)
from app.schemas.common import IdsBody, PhotoIdsBody
from app.services.collections import CollectionService

router = APIRouter(prefix="/collections", tags=["admin-collections"])


@router.get("")
def list_collections(
    collections: CollectionService = Depends(get_collection_service),
) -> list[CollectionOut]:
    return collections.list_collections()


@router.post("", status_code=201)
def create(
    body: CollectionCreate,
    collections: CollectionService = Depends(get_collection_service),
) -> CollectionOut:
    collection = collections.create_collection(**body.model_dump())
    return collection


@router.put("/order", status_code=204)
def reorder(
    body: IdsBody,
    collections: CollectionService = Depends(get_collection_service),
) -> Response:
    collections.reorder_collections(body.ids)
    return Response(status_code=204)


@router.get("/{collection_id}")
def get(
    collection_id: ResourceId, collections: CollectionService = Depends(get_collection_service)
) -> CollectionOut:
    return collections.get_collection(collection_id)


@router.patch("/{collection_id}")
def update(
    collection_id: ResourceId,
    body: CollectionPatch,
    collections: CollectionService = Depends(get_collection_service),
) -> CollectionOut:
    collection = collections.update_collection(collection_id, body)
    return collection


@router.delete("/{collection_id}", status_code=204)
def delete(
    collection_id: ResourceId,
    collections: CollectionService = Depends(get_collection_service),
) -> Response:
    collections.delete_collection(collection_id)
    return Response(status_code=204)


@router.post("/{collection_id}/publish")
def publish(
    collection_id: ResourceId,
    collections: CollectionService = Depends(get_collection_service),
) -> CollectionOut:
    collection = collections.set_status(collection_id, Status.PUBLISHED)
    return collection


@router.post("/{collection_id}/unpublish")
def unpublish(
    collection_id: ResourceId,
    collections: CollectionService = Depends(get_collection_service),
) -> CollectionOut:
    collection = collections.set_status(collection_id, Status.DRAFT)
    return collection


@router.put("/{collection_id}/covers")
def set_covers(
    collection_id: ResourceId,
    body: PhotoIdsBody,
    collections: CollectionService = Depends(get_collection_service),
) -> CollectionOut:
    collection = collections.set_covers(collection_id, body.photo_ids)
    return collection


@router.post("/{collection_id}/chapters", status_code=201)
def create_chapter(
    collection_id: ResourceId,
    body: ChapterCreate,
    collections: CollectionService = Depends(get_collection_service),
) -> ChapterOut:
    chapter = collections.create_chapter(collection_id, body.title, body.note)
    return chapter


@router.put("/{collection_id}/chapters/order", status_code=204)
def reorder_chapters(
    collection_id: ResourceId,
    body: IdsBody,
    collections: CollectionService = Depends(get_collection_service),
) -> Response:
    collections.reorder_chapters(collection_id, body.ids)
    return Response(status_code=204)
