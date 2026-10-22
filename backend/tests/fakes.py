"""In-memory stand-ins for external systems, shared by the test suite."""

from datetime import UTC, datetime, timedelta

from app.integrations.storage import Bucket
from app.integrations.unsplash import UnsplashPhoto, UnsplashSummary


class FakeStorage:
    """Implements the `Storage` protocol with dicts."""

    def __init__(self, cdn_base_url: str = "https://cdn.test") -> None:
        self.cdn_base_url = cdn_base_url
        self.objects: dict[tuple[Bucket, str], tuple[bytes, str]] = {}

    def presign_put(self, bucket: Bucket, key: str, content_type: str, expires: int) -> str:
        return f"https://fake-r2/{bucket.value}/{key}?put&expires={expires}"

    def presign_get(self, bucket: Bucket, key: str, expires: int) -> str:
        return f"https://fake-r2/{bucket.value}/{key}?get&expires={expires}"

    def get_bytes(self, bucket: Bucket, key: str) -> bytes:
        return self.objects[(bucket, key)][0]

    def put_bytes(
        self,
        bucket: Bucket,
        key: str,
        data: bytes,
        content_type: str,
        cache_control: str | None = None,
    ) -> None:
        self.objects[(bucket, key)] = (data, content_type)

    def delete(self, bucket: Bucket, key: str) -> None:
        self.objects.pop((bucket, key), None)

    def exists(self, bucket: Bucket, key: str) -> bool:
        return (bucket, key) in self.objects

    def size(self, bucket: Bucket, key: str) -> int:
        return len(self.objects[(bucket, key)][0])

    def list_keys(self, bucket: Bucket, prefix: str) -> list[str]:
        return [k for (b, k) in self.objects if b is bucket and k.startswith(prefix)]

    def public_url(self, key: str) -> str:
        return f"{self.cdn_base_url}/{key}"


class FakeClock:
    """A clock the test moves by hand."""

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)


class FakeNotifier:
    """Records messages; set `fail` to simulate Telegram being down."""

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.fail = False

    def send(self, text: str) -> None:
        if self.fail:
            raise RuntimeError("telegram is down")
        self.sent.append(text)


class FakeUnsplash:
    """Stands in for the Unsplash API. `photos` is newest-first, like the real listing.

    Every API request (list, details, download tracking) costs one unit of `budget`;
    when it runs out the next request raises RateLimited, like the real service.
    """

    def __init__(
        self, ids: list[str] | None = None, *, page_size: int = 30, budget: int | None = None
    ) -> None:
        self.ids = ids or []
        self.page_size = page_size
        self.budget = budget
        self.files: dict[str, bytes] = {}
        self.list_calls: list[int] = []
        self.get_calls: list[str] = []
        self.tracked: list[str] = []

    @property
    def per_page(self) -> int:
        return self.page_size

    @property
    def rate_limit_remaining(self) -> int | None:
        return self.budget

    def _spend(self) -> None:
        from app.integrations.unsplash import RateLimited

        if self.budget is not None:
            if self.budget <= 0:
                raise RateLimited("out of budget")
            self.budget -= 1

    def list_latest(self, page: int) -> "list[UnsplashSummary]":
        self._spend()
        self.list_calls.append(page)
        chunk = self.ids[(page - 1) * self.page_size : page * self.page_size]
        return [UnsplashSummary(id=i) for i in chunk]

    def get_photo(self, photo_id: str) -> "UnsplashPhoto":
        self._spend()
        self.get_calls.append(photo_id)
        return UnsplashPhoto(
            id=photo_id,
            title=f"Title {photo_id}",
            place=f"Place {photo_id}",
            html_url=f"https://unsplash.com/photos/{photo_id}",
            download_location=f"https://api.unsplash.com/photos/{photo_id}/download",
        )

    def download_original(self, photo: "UnsplashPhoto") -> bytes:
        self._spend()
        self.tracked.append(photo.id)
        from tests.images import make_jpeg

        return self.files.get(photo.id) or make_jpeg((60, 40))
