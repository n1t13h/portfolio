import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from app.core.config import Settings
from app.integrations.storage import Bucket, R2Storage


def _storage(settings: Settings) -> R2Storage:
    return R2Storage(
        settings.model_copy(
            update={
                "r2_endpoint": "https://acct.r2.cloudflarestorage.com",
                "r2_access_key": "AK",
                "r2_secret_key": "SK",
                "r2_public_bucket": "pub",
                "r2_private_bucket": "priv",
            }
        )
    )


def test_presigned_put_targets_private_bucket_and_expires(settings: Settings) -> None:
    url = _storage(settings).presign_put(Bucket.PRIVATE, "o/1.jpg", "image/jpeg", 600)
    assert url.startswith("https://acct.r2.cloudflarestorage.com/priv/o/1.jpg?")
    assert "X-Amz-Expires=600" in url


def test_public_url_has_no_double_slash(settings: Settings) -> None:
    assert _storage(settings).public_url("p/1.webp") == "https://cdn.test/p/1.webp"


def test_links_for_the_browser_can_use_a_different_endpoint_than_the_server_does(
    settings: Settings,
) -> None:
    """Locally the API reaches the store as http://s3:9090 but the browser needs localhost."""
    storage = R2Storage(
        settings.model_copy(
            update={
                "r2_endpoint": "http://s3:9090",
                "r2_presign_endpoint": "http://localhost:9090",
                "r2_access_key": "AK",
                "r2_secret_key": "SK",
                "r2_public_bucket": "pub",
                "r2_private_bucket": "priv",
            }
        )
    )
    assert storage.presign_put(Bucket.PRIVATE, "o/1.jpg", "image/jpeg", 60).startswith(
        "http://localhost:9090/priv/o/1.jpg?"
    )
    assert storage.presign_get(Bucket.PRIVATE, "d/1.jpg", 60).startswith(
        "http://localhost:9090/priv/d/1.jpg?"
    )


# -- exists(): only a real 404 means "not there" ------------------------------------------


def _stubbed(settings: Settings) -> tuple[R2Storage, Stubber]:
    storage = R2Storage(
        settings.model_copy(
            update={
                "r2_endpoint": "https://acct.r2.cloudflarestorage.com",
                "r2_access_key": "AK",
                "r2_secret_key": "SK",
                "r2_public_bucket": "pub",
                "r2_private_bucket": "priv",
            }
        )
    )
    stubber = Stubber(storage._client)  # noqa: SLF001  (no network: the SDK client is stubbed)
    return storage, stubber


def test_exists_is_true_when_the_object_is_there(settings: Settings) -> None:
    storage, stubber = _stubbed(settings)
    stubber.add_response("head_object", {"ContentLength": 3})
    with stubber:
        assert storage.exists(Bucket.PRIVATE, "o/1.jpg") is True


@pytest.mark.parametrize("code", ["404", "NoSuchKey", "NotFound"])
def test_exists_is_false_only_for_a_genuine_not_found(settings: Settings, code: str) -> None:
    storage, stubber = _stubbed(settings)
    stubber.add_client_error("head_object", service_error_code=code, http_status_code=404)
    with stubber:
        assert storage.exists(Bucket.PRIVATE, "o/1.jpg") is False


@pytest.mark.parametrize(
    ("code", "status"),
    [("403", 403), ("AccessDenied", 403), ("InternalError", 500), ("SlowDown", 503)],
)
def test_exists_does_not_hide_auth_throttling_or_server_errors_as_missing(
    settings: Settings, code: str, status: int
) -> None:
    storage, stubber = _stubbed(settings)
    stubber.add_client_error("head_object", service_error_code=code, http_status_code=status)
    with stubber, pytest.raises(ClientError):
        storage.exists(Bucket.PRIVATE, "o/1.jpg")
