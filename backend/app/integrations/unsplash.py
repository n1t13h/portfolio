"""The Unsplash API behind a small interface, plus the field mapping the site relies on."""

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx

from app.core.config import Settings

API_BASE = "https://api.unsplash.com"
PER_PAGE = 30
SPACING_SECONDS = 1.2  # the demo tier allows 50 requests/hour; stay well clear of bursts
COUNTRY_OR_STATE = {"india"}


class RateLimited(Exception):
    """Unsplash says we are out of requests for this hour."""


class DownloadTooLarge(ValueError):
    """The image file is bigger than we accept."""


@dataclass(frozen=True)
class UnsplashSummary:
    id: str


@dataclass(frozen=True)
class UnsplashPhoto:
    id: str
    title: str
    place: str | None
    html_url: str
    download_location: str


class UnsplashClient(Protocol):
    @property
    def per_page(self) -> int: ...
    @property
    def rate_limit_remaining(self) -> int | None: ...
    def list_latest(self, page: int) -> list[UnsplashSummary]:
        """One page of the user's photos, newest first. An empty or short page is the last."""
        ...

    def get_photo(self, photo_id: str) -> UnsplashPhoto: ...
    def download_original(self, photo: UnsplashPhoto) -> bytes:
        """Report the download to Unsplash (as their guidelines ask), then fetch the file."""
        ...


def _clean(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def to_title(api: Mapping[str, Any]) -> str:
    title = _clean(api.get("alt_description")) or _clean(api.get("description")) or "Untitled"
    return title[0].upper() + title[1:]


def to_place(location: Mapping[str, Any] | None) -> str | None:
    """Ported from scripts/to-snapshot-photo.mjs so imported places match the existing ones."""
    if not location:
        return None
    raw_name = location.get("name") or ""
    parts = [p.strip() for p in raw_name.split(",") if p.strip()]
    city = _clean(location.get("city"))
    city_ok = city if city and city.lower() not in COUNTRY_OR_STATE else None
    # Just "India" or "<State>, India": too coarse to show.
    if parts and len(parts) <= 2 and parts[-1].lower() == "india":
        return city_ok
    first = _clean(raw_name.split(",")[0])
    usable = first if first and first.lower() not in COUNTRY_OR_STATE else None
    if not usable:
        return city_ok
    return f"{usable}, {city}" if city and city.lower() != usable.lower() else usable


class HttpxUnsplashClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._user = settings.unsplash_user
        self._max_bytes = settings.max_upload_bytes
        self._sleep = sleep
        self._api = httpx.Client(
            base_url=API_BASE,
            headers={"Authorization": f"Client-ID {settings.unsplash_access_key}"},
            timeout=30,
            transport=transport,
        )
        # Image files come from another host; the API key must never be sent there.
        self._files = httpx.Client(timeout=120, transport=transport)
        self._made_call = False
        self._remaining: int | None = None

    @property
    def per_page(self) -> int:
        return PER_PAGE

    @property
    def rate_limit_remaining(self) -> int | None:
        return self._remaining

    def list_latest(self, page: int) -> list[UnsplashSummary]:
        params = {"page": page, "per_page": PER_PAGE, "order_by": "latest"}
        body = self._api_get(f"/users/{self._user}/photos", params).json()
        return [UnsplashSummary(id=item["id"]) for item in body]

    def get_photo(self, photo_id: str) -> UnsplashPhoto:
        api = self._api_get(f"/photos/{photo_id}").json()
        return UnsplashPhoto(
            id=api["id"],
            title=to_title(api),
            place=to_place(api.get("location")),
            html_url=api["links"]["html"],
            download_location=api["links"]["download_location"],
        )

    def download_original(self, photo: UnsplashPhoto) -> bytes:
        if not _is_https_host(photo.download_location, lambda h: h == "api.unsplash.com"):
            raise ValueError("unexpected download_location (not https on api.unsplash.com)")
        file_url = self._api_get(photo.download_location).json()["url"]
        if not _is_https_host(
            file_url, lambda h: h == "unsplash.com" or h.endswith(".unsplash.com")
        ):
            raise ValueError("unexpected file url (not https on an unsplash.com host)")
        return self._fetch_capped(file_url)

    def _fetch_capped(self, url: str) -> bytes:
        with self._files.stream("GET", url) as response:
            response.raise_for_status()
            if int(response.headers.get("content-length", 0)) > self._max_bytes:
                raise DownloadTooLarge(f"file is larger than {self._max_bytes} bytes")
            body = bytearray()
            for chunk in response.iter_bytes():
                body += chunk
                if len(body) > self._max_bytes:
                    raise DownloadTooLarge(f"file is larger than {self._max_bytes} bytes")
        return bytes(body)

    def _api_get(self, url: str, params: Mapping[str, Any] | None = None) -> httpx.Response:
        if self._made_call:
            self._sleep(SPACING_SECONDS)
        self._made_call = True
        response = self._api.get(url, params=params)
        remaining = response.headers.get("X-Ratelimit-Remaining")
        if remaining is not None:
            self._remaining = int(remaining)
        if response.status_code == 429 or (
            response.status_code == 403 and _says_rate_limited(response)
        ):
            raise RateLimited(f"HTTP {response.status_code} from Unsplash")
        response.raise_for_status()
        return response


def _says_rate_limited(response: httpx.Response) -> bool:
    """Unsplash answers 403 when the hourly limit is hit, but 403 also means a bad key."""
    return (
        response.headers.get("X-Ratelimit-Remaining") == "0"
        or "rate limit" in response.text.lower()
    )


def _is_https_host(url: str, host_ok: Callable[[str], bool]) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname is not None and host_ok(parsed.hostname)
