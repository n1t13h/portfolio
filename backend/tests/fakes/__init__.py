"""In-memory stand-ins for the outside world, shared by every test."""

from tests.fakes.clock import FakeClock
from tests.fakes.notifier import FakeNotifier
from tests.fakes.storage import FakeStorage
from tests.fakes.unsplash import FakeUnsplash
from tests.fakes.uow import FakeUnitOfWork

__all__ = ["FakeClock", "FakeNotifier", "FakeStorage", "FakeUnitOfWork", "FakeUnsplash"]
