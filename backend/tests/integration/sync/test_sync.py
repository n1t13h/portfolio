import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import AuditLog, Photo, SyncState
from app.services.sync import SyncService
from tests.fakes import FakeClock, FakeStorage, FakeUnsplash


@pytest.fixture
def service(
    client: TestClient,
    settings: Settings,
    storage: FakeStorage,
    unsplash: FakeUnsplash,
    clock: FakeClock,
) -> SyncService:
    return SyncService(client.app.state.uow_factory, unsplash, storage, settings, clock)  # type: ignore[attr-defined]


def photos(db: Session) -> dict[str, Photo]:
    db.expire_all()
    return {p.unsplash_id: p for p in db.scalars(select(Photo)) if p.unsplash_id}


def state(db: Session) -> SyncState:
    db.expire_all()
    row = db.get(SyncState, 1)
    assert row is not None
    return row


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
