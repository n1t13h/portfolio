"""What anonymous visitors may see: published photos and collections, and download links.

The visibility rules (published, and not inside a draft collection) live in the catalog
repository; this service shapes the result for the public site.
"""

from app.core.errors import NotFound
from app.integrations.storage import Bucket, Storage
from app.models import Chapter, Collection, Photo
from app.schemas.public import PublicCollection, PublicCollectionSummary, PublicPhoto
from app.services.mappers import public_collection, public_photo, public_summary
from app.uow import UnitOfWorkFactory

DOWNLOAD_URL_TTL_SECONDS = 300


def _covers(collection: Collection, visible: dict[str, Photo]) -> list[Photo]:
    return [visible[pid] for pid in collection.cover_photo_ids if pid in visible]


class CatalogService:
    def __init__(self, uow_factory: UnitOfWorkFactory, storage: Storage) -> None:
        self._uow = uow_factory
        self._storage = storage

    def photos(self) -> list[PublicPhoto]:
        with self._uow() as uow:
            return [public_photo(p, self._storage) for p in uow.catalog.list_public_photos()]

    def collections(self) -> list[PublicCollectionSummary]:
        with self._uow() as uow:
            collections = uow.catalog.list_published_collections()
            by_collection = uow.catalog.published_photos_by_collection([c.id for c in collections])
            return [
                public_summary(
                    c,
                    _covers(c, {p.id: p for p in by_collection.get(c.id, [])}),
                    self._storage,
                )
                for c in collections
            ]

    def collection(self, slug: str) -> PublicCollection:
        with self._uow() as uow:
            collection = uow.catalog.get_published_collection(slug)
            if collection is None:
                raise NotFound("collection not found")
            chapters = uow.catalog.list_chapters(collection.id)
            by_chapter = uow.catalog.published_photos_by_chapter([ch.id for ch in chapters])
            visible = {p.id: p for photos in by_chapter.values() for p in photos}
            shown: list[tuple[Chapter, list[Photo]]] = [
                (ch, by_chapter[ch.id]) for ch in chapters if by_chapter[ch.id]
            ]
            return public_collection(collection, _covers(collection, visible), shown, self._storage)

    def download_url(self, photo_id: str) -> str:
        """A short-lived link to the download copy, for a public photo whose owner allowed it."""
        with self._uow() as uow:
            photo = uow.catalog.get_downloadable_photo(photo_id)
            if photo is None or not photo.download_key:
                raise NotFound("not found")
            return self._storage.presign_get(
                Bucket.PRIVATE, photo.download_key, DOWNLOAD_URL_TTL_SECONDS
            )
