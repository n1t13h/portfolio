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
