from collections.abc import Iterator

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import Base, make_engine, make_session_factory
from app.models import Chapter, Collection, Photo


@pytest.fixture
def session() -> Iterator[Session]:
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    with make_session_factory(engine)() as s:
        yield s


def _photo(id_: str, **kw: object) -> Photo:
    return Photo(id=id_, title=id_, aspect_ratio=1.5, **kw)


def test_deleting_chapter_unassigns_photos(session: Session) -> None:
    col = Collection(id="c1", slug="a", title="A", sort_position=0)
    ch = Chapter(id="ch1", collection=col, title="One", position=0)
    session.add_all([col, ch, _photo("p1", chapter=ch, position_in_chapter=0)])
    session.commit()

    session.delete(ch)
    session.commit()

    photo = session.get(Photo, "p1")
    assert photo is not None
    assert photo.chapter_id is None


def test_deleting_collection_removes_chapters_keeps_photos(session: Session) -> None:
    col = Collection(id="c1", slug="a", title="A", sort_position=0)
    ch = Chapter(id="ch1", collection=col, title="One", position=0)
    session.add_all([col, ch, _photo("p1", chapter=ch, position_in_chapter=0)])
    session.commit()

    session.delete(col)
    session.commit()

    assert session.get(Chapter, "ch1") is None
    photo = session.get(Photo, "p1")
    assert photo is not None
    assert photo.chapter_id is None


def test_unsplash_id_is_unique(session: Session) -> None:
    session.add_all([_photo("p1", unsplash_id="u1"), _photo("p2", unsplash_id="u1")])
    with pytest.raises(IntegrityError):
        session.commit()


def test_new_photo_defaults_to_private_draft(session: Session) -> None:
    session.add(_photo("p1"))
    session.commit()
    photo = session.get(Photo, "p1")
    assert photo is not None
    assert photo.status == "draft"
    assert photo.allow_download is False
