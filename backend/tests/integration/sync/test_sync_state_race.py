"""The SQL sync-state repository turns the database's duplicate-row error into a domain error,
so services never see SQLAlchemy exceptions."""

import pytest

from app.core.db import Base, make_engine, make_session_factory
from app.core.errors import Conflict
from app.uow import SqlAlchemyUnitOfWork


def test_creating_the_row_when_another_process_just_did_raises_conflict_not_integrity_error() -> (
    None
):
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    uow = SqlAlchemyUnitOfWork(make_session_factory(engine))
    with uow as other:
        other.sync_state.get_or_create()
        other.commit()  # "the other process" has created the row

    with uow as ours:
        real_get = ours.session.get
        looked = {"already": False}

        def first_look_finds_nothing(*args: object, **kwargs: object) -> object:
            """As in a real race: we look, the row is not there yet, then the other side wins."""
            if not looked["already"]:
                looked["already"] = True
                return None
            return real_get(*args, **kwargs)  # type: ignore[arg-type]

        ours.session.get = first_look_finds_nothing  # type: ignore[method-assign, assignment]
        with pytest.raises(Conflict):
            ours.sync_state.get_or_create()
