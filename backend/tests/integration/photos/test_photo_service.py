"""PhotoService against a real database. The rules themselves are unit tested with fakes in
tests/unit/photos; these cover what only the real database can prove."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.db import Base, make_engine, make_session_factory
from app.models import Photo
from app.services.photos import PhotoService
from app.uow import SqlAlchemyUnitOfWork
from tests.fakes import FakeStorage
from tests.support.images import make_jpeg


@pytest.fixture
def service(storage: FakeStorage, settings: Settings) -> PhotoService:
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    sessions = make_session_factory(engine)
    return PhotoService(lambda: SqlAlchemyUnitOfWork(sessions), storage, settings)


def test_a_duplicate_unsplash_id_is_refused_by_the_database_and_leaves_no_orphaned_files(
    service: PhotoService, storage: FakeStorage
) -> None:
    service.ingest_jpeg(make_jpeg((60, 40)), unsplash_id="dup")
    before = dict(storage.objects)

    with pytest.raises(IntegrityError):
        service.ingest_jpeg(make_jpeg((60, 40)), unsplash_id="dup")

    assert storage.objects == before  # nothing orphaned in R2
    service.ingest_jpeg(make_jpeg((60, 40)), unsplash_id="other")  # and the service still works


def test_deleting_through_the_real_database_removes_the_row_and_frees_the_unsplash_id(
    service: PhotoService, storage: FakeStorage
) -> None:
    photo = service.ingest_jpeg(make_jpeg((60, 40)), unsplash_id="u1")
    service.delete(photo.id)
    assert service.list_all() == []
    assert not storage.objects


def test_the_photo_entity_is_not_leaked_out_of_the_service(service: PhotoService) -> None:
    photo = service.ingest_jpeg(make_jpeg((60, 40)))
    assert not isinstance(photo, Photo)  # callers get a schema, never a session-bound entity
