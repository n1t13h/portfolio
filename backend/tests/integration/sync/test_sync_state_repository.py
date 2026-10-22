"""Repository contract for the sync state row and its run lock."""

from datetime import timedelta

from app.uow import AbstractUnitOfWork
from tests.support.builders import at

HOUR = timedelta(hours=1)


def test_the_state_row_is_created_once_with_empty_defaults(uow: AbstractUnitOfWork) -> None:
    with uow:
        row = uow.sync_state.get_or_create()
        assert row.id == 1
        assert (row.running, row.last_imported, row.pending, row.skipped) == (False, 0, {}, {})
        uow.commit()
    with uow:
        again = uow.sync_state.get_or_create()
        assert again.id == 1


def test_the_lock_can_be_taken_when_free_and_only_once(uow: AbstractUnitOfWork) -> None:
    with uow:
        uow.sync_state.get_or_create()
        assert uow.sync_state.try_acquire(at(0), at(0) - HOUR) is True
        uow.commit()
    with uow:
        assert uow.sync_state.try_acquire(at(1), at(1) - HOUR) is False
        row = uow.sync_state.get_or_create()
        assert row.running is True


def test_a_lock_from_a_crashed_run_is_taken_over_once_stale(uow: AbstractUnitOfWork) -> None:
    with uow:
        uow.sync_state.get_or_create()
        assert uow.sync_state.try_acquire(at(0), at(0) - HOUR)
        uow.commit()
    with uow:
        later = at(0) + timedelta(hours=2)
        assert uow.sync_state.try_acquire(later, later - HOUR) is True


def test_a_released_lock_can_be_taken_again(uow: AbstractUnitOfWork) -> None:
    with uow:
        row = uow.sync_state.get_or_create()
        assert uow.sync_state.try_acquire(at(0), at(0) - HOUR)
        row.running = False
        uow.commit()
    with uow:
        assert uow.sync_state.try_acquire(at(1), at(1) - HOUR) is True


def test_peeking_at_the_state_never_creates_it(uow: AbstractUnitOfWork) -> None:
    with uow:
        assert uow.sync_state.get() is None
        uow.sync_state.get_or_create()
        uow.commit()
    with uow:
        row = uow.sync_state.get()
        assert row is not None and row.id == 1
