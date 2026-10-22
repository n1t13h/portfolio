"""In-memory stand-ins: FakeUnsplash."""

from app.integrations.unsplash import UnsplashPhoto, UnsplashSummary


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
        from tests.support.images import make_jpeg

        return self.files.get(photo.id) or make_jpeg((60, 40))
