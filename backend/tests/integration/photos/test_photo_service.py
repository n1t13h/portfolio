import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.services.images import InvalidImage
from app.services.photos import PhotoService
from tests.fakes import FakeStorage
from tests.support.images import make_jpeg


def test_ingest_rejects_files_over_the_upload_limit(
    db: Session, storage: FakeStorage, settings: Settings
) -> None:
    small = settings.model_copy(update={"max_upload_bytes": 500})
    with pytest.raises(InvalidImage, match="too large"):
        PhotoService(db, storage, small).ingest_jpeg(make_jpeg((400, 400)))
    assert storage.objects == {}


def test_failed_insert_removes_the_files_it_wrote_and_leaves_the_session_usable(
    db: Session, storage: FakeStorage, settings: Settings
) -> None:
    from sqlalchemy.exc import IntegrityError

    photos = PhotoService(db, storage, settings)
    photos.ingest_jpeg(make_jpeg((60, 40)), unsplash_id="dup")
    before = dict(storage.objects)

    with pytest.raises(IntegrityError):
        photos.ingest_jpeg(make_jpeg((60, 40)), unsplash_id="dup")

    assert storage.objects == before  # nothing orphaned in R2
    photos.ingest_jpeg(make_jpeg((60, 40)), unsplash_id="other")  # and later photos still work


def test_delete_succeeds_even_when_removing_files_from_r2_fails(
    db: Session, storage: FakeStorage, settings: Settings
) -> None:
    photos = PhotoService(db, storage, settings)
    photo = photos.ingest_jpeg(make_jpeg((60, 40)))

    def boom(*args: object) -> None:
        raise RuntimeError("r2 unreachable")

    storage.delete = boom  # type: ignore[method-assign, assignment]
    photos.delete(photo.id)  # no exception: a leftover file is harmless, a dangling row is not

    assert photos.list_all() == []
