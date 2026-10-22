import httpx
import pytest

from app.core.config import Settings
from app.integrations.unsplash import (
    DownloadTooLarge,
    HttpxUnsplashClient,
    RateLimited,
    UnsplashNotConfigured,
    UnsplashPhoto,
    to_place,
    to_title,
)

PHOTO_JSON = {
    "id": "abc",
    "alt_description": "performer creating a fiery hoop",
    "description": None,
    "location": {"name": "Ram Ghat, Ujjain, Madhya Pradesh, India", "city": "Ujjain"},
    "links": {
        "html": "https://unsplash.com/photos/abc",
        "download_location": "https://api.unsplash.com/photos/abc/download?ixid=1",
    },
}


def make_client(
    settings: Settings, handler: httpx.MockTransport, sleeps: list[float] | None = None
) -> HttpxUnsplashClient:
    configured = settings.model_copy(update={"unsplash_access_key": "KEY", "unsplash_user": "me"})
    return HttpxUnsplashClient(
        configured, transport=handler, sleep=(sleeps if sleeps is not None else []).append
    )


def test_list_latest_sends_auth_and_parses_ids(settings: Settings) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200, json=[{"id": "a"}, {"id": "b"}], headers={"X-Ratelimit-Remaining": "41"}
        )

    client = make_client(settings, httpx.MockTransport(handler))
    assert [s.id for s in client.list_latest(2)] == ["a", "b"]
    [request] = seen
    assert request.url.path == "/users/me/photos"
    assert dict(request.url.params) == {"page": "2", "per_page": "30", "order_by": "latest"}
    assert request.headers["Authorization"] == "Client-ID KEY"
    assert client.rate_limit_remaining == 41


def test_http_429_is_a_rate_limit(settings: Settings) -> None:
    client = make_client(settings, httpx.MockTransport(lambda r: httpx.Response(429)))
    with pytest.raises(RateLimited):
        client.list_latest(1)


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(403, headers={"X-Ratelimit-Remaining": "0"}),
        httpx.Response(403, text="Rate Limit Exceeded"),
    ],
)
def test_a_403_that_says_rate_limit_is_a_rate_limit(
    settings: Settings, response: httpx.Response
) -> None:
    client = make_client(settings, httpx.MockTransport(lambda r: response))
    with pytest.raises(RateLimited):
        client.list_latest(1)


def test_a_403_for_a_bad_key_is_a_real_error_not_a_quiet_rate_limit(settings: Settings) -> None:
    body = "OAuth error: The access token is invalid"
    client = make_client(settings, httpx.MockTransport(lambda r: httpx.Response(403, text=body)))
    with pytest.raises(httpx.HTTPStatusError):
        client.list_latest(1)


def test_other_http_errors_propagate(settings: Settings) -> None:
    client = make_client(settings, httpx.MockTransport(lambda r: httpx.Response(500)))
    with pytest.raises(httpx.HTTPStatusError):
        client.list_latest(1)


def test_get_photo_maps_fields(settings: Settings) -> None:
    client = make_client(
        settings, httpx.MockTransport(lambda r: httpx.Response(200, json=PHOTO_JSON))
    )
    assert client.get_photo("abc") == UnsplashPhoto(
        id="abc",
        title="Performer creating a fiery hoop",
        place="Ram Ghat, Ujjain",
        html_url="https://unsplash.com/photos/abc",
        download_location="https://api.unsplash.com/photos/abc/download?ixid=1",
    )


def test_download_original_tracks_then_fetches_without_the_api_key(settings: Settings) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.host == "api.unsplash.com":
            return httpx.Response(200, json={"url": "https://images.unsplash.com/photo-abc?raw"})
        return httpx.Response(200, content=b"JPEGBYTES")

    client = make_client(settings, httpx.MockTransport(handler))
    photo = UnsplashPhoto(
        "abc", "t", None, "h", "https://api.unsplash.com/photos/abc/download?ixid=1"
    )

    assert client.download_original(photo) == b"JPEGBYTES"
    tracking, file_request = seen
    assert tracking.url.host == "api.unsplash.com"
    assert tracking.headers["Authorization"] == "Client-ID KEY"
    assert file_request.url.host == "images.unsplash.com"
    assert "Authorization" not in file_request.headers


def test_api_calls_are_spaced_out(settings: Settings) -> None:
    sleeps: list[float] = []
    client = make_client(
        settings, httpx.MockTransport(lambda r: httpx.Response(200, json=[])), sleeps
    )
    client.list_latest(1)
    client.list_latest(2)
    assert sleeps == [1.2]  # none before the first call, one pause before the second


@pytest.mark.parametrize(
    ("api", "expected"),
    [
        ({"alt_description": "a cat", "description": "d"}, "A cat"),
        ({"alt_description": None, "description": "  night market "}, "Night market"),
        ({"alt_description": " ", "description": None}, "Untitled"),
        ({}, "Untitled"),
    ],
)
def test_title_prefers_alt_text_then_description(api: dict[str, str | None], expected: str) -> None:
    assert to_title(api) == expected


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        (None, None),
        ({"name": "India"}, None),
        ({"name": "Madhya Pradesh, India", "city": "Indore"}, "Indore"),
        ({"name": "Madhya Pradesh, India"}, None),
        ({"name": "Omkareshwar", "city": None}, "Omkareshwar"),
        ({"name": "Indore", "city": "indore"}, "Indore"),
        ({"name": "Ram Ghat, Ujjain, Madhya Pradesh, India", "city": "Ujjain"}, "Ram Ghat, Ujjain"),
        ({"name": "India, India", "city": "India"}, None),
    ],
)
def test_place_matches_the_old_snapshot_script(
    location: dict[str, str | None] | None, expected: str | None
) -> None:
    assert to_place(location) == expected


def _tracking_then(
    file_url: str, file_response: httpx.Response | None = None
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.unsplash.com":
            return httpx.Response(200, json={"url": file_url})
        return file_response or httpx.Response(200, content=b"x")

    return httpx.MockTransport(handler)


GOOD_LOCATION = "https://api.unsplash.com/photos/abc/download?ixid=1"


@pytest.mark.parametrize(
    "location",
    [
        "http://api.unsplash.com/photos/abc/download",  # would send the key in clear text
        "https://evil.example/photos/abc/download",
        "https://api.unsplash.com.evil.example/x",
    ],
)
def test_download_location_must_be_https_on_the_unsplash_api(
    settings: Settings, location: str
) -> None:
    client = make_client(settings, _tracking_then("https://images.unsplash.com/x"))
    with pytest.raises(ValueError, match="download_location"):
        client.download_original(UnsplashPhoto("abc", "t", None, "h", location))


@pytest.mark.parametrize(
    "file_url",
    [
        "http://images.unsplash.com/photo-1",
        "https://evil.example/photo-1",
        "https://images.unsplash.com.evil.example/photo-1",
    ],
)
def test_file_url_must_be_https_on_an_unsplash_image_host(
    settings: Settings, file_url: str
) -> None:
    client = make_client(settings, _tracking_then(file_url))
    with pytest.raises(ValueError, match="file url"):
        client.download_original(UnsplashPhoto("abc", "t", None, "h", GOOD_LOCATION))


def test_download_is_capped_while_streaming(settings: Settings) -> None:
    small = settings.model_copy(update={"max_upload_bytes": 100})
    transport = _tracking_then(
        "https://images.unsplash.com/photo-1", httpx.Response(200, content=b"x" * 500)
    )
    client = HttpxUnsplashClient(
        small.model_copy(update={"unsplash_access_key": "K"}),
        transport=transport,
        sleep=lambda _: None,
    )
    with pytest.raises(DownloadTooLarge):
        client.download_original(UnsplashPhoto("abc", "t", None, "h", GOOD_LOCATION))


def test_a_missing_access_key_is_reported_plainly_without_calling_unsplash(
    settings: Settings,
) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=[])

    unconfigured = settings.model_copy(update={"unsplash_access_key": ""})
    client = HttpxUnsplashClient(unconfigured, transport=httpx.MockTransport(handler))

    with pytest.raises(UnsplashNotConfigured, match="UNSPLASH_ACCESS_KEY"):
        client.list_latest(1)
    assert calls == []
