import pytest

from app.integrations.storage import Bucket, Storage
from tests.fakes import FakeStorage


def test_fake_storage_roundtrip() -> None:
    storage: Storage = FakeStorage()
    storage.put_bytes(Bucket.PRIVATE, "a/b.jpg", b"data", "image/jpeg")
    assert storage.get_bytes(Bucket.PRIVATE, "a/b.jpg") == b"data"
    assert storage.exists(Bucket.PRIVATE, "a/b.jpg")
    storage.delete(Bucket.PRIVATE, "a/b.jpg")
    assert not storage.exists(Bucket.PRIVATE, "a/b.jpg")


def test_buckets_are_separate() -> None:
    storage = FakeStorage()
    storage.put_bytes(Bucket.PRIVATE, "k", b"x", "image/jpeg")
    with pytest.raises(KeyError):
        storage.get_bytes(Bucket.PUBLIC, "k")


def test_public_url_uses_cdn_base_url() -> None:
    assert FakeStorage("https://cdn.test").public_url("p/1.webp") == "https://cdn.test/p/1.webp"


def test_size_reports_object_length() -> None:
    storage = FakeStorage()
    storage.put_bytes(Bucket.PRIVATE, "k", b"12345", "image/jpeg")
    assert storage.size(Bucket.PRIVATE, "k") == 5


def test_list_keys_filters_by_prefix() -> None:
    storage = FakeStorage()
    for key in ("backups/a.db", "backups/b.db", "originals/x.jpg"):
        storage.put_bytes(Bucket.PRIVATE, key, b"x", "application/octet-stream")
    storage.put_bytes(Bucket.PUBLIC, "backups/other.db", b"x", "application/octet-stream")
    assert sorted(storage.list_keys(Bucket.PRIVATE, "backups/")) == ["backups/a.db", "backups/b.db"]
