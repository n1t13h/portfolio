"""In-memory stand-ins: FakeClock."""

from datetime import UTC, datetime, timedelta


class FakeClock:
    """A clock the test moves by hand."""

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)
