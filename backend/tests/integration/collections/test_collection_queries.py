"""Loading many collections must not issue a query per collection or chapter."""

from sqlalchemy import event

from app.core.db import Base, make_engine, make_session_factory
from app.schemas.collections import CollectionOut
from app.uow import SqlAlchemyUnitOfWork
from tests.support.builders import make_chapter, make_collection, make_photo


def test_listing_collections_with_chapters_and_photos_uses_a_fixed_number_of_queries() -> None:
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    uow = SqlAlchemyUnitOfWork(make_session_factory(engine))

    def build(n: int) -> None:
        with uow:
            for i in range(n):
                uow.collections.add(make_collection(f"c{n}-{i}", slug=f"c{n}-{i}", sort_position=i))
                uow.collections.add_chapter(make_chapter(f"ch{n}-{i}", f"c{n}-{i}"))
                uow.photos.add(make_photo(f"p{n}-{i}", chapter_id=f"ch{n}-{i}"))
            uow.commit()

    def queries_to_list() -> int:
        count = [0]

        def bump(*_: object) -> None:
            count[0] += 1

        event.listen(engine, "before_cursor_execute", bump)
        with uow:
            out = [CollectionOut.model_validate(c) for c in uow.collections.list_ordered()]
        event.remove(engine, "before_cursor_execute", bump)
        assert all(len(c.chapters) == 1 and len(c.chapters[0].photo_ids) == 1 for c in out)
        return count[0]

    build(1)
    few = queries_to_list()
    build(6)
    assert queries_to_list() == few
