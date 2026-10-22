"""Admin chapter routes: edit, delete, and managing the photos inside a chapter."""

from fastapi import APIRouter, Depends, Response

from app.api.admin.collection_schemas import (
    ChapterOut,
    ChapterPatch,
    IdsBody,
    PhotoIdsBody,
    chapter_out,
)
from app.api.admin.deps import Auditor, get_auditor, get_collection_service
from app.api.schemas import ResourceId
from app.services.collections import CollectionService

router = APIRouter(prefix="/chapters", tags=["admin-chapters"])


@router.patch("/{chapter_id}")
def update(
    chapter_id: ResourceId,
    body: ChapterPatch,
    collections: CollectionService = Depends(get_collection_service),
    audit: Auditor = Depends(get_auditor),
) -> ChapterOut:
    chapter = collections.update_chapter(chapter_id, body.model_dump(exclude_unset=True))
    audit("chapter.update", chapter_id)
    return chapter_out(chapter)


@router.delete("/{chapter_id}", status_code=204)
def delete(
    chapter_id: ResourceId,
    collections: CollectionService = Depends(get_collection_service),
    audit: Auditor = Depends(get_auditor),
) -> Response:
    collections.delete_chapter(chapter_id)
    audit("chapter.delete", chapter_id)
    return Response(status_code=204)


@router.post("/{chapter_id}/photos")
def assign_photos(
    chapter_id: ResourceId,
    body: PhotoIdsBody,
    collections: CollectionService = Depends(get_collection_service),
    audit: Auditor = Depends(get_auditor),
) -> ChapterOut:
    chapter = collections.assign_photos(chapter_id, body.photo_ids)
    audit("chapter.assign_photos", chapter_id)
    return chapter_out(chapter)


@router.put("/{chapter_id}/photos/order", status_code=204)
def reorder_photos(
    chapter_id: ResourceId,
    body: IdsBody,
    collections: CollectionService = Depends(get_collection_service),
    audit: Auditor = Depends(get_auditor),
) -> Response:
    collections.reorder_photos(chapter_id, body.ids)
    audit("chapter.reorder_photos", chapter_id)
    return Response(status_code=204)


@router.delete("/{chapter_id}/photos/{photo_id}", status_code=204)
def remove_photo(
    chapter_id: ResourceId,
    photo_id: ResourceId,
    collections: CollectionService = Depends(get_collection_service),
    audit: Auditor = Depends(get_auditor),
) -> Response:
    collections.remove_photo(chapter_id, photo_id)
    audit("chapter.remove_photo", f"{chapter_id}/{photo_id}")
    return Response(status_code=204)
