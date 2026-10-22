"""Fixtures for integration tests: the real app over an in-memory SQLite database."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers tables)
from app.core.config import Settings
from app.core.db import Base
from app.main import create_app
from app.services.auth import AuthService
from tests.fakes import FakeClock, FakeNotifier, FakeStorage, FakeUnsplash
from tests.support.auth import AdminCreds

ADMIN_PASSWORD = "correct horse battery staple"


@pytest.fixture
def client(
    settings: Settings,
    storage: FakeStorage,
    clock: FakeClock,
    notifier: FakeNotifier,
    unsplash: FakeUnsplash,
) -> Iterator[TestClient]:
    app = create_app(settings, storage=storage, clock=clock, notifier=notifier, unsplash=unsplash)
    Base.metadata.create_all(app.state.engine)  # production gets its schema from Alembic
    # https base URL so the browser-style cookie jar sends Secure cookies back
    with TestClient(app, base_url="https://testserver") as c:
        yield c


@pytest.fixture
def db(client: TestClient) -> Iterator[Session]:
    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        yield session


@pytest.fixture
def admin(db: Session, settings: Settings, clock: FakeClock) -> AdminCreds:
    created = AuthService(db, settings, clock).create_admin("nitish", ADMIN_PASSWORD)
    return AdminCreds("nitish", ADMIN_PASSWORD, created.totp_secret, created.recovery_codes)


@pytest.fixture
def admin_url(settings: Settings) -> str:
    return f"/a/{settings.admin_path_prefix}"


@pytest.fixture
def admin_client(
    client: TestClient, admin: AdminCreds, admin_url: str, clock: FakeClock
) -> TestClient:
    """A client with the CSRF header set and a logged-in admin session."""
    client.headers["X-CSRF"] = "1"
    resp = client.post(
        f"{admin_url}/auth/login",
        json={"username": admin.username, "password": admin.password, "code": admin.code(clock)},
    )
    assert resp.status_code == 200, resp.text
    clock.advance(30)  # next login in the same test needs a fresh TOTP step
    return client
