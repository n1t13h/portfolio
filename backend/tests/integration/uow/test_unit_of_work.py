"""The SQLAlchemy unit of work itself: transactions, sessions and the attached repositories."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.db import Base, make_engine, make_session_factory
from app.uow import SqlAlchemyUnitOfWork
from tests.support.builders import make_photo


@pytest.fixture
def sql_uow() -> SqlAlchemyUnitOfWork:
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    return SqlAlchemyUnitOfWork(make_session_factory(engine))


def test_every_repository_is_available_inside_the_block(sql_uow: SqlAlchemyUnitOfWork) -> None:
    with sql_uow as uow:
        for name in (
            "photos",
            "collections",
            "catalog",
            "admins",
            "login_failures",
            "audit",
            "sync_state",
            "contacts",
        ):
            assert getattr(uow, name) is not None


def test_enter_returns_the_unit_of_work_itself(sql_uow: SqlAlchemyUnitOfWork) -> None:
    with sql_uow as uow:
        assert uow is sql_uow


def test_committed_work_is_visible_to_the_next_block(sql_uow: SqlAlchemyUnitOfWork) -> None:
    with sql_uow as uow:
        uow.photos.add(make_photo("p1"))
        uow.commit()
    with sql_uow as uow:
        assert uow.photos.get("p1") is not None


def test_each_block_uses_a_fresh_session_and_closes_it(sql_uow: SqlAlchemyUnitOfWork) -> None:
    with sql_uow:
        first = sql_uow.session
    with sql_uow:
        assert sql_uow.session is not first


def test_flush_makes_pending_rows_visible_inside_the_transaction_only(
    sql_uow: SqlAlchemyUnitOfWork,
) -> None:
    with sql_uow as uow:
        uow.photos.add(make_photo("p1"))
        uow.flush()
        assert uow.photos.get("p1") is not None
    with sql_uow as uow:
        assert uow.photos.get("p1") is None  # never committed


def test_a_failing_commit_leaves_the_unit_of_work_reusable(sql_uow: SqlAlchemyUnitOfWork) -> None:
    with sql_uow as uow:
        uow.photos.add(make_photo("a", unsplash_id="same"))
        uow.commit()
    with pytest.raises(IntegrityError), sql_uow as uow:
        uow.photos.add(make_photo("b", unsplash_id="same"))
        uow.commit()
    with sql_uow as uow:
        assert uow.photos.get("a") is not None and uow.photos.get("b") is None
