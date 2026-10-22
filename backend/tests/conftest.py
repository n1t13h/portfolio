"""Fixtures shared by unit and integration tests: throwaway settings and in-memory fakes."""

import pytest

from app.core.config import Settings
from tests.fakes import FakeClock, FakeNotifier, FakeStorage, FakeUnsplash


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
