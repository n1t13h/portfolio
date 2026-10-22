from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.integrations.storage import Bucket
from app.models import AuditLog, Photo, Status, SyncState
from app.services.sync import SyncAlreadyRunning, SyncService
from tests.fakes import FakeClock, FakeStorage, FakeUnsplash


@pytest.fixture
def service(
    client: TestClient,
    settings: Settings,
    storage: FakeStorage,
    unsplash: FakeUnsplash,
    clock: FakeClock,
) -> SyncService:
    return SyncService(client.app.state.session_factory, unsplash, storage, settings, clock)  # type: ignore[attr-defined]


def photos(db: Session) -> dict[str, Photo]:
    db.expire_all()
    return {p.unsplash_id: p for p in db.scalars(select(Photo)) if p.unsplash_id}


def state(db: Session) -> SyncState:
    db.expire_all()
    row = db.get(SyncState, 1)
    assert row is not None
    return row


def test_imports_only_unknown_photos_as_drafts(
    service: SyncService, unsplash: FakeUnsplash, storage: FakeStorage, db: Session
) -> None:
    unsplash.ids = ["k1"]
    service.run()
    unsplash.ids = ["n2", "n1", "k1"]

    result = service.run()

    assert result.imported == 2
    imported = photos(db)
    assert set(imported) == {"k1", "n1", "n2"}
    new = imported["n2"]
    assert (new.status, new.allow_download) == (Status.DRAFT, False)
    assert (new.title, new.place) == ("Title n2", "Place n2")
    assert new.unsplash_url == "https://unsplash.com/photos/n2"
    assert storage.exists(Bucket.PRIVATE, f"originals/{new.id}.jpg")
    assert unsplash.get_calls == ["k1", "n1", "n2"]  # k1 only from the first run


def test_stops_listing_at_first_known_id(service: SyncService, unsplash: FakeUnsplash) -> None:
    unsplash.ids = ["k1"]
    service.run()
    unsplash.get_calls.clear()
    unsplash.list_calls.clear()
    unsplash.ids = ["n1", "k1", "older-unknown"]

    service.run()

    assert unsplash.get_calls == ["n1"]
    assert unsplash.list_calls == [1]


def test_empty_run_makes_one_listing_request_and_nothing_else(
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


def test_full_resync_walks_all_pages_and_finds_older_unknowns(
    service: SyncService, unsplash: FakeUnsplash, db: Session
) -> None:
    unsplash.page_size = 2
    unsplash.ids = ["k1"]
    service.run()
    unsplash.ids = ["k1", "a", "b", "c"]
    unsplash.list_calls.clear()

    assert service.run().imported == 0  # normal run stops at k1
    assert unsplash.list_calls == [1]

    unsplash.list_calls.clear()
    result = service.run(full=True)

    assert result.imported == 3
    assert unsplash.list_calls == [1, 2, 3]  # page 3 is empty, which ends the walk
    assert set(photos(db)) == {"k1", "a", "b", "c"}


def test_track_download_called_once_per_import(
    service: SyncService, unsplash: FakeUnsplash
) -> None:
    unsplash.ids = ["b", "a"]
    service.run()
    assert sorted(unsplash.tracked) == ["a", "b"]


def test_stops_cleanly_when_rate_limit_exhausted_and_resumes_next_run(
    service: SyncService, unsplash: FakeUnsplash, db: Session
) -> None:
    unsplash.ids = ["a", "b", "c"]  # a is newest
    unsplash.budget = 5  # 1 listing + 2 requests for each of two photos

    first = service.run()

    assert (first.imported, first.stopped_early) == (2, True)
    assert set(photos(db)) == {"b", "c"}  # oldest first
    assert state(db).pending == {"a": 0}
    assert state(db).rate_limit_remaining == 0

    unsplash.budget = 50
    second = service.run()

    assert (second.imported, second.stopped_early) == (1, False)
    assert set(photos(db)) == {"a", "b", "c"}
    assert state(db).pending == {}
    assert len(photos(db)) == 3  # nothing imported twice


def test_does_not_start_a_photo_it_cannot_finish(
    service: SyncService, unsplash: FakeUnsplash, db: Session
) -> None:
    unsplash.ids = ["a"]
    unsplash.budget = 2  # listing leaves 1, but a photo needs 2 requests

    result = service.run()

    assert (result.imported, result.stopped_early) == (0, True)
    assert unsplash.get_calls == []
    assert state(db).pending == {"a": 0}


def test_failed_photo_is_reported_and_does_not_stop_the_others(
    service: SyncService, unsplash: FakeUnsplash, db: Session
) -> None:
    unsplash.ids = ["good2", "bad", "good1"]
    unsplash.files["bad"] = b"this is not a jpeg"

    result = service.run()

    assert result.imported == 2
    assert result.error is not None and "bad" in result.error
    assert set(photos(db)) == {"good1", "good2"}
    assert state(db).pending == {"bad": 1}
    assert state(db).last_error == result.error


def test_a_photo_that_keeps_failing_is_given_up_on(
    service: SyncService, unsplash: FakeUnsplash, db: Session
) -> None:
    unsplash.ids = ["bad"]
    unsplash.files["bad"] = b"nope"
    for _ in range(3):
        service.run()
    assert state(db).pending == {}
    assert state(db).skipped == {"bad": "failed"}
    assert "giving up" in (state(db).last_error or "")

    unsplash.get_calls.clear()
    service.run()
    assert unsplash.get_calls == []  # not rediscovered and retried forever


def test_full_resync_gives_failed_photos_another_chance(
    service: SyncService, unsplash: FakeUnsplash, db: Session
) -> None:
    unsplash.ids = ["bad"]
    unsplash.files["bad"] = b"nope"
    for _ in range(3):
        service.run()
    del unsplash.files["bad"]  # fixed upstream

    service.run(full=True)

    assert set(photos(db)) == {"bad"}
    assert state(db).skipped == {}


def test_photo_deleted_by_the_admin_is_not_imported_again(
    admin_client: TestClient,
    admin_url: str,
    service: SyncService,
    unsplash: FakeUnsplash,
    db: Session,
) -> None:
    unsplash.ids = ["newest", "older"]
    service.run()
    newest = photos(db)["newest"]
    assert admin_client.delete(f"{admin_url}/photos/{newest.id}").status_code == 204
    unsplash.get_calls.clear()

    service.run()
    service.run(full=True)

    assert set(photos(db)) == {"older"}
    assert unsplash.get_calls == []
    assert state(db).skipped == {"newest": "deleted"}


def test_second_run_while_running_is_refused(service: SyncService) -> None:
    service.acquire()
    with pytest.raises(SyncAlreadyRunning):
        service.acquire()
    with pytest.raises(SyncAlreadyRunning):
        service.run()


def test_a_stale_lock_from_a_crashed_run_is_taken_over(
    service: SyncService, clock: FakeClock
) -> None:
    service.acquire()
    clock.advance(2 * 3600)
    service.acquire()  # does not raise


def test_lock_is_released_even_when_the_run_crashes(
    service: SyncService, unsplash: FakeUnsplash, db: Session
) -> None:
    def boom(page: int) -> list[Any]:
        raise RuntimeError("network down")

    unsplash.list_latest = boom  # type: ignore[method-assign]
    result = service.run()
    assert result.error is not None and "network down" in result.error
    assert state(db).running is False
    service.acquire()  # and a new run may start


def test_status_reports_the_last_run(
    service: SyncService, unsplash: FakeUnsplash, clock: FakeClock
) -> None:
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


# -- admin API -------------------------------------------------------------------------------


def test_manual_trigger_imports_in_the_background_and_is_audited(
    admin_client: TestClient, admin_url: str, unsplash: FakeUnsplash, db: Session
) -> None:
    unsplash.ids = ["b", "a"]
    resp = admin_client.post(f"{admin_url}/sync")
    assert resp.status_code == 202

    status = admin_client.get(f"{admin_url}/sync/status").json()
    assert (status["running"], status["lastImported"], status["lastError"]) == (False, 2, None)
    assert set(photos(db)) == {"a", "b"}
    assert "sync.start" in [r.action for r in db.scalars(select(AuditLog))]


def test_manual_trigger_refused_while_a_sync_is_running(
    admin_client: TestClient, admin_url: str, service: SyncService
) -> None:
    service.acquire()
    assert admin_client.post(f"{admin_url}/sync").status_code == 409
    assert admin_client.post(f"{admin_url}/sync/full").status_code == 409


def test_full_resync_endpoint_walks_every_page(
    admin_client: TestClient, admin_url: str, unsplash: FakeUnsplash, service: SyncService
) -> None:
    unsplash.ids = ["k"]
    service.run()
    unsplash.ids = ["k", "old"]
    admin_client.post(f"{admin_url}/sync")
    assert unsplash.get_calls.count("old") == 0
    admin_client.post(f"{admin_url}/sync/full")
    assert unsplash.get_calls.count("old") == 1


def test_sync_routes_require_admin(client: TestClient, admin_url: str) -> None:
    client.headers["X-CSRF"] = "1"
    for method, path in [("POST", "/sync"), ("POST", "/sync/full"), ("GET", "/sync/status")]:
        assert client.request(method, f"{admin_url}{path}").status_code == 401


def test_status_lock_age_uses_the_clock(service: SyncService, clock: FakeClock) -> None:
    service.acquire()
    assert service.status().running is True
    clock.advance(timedelta(hours=2).total_seconds())
    assert service.status().running is False  # a stale lock no longer counts as running


def test_a_bad_api_key_is_reported_not_mistaken_for_a_rate_limit(
    service: SyncService, unsplash: FakeUnsplash, db: Session
) -> None:
    import httpx

    def unauthorised(page: int) -> list[Any]:
        raise httpx.HTTPStatusError(
            "forbidden", request=httpx.Request("GET", "u"), response=httpx.Response(403)
        )

    unsplash.list_latest = unauthorised  # type: ignore[method-assign]
    result = service.run()
    assert result.stopped_early is False
    assert result.error is not None and "forbidden" in result.error
    assert state(db).last_error == result.error
