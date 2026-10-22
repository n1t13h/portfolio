"""Fixtures shared by unit and integration tests: throwaway settings and in-memory fakes."""

import pytest

import app.models  # noqa: F401  (registers tables)
from app.core.config import Settings
from app.core.db import Base, make_engine, make_session_factory
from app.uow import AbstractUnitOfWork, SqlAlchemyUnitOfWork
from tests.fakes import FakeClock, FakeNotifier, FakeStorage, FakeUnitOfWork, FakeUnsplash


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="sqlite://",
        admin_path_prefix="test-admin-prefix",
        session_secret="test-secret-test-secret",
        cdn_base_url="https://cdn.test",
    )


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def storage() -> FakeStorage:
    return FakeStorage()


@pytest.fixture
def notifier() -> FakeNotifier:
    return FakeNotifier()


@pytest.fixture
def unsplash() -> FakeUnsplash:
    return FakeUnsplash()


@pytest.fixture
def fake_uow() -> FakeUnitOfWork:
    """An in-memory unit of work, for unit-testing services."""
    return FakeUnitOfWork()


@pytest.fixture(params=["fake", "sql"])
def uow(request: pytest.FixtureRequest) -> AbstractUnitOfWork:
    """Both implementations; repository contract tests run against each so the fake cannot drift."""
    if request.param == "fake":
        return FakeUnitOfWork()
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    return SqlAlchemyUnitOfWork(make_session_factory(engine))
