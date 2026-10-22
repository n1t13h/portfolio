"""SyncService against the in-memory unit of work, fake Unsplash, fake storage and a hand-moved
clock. No database and no network."""

from datetime import timedelta
from typing import Any

import httpx
import pytest

from app.core.config import Settings
from app.integrations.storage import Bucket
from app.models import Photo, Status, SyncState
from app.services.photos import PhotoService
from app.services.sync import SyncAlreadyRunning, SyncService
from tests.fakes import FakeClock, FakeStorage, FakeUnitOfWork, FakeUnsplash


@pytest.fixture
def service(
    fake_uow: FakeUnitOfWork,
    unsplash: FakeUnsplash,
    storage: FakeStorage,
    settings: Settings,
    clock: FakeClock,
) -> SyncService:
    return SyncService(lambda: fake_uow, unsplash, storage, settings, clock)


def photos(uow: FakeUnitOfWork) -> dict[str, Photo]:
    return {p.unsplash_id: p for p in uow.store.photos.values() if p.unsplash_id}


def state(uow: FakeUnitOfWork) -> SyncState:
    assert uow.store.sync_state is not None
    return uow.store.sync_state


# -- what gets imported -------------------------------------------------------------------


def test_only_unknown_photos_are_imported_as_drafts_with_unsplash_details(
    service: SyncService,
    unsplash: FakeUnsplash,
    storage: FakeStorage,
    fake_uow: FakeUnitOfWork,
) -> None:
    unsplash.ids = ["k1"]
    service.run()
    unsplash.ids = ["n2", "n1", "k1"]

    result = service.run()

    assert result.imported == 2
    imported = photos(fake_uow)
    assert set(imported) == {"k1", "n1", "n2"}
    new = imported["n2"]
    assert (new.status, new.allow_download) == (Status.DRAFT, False)
    assert (new.title, new.place) == ("Title n2", "Place n2")
    assert new.unsplash_url == "https://unsplash.com/photos/n2"
    assert storage.exists(Bucket.PRIVATE, f"originals/{new.id}.jpg")
    assert unsplash.get_calls == ["k1", "n1", "n2"]  # k1 only from the first run


def test_new_photos_are_imported_oldest_first_so_the_library_order_matches_time(
    service: SyncService, unsplash: FakeUnsplash, fake_uow: FakeUnitOfWork
) -> None:
    unsplash.ids = ["newest", "middle", "oldest"]  # Unsplash lists newest first
    service.run()
    ordered = sorted(photos(fake_uow).values(), key=lambda p: p.sort_position)
    assert [p.unsplash_id for p in ordered] == ["oldest", "middle", "newest"]


def test_the_listing_stops_at_the_first_photo_already_imported(
    service: SyncService, unsplash: FakeUnsplash
) -> None:
    unsplash.ids = ["k1"]
    service.run()
    unsplash.get_calls.clear()
    unsplash.list_calls.clear()
    unsplash.ids = ["n1", "k1", "older-unknown"]

    service.run()

    assert unsplash.get_calls == ["n1"]
    assert unsplash.list_calls == [1]


def test_a_run_with_nothing_new_costs_one_listing_request(
    service: SyncService, unsplash: FakeUnsplash
) -> None:
    unsplash.ids = ["k1"]
    service.run()
    unsplash.get_calls.clear()
    unsplash.tracked.clear()
    unsplash.list_calls.clear()

    result = service.run()

    assert result.imported == 0
    assert unsplash.list_calls == [1]
    assert unsplash.get_calls == [] and unsplash.tracked == []


def test_a_full_resync_walks_every_page_and_finds_older_unknowns(
    service: SyncService, unsplash: FakeUnsplash, fake_uow: FakeUnitOfWork
) -> None:
    unsplash.page_size = 2
    unsplash.ids = ["k1"]
    service.run()
    unsplash.ids = ["k1", "a", "b", "c"]
    unsplash.list_calls.clear()

    assert service.run().imported == 0  # a normal run stops at k1
    assert unsplash.list_calls == [1]

    unsplash.list_calls.clear()
    result = service.run(full=True)

    assert result.imported == 3
    assert unsplash.list_calls == [1, 2, 3]  # page 3 is empty, which ends the walk
    assert set(photos(fake_uow)) == {"k1", "a", "b", "c"}


def test_every_import_reports_the_download_to_unsplash(
    service: SyncService, unsplash: FakeUnsplash
) -> None:
    unsplash.ids = ["b", "a"]
    service.run()
    assert sorted(unsplash.tracked) == ["a", "b"]


# -- rate limits and failures -------------------------------------------------------------


def test_it_stops_cleanly_when_the_rate_limit_runs_out_and_resumes_next_run(
    service: SyncService, unsplash: FakeUnsplash, fake_uow: FakeUnitOfWork
) -> None:
    unsplash.ids = ["a", "b", "c"]  # a is newest
    unsplash.budget = 5  # 1 listing + 2 requests for each of two photos

    first = service.run()

    assert (first.imported, first.stopped_early) == (2, True)
    assert set(photos(fake_uow)) == {"b", "c"}  # oldest first
    assert state(fake_uow).pending == {"a": 0}
    assert state(fake_uow).rate_limit_remaining == 0

    unsplash.budget = 50
    second = service.run()

    assert (second.imported, second.stopped_early) == (1, False)
    assert set(photos(fake_uow)) == {"a", "b", "c"}
    assert state(fake_uow).pending == {}
    assert len(photos(fake_uow)) == 3  # nothing imported twice


def test_it_does_not_start_a_photo_it_cannot_finish(
    service: SyncService, unsplash: FakeUnsplash, fake_uow: FakeUnitOfWork
) -> None:
    unsplash.ids = ["a"]
    unsplash.budget = 2  # the listing leaves 1, but a photo needs 2 requests

    result = service.run()

    assert (result.imported, result.stopped_early) == (0, True)
    assert unsplash.get_calls == []
    assert state(fake_uow).pending == {"a": 0}


def test_a_failing_photo_is_reported_and_does_not_stop_the_others(
    service: SyncService, unsplash: FakeUnsplash, fake_uow: FakeUnitOfWork
) -> None:
    unsplash.ids = ["good2", "bad", "good1"]
    unsplash.files["bad"] = b"this is not a jpeg"

    result = service.run()

    assert result.imported == 2
    assert result.error is not None and "bad" in result.error
    assert set(photos(fake_uow)) == {"good1", "good2"}
    assert state(fake_uow).pending == {"bad": 1}
    assert state(fake_uow).last_error == result.error


def test_a_photo_that_keeps_failing_is_given_up_on_and_not_rediscovered(
    service: SyncService, unsplash: FakeUnsplash, fake_uow: FakeUnitOfWork
) -> None:
    unsplash.ids = ["bad"]
    unsplash.files["bad"] = b"nope"
    for _ in range(3):
        service.run()
    assert state(fake_uow).pending == {}
    assert state(fake_uow).skipped == {"bad": "failed"}
    assert "giving up" in (state(fake_uow).last_error or "")

    unsplash.get_calls.clear()
    service.run()
    assert unsplash.get_calls == []


def test_a_full_resync_gives_failed_photos_another_chance(
    service: SyncService, unsplash: FakeUnsplash, fake_uow: FakeUnitOfWork
) -> None:
    unsplash.ids = ["bad"]
    unsplash.files["bad"] = b"nope"
    for _ in range(3):
        service.run()
    del unsplash.files["bad"]  # fixed upstream

    service.run(full=True)

    assert set(photos(fake_uow)) == {"bad"}
    assert state(fake_uow).skipped == {}


def test_a_photo_deleted_by_the_admin_is_never_imported_again(
    service: SyncService,
    unsplash: FakeUnsplash,
    storage: FakeStorage,
    settings: Settings,
    fake_uow: FakeUnitOfWork,
) -> None:
    unsplash.ids = ["newest", "older"]
    service.run()
    PhotoService(lambda: fake_uow, storage, settings).delete(photos(fake_uow)["newest"].id)
    unsplash.get_calls.clear()

    service.run()
    service.run(full=True)

    assert set(photos(fake_uow)) == {"older"}
    assert unsplash.get_calls == []
    assert state(fake_uow).skipped == {"newest": "deleted"}


def test_a_bad_api_key_is_reported_not_mistaken_for_a_rate_limit(
    service: SyncService, unsplash: FakeUnsplash, fake_uow: FakeUnitOfWork
) -> None:
    def unauthorised(page: int) -> list[Any]:
        raise httpx.HTTPStatusError(
            "forbidden", request=httpx.Request("GET", "u"), response=httpx.Response(403)
        )

    unsplash.list_latest = unauthorised  # type: ignore[method-assign]

    result = service.run()

    assert result.stopped_early is False
    assert result.error is not None and "forbidden" in result.error
    assert state(fake_uow).last_error == result.error


# -- the run lock -------------------------------------------------------------------------


def test_only_one_run_at_a_time(service: SyncService) -> None:
    service.acquire()
    with pytest.raises(SyncAlreadyRunning):
        service.acquire()
    with pytest.raises(SyncAlreadyRunning):
        service.run()


def test_a_lock_from_a_crashed_run_is_taken_over_after_an_hour(
    service: SyncService, clock: FakeClock
) -> None:
    service.acquire()
    clock.advance(2 * 3600)
    service.acquire()  # does not raise


def test_the_lock_is_released_even_when_the_run_crashes(
    service: SyncService, unsplash: FakeUnsplash, fake_uow: FakeUnitOfWork
) -> None:
    def boom(page: int) -> list[Any]:
        raise RuntimeError("network down")

    unsplash.list_latest = boom  # type: ignore[method-assign]

    result = service.run()

    assert result.error is not None and "network down" in result.error
    assert state(fake_uow).running is False
    service.acquire()  # and a new run may start


# -- status -------------------------------------------------------------------------------


def test_status_reports_the_last_run(service: SyncService, unsplash: FakeUnsplash) -> None:
    unsplash.ids = ["a"]
    service.run()
    status = service.status()
    assert (status.running, status.last_imported, status.last_error, status.pending) == (
        False,
        1,
        None,
        0,
    )
    assert status.last_finished_at is not None


def test_status_before_any_run_is_empty_and_idle(service: SyncService) -> None:
    status = service.status()
    assert (status.running, status.last_started_at, status.last_imported, status.pending) == (
        False,
        None,
        0,
        0,
    )


def test_a_stale_lock_no_longer_counts_as_running(service: SyncService, clock: FakeClock) -> None:
    service.acquire()
    assert service.status().running is True
    clock.advance(timedelta(hours=2).total_seconds())
    assert service.status().running is False


def test_two_processes_racing_to_create_the_state_row_do_not_break_taking_the_lock(
    service: SyncService, fake_uow: FakeUnitOfWork
) -> None:
    """The other process creates (and commits) the row between our look and our insert."""
    from app.core.errors import Conflict

    real = fake_uow.sync_state.get_or_create
    calls = {"n": 0}

    def racing() -> SyncState:
        calls["n"] += 1
        if calls["n"] == 1:
            real()
            fake_uow.commit()  # the other process's commit survives our rollback
            raise Conflict("the sync state was created concurrently")
        return real()

    fake_uow.sync_state.get_or_create = racing  # type: ignore[method-assign]

    service.acquire()  # does not raise

    assert state(fake_uow).running is True


# -- robustness ---------------------------------------------------------------------------


def test_a_failure_while_a_run_is_starting_still_releases_the_lock_and_keeps_saved_state(
    service: SyncService, fake_uow: FakeUnitOfWork
) -> None:
    service.acquire()
    with fake_uow as uow:
        row = uow.sync_state.get_or_create()
        row.pending, row.skipped = {"x": 1}, {"y": "failed"}
        uow.commit()
    fake_uow.fail_next_commit(RuntimeError("database is locked"))

    result = service.execute()  # its first commit fails

    assert result.error is not None and "database is locked" in result.error
    assert state(fake_uow).running is False  # not stuck as 'already running' for an hour
    assert (state(fake_uow).pending, state(fake_uow).skipped) == ({"x": 1}, {"y": "failed"})
    service.acquire()  # and a new run may start


def test_asking_for_the_status_never_writes(service: SyncService, fake_uow: FakeUnitOfWork) -> None:
    status = service.status()
    assert (status.running, status.last_imported, status.pending) == (False, 0, 0)
    assert fake_uow.commits == 0 and fake_uow.store.sync_state is None


def test_a_photo_the_admin_deletes_during_a_run_is_not_forgotten_by_the_run(
    service: SyncService,
    unsplash: FakeUnsplash,
    storage: FakeStorage,
    settings: Settings,
    fake_uow: FakeUnitOfWork,
) -> None:
    unsplash.ids = ["k"]
    service.run()
    deleted_id = photos(fake_uow)["k"].id

    unsplash.ids = ["new", "k"]
    original_get = unsplash.get_photo
    deleted = {"done": False}

    def get_photo_while_the_admin_deletes(photo_id: str) -> Any:
        if not deleted["done"]:  # the admin deletes k in the middle of the run
            deleted["done"] = True
            PhotoService(lambda: fake_uow, storage, settings).delete(deleted_id)
        return original_get(photo_id)

    unsplash.get_photo = get_photo_while_the_admin_deletes  # type: ignore[method-assign]

    service.run()

    assert state(fake_uow).skipped == {"k": "deleted"}  # the run's final write kept it
    unsplash.get_calls.clear()
    service.run(full=True)
    assert "k" not in photos(fake_uow) and "k" not in unsplash.get_calls


def test_starting_a_manual_sync_is_audited_in_the_same_transaction_as_taking_the_lock(
    service: SyncService, fake_uow: FakeUnitOfWork, clock: FakeClock
) -> None:
    from app.services.audit import AuditTrail

    service.acquire(AuditTrail(clock, "9.9.9.9"), "full")

    [entry] = fake_uow.store.audit
    assert (entry.action, entry.target, entry.ip) == ("sync.start", "full", "9.9.9.9")


def test_a_refused_start_is_not_audited_and_the_timer_style_start_is_not_either(
    service: SyncService, fake_uow: FakeUnitOfWork, clock: FakeClock
) -> None:
    from app.services.audit import AuditTrail

    service.acquire()  # the scheduled run: no admin involved
    with pytest.raises(SyncAlreadyRunning):
        service.acquire(AuditTrail(clock, "9.9.9.9"), "incremental")
    assert fake_uow.store.audit == []
