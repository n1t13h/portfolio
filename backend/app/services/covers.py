"""Collection covers must always be photos that are still in the collection."""

from collections.abc import Iterable

from app.uow import AbstractUnitOfWork


def prune_covers(uow: AbstractUnitOfWork, collection_ids: Iterable[str]) -> None:
    """Drop cover photos that are no longer in their collection. The caller commits.

    Call after photos leave a collection (moved, removed from a chapter, deleted), once the
    change has been flushed so the membership query sees it.
    """
    for collection_id in collection_ids:
        collection = uow.collections.get(collection_id)
        if collection is None or not collection.cover_photo_ids:
            continue
        inside = uow.photos.ids_in_collection(collection_id)
        collection.cover_photo_ids = [p for p in collection.cover_photo_ids if p in inside]
